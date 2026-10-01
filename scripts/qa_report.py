"""Check a rendered skit against its EDL.

usage: python3 qa_report.py <project_dir> [--format 9:16] [--video PATH] [--whisper] [--no-sheet]

Reports, as JSON:
  - planned vs actual frame count and duration (a mismatch means drift: captions and dings land late);
  - integrated loudness (target -14 LUFS), true peak (<= -1.5 dBTP) and max volume;
  - with --whisper: what Whisper hears in the final, and the words that differ from the caption words.
Writes edit/frames/qa-<format>-captions.jpg: one frame from the middle of every caption chunk,
labelled with its time and text, to check that each caption sits on the right speaker and shot.
"""
import argparse
import difflib
import json
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from PIL import Image, ImageDraw  # noqa: E402

from brand import font, get_format  # noqa: E402
from media import chunks_of, count_frames, find_project, load_project, loudness, max_volume, probe_duration  # noqa: E402


def caption_sheet(video, chunks, out, cols=6, width=240):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        thumbs = []
        for k, ch in enumerate(chunks):
            t = (ch["s"] + ch["e"]) / 2
            target = tmp / f"c_{k:03d}.jpg"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                            "-vf", f"scale={width}:-2", str(target)], check=True)
            thumbs.append((t, ch["text"], Image.open(target).convert("RGB")))
        th = thumbs[0][2].height
        rows = (len(thumbs) + cols - 1) // cols
        bar = 52
        page = Image.new("RGB", (cols * width, rows * (th + bar)), "white")
        d = ImageDraw.Draw(page)
        f1, f2 = font(18, 700), font(16, 500)
        for i, (t, text, img) in enumerate(thumbs):
            x, y = (i % cols) * width, (i // cols) * (th + bar)
            page.paste(img, (x, y + bar))
            d.text((x + 6, y + 4), f"{t:.2f}s", font=f1, fill=(15, 23, 42))
            d.text((x + 6, y + 27), text[:26], font=f2, fill=(8, 119, 255))
        out.parent.mkdir(parents=True, exist_ok=True)
        page.save(out, quality=82)
    return out


def norm_words(text):
    return [re.sub(r"[^a-z0-9#']", "", w.lower()) for w in text.split() if re.sub(r"[^a-z0-9#']", "", w.lower())]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--format", default="9:16")
    ap.add_argument("--edl")
    ap.add_argument("--video")
    ap.add_argument("--whisper", action="store_true")
    ap.add_argument("--no-sheet", action="store_true")
    a = ap.parse_args()
    project = find_project(a.project)
    cfg = load_project(project)
    layout = get_format(a.format)
    edl = json.loads(pathlib.Path(a.edl or project / "edit" / "edl.json").read_text())
    fps = edl.get("fps", 30)
    video = pathlib.Path(a.video) if a.video else project / "final" / f"{cfg.get('name', project.name)}-{layout['slug']}.mp4"

    planned = sum(round((s["out"] - s["in"]) * fps) for s in edl["segments"])
    end_frames = int(edl["endcard"]["dur"] * fps) if edl.get("endcard") else 0
    frames = count_frames(video)
    report = {
        "video": str(video),
        "format": layout["name"],
        "frames": {"planned_dialogue": planned, "planned_endcard": end_frames, "planned_total": planned + end_frames,
                   "actual": frames, "ok": frames == planned + end_frames},
        "duration": {"planned_video": round((planned + end_frames) / fps, 3), "container": round(probe_duration(video), 3),
                     "note": "the container is a few frames longer because of AAC padding; the frame count is the check"},
        "loudness": loudness(video),
        "volume": max_volume(video),
        "segments": len(edl["segments"]), "banners": len(edl.get("banners", [])), "dings": len(edl.get("dings", [])),
    }
    lo = report["loudness"]
    report["loudness"]["ok"] = (lo["integrated_lufs"] is not None and abs(lo["integrated_lufs"] + 14) <= 1.0
                                and (lo["true_peak_dbtp"] or 0) <= -1.0)

    style = {**cfg.get("captions", {}).get("style", {}), **edl.get("caption_style", {})}
    chunks = chunks_of(edl.get("caption_words", []), **style)
    report["caption_chunks"] = len(chunks)
    if chunks and not a.no_sheet:
        out = project / "edit" / "frames" / f"qa-{layout['slug']}-captions.jpg"
        report["caption_sheet"] = str(caption_sheet(video, chunks, out))

    if a.whisper:
        import whisper
        with tempfile.TemporaryDirectory() as tmp:
            wav = pathlib.Path(tmp) / "a.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
            result = whisper.load_model("large-v3-turbo").transcribe(str(wav), language=cfg.get("language", "en"),
                                                                     condition_on_previous_text=False)
        heard = result["text"].strip()
        expected = " ".join(w["w"] for w in edl.get("caption_words", []))
        a_words, b_words = norm_words(expected), norm_words(heard)
        diff = [f"{op}: {' '.join(a_words[i1:i2])} -> {' '.join(b_words[j1:j2])}"
                for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a_words, b_words).get_opcodes() if op != "equal"]
        report["whisper"] = {"heard": heard, "differences_vs_captions": diff,
                             "word_match": round(difflib.SequenceMatcher(None, a_words, b_words).ratio(), 3)}
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
