"""Start a new skit project folder from the templates.

usage: python3 new_project.py <slug> [--date YYYY-MM-DD] [--root DIR] [--title "..."]

Root: --root, else $YESOPEN_SHORTS_ROOT, else <localesto>/output/yesopen-shorts, else ./yesopen-shorts.
Creates <root>/<date>-<slug>/ with project.json, script.md, reference/analysis.md,
edit/cuts.json, args/ (still and take templates) and empty stills/, takes/, final/ folders,
and a .gitignore that keeps reference/private/ (someone else's frames and transcript) out of git.
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

TEMPLATES = SKILL / "templates"


def default_root():
    env = os.environ.get("YESOPEN_SHORTS_ROOT")
    if env:
        return pathlib.Path(env).expanduser()
    root = localesto_root()
    return root / "output" / "yesopen-shorts" if root else pathlib.Path.cwd() / "yesopen-shorts"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--root")
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    root = pathlib.Path(a.root).expanduser() if a.root else default_root()
    project = root / f"{a.date}-{a.slug}"
    if project.exists():
        raise SystemExit(f"{project} already exists")
    for sub in ("reference/private", "args", "stills", "takes", "edit/frames", "final"):
        (project / sub).mkdir(parents=True)
    cfg = json.loads((TEMPLATES / "project.json").read_text())
    cfg["slug"], cfg["date"] = a.slug, a.date
    cfg["name"] = a.slug
    if a.title:
        cfg["title"] = a.title
    (project / "project.json").write_text(json.dumps(cfg, indent=1, ensure_ascii=False) + "\n")
    shutil.copyfile(TEMPLATES / "script.md", project / "script.md")
    shutil.copyfile(TEMPLATES / "analysis.md", project / "reference" / "analysis.md")
    shutil.copyfile(TEMPLATES / "cuts.json", project / "edit" / "cuts.json")
    for name in ("still.json", "take.json"):
        shutil.copyfile(TEMPLATES / "args" / name, project / "args" / name)
    (project / ".gitignore").write_text("reference/private/\nedit/work/\n__pycache__/\n.DS_Store\n")
    print(project)


if __name__ == "__main__":
    main()
