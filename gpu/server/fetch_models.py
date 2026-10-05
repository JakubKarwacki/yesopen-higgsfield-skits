#!/usr/bin/env python3
"""Download the model files listed in server/manifest.json into the ComfyUI models folder.

Each file goes to <models>/<directory>/<name>. A file that is already there with the right size is skipped, so the
script can run again after an interruption, on a kept disk, or for a later stage. Downloads resume from a .part
file, run several at a time, and are checked against the manifest's size and, where Hugging Face publishes it,
SHA-256. The Hugging Face token (HF_TOKEN, needed only for gated repositories such as LTX-2.5) is sent to
huggingface.co only, never to the storage the download is redirected to, and never printed. Before the first byte
it checks that the disk has room for what is missing plus --keep-free-gb; if not, it downloads nothing.

Usage:
  python3 fetch_models.py --models /srv/yesopen/models --stage before_start
  python3 fetch_models.py --models /srv/yesopen/models --stage after_start --jobs 6
  python3 fetch_models.py --models /srv/yesopen/models --templates two-shot      # an option, on request
  python3 fetch_models.py --models /srv/yesopen/models --check                   # report only
Stages: before_start, after_start, manual, all. Variant B (MiniMax H3) only with --variant-b.
"""
import argparse
import fcntl
import hashlib
import json
import os
import shutil
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

MANIFEST = Path(__file__).resolve().parent / "manifest.json"
CHUNK = 8 << 20
print_lock = threading.Lock()


def say(message: str) -> None:
    with print_lock:
        print(message, flush=True)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


TOKEN_HOSTS = ("huggingface.co",)


def is_hugging_face(url: str) -> bool:
    host = urllib.parse.urlparse(url).hostname or ""
    return any(host == h or host.endswith("." + h) for h in TOKEN_HOSTS)


def open_url(url: str, token, headers: dict, timeout: float, hops: int = 5):
    """GET that follows redirects itself, so the token goes to huggingface.co only and never to the storage host."""
    for _ in range(hops):
        request_headers = {"User-Agent": "yesopen-gpu-stack", **headers}
        if token and is_hugging_face(url):
            request_headers["Authorization"] = f"Bearer {token}"
        try:
            return OPENER.open(urllib.request.Request(url, headers=request_headers), timeout=timeout)
        except urllib.error.HTTPError as error:
            if error.code in (301, 302, 303, 307, 308) and error.headers.get("Location"):
                url = urllib.parse.urljoin(url, error.headers["Location"])
                continue
            if error.code in (401, 403) and is_hugging_face(url):
                raise RuntimeError("access denied: gated repository; accept the licence on the model page and "
                                   "set HF_TOKEN") from None
            raise RuntimeError(f"HTTP {error.code} from {urllib.parse.urlparse(url).hostname}") from None
    raise RuntimeError("too many redirects")


def download(entry: dict, target: Path, token, timeout: float, retries: int) -> float:
    part = target.with_name(target.name + ".part")
    target.parent.mkdir(parents=True, exist_ok=True)
    size = entry["size"]
    for attempt in range(1, retries + 1):
        have = part.stat().st_size if part.exists() else 0
        if have > size:
            part.unlink()
            have = 0
        try:
            start, received = time.time(), 0
            with open_url(entry["url"], token, {"Range": f"bytes={have}-"} if have else {}, timeout) as response:
                if have and response.status != 206:
                    have = 0  # the server ignored the range: start over
                with open(part, "ab" if have else "wb") as handle:
                    while block := response.read(CHUNK):
                        handle.write(block)
                        received += len(block)
            if part.stat().st_size != size:
                raise RuntimeError(f"got {part.stat().st_size} of {size} bytes")
            part.replace(target)
            return received / max(time.time() - start, 1e-6)
        except (OSError, RuntimeError) as error:
            if "access denied" in str(error) or attempt == retries:
                raise
            say(f"  retry {attempt}/{retries - 1} {entry['name']}: {error}")
            time.sleep(min(30, 2 ** attempt))
    raise RuntimeError("unreachable")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while block := handle.read(CHUNK):
            digest.update(block)
    return digest.hexdigest()


def select(manifest: dict, stage: str, templates: list | None, variant_b: bool) -> list:
    order = ["before_start", "after_start", "manual"]
    chosen = []
    for entry in manifest["files"]:
        if entry["variant"] == "B" and not variant_b:
            continue
        if templates:
            if not set(templates) & set(entry["templates"]):
                continue
        elif stage != "all" and entry["stage"] != stage:
            continue
        chosen.append(entry)
    return sorted(chosen, key=lambda e: (order.index(e["stage"]), -e["size"]))


