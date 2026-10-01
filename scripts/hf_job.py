"""Higgsfield platform API jobs for the skits. Never prints or logs credentials.

usage (through the hf-job launcher, which supplies the key):
  hf-job submit <label> <model> <args.json> <outdir>   submit, wait, download to <outdir>/<label>-<i>.<ext>
  hf-job resume <label> <request_id> <outdir>          wait for an earlier request and download it
  hf-job status <request_id>                           raw status JSON (free)
  hf-job upload <file>                                 upload a local image/video/audio, print its URL
  hf-job cost <model> <args.json>                      list-price estimate, no key needed, nothing sent

Every submit/finish is appended to <outdir>/jobs.jsonl (label, model, request_id, status,
args without the prompt, output URLs and files), so a lost terminal never loses a paid job:
read the request_id from jobs.jsonl and `resume` it.

Local media in args (image_url, end_image_url, image_urls, video_urls, audio_urls) may be
file paths relative to the args file; submit uploads them first and logs the URLs it got.
"""
import json
import pathlib
import sys
import time
import urllib.request

LOG = "jobs.jsonl"
MEDIA_KEYS = ("image_url", "end_image_url")
MEDIA_LIST_KEYS = ("image_urls", "video_urls", "audio_urls")

# List prices in USD, read from open.higgsfield.ai/pricing on 2026-10-01. Check the page
# before a big batch; the real charge also depends on the account's top-up tier.
PRICES = {
    "bytedance/seedance-2.5/image-to-video": ("second", 0.2068),
    "bytedance/seedance-2.5/text-to-video": ("second", 0.2068),
    "bytedance/seedance-2.5/reference-to-video": ("second", 0.248),
    "higgsfield-ai/soul/v2/standard": ("image", 0.0126),
}


