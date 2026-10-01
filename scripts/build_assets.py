"""Render a project's overlays for each output format, and its notification sound.

usage: python3 build_assets.py <project_dir> [--formats 9:16,4:5,1:1,16:9] [--sheet]

Reads project.json ("notifications", "notification_app", "endcard") and writes
  edit/assets/ding.wav
  edit/assets/<format>/<notification name>.png   e.g. notif-1.png
  edit/assets/<format>/endcard.png
  edit/assets/<format>/caption-sample.png
--sheet also writes edit/frames/assets-<format>.jpg, all overlays on one grey page for review.
"""
import argparse
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from PIL import Image  # noqa: E402

from brand import FORMATS, SKILL, caption, endcard, get_format, notification  # noqa: E402
from media import find_project, load_project  # noqa: E402

DING_SRC = SKILL / "assets" / "sfx" / "ding.wav"
# Two-tone "ding" (E6 then B6) with a soft decay; this is how assets/sfx/ding.wav was made.
DING_EXPR = ("aevalsrc='0.32*sin(2*PI*1318.5*t)*exp(-9*t)+0.28*sin(2*PI*1975.5*(t-0.11))*exp(-7*(t-0.11))"
             "*gte(t\\,0.11)':s=48000:d=0.9")


def make_ding(target: pathlib.Path):
    if DING_SRC.exists():
        shutil.copyfile(DING_SRC, target)
        return
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", DING_EXPR,
                    "-af", "lowpass=f=7000,afade=t=out:st=0.65:d=0.25", "-ac", "2", str(target)], check=True)


def build(project: pathlib.Path, formats, sheet=False):
    cfg = load_project(project)
    app = cfg.get("notification_app", "YesOpen")
    default_when = cfg.get("notification_when", "now")
    base = project / "edit" / "assets"
    base.mkdir(parents=True, exist_ok=True)
    make_ding(base / "ding.wav")
    written = []
    for name in formats:
        layout = get_format(name)
        W, H = layout["size"]
        out = base / layout["slug"]
        out.mkdir(parents=True, exist_ok=True)
        for key, note in cfg.get("notifications", {}).items():
            body, when = (note, default_when) if isinstance(note, str) else (note["body"], note.get("when", default_when))
            img = notification(body, when, app, layout["banner_scale"])
            img.save(out / f"{key}.png")
            written.append(out / f"{key}.png")
        card = cfg.get("endcard")
        if card:
            endcard(card["tagline"], card.get("url", "yesopens.com"), (W, H)).save(out / "endcard.png")
            written.append(out / "endcard.png")
        sample = cfg.get("captions", {}).get("sample", "It's not you.")
        caption(sample, width=W, size=layout["caption_size"]).save(out / "caption-sample.png")
        written.append(out / "caption-sample.png")
        if sheet:
            written.append(review_sheet(project, layout, out))
    return written


def review_sheet(project, layout, folder):
    """All overlays of one format on a grey page, at half size."""
    imgs = [Image.open(p).convert("RGBA") for p in sorted(folder.glob("*.png"))]
    scale = 0.5
    width = max(int(i.width * scale) for i in imgs) + 40
    height = sum(int(i.height * scale) + 20 for i in imgs) + 20
    page = Image.new("RGBA", (width, height), (150, 150, 150, 255))
    y = 20
    for img in imgs:
        small = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
        page.alpha_composite(small, (20, y))
        y += small.height + 20
    target = project / "edit" / "frames" / f"assets-{layout['slug']}.jpg"
    target.parent.mkdir(parents=True, exist_ok=True)
    page.convert("RGB").save(target, quality=85)
    return target


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--formats", default=",".join(FORMATS))
    ap.add_argument("--sheet", action="store_true")
    a = ap.parse_args()
    project = find_project(a.project)
    for p in build(project, a.formats.split(","), a.sheet):
        print(p)


if __name__ == "__main__":
    main()
