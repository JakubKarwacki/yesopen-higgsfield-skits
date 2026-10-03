"""Start a new skit project folder from the templates.

usage: python3 new_project.py <slug> [--engine gpu|higgsfield] [--date YYYY-MM-DD] [--root DIR] [--title "..."]

Root: --root, else $YESOPEN_SHORTS_ROOT, else <localesto>/output/yesopen-shorts, else ./yesopen-shorts.
Creates <root>/<date>-<slug>/ with project.json, script.md, reference/analysis.md, edit/cuts.json and empty
stills/, takes/, final/ folders, and a .gitignore that keeps reference/private/ (someone else's frames and
transcript) out of git. The GPU engine (default) also gets lines.json and voices/, voice/, lines/; the Higgsfield
engine gets args/ with the still and take request templates. Prints the project folder.
"""
import argparse
import datetime
import json
import os
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from brand import SKILL, localesto_root  # noqa: E402

from languages import language_code, language_label

TEMPLATES = SKILL / "templates"

# templates/project.json is written for the GPU engine; a Higgsfield project names its stills, voices and
# takes the way hf-job writes them
HIGGSFIELD = {
    "cast": {
        "char1": {"still": "stills/still-char1-0.png", "url": "", "args": "args/still-char1.json",
                  "voice": "calm, warm American male voice"},
        "char2": {"still": "stills/still-char2-0.png", "url": "", "args": "args/still-char2.json",
                  "voice": "crisp, confident American female voice"},
    },
    "takes": {"c1a": "takes/take-char1-1-720p-0.mp4", "c2a": "takes/take-char2-1-720p-0.mp4"},
}


def default_root():
    env = os.environ.get("YESOPEN_SHORTS_ROOT")
    if env:
        return pathlib.Path(env).expanduser()
    root = localesto_root()
    return root / "output" / "yesopen-shorts" if root else pathlib.Path.cwd() / "yesopen-shorts"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--engine", choices=("gpu", "higgsfield"), default="gpu")
    ap.add_argument("--language", type=language_code, default="en")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--root")
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    root = pathlib.Path(a.root).expanduser() if a.root else default_root()
    project = root / f"{a.date}-{a.slug}"
    if project.exists():
        raise SystemExit(f"{project} already exists")
    folders = ["reference/private", "stills", "takes", "edit/frames", "final"]
    folders += ["voices", "voice", "lines"] if a.engine == "gpu" else ["args"]
    for sub in folders:
        (project / sub).mkdir(parents=True)
    cfg = json.loads((TEMPLATES / "project.json").read_text())
    cfg["slug"], cfg["date"] = a.slug, a.date
    cfg["name"] = a.slug
    cfg["engine"] = a.engine
    cfg["language"] = a.language
    if a.engine == "higgsfield":
        cfg.update(HIGGSFIELD)
    if a.title:
        cfg["title"] = a.title
    (project / "project.json").write_text(json.dumps(cfg, indent=1, ensure_ascii=False) + "\n")
    shutil.copyfile(TEMPLATES / "script.md", project / "script.md")
    shutil.copyfile(TEMPLATES / "voice-validation.md", project / "voice-validation.md")
    shutil.copyfile(TEMPLATES / "analysis.md", project / "reference" / "analysis.md")
    shutil.copyfile(TEMPLATES / "cuts.json", project / "edit" / "cuts.json")
    if a.engine == "gpu":
        lines = json.loads((TEMPLATES / 'lines.json').read_text())
        lines['language'] = language_label(a.language)
        (project / 'lines.json').write_text(json.dumps(lines, ensure_ascii=False, indent=1) + '\n')
    else:
        for name in ("still.json", "take.json"):
            shutil.copyfile(TEMPLATES / "args" / name, project / "args" / name)
    (project / ".gitignore").write_text("reference/private/\nedit/work/\n__pycache__/\n.DS_Store\n")
    print(project)


if __name__ == "__main__":
    main()
