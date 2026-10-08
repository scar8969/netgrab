import argparse
import asyncio
from . import paths

def cmd_dl(args):
    """Download every URL listed in a local link file, one at a time.

    Both imports are local so `python cli.py --help` works without aiohttp or
    flask-sqlalchemy installed -- the help text is what a fresh clone runs first.
    """
    from .dl.worker import DownloadWorker

    with open(args.links, encoding="utf-8") as fh:
        urls = [line.strip() for line in fh if line.strip()]
    if not urls:
        print("[ctfile] %s has no URLs" % args.links)
        return 2
    worker = DownloadWorker(args.out, speed_limit=args.limit)
    failed = 0
    for url in urls:
        name = url.rstrip("/").split("/")[-1] or "download"
        print("[ctfile] %s" % name)
        try:
            asyncio.run(worker.download(url, name))
        except Exception as exc:  # noqa: BLE001 - one bad link must not stop the batch
            failed += 1
            print("[ctfile] failed %s: %s" % (name, exc))
    print("[ctfile] done: %d/%d files" % (len(urls) - failed, len(urls)))
    return 1 if failed else 0

def main():
    p = argparse.ArgumentParser(prog="ctfile-dl")
    sub = p.add_subparsers(dest="cmd")
    d = sub.add_parser("dl", help="download every URL in a link file")
    d.add_argument("links")
    d.add_argument("--out", default=str(paths.DATA_DIR))
    d.add_argument("--parallel", type=int, default=4)
    d.add_argument("--limit", type=int, default=0, help="bytes/second cap, 0 = unlimited")
    args = p.parse_args()
    if args.cmd == "dl":
        return cmd_dl(args)
    p.print_help()
    return 1
