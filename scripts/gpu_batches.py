#!/usr/bin/env python3
"""Write the GPU engine's batch files from the skit's lines.json, so every job is written down and repeatable.

usage (PROJECT is the skit folder, default the current one):
  python3 gpu_batches.py stills [PROJECT]                  stills/batch.json: 4 Z-Image candidates per character
                                                           that has a "look" and no picked still yet
  python3 gpu_batches.py voice [PROJECT]                   voice/batch.json: two tts takes of every line
  python3 gpu_batches.py reseed ID [PROJECT] [--n 4] [--first-seed N] [--text "..."] [--exaggeration 0.5]
                                                           voice/batch-<ID>.json: new tts takes of one line, also
                                                           with another spelling ("2 AM") or performance
  python3 gpu_batches.py takes [PROJECT] [--only l16] [--out takes/batch-l16.json]
                                                           takes/batch.json: one talk take per fitted line
  python3 gpu_batches.py estimate [PROJECT]                the jobs and the GPU minutes, before a session

Run every file with `gpu.py batch <file>`. lines.json (start from templates/lines.json):

  language     the tts language: "English (en)", "Polish (pl)", "German (de)", ...
  characters   per character: voice (a 5-15 s sample), still (the picked image), who / where / him (the take
               prompt: "The bearded gym owner", "in his small gym", "him" or "her"), look (the Z-Image prompt)
  take         template with {who} {where} {him} {action}, tail (seconds of acting after the line), seed (base)
  lines        id, who, text, exaggeration, acting; optional: action (what we see in the take, default acting),
               still (another picture of the character), tail, seed, prompt (the whole take prompt),
               silence_before (seconds the character acts before speaking), seconds (the whole take)

Seeds are fixed, so a batch written twice is the same batch: tts takes 100 + 2i and 101 + 2i for line i
(counted from 0), takes `take.seed` + line number, stills 1000 + 10 x character number + candidate.
gpu.py batch skips a job whose name is already in the folder's jobs.jsonl, so a line with a new text or a new
fit needs new names (reseed) or a separate batch run with --force; this script warns when that would happen.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

TAKE_TEMPLATE = (
    "Single continuous handheld vertical smartphone shot, no cuts, camera at eye level facing {him}, slight "
    "natural handheld movement, the framing stays the same with no zoom and no push-in. {who} stays in place "
    "{where} and talks directly into the camera lens as if to the person filming {him}, {action}. Natural, "
    "understated comedic acting. No other people, no text on screen.")
DEFAULT_TAKE = {"template": TAKE_TEMPLATE, "tail": 0.6, "seed": 500}

# GPU seconds per job on one H200, from ComfyUI's own history (2 October 2026): (first job, loading the model;
# every later job). The B200 is not measured yet.
GPU_SECONDS = {"still": (9.6, 2.8), "still-edit": (15.7, 5.0), "tts": (10.8, 4.0), "talk": (35.4, 13.4),
               "music": (17.8, 17.8)}


from languages import project_language, language_label, language_code, require_speech


def load(project: Path) -> dict:
    path = project / "lines.json"
    if not path.exists():
        raise SystemExit(f"no {path}: copy $SK/templates/lines.json there and fill it")
    doc = json.loads(path.read_text())
    cfg_path = project / 'project.json'
    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    doc['language'] = language_label(project_language(cfg, doc))
    ids = [line["id"] for line in doc.get("lines", [])]
    if len(ids) != len(set(ids)):
        raise SystemExit("lines.json: every line needs its own id")
    for line in doc.get("lines", []):
        if line.get("who") not in doc.get("characters", {}):
            raise SystemExit(f"lines.json: {line['id']} is spoken by '{line.get('who')}', who is not in characters")
    return doc


def rel(project: Path, folder: str, path: str) -> str:
    """lines.json paths are relative to the project; a batch file's paths are relative to its own folder."""
    return os.path.relpath(project / path, project / folder)


def write(project: Path, name: str, jobs: list) -> Path:
    target = project / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"jobs": jobs}, indent=1, ensure_ascii=False) + "\n")
    warn_done(target.parent, jobs)
    print(f"{target.relative_to(project)}: {len(jobs)} jobs")
    return target