def bytes_to_fetch(entries: list, root: Path) -> int:
    """What the download still writes: every file not in place, less what its .part file already holds."""
    total = 0
    for entry in entries:
        target = root / entry["directory"] / entry["name"]
        if target.exists() and target.stat().st_size == entry["size"]:
            continue
        part = target.with_name(target.name + ".part")
        have = part.stat().st_size if part.exists() else 0
        total += entry["size"] - (have if have <= entry["size"] else 0)
    return total


def free_bytes(path: Path) -> int:
    while not path.exists():  # the models folder of a fresh disk does not exist yet
        path = path.parent
    return shutil.disk_usage(path).free


def fetch_one(entry: dict, root: Path, token, timeout, retries, verify) -> str:
    # One lock per file: a second run (bootstrap again while the background stage is still going) waits for the
    # file the first one is fetching and then finds it present, instead of writing into the same .part file.
    locks = root / ".fetch-locks"
    locks.mkdir(parents=True, exist_ok=True)
    with open(locks / f"{entry['directory'].replace('/', '__')}__{entry['name']}.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return fetch_unlocked(entry, root, token, timeout, retries, verify)


def fetch_unlocked(entry: dict, root: Path, token, timeout, retries, verify) -> str:
    target = root / entry["directory"] / entry["name"]
    if target.exists() and target.stat().st_size == entry["size"]:
        if verify and entry.get("sha256") and sha256(target) != entry["sha256"]:
            target.unlink()
        else:
            return "present"
    if entry.get("gated") and not token:
        raise RuntimeError("gated repository and no HF_TOKEN")
    say(f"  get  {entry['directory']}/{entry['name']} ({entry['size'] / 1e9:.2f} GB)")
    speed = download(entry, target, token, timeout, retries)
    if entry.get("sha256"):
        actual = sha256(target)
        if actual != entry["sha256"]:
            target.unlink()
            raise RuntimeError(f"SHA-256 mismatch ({actual[:12]} instead of {entry['sha256'][:12]}); file removed")
    return f"downloaded at {speed / 1e6:.0f} MB/s" + (", SHA-256 ok" if entry.get("sha256") else ", size ok")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--stage", default="before_start", choices=["before_start", "after_start", "manual", "all"])
    parser.add_argument("--templates", help="comma-separated template ids instead of a stage")
    parser.add_argument("--variant-b", action="store_true", help="also MiniMax H3 (only with MiniMax's consent)")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--verify", action="store_true", help="also hash files that are already present")
    parser.add_argument("--check", action="store_true", help="only report what is missing")
    parser.add_argument("--keep-free-gb", type=float, default=15,
                        help="disk space to leave for outputs and image builds (default 15)")
    args = parser.parse_args(argv)
    manifest = json.loads(args.manifest.read_text())
    entries = select(manifest, args.stage, args.templates.split(",") if args.templates else None, args.variant_b)
    token = os.environ.get("HF_TOKEN") or None
    total = sum(e["size"] for e in entries)
    say(f"{len(entries)} file{'' if len(entries) == 1 else 's'}, {total / 1e9:.1f} GB ({args.templates or args.stage}) -> {args.models}")
    need, free = bytes_to_fetch(entries, args.models), free_bytes(args.models)
    say(f"to download {need / 1e9:.1f} GB, free on the disk {free / 1e9:.1f} GB")
    if args.check:
        missing = [e for e in entries if not ((args.models / e["directory"] / e["name"]).exists()
                                              and (args.models / e["directory"] / e["name"]).stat().st_size == e["size"])]
        for e in missing:
            say(f"  missing {e['directory']}/{e['name']}")
        say(f"{len(entries) - len(missing)} of {len(entries)} present")
        return 1 if missing else 0
    if need and need + args.keep_free_gb * 1e9 > free:
        say(f"not enough disk space: {need / 1e9:.1f} GB to download and {args.keep_free_gb:g} GB to keep free, "
            f"but {free / 1e9:.1f} GB free. Nothing was downloaded: enlarge the disk or remove models you do not "
            f"use, then run again.")
        return 1
    failures = 0
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = {pool.submit(fetch_one, e, args.models, token, args.timeout, args.retries, args.verify): e
                   for e in entries}
        for future in as_completed(futures):
            entry = futures[future]
            try:
                say(f"  ok   {entry['directory']}/{entry['name']}: {future.result()}")
            except Exception as error:  # report every file, fail at the end
                failures += 1
                say(f"  FAIL {entry['directory']}/{entry['name']}: {error}")
    say(f"done: {len(entries) - failures} of {len(entries)} files in place")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
