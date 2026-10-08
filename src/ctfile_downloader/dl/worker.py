import aiohttp, asyncio, os

class DownloadWorker:
    def __init__(self, out_dir: str = "./downloads", speed_limit: int = 0):
        self.out_dir = out_dir
        self.speed_limit = speed_limit

    async def download(self, url, dest, resume=True):
        dest_path = os.path.join(self.out_dir, dest)
        part = dest_path + ".part"
        offset = os.path.getsize(part) if resume and os.path.exists(part) else 0
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url, headers=headers) as r:
                if r.status not in (200, 206):
                    raise RuntimeError(f"HTTP {r.status}")
                mode = "ab" if offset else "wb"
                with open(part, mode) as f:
                    async for chunk in r.content.iter_chunked(65536):
                        f.write(chunk)
                        if self.speed_limit:
                            await asyncio.sleep(len(chunk) / self.speed_limit)
        os.rename(part, dest_path)

    def progress(self, file):
        return file.downloaded / file.size if file.size else 0