def warn_done(folder: Path, jobs: list) -> None:
    """Name the jobs that gpu.py batch would skip although their values changed since they were made."""
    log = folder / "jobs.jsonl"
    if not log.exists():
        return
    made = {}
    for row in log.read_text().splitlines():
        if row.strip():
            item = json.loads(row)
            made[item["name"]] = item.get("values", {})
    def differs(key, old, new):
        if isinstance(new, str) and new.startswith(("../", "./", "/")):
            return False  # files: the log holds absolute paths
        if key == "seconds":
            # the client rounds a talk take up to whole groups of 8 frames at 24 fps, less than 1/3 s more
            return not (float(old) - 1 / 3 - 1e-6 < float(new) <= float(old) + 1e-6)
        return old != new

    for job in jobs:
        before = made.get(job["name"])
        if before is None:
            continue
        changed = [key for key, value in job["set"].items() if key in before and differs(key, before[key], value)]
        if not changed:
            continue
        if job["template"] == "tts":
            fix = "make new takes with gpu_batches.py reseed"
        else:
            fix = (f"move the old {job['name']} files to {folder.name}/old/, write a batch of that job alone "
                   f"(--only {job['name']} --out {folder.name}/batch-{job['name']}.json) and run it with --force")
        print(f"  {job['name']} was made before with another {', '.join(changed)}, so gpu.py batch will skip it: "
              f"{fix}.", file=sys.stderr)


def cmd_stills(project: Path, doc: dict, args) -> None:
    jobs = []
    for c, (name, char) in enumerate(doc["characters"].items()):
        if char.get("still") and (project / char["still"]).exists():
            continue
        if not char.get("look"):
            print(f"{name}: no still and no look; write the Z-Image prompt into characters.{name}.look")
            continue
        for k in range(args.n):
            jobs.append({"name": f"still-{name}-{k}", "template": "still",
                         "set": {"prompt": char["look"], "seed": 1000 + 10 * c + k}})
    if jobs:
        write(project, "stills/batch.json", jobs)


def tts_job(project: Path, doc: dict, line: dict, seed: int, text=None, exaggeration=None) -> dict:
    char = doc["characters"][line["who"]]
    lang = project_language({}, doc)
    if 'language' in line and language_code(line['language']) != lang:
        raise ValueError('Mixed-language lines require separate project revisions')
    require_speech(text or line['text'], lang)
    return {"name": f"{line['id']}-s{seed}", "template": "tts",
            "set": {"text": text or line["text"], "language": language_label(lang),
                    "voice": rel(project, "voice", char["voice"]),
                    "exaggeration": exaggeration if exaggeration is not None else line.get("exaggeration", 0.5),
                    "cfg_weight": line.get("cfg_weight", doc.get("voice", {}).get("cfg_weight", 0.5)),
                    "seed": seed}}


def cmd_voice(project: Path, doc: dict, args) -> None:
    jobs = []
    for i, line in enumerate(doc["lines"]):
        jobs += [tts_job(project, doc, line, 100 + 2 * i), tts_job(project, doc, line, 101 + 2 * i)]
    write(project, "voice/batch.json", jobs)


def used_seeds(project: Path) -> set:
    seeds = set()
    for batch in (project / "voice").glob("*.json"):
        for job in json.loads(batch.read_text()).get("jobs", []):
            seeds.add(job["set"].get("seed"))
    return seeds


def cmd_reseed(project: Path, doc: dict, args) -> None:
    line = next((l for l in doc["lines"] if l["id"] == args.id), None)
    if line is None:
        raise SystemExit(f"no line {args.id} in lines.json")
    first = args.first_seed if args.first_seed is not None else max(used_seeds(project) | {199}) + 1
    jobs = [tts_job(project, doc, line, first + k, args.text, args.exaggeration) for k in range(args.n)]
    name = f"voice/batch-{args.id}.json"
    if (project / name).exists():
        name = f"voice/batch-{args.id}-s{first}.json"  # keep the earlier reseed's file: it documents those takes
    write(project, name, jobs)
    print(f"then: gpu.py batch {name}; fit_lines.py lines.json voice lines --only {args.id}")


def line_seconds(project: Path, line_id: str) -> float:
    fit = project / "lines" / "fit.json"
    report = json.loads(fit.read_text()) if fit.exists() else {}
    entry = report.get(line_id)
    if not entry or not entry.get("ok", True) or not (project / "lines" / f"{line_id}.wav").exists():
        raise SystemExit(f"{line_id} has no fitted line: run fit_lines.py lines.json voice lines first")
    return float(entry["seconds"])


def duration(path: Path) -> float:
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "default=nw=1:nk=1", str(path)]))


