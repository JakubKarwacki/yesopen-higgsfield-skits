#!/usr/bin/env python3
"""Let a local ComfyUI (same version, same custom nodes, no GPU, no models) validate every workflow.

ComfyUI checks a job when it is queued: every node type exists, every input is present and of the right type,
every option is allowed, every model and input file exists. This script makes that check possible without the
weights: it creates empty placeholder files with the manifest's names in the local models folders, uploads small
test media, sends each template through client/gpu.py exactly as a real job (parameters, uploads, LTX length
rule) with --validate-only, and removes the placeholders again. Execution is stopped right after acceptance.

Usage:
  python3 tools/validate_local.py --comfy-dir /path/to/ComfyUI [--url http://127.0.0.1:8188] [--only talk,tts]
"""
import argparse
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "client"))
import gpu  # noqa: E402

SAMPLE_VALUES = {
    "prompt": "A woman in a gym office looks at her phone and sighs.",
    "text": "Dzień dobry, tu YesOpen. Odpisaliśmy już na wszystkie opinie.",
    "dialog": "SPEAKER A: Who is going to reply to the reviews?\nSPEAKER B: Not me.",
    "tags": "instrumental, light comedic underscore, pizzicato strings, soft percussion",
    "seconds": {"int": "5", "float": "3.2"},
    "bpm": "100",
}


def make_media(folder: Path) -> dict:
    image, audio, video = folder / "still.png", folder / "line.wav", folder / "take.mp4"
    image.write_bytes(gpu.png_rgba(64, 112, lambda x, y: 255))
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=220:duration=3", "-ar", "48000",
                    str(audio)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=128x224:rate=24:duration=1",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video)], check=True)
    return {"image": image, "audio": audio, "video": video}


def sample_values(spec: dict, media: dict) -> dict:
    given = {}
    for name, param in spec["params"].items():
        if not param.get("required"):
            continue
        kind = param["type"]
        if kind in ("image", "audio", "video"):
            given[name] = str(media[kind])
        elif name == "seconds":
            given[name] = SAMPLE_VALUES["seconds"][kind]
        else:
            given[name] = SAMPLE_VALUES.get(name, SAMPLE_VALUES["prompt"])
    return given


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--comfy-dir", required=True, type=Path)
    parser.add_argument("--url", default="http://127.0.0.1:8188")
    parser.add_argument("--only")
    args = parser.parse_args()
    manifest = json.loads(gpu.MANIFEST.read_text())
    templates = args.only.split(",") if args.only else sorted(p.stem for p in gpu.PARAMS_DIR.glob("*.json"))
    created = []
    for entry in manifest["files"]:
        path = args.comfy_dir / "models" / entry["directory"] / entry["name"]
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
            created.append(path)
    comfy = gpu.Comfy(args.url)
    object_info = comfy.get("/object_info")
    failures = 0
    try:
        with tempfile.TemporaryDirectory(prefix="validate-") as tmp:
            media = make_media(Path(tmp))
            for template in templates:
                _, spec = gpu.load_template(template)
                try:
                    job = gpu.prepare_job(template, sample_values(spec, media), random.Random(1), Path(tmp), object_info)
                    gpu.run_job(comfy, job, Path(tmp) / "out", template, timeout=60, validate_only=True)
                    print(f"ok   {template:12} {len(job['prompt'])} nodes accepted by ComfyUI")
                except SystemExit as error:
                    failures += 1
                    print(f"FAIL {template:12} {error}")
    finally:
        for path in created:
            path.unlink(missing_ok=True)
    print(f"{len(templates) - failures} of {len(templates)} workflows accepted; "
          f"{len(created)} placeholder files created and removed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
