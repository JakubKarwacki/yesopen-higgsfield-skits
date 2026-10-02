#!/usr/bin/env python3
"""Download the selected official ComfyUI templates at the pinned commit.

Reads workflows/templates.json and writes, for each template:
  workflows/ui/<name>.json        the template exactly as Comfy-Org publishes it
  workflows/ui/index.json         title, description, size and minimum ComfyUI version of each one

Usage:
  python3 tools/fetch_templates.py            # download (skips files that already match)
  python3 tools/fetch_templates.py --check    # only compare local files with the pinned commit
"""
import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "workflows" / "templates.json"
UI_DIR = ROOT / "workflows" / "ui"


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def raw_url(repo: str, commit: str, path: str) -> str:
    return f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"


def index_entries(repo: str, commit: str, names: set) -> dict:
    """Merge the human index (title, size) with the MCP index (minimum ComfyUI version, inputs, outputs)."""
    entries = {}
    for category in json.loads(fetch(raw_url(repo, commit, "templates/index.json"))):
        for item in category.get("templates", []):
            if item["name"] in names:
                entries[item["name"]] = {
                    "category": category.get("title") or category.get("category"),
                    "title": item.get("title"),
                    "description": item.get("description"),
                    "models": item.get("models"),
                    "date": item.get("date"),
                    "download_bytes": item.get("size"),
                    "requires_custom_nodes": item.get("requiresCustomNodes", []),
                    "tutorial": item.get("tutorialUrl"),
                }
    for category in json.loads(fetch(raw_url(repo, commit, "templates/index.mcp.json"))):
        for item in category.get("templates", []):
            if item["name"] in entries:
                entries[item["name"]]["min_comfyui"] = item.get("minComfyUIVersion")
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="compare only, write nothing")
    args = parser.parse_args()

    config = json.loads(CONFIG.read_text())
    repo, commit = config["source"]["repo"], config["source"]["commit"]
    UI_DIR.mkdir(parents=True, exist_ok=True)
    mismatches = 0
    for template in config["templates"]:
        name = template["name"]
        remote = fetch(raw_url(repo, commit, f"templates/{name}.json"))
        target = UI_DIR / f"{name}.json"
        local = target.read_bytes() if target.exists() else None
        if local == remote:
            state = "same"
        elif args.check:
            state = "DIFFERENT" if local else "MISSING"
            mismatches += 1
        else:
            target.write_bytes(remote)
            state = "written"
        print(f"{template['id']:12} {name:42} {hashlib.sha256(remote).hexdigest()[:12]} {state}")

    if not args.check:
        names = {t["name"] for t in config["templates"]}
        entries = index_entries(repo, commit, names)
        missing = sorted(names - set(entries))
        if missing:
            print("not in the template index:", ", ".join(missing), file=sys.stderr)
        index = {"source": config["source"], "templates": entries}
        (UI_DIR / "index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