def pad_line(project: Path, line_id: str, before: float) -> str:
    """lines/<id>-pad.wav: `before` seconds of silence, then the fitted line (the character acts, then speaks)."""
    src, dst = project / "lines" / f"{line_id}.wav", project / "lines" / f"{line_id}-pad.wav"
    meta = dst.with_suffix('.source.json')
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    expected = {'source_sha256': digest, 'silence_before': before}
    if (dst.exists() and meta.exists() and json.loads(meta.read_text()) == expected
            and abs(duration(dst) - before - duration(src)) < 0.01):
        return f"lines/{line_id}-pad.wav"
    meta.unlink(missing_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-t", f"{before}", "-i",
                    "anullsrc=r=48000:cl=mono", "-i", str(src), "-filter_complex",
                    "[1:a]aformat=sample_rates=48000:channel_layouts=mono[l];[0:a][l]concat=n=2:v=0:a=1",
                    str(dst)], check=True)
    meta.write_text(json.dumps(expected))
    return f"lines/{line_id}-pad.wav"


def cmd_takes(project: Path, doc: dict, args) -> None:
    take = {**DEFAULT_TAKE, **doc.get("take", {})}
    only = set(args.only.split(",")) if args.only else None
    jobs = []
    for i, line in enumerate(doc["lines"]):
        if only and line["id"] not in only:
            continue
        char = doc["characters"][line["who"]]
        seconds = line_seconds(project, line["id"])
        audio = f"lines/{line['id']}.wav"
        if line.get("silence_before"):
            audio = pad_line(project, line["id"], line["silence_before"])
            seconds += line["silence_before"]
        tail = line.get("tail", take["tail"])
        prompt = line.get("prompt") or take["template"].format(
            who=char["who"], where=char["where"], him=char.get("him", "him"),
            action=line.get("action", line.get("acting", "")))
        jobs.append({"name": line["id"], "template": "talk",
                     "set": {"image": rel(project, "takes", line.get("still") or char["still"]),
                             "audio": rel(project, "takes", audio), "prompt": prompt,
                             "seconds": line.get("seconds", round(seconds + tail, 2)),
                             "seed": line.get("seed", take["seed"] + i + 1)}})
    for job in jobs:
        line = next(item for item in doc["lines"] if item["id"] == job["name"])
        for option in ("enhance_prompt", "cfg_first", "negative_prompt"):
            if option in line or option in take:
                job["set"][option] = line.get(option, take.get(option))
    if not jobs:
        raise SystemExit("no lines matched --only")
    write(project, args.out or "takes/batch.json", jobs)


def cmd_estimate(project: Path, doc: dict, args) -> None:
    n_lines = len(doc["lines"])
    new_chars = [c for c in doc["characters"].values()
                 if not (c.get("still") and (project / c["still"]).exists())]
    count = {"still": 4 * len(new_chars), "tts": 2 * n_lines, "talk": n_lines,
             "music": 1 if json.loads((project / "project.json").read_text()).get("music") else 0}
    total = 0.0
    for template, n in count.items():
        if n:
            first, later = GPU_SECONDS[template]
            seconds = first + later * (n - 1)
            total += seconds
            print(f"{template:6} {n:3} jobs  {seconds / 60:5.1f} min")
    print(f"GPU time about {total / 60:.0f} min on an H200, plus reseeds and retakes (the pilot: 10.4 min for 21 "
          f"lines). The machine bills from start to delete: the pilot's whole session took about 1 h.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("stills")
    p.add_argument("--n", type=int, default=4)
    sub.add_parser("voice")
    p = sub.add_parser("reseed")
    p.add_argument("id")
    p.add_argument("--n", type=int, default=4)
    p.add_argument("--first-seed", type=int)
    p.add_argument("--text", help="the line spelled differently for the voice only (fit_lines still checks the script)")
    p.add_argument("--exaggeration", type=float)
    p = sub.add_parser("takes")
    p.add_argument("--only", help="comma-separated line ids")
    p.add_argument("--out", help="batch file, relative to the project (default takes/batch.json)")
    sub.add_parser("estimate")
    for p in sub.choices.values():
        p.add_argument("project", nargs="?", default=".")
    args = ap.parse_args()
    project = Path(args.project).resolve()
    doc = load(project)
    {"stills": cmd_stills, "voice": cmd_voice, "reseed": cmd_reseed, "takes": cmd_takes,
     "estimate": cmd_estimate}[args.command](project, doc, args)


if __name__ == "__main__":
    main()
