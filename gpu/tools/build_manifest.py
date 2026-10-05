#!/usr/bin/env python3
"""Build server/manifest.json: every model file the selected templates need, pinned and sized.

For each template it takes the models the official template declares (node properties.models), applies our URL
overrides and adds the extra files our custom nodes load (workflows/templates.json -> extra_models). It checks that
every model file the converted API prompt references is covered, then asks the Hugging Face API for each repository's
current commit, licence and gating, and for each file's size and SHA-256. URLs are pinned to that commit, so a later
upstream change cannot silently swap a model under the same name.

A file is fetched at the earliest stage of any template using it:
  before_start  needed before the first job (character stills, voices, lip sync)
  after_start   downloaded in the background while the first jobs run
  manual        only on request (options and variant B)

Usage:
  python3 tools/build_manifest.py            # write server/manifest.json
  python3 tools/build_manifest.py --check    # fail if the manifest on disk is out of date

Gated repositories (LTX-2.5) list their files without a token; a token is not needed to build the manifest.
"""
import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "workflows" / "templates.json"
UI_DIR = ROOT / "workflows" / "ui"
API_DIR = ROOT / "workflows" / "api"
MANIFEST = ROOT / "server" / "manifest.json"
STAGES = ["before_start", "after_start", "manual"]
MODEL_FILE = re.compile(r"\.(safetensors|pt|pth|ckpt|bin|gguf|onnx)$")
HF_URL = re.compile(r"^https://huggingface\.co/(?P<repo>[^/]+/[^/]+)/resolve/(?P<rev>[^/]+)/(?P<path>.+)$")


def api_get(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "yesopen-gpu-stack"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())


def declared_models(template: dict) -> list:
    subgraphs = (template.get("definitions") or {}).get("subgraphs") or []
    nodes = list(template["nodes"]) + [n for sg in subgraphs for n in sg["nodes"]]
    found = {}
    for node in nodes:
        for model in (node.get("properties") or {}).get("models") or []:
            found[(model["directory"], model["name"])] = model["url"]
    return [{"directory": d, "name": n, "url": u} for (d, n), u in sorted(found.items())]


def referenced_files(prompt: dict) -> set:
    return {value for node in prompt.values() for value in node["inputs"].values()
            if isinstance(value, str) and MODEL_FILE.search(value)}


def override(model: dict, overrides: dict) -> dict:
    """Our source for a declared file. A URL that ends in another file name swaps the file for that one (another
    precision of the same model, say); patches.json then points the loader at the new name."""
    url = overrides.get(model["url"])
    if not url:
        return model
    return {**model, "url": url, "name": urllib.parse.unquote(url.rpartition("/")[2]), "replaces_url": model["url"]}


def collect(config: dict) -> dict:
    """Map (directory, name) -> file entry with the templates that use it."""
    files = {}
    overrides = config.get("url_overrides", {})
    for template in config["templates"]:
        ui = json.loads((UI_DIR / f"{template['name']}.json").read_text())
        models = [override(model, overrides) for model in declared_models(ui)]
        extra = config.get("extra_models", {}).get(template["id"])
        if extra:
            models += [{"directory": extra["directory"], "name": name,
                        "url": f"https://huggingface.co/{extra['repo']}/resolve/main/{name}"} for name in extra["files"]]
        prompt = json.loads((API_DIR / f"{template['id']}.json").read_text())
        missing = referenced_files(prompt) - {m["name"] for m in models}
        if missing:
            raise SystemExit(f"{template['id']}: prompt uses model files no template declares: {sorted(missing)}")
        for model in models:
            key = (model["directory"], model["name"])
            entry = files.setdefault(key, {"directory": model["directory"], "name": model["name"],
                                           "source_url": model["url"],
                                           "templates": [], "stage": "manual", "variant": "B"})
            if "replaces_url" in model:
                entry["replaces_url"] = model["replaces_url"]
            entry["templates"].append(template["id"])
            if STAGES.index(template["load"]) < STAGES.index(entry["stage"]):
                entry["stage"] = template["load"]
            if template["variant"] == "A":
                entry["variant"] = "A"
    return files


