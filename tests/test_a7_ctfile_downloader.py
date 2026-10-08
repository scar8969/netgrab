"""A7 ctfile-downloader — tests.  Run: pytest test_a7_ctfile_downloader.py

The suite runs hermetically: the download tests drive DownloadWorker with an
in-process fake aiohttp session, and pass the destination path *explicitly* so
`os.makedirs` never touches a directory pytest did not create.  The host sandbox
denies both `HTTPServer(("127.0.0.1", 0))` and creation of `tmp_path/...` beneath
a 0o700 parent, which is why the original ranged-server variant errored at setup.
The ranged-HTTP half of the contract is still covered: FakeResponse answers 206 +
Content-Range for a ranged request, and the worker must append rather than
truncate, so a resume that ignored the offset fails on byte equality.
"""
import os
import sys

import pytest

DATA = b"x" * 100000  # 100KB

class FakeResponse:
    """Just enough of an aiohttp response: status + chunked body."""

    def __init__(self, body, status=200, headers=None):
        self.status = status
        self.headers = headers or {}
        self._body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    @property
    def content(self):
        """aiohttp exposes the stream as `r.content`; this object IS the stream."""
        return self

    async def iter_chunked(self, n):
        for i in range(0, len(self._body), n):
            yield self._body[i:i + n]

class FakeSession:
    """Range-aware stand-in for aiohttp.ClientSession.

    `seen` records every request so a test can assert the worker actually asked
    for a byte range instead of silently re-fetching the whole file.
    """

    def __init__(self, body=DATA):
        self.body = body
        self.seen = []

    def get(self, url, headers=None):
        headers = headers or {}
        self.seen.append((url, dict(headers)))
        rng = headers.get("Range", "")
        if rng:
            start = int(rng.split("=")[1].split("-")[0])
            return FakeResponse(self.body[start:], 206,
                                {"Content-Range":
                                 "bytes %d-%d/%d" % (start, len(self.body) - 1, len(self.body))})
        return FakeResponse(self.body, 200)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

def _worker(tmp_path, session, **kw):
    """Build a worker whose out_dir IS tmp_path, so only pytest creates it."""
    from ctfile_downloader.dl.worker import DownloadWorker
    return DownloadWorker(out_dir=str(tmp_path), **kw), session

def _download(tmp_path, session, dest):
    import asyncio
    """Run one download against `session`, without a socket."""
    import aiohttp

    real = aiohttp.ClientSession
    try:
        aiohttp.ClientSession = lambda *a, **k: session
        w, _ = _worker(tmp_path, session)
        asyncio.run(w.download("http://example.invalid/file", dest))
    finally:
        aiohttp.ClientSession = real

def test_extract_links():
    from ctfile_downloader.dl.extract import extract_links
    # no network — just verify the regex path exists
    assert callable(extract_links)

def test_resume_offset(tmp_path):
    from ctfile_downloader.dl.resume import resume_offset
    p = tmp_path / "f.part"
    p.write_bytes(b"abc")
    assert resume_offset(str(p)) == 3
    assert resume_offset(str(tmp_path / "missing.part")) == 0

def test_download_full(tmp_path):
    s = FakeSession()
    _download(tmp_path, s, "out.bin")
    assert (tmp_path / "out.bin").read_bytes() == DATA
    assert s.seen[0][1] == {}          # no Range when starting from zero
    assert not (tmp_path / "out.bin.part").exists()  # .part was renamed

def test_download_resume(tmp_path):
    (tmp_path / "out2.bin.part").write_bytes(DATA[:50000])
    s = FakeSession()
    _download(tmp_path, s, "out2.bin")
    assert (tmp_path / "out2.bin").read_bytes() == DATA
    assert s.seen[0][1] == {"Range": "bytes=50000-"}   # it resumed, not restarted

def test_download_rejects_error_status(tmp_path):
    """A 4xx must raise and leave no renamed final file."""
    import asyncio
    import aiohttp
    from ctfile_downloader.dl.worker import DownloadWorker

    class Bad(FakeSession):
        def get(self, url, headers=None):
            return FakeResponse(b"", 404)

    real = aiohttp.ClientSession
    try:
        aiohttp.ClientSession = lambda *a, **k: Bad()
        w = DownloadWorker(out_dir=str(tmp_path))
        with pytest.raises(RuntimeError):
            asyncio.run(w.download("http://example.invalid/file", "bad.bin"))
    finally:
        aiohttp.ClientSession = real
    assert not (tmp_path / "bad.bin").exists()
