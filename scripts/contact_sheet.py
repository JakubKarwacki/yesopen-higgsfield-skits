"""Contact sheets from images: reference frames, Soul candidates, cast options.

usage: python3 contact_sheet.py <image|folder> [...] -o out.jpg [--cols 5] [--per-sheet 10]
                                [--width 360] [--label name|index|none] [--pattern "*.jpg"]

With --per-sheet the images are split over out-01.jpg, out-02.jpg, ...
Labels: "name" prints the file name (f_00450.jpg -> 4.50s when the name encodes centiseconds,
as capture_reference.mjs writes them), "index" prints #1, #2, ...
"""
import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from PIL import Image, ImageDraw  # noqa: E402

from brand import font  # noqa: E402

EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def label_for(path: pathlib.Path, index: int, mode: str) -> str:
    if mode == "index":
        return f"#{index + 1}"
    if mode == "none":
        return ""
    m = re.fullmatch(r"f_(\d{5})", path.stem)
    return f"{int(m.group(1)) / 100:.2f}s" if m else path.stem


def render(paths, out, cols, width, mode, offset=0):
    thumbs = []
    for p in paths:
        img = Image.open(p).convert("RGB")
        thumbs.append(img.resize((width, round(img.height * width / img.width)), Image.LANCZOS))
    th = max(t.height for t in thumbs)
    rows = (len(thumbs) + cols - 1) // cols
    bar = 34 if mode != "none" else 0
    page = Image.new("RGB", (cols * width + (cols + 1) * 8, rows * (th + bar + 8) + 8), "white")
    d = ImageDraw.Draw(page)
    f = font(22, 700)
    for i, (p, t) in enumerate(zip(paths, thumbs)):
        x = 8 + (i % cols) * (width + 8)
        y = 8 + (i // cols) * (th + bar + 8)
        page.paste(t, (x, y + bar))
        if bar:
            text = label_for(p, offset + i, mode)
            while text and f.getlength(text) > width - 8:
                text = text[:-2] + "…"  # keep labels inside their own cell
            d.text((x + 4, y + 4), text, font=f, fill=(15, 23, 42))
    out.parent.mkdir(parents=True, exist_ok=True)
    page.save(out, quality=85)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--per-sheet", type=int)
    ap.add_argument("--width", type=int, default=360)
    ap.add_argument("--label", choices=["name", "index", "none"], default="name")
    ap.add_argument("--pattern", default="*")
    a = ap.parse_args()
    paths = []
    for item in a.inputs:
        p = pathlib.Path(item)
        if p.is_dir():
            paths += sorted(x for x in p.glob(a.pattern) if x.suffix.lower() in EXTS)
        elif p.suffix.lower() in EXTS:
            paths.append(p)
    if not paths:
        raise SystemExit("no images found")
    out = pathlib.Path(a.out)
    if not a.per_sheet or len(paths) <= a.per_sheet:
        print(render(paths, out, a.cols, a.width, a.label))
        return
    for n, i in enumerate(range(0, len(paths), a.per_sheet), 1):
        print(render(paths[i:i + a.per_sheet], out.with_name(f"{out.stem}-{n:02d}{out.suffix}"), a.cols, a.width, a.label, i))


if __name__ == "__main__":
    main()
