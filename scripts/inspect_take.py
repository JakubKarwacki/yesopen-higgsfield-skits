"""Transcribe one generated take with word timestamps and draw a labelled frame sheet.

usage: python3 inspect_take.py <take.mp4> [--step 0.5] [--lang en] [--model large-v3-turbo]
                               [--thr -26] [--frames-dir DIR] [--no-sheet] [--no-whisper]

Writes <take>.words.json next to the take (make_edl.py reads it) and, unless --no-sheet,
<project>/edit/frames/<take>_sheet.jpg (10 frames per row, `step` seconds apart).
Prints every spoken line (split on pauses > 0.6 s) with Whisper's times and the times
refined against the audio envelope, plus the take's room tone, so you can see clipped
starts and pick the speech threshold before cutting.
"""
import argparse
import json
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from PIL import Image, ImageDraw  # noqa: E402

from brand import font  # noqa: E402
from media import HOP, envelope, refine  # noqa: E402


def transcribe(src, lang, model_name):
    import whisper
    with tempfile.TemporaryDirectory() as tmp:
        wav = pathlib.Path(tmp) / "a.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
        model = whisper.load_model(model_name)
        result = model.transcribe(str(wav), language=lang, word_timestamps=True, condition_on_previous_text=False)
    return [{"w": w["word"].strip(), "s": round(w["start"], 2), "e": round(w["end"], 2)}
            for seg in result["segments"] for w in seg["words"]]


def frame_sheet(src, step, out, cols=10, width=180):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", f"fps=1/{step},scale={width}:-2",
                        str(tmp / "f_%03d.jpg")], check=True)
        frames = sorted(tmp.glob("f_*.jpg"))
        fw, fh = Image.open(frames[0]).size
        rows = (len(frames) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * fw, rows * (fh + 26)), "white")
        d = ImageDraw.Draw(sheet)
        f = font(20, 700)
        for i, p in enumerate(frames):
            x, y = (i % cols) * fw, (i // cols) * (fh + 26)
            sheet.paste(Image.open(p), (x, y + 26))
            d.text((x + 6, y + 2), f"{i * step:.1f}s", font=f, fill=(15, 23, 42))
        out.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(out, quality=82)
    return out


def room_tone(env, words, margin=0.15):
    """Median level (dB) of the take where nobody speaks: outside every word +- margin."""
    import numpy as np
    mask = np.ones(len(env), bool)
    for w in words:
        mask[max(0, int((w["s"] - margin) / HOP)): int((w["e"] + margin) / HOP) + 1] = False
    quiet = env[mask]
    return float(np.percentile(quiet, 50)) if len(quiet) else None, float(np.percentile(quiet, 90)) if len(quiet) else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("take")
    ap.add_argument("--step", type=float, default=0.5)
    ap.add_argument("--lang", default="en")
    ap.add_argument("--model", default="large-v3-turbo")
    ap.add_argument("--thr", type=float, default=-26.0, help="speech threshold in dB for the refined times")
    ap.add_argument("--frames-dir")
    ap.add_argument("--no-sheet", action="store_true")
    ap.add_argument("--no-whisper", action="store_true", help="reuse the existing .words.json")
    a = ap.parse_args()

    src = pathlib.Path(a.take).resolve()
    words_path = src.with_suffix(".words.json")
    if a.no_whisper and words_path.exists():
        words = json.loads(words_path.read_text())
    else:
        words = transcribe(src, a.lang, a.model)
        words_path.write_text(json.dumps(words, indent=1))

    sheet = None
    if not a.no_sheet:
        frames_dir = pathlib.Path(a.frames_dir) if a.frames_dir else (
            src.parent.parent / "edit" / "frames" if src.parent.name == "takes" else src.parent)
        sheet = frame_sheet(src, a.step, frames_dir / f"{src.stem}_sheet.jpg")

    env = envelope(src)
    median, p90 = room_tone(env, words)
    lines, cur = [], []
    for w in words:
        if cur and w["s"] - cur[-1]["e"] > 0.6:
            lines.append(cur)
            cur = []
        cur.append(w)
    if cur:
        lines.append(cur)
    print(f"{src.name}: {len(words)} words, {len(lines)} lines")
    if median is not None:
        warn = "  <- threshold too close to room tone, raise --thr" if a.thr - p90 < 3 else ""
        print(f"room tone: median {median:.1f} dB, p90 {p90:.1f} dB; speech threshold {a.thr:.1f} dB{warn}")
    print("whisper          refined          line")
    for ln in lines:
        s, e = ln[0]["s"], ln[-1]["e"]
        rs, re_ = refine(env, s, e, a.thr)
        flag = "  <- start moved" if s - rs > 0.15 else ""
        flag += "  <- end moved" if re_ - e > 0.15 else ""
        print(f"{s:6.2f}-{e:6.2f}    {rs:6.2f}-{re_:6.2f}    " + " ".join(x["w"] for x in ln) + flag)
    print("words:", words_path)
    if sheet:
        print("sheet:", sheet)


if __name__ == "__main__":
    main()
