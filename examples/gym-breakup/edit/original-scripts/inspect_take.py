"""Word timestamps and a labelled frame sheet for one generated take.

usage: python3 inspect_take.py takes/<take>.mp4 [step_seconds]
writes takes/<take>.words.json and edit/frames/<take>_sheet.jpg
"""
import json
import pathlib
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

from brand import font

src = pathlib.Path(sys.argv[1]).resolve()
step = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
here = pathlib.Path(__file__).parent

with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    wav = tmp / "a.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
    import whisper
    model = whisper.load_model("large-v3-turbo")
    result = model.transcribe(str(wav), language="en", word_timestamps=True, condition_on_previous_text=False)
    words = [{"w": w["word"].strip(), "s": round(w["start"], 2), "e": round(w["end"], 2)}
             for seg in result["segments"] for w in seg["words"]]
    src.with_suffix(".words.json").write_text(json.dumps(words, indent=1))

    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", f"fps=1/{step},scale=180:-2",
                    str(tmp / "f_%03d.jpg")], check=True)
    frames = sorted(tmp.glob("f_*.jpg"))
    fw, fh = Image.open(frames[0]).size
    cols = 10
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * fw, rows * (fh + 26)), "white")
    d = ImageDraw.Draw(sheet)
    f = font(20, 700)
    for i, p in enumerate(frames):
        x, y = (i % cols) * fw, (i // cols) * (fh + 26)
        sheet.paste(Image.open(p), (x, y + 26))
        d.text((x + 6, y + 2), f"{i * step:.1f}s", font=f, fill=(15, 23, 42))
    out = here / "frames" / f"{src.stem}_sheet.jpg"
    sheet.save(out, quality=82)

# group words into lines on pauses longer than 0.6 s
lines, cur = [], []
for w in words:
    if cur and w["s"] - cur[-1]["e"] > 0.6:
        lines.append(cur)
        cur = []
    cur.append(w)
if cur:
    lines.append(cur)
for ln in lines:
    print(f"{ln[0]['s']:6.2f}-{ln[-1]['e']:6.2f}  " + " ".join(x["w"] for x in ln))
print("sheet:", out)
