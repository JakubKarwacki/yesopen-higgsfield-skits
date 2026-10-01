"""Labelled frame sheet of any video, for checking cuts, zooms, captions and banners at a glance.

usage: python3 qa_sheet.py <video> <out.jpg> [--step 1.0] [--start 0] [--end SECONDS] [--cols 8] [--width 216]
"""
import argparse
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from PIL import Image, ImageDraw  # noqa: E402

from brand import font  # noqa: E402


def sheet(src, out, step=1.0, start=0.0, end=None, cols=8, width=216):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        args = ["ffmpeg", "-v", "error", "-y", "-ss", str(start)] + (["-to", str(end)] if end else []) + [
            "-i", str(src), "-vf", f"fps=1/{step},scale={width}:-2", str(tmp / "f_%04d.jpg")]
        subprocess.run(args, check=True)
        frames = sorted(tmp.glob("f_*.jpg"))
        fw, fh = Image.open(frames[0]).size
        rows = (len(frames) + cols - 1) // cols
        page = Image.new("RGB", (cols * fw, rows * (fh + 26)), "white")
        d = ImageDraw.Draw(page)
        f = font(20, 700)
        for i, p in enumerate(frames):
            x, y = (i % cols) * fw, (i // cols) * (fh + 26)
            page.paste(Image.open(p), (x, y + 26))
            d.text((x + 6, y + 2), f"{start + i * step:.1f}s", font=f, fill=(15, 23, 42))
        pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
        page.save(out, quality=80)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--step", type=float, default=1.0)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float)
    ap.add_argument("--cols", type=int, default=8)
    ap.add_argument("--width", type=int, default=216)
    a = ap.parse_args()
    print(sheet(a.video, a.out, a.step, a.start, a.end, a.cols, a.width))


if __name__ == "__main__":
    main()
