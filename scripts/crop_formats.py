"""Cut 4:5 and 1:1 from the finished 9:16 master with ffmpeg instead of rendering them from the takes.

The picture is cropped with the window in brand.CROP_FROM_9X16 (pulled up from the centre: faces sit high,
captions at caption_y 0.646); the end card is not cropped but replaced by the format's own card from
edit/assets/<format>/endcard.png for the last endcard.dur seconds. The audio is copied, so loudness stays
exactly as mastered. Render the master with `assemble.py --crop-safe` so the notification banner lies inside
both windows. 16:9 is still rendered by assemble.py (the vertical picture cannot become a wide one).

usage: python3 crop_formats.py <project_dir> [--format 4:5,1:1] [--master final/<name>-9x16.mp4]
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from brand import CROP_FROM_9X16, get_format  # noqa: E402
from media import find_project, load_project, probe_duration, run  # noqa: E402


def crop(project, master, name, endcard_dur):
    layout = get_format(name)
    W, H = layout["size"]
    top = CROP_FROM_9X16[layout["name"]]["top"]
    if top < 0 or top + H > 1920:
        raise SystemExit(f"crop window {top}..{top + H} is outside the 1080x1920 master")
    card = project / "edit" / "assets" / layout["slug"] / "endcard.png"
    out = master.with_name(master.name.replace("-9x16", f"-{layout['slug']}"))
    total = probe_duration(master)
    inputs = ["-i", master]
    if endcard_dur and card.exists():
        start = max(0.0, total - endcard_dur)
        inputs += ["-loop", "1", "-i", card]
        graph = (f"[0:v]crop={W}:{H}:0:{top},setsar=1[pic];[1:v]scale={W}:{H},format=rgba[card];"
                 f"[pic][card]overlay=0:0:enable='gte(t,{start:.3f})':shortest=1[v]")
    else:
        graph = f"[0:v]crop={W}:{H}:0:{top},setsar=1[v]"
    run(inputs + ["-filter_complex", graph, "-map", "[v]", "-map", "0:a", "-t", f"{total:.3f}",
                  "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-profile:v", "high",
                  "-c:a", "copy", "-movflags", "+faststart", out])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--format", default="4:5,1:1", help="formats to cut from the 9:16 master (4:5, 1:1)")
    ap.add_argument("--master", help="the 9:16 master; default final/<name>-9x16.mp4")
    a = ap.parse_args()
    project = find_project(a.project)
    cfg = load_project(project)
    master = pathlib.Path(a.master) if a.master else project / "final" / f"{cfg.get('name', project.name)}-9x16.mp4"
    if not master.exists():
        raise SystemExit(f"no 9:16 master at {master}: run assemble.py --format 9:16 --crop-safe first")
    edl = json.loads((project / "edit" / "edl.json").read_text())
    endcard_dur = (edl.get("endcard") or {}).get("dur", 0)
    for name in a.format.split(","):
        if get_format(name)["name"] not in CROP_FROM_9X16:
            raise SystemExit(f"{name}: only {', '.join(CROP_FROM_9X16)} are cut from the 9:16 master")
        out = crop(project, master, name, endcard_dur)
        print(json.dumps({"format": get_format(name)["name"], "out": str(out), "duration": round(probe_duration(out), 3),
                          "from": str(master)}))


if __name__ == "__main__":
    main()