def log(outdir: pathlib.Path, record: dict) -> None:
    record["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(outdir / LOG, "a") as fh:
        fh.write(json.dumps(record) + "\n")


def estimate(model: str, arguments: dict) -> dict:
    unit, price = PRICES.get(model, (None, None))
    if unit == "second":
        qty = arguments.get("duration", 5)
    elif unit == "image":
        qty = arguments.get("batch_size", 1)
    else:
        return {"model": model, "estimate_usd": None, "note": "no list price stored; check open.higgsfield.ai/pricing"}
    return {"model": model, "unit": unit, "quantity": qty, "unit_price_usd": price,
            "estimate_usd": round(qty * price, 4), "note": "list price; resolution and top-up tier can change it"}


def upload(path: pathlib.Path) -> str:
    import higgsfield_client
    return higgsfield_client.upload_file(path)


def upload_local_media(arguments: dict, base: pathlib.Path) -> dict:
    def fix(value):
        if isinstance(value, str) and not value.startswith(("http://", "https://", "data:")):
            path = (base / value).resolve()
            if not path.exists():
                raise SystemExit(f"media file not found: {path}")
            url = upload(path)
            print(f"uploaded {path.name} -> {url}", file=sys.stderr)
            return url
        return value

    out = dict(arguments)
    for key in MEDIA_KEYS:
        if key in out:
            out[key] = fix(out[key])
    for key in MEDIA_LIST_KEYS:
        if key in out:
            out[key] = [fix(v) for v in out[key]]
    return out


def finish(label: str, model: str, ctrl, outdir: pathlib.Path) -> int:
    from higgsfield_client import Completed
    last = None
    started = time.time()
    for status in ctrl.poll_request_status(delay=5):
        name = type(status).__name__
        if name != last:
            print(f"[{label}] {name} after {time.time() - started:.0f}s", file=sys.stderr, flush=True)
            last = name
    if last != Completed.__name__:
        detail = None
        try:
            detail = status_json(ctrl.request_id)
        except Exception:  # noqa: BLE001 - the status text is a nice-to-have
            pass
        reason = (detail or {}).get("error") or (detail or {}).get("message")
        log(outdir, {"label": label, "model": model, "request_id": ctrl.request_id, "status": last,
                     **({"reason": str(reason)[:500]} if reason else {})})
        print(f"[{label}] ended with {last}" + (f": {reason}" if reason else ""), file=sys.stderr)
        return 1
    result = ctrl.get()
    urls = [i["url"] for k in ("images", "videos", "audios") for i in (result.get(k) or []) if isinstance(i, dict) and i.get("url")]
    for key in ("video", "image", "audio"):
        item = result.get(key)
        if isinstance(item, dict) and item.get("url"):
            urls.append(item["url"])
    if not urls:
        log(outdir, {"label": label, "model": model, "request_id": ctrl.request_id, "status": "no_output", "keys": sorted(result)})
        print(f"[{label}] completed without output urls: {sorted(result)}", file=sys.stderr)
        return 1
    files = []
    for index, url in enumerate(urls):
        suffix = pathlib.Path(url.split("?")[0]).suffix or ".bin"
        target = outdir / f"{label}-{index}{suffix}"
        urllib.request.urlretrieve(url, target)
        files.append(str(target))
    log(outdir, {"label": label, "model": model, "request_id": ctrl.request_id, "status": "completed",
                 "seconds": round(time.time() - started), "urls": urls, "files": files})
    print(json.dumps({"label": label, "files": files, "urls": urls}))
    return 0


def status_json(request_id: str) -> dict:
    import higgsfield_client
    client = higgsfield_client.SyncClient()
    ctrl = client.get_request_controller(request_id)
    return client._transport.request("GET", ctrl.status_url).json()


def main() -> int:
    argv = sys.argv[1:]
    mode = argv[0] if argv else ""
    if mode == "cost" and len(argv) == 3:
        print(json.dumps(estimate(argv[1], json.loads(pathlib.Path(argv[2]).read_text())), indent=1))
        return 0
    if mode == "upload" and len(argv) == 2:
        path = pathlib.Path(argv[1]).resolve()
        print(json.dumps({"file": str(path), "url": upload(path)}))
        return 0
    if mode == "status" and len(argv) == 2:
        print(json.dumps(status_json(argv[1]), indent=1)[:3000])
        return 0
    if mode == "resume" and len(argv) == 4:
        import higgsfield_client
        label, request_id, outdir = argv[1], argv[2], pathlib.Path(argv[3])
        outdir.mkdir(parents=True, exist_ok=True)
        ctrl = higgsfield_client.SyncClient().get_request_controller(request_id)
        return finish(label, "resumed", ctrl, outdir)
    if mode == "submit" and len(argv) == 5:
        import higgsfield_client
        label, model, args_path, outdir = argv[1], argv[2], pathlib.Path(argv[3]), pathlib.Path(argv[4])
        outdir.mkdir(parents=True, exist_ok=True)
        arguments = upload_local_media(json.loads(args_path.read_text()), args_path.parent)
        cost = estimate(model, arguments)
        if cost.get("estimate_usd") is not None:
            print(f"[{label}] list-price estimate ${cost['estimate_usd']}", file=sys.stderr)
        try:
            ctrl = higgsfield_client.submit(model, arguments=arguments)
        except higgsfield_client.HiggsfieldClientError as exc:
            print(f"[{label}] submit failed: {type(exc).__name__}: {str(exc)[:300]}", file=sys.stderr)
            log(outdir, {"label": label, "model": model, "status": "submit_failed", "error": type(exc).__name__,
                         "args_file": str(args_path)})
            return 1
        log(outdir, {"label": label, "model": model, "request_id": ctrl.request_id, "status": "submitted",
                     "args_file": str(args_path), "args": {k: v for k, v in arguments.items() if k != "prompt"}})
        print(f"[{label}] submitted {ctrl.request_id}", file=sys.stderr, flush=True)
        return finish(label, model, ctrl, outdir)
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
