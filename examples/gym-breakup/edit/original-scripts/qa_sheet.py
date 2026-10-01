"""Labelled frame sheet of an edited video. usage: python3 qa_sheet.py in.mp4 out.jpg [step] [start] [end]"""
import pathlib
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

from brand import font

src, out = sys.argv[1], sys.argv[2]
step = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
start = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
end = sys.argv[5] if len(sys.argv) > 5 else None
with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    args = ["ffmpeg", "-v", "error", "-y", "-ss", str(start)] + (["-to", end] if end else []) + ["-i", src,
            "-vf", f"fps=1/{step},scale=216:-2", str(tmp / "f_%03d.jpg")]
    subprocess.run(args, check=True)
    frames = sorted(tmp.glob("f_*.jpg"))
    fw, fh = Image.open(frames[0]).size
    cols = 8
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * fw, rows * (fh + 26)), "white")
    d = ImageDraw.Draw(sheet)
    f = font(20, 700)
    for i, p in enumerate(frames):
        x, y = (i % cols) * fw, (i // cols) * (fh + 26)
        sheet.paste(Image.open(p), (x, y + 26))
        d.text((x + 6, y + 2), f"{start + i * step:.1f}s", font=f, fill=(15, 23, 42))
    sheet.save(out, quality=80)
print(out)