def repo_info(repo: str) -> dict:
    data = api_get(f"https://huggingface.co/api/models/{repo}?expand[]=sha&expand[]=gated&expand[]=cardData")
    card = data.get("cardData") or {}
    license_id = card.get("license")
    if license_id == "other":
        license_id = card.get("license_name") or "other"
    return {"commit": data["sha"], "gated": bool(data.get("gated")), "license": license_id,
            "license_link": card.get("license_link")}


def path_info(repo: str, commit: str, paths: list) -> dict:
    """Size and SHA-256 of files in one repository at one commit. The tree listing also works for gated repositories
    (the hash is masked there, the size is not), unlike paths-info."""
    result = {}
    for folder in sorted({p.rpartition("/")[0] for p in paths}):
        suffix = f"/{urllib.parse.quote(folder)}" if folder else ""
        for item in api_get(f"https://huggingface.co/api/models/{repo}/tree/{commit}{suffix}"):
            oid = (item.get("lfs") or {}).get("oid") or ""
            result[item["path"]] = {"size": item.get("size"),
                                    "sha256": oid if re.fullmatch(r"[0-9a-f]{64}", oid) else None}
    return result


def resolve(files: dict) -> list:
    by_repo = {}
    for entry in files.values():
        match = HF_URL.match(entry["source_url"])
        if not match:
            raise SystemExit(f"not a Hugging Face URL: {entry['source_url']}")
        entry["repo"], entry["path"] = match["repo"], urllib.parse.unquote(match["path"])
        by_repo.setdefault(entry["repo"], []).append(entry)
    with ThreadPoolExecutor(max_workers=8) as pool:
        infos = dict(zip(by_repo, pool.map(repo_info, by_repo)))
        details = dict(zip(by_repo, pool.map(
            lambda repo: path_info(repo, infos[repo]["commit"], [e["path"] for e in by_repo[repo]]), by_repo)))
    out = []
    for repo, entries in sorted(by_repo.items()):
        info = infos[repo]
        for entry in entries:
            detail = details[repo].get(entry["path"])
            if not detail:
                raise SystemExit(f"{repo}: {entry['path']} does not exist at {info['commit']}")
            out.append({
                "name": entry["name"], "directory": entry["directory"],
                "url": f"https://huggingface.co/{repo}/resolve/{info['commit']}/{urllib.parse.quote(entry['path'])}",
                "size": detail["size"], "sha256": detail["sha256"],
                "stage": entry["stage"], "variant": entry["variant"], "templates": sorted(entry["templates"]),
                "repo": repo, "license": info["license"], "license_link": info["license_link"],
                "gated": info["gated"], **({"replaces_url": entry["replaces_url"]} if "replaces_url" in entry else {}),
            })
    return sorted(out, key=lambda f: (STAGES.index(f["stage"]), f["directory"], f["name"]))


def totals(files: list) -> dict:
    result = {}
    for stage in STAGES:
        chosen = [f for f in files if f["stage"] == stage]
        result[stage] = {"files": len(chosen), "gb": round(sum(f["size"] for f in chosen) / 1e9, 1)}
    variant_a = [f for f in files if f["variant"] == "A" and f["stage"] != "manual"]
    result["variant_A_automatic"] = {"files": len(variant_a), "gb": round(sum(f["size"] for f in variant_a) / 1e9, 1)}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text())
    files = resolve(collect(config))
    manifest = {
        "_doc": "Generated by tools/build_manifest.py from workflows/templates.json. Do not edit by hand.",
        "comfyui": config["comfyui"], "templates_commit": config["source"]["commit"],
        "custom_nodes": config["custom_nodes"], "totals": totals(files), "files": files,
    }
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        current = MANIFEST.read_text() if MANIFEST.exists() else ""
        if current != text:
            print("server/manifest.json is out of date (or upstream moved); run tools/build_manifest.py", file=sys.stderr)
            return 1
        print("manifest up to date")
        return 0
    MANIFEST.parent.mkdir(exist_ok=True)
    MANIFEST.write_text(text)
    for stage, total in manifest["totals"].items():
        print(f"{stage:20} {total['files']:3} files {total['gb']:7.1f} GB")
    gated = sorted({f["repo"] for f in files if f["gated"]})
    print("gated (needs HF token + Agree on the model page):", ", ".join(gated) or "none")
    print("licences:", ", ".join(sorted({f"{f['repo']}={f['license']}" for f in files})))
    return 0


if __name__ == "__main__":
    sys.exit(main())
