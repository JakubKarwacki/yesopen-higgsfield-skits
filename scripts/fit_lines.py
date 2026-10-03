"""Check every TTS take against its script line, cut off anything the model added, pick the best seed.

usage: python3 fit_lines.py LINES_JSON VOICE_DIR OUT_DIR [--only l01,l02] [--lead 0.3] [--tail 0.12]
                            [--max-pause 0.75] [--model large-v3-turbo]

LINES_JSON: {"lines": [{"id": "l01", "text": "Hey... I think we should break up."}, ...]}
VOICE_DIR:  the gpu engine's tts outputs, <id>-s<seed>.audio.flac (two seeds per line is the default batch).

Chatterbox often keeps talking after the line, with invented words up to its token limit, and sometimes hums
or mumbles inside a pause. For each take this script transcribes with word timestamps and passes it when the
script's words appear at its start (letters compared without spaces, so "an app" = "a nap") and nothing
untranscribed sounds between the words. The best take is cut just after its last script word (extended to where
the sound really ends), pauses longer than --max-pause between words are shortened, and the line is written as
OUT_DIR/<id>.wav, 48 kHz mono, with --lead seconds of silence in front so the face starts still. A take whose
last word carries the script's "?" or "!" wins a tie. OUT_DIR/fit.json records every choice; lines without a
passing take print FAILED: run their tts job again with other seeds.
"""
import argparse
import difflib
import json
import re
import subprocess
from pathlib import Path

import numpy as np

from languages import (normalize, project_language, language_code, require_speech,
                       verify_whisper_model)


def letters(text: str, language='en', number_aliases=None) -> str:
    return normalize(text, language, number_aliases)


def load(path: Path, rate=48000) -> np.ndarray:
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(rate),
                                   "-f", "f32le", "-"])
    return np.frombuffer(raw, np.float32)


def sound_end(audio: np.ndarray, t: float, rate=48000, thr_db=-38.0, reach=0.45) -> float:
    """Where the sound after time t really fades out (10 ms hops), at most `reach` seconds later."""
    hop = rate // 100
    i = int(t * rate)
    end = t
    quiet = 0
    for k in range(int(reach * 100)):
        a, b = i + k * hop, i + (k + 1) * hop
        if b > len(audio):
            break
        level = 20 * np.log10(np.sqrt(np.mean(audio[a:b] ** 2)) + 1e-9)
        if level > thr_db:
            end, quiet = b / rate, 0
        else:
            quiet += 1
            if quiet >= 8:
                break
    return end


def shorten_pauses(audio: np.ndarray, spans: list, max_pause: float, rate=48000, thr_db=-38.0):
    """Shorten silences between consecutive words to max_pause: TTS sometimes stops for seconds at '...'."""
    hop = rate // 100
    n = len(audio) // hop
    level = 20 * np.log10(np.sqrt((audio[: n * hop].reshape(n, hop) ** 2).mean(axis=1)) + 1e-9)
    cuts = []
    for (_, end), (start, _) in zip(spans, spans[1:]):
        lo, hi = max(int((end - 0.15) * 100), 0), min(int((start + 0.15) * 100), n)
        run_start, best = None, (0, 0)
        for i in range(lo, hi + 1):
            quiet = i < hi and level[i] < thr_db
            if quiet and run_start is None:
                run_start = i
            elif not quiet and run_start is not None:
                if i - run_start > best[1] - best[0]:
                    best = (run_start, i)
                run_start = None
        length = (best[1] - best[0]) / 100
        if length > max_pause:
            middle = (best[0] + best[1]) / 2 / 100
            cuts.append((middle - (length - max_pause) / 2, middle + (length - max_pause) / 2))
    if not cuts:
        return audio, 0.0
    pieces, last = [], 0
    for a, b in cuts:
        pieces.append(audio[last: int(a * rate)])
        last = int(b * rate)
    pieces.append(audio[last:])
    return np.concatenate(pieces), sum(b - a for a, b in cuts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lines")
    ap.add_argument("voice_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--lead", type=float, default=0.3)
    ap.add_argument("--tail", type=float, default=0.12)
    ap.add_argument("--model", default="large-v3-turbo")
    ap.add_argument("--lang", help="explicit ASR language; must match declared project language")
    ap.add_argument("--only", help="comma-separated line ids")
    ap.add_argument("--max-pause", type=float, default=0.75,
                    help="silences between the line's words longer than this are shortened to it")
    a = ap.parse_args()
    doc = json.loads(Path(a.lines).read_text())
    cfg_path = Path(a.lines).parent / 'project.json'
    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    lang = project_language(cfg, doc)
    if a.lang:
        explicit = language_code(a.lang)
        if ('language' in doc or 'language' in cfg) and explicit != lang:
            raise ValueError('--lang conflicts with project language')
        lang = explicit
    verify_whisper_model(a.model, lang)
    lines = doc['lines']
    for line in lines:
        require_speech(line['text'], lang)
    import speech
    model = speech.load_model(a.model)
    if a.only:
        lines = [l for l in lines if l["id"] in a.only.split(",")]
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "fit.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    aliases = cfg.get('speech', {}).get('number_aliases', {})
    for line in lines:
        want = letters(line["text"], lang, aliases)
        best = None
        for take in sorted(Path(a.voice_dir).glob(f"{line['id']}-s*.audio.flac")):
            result = model.transcribe(str(take), language=lang, word_timestamps=True,
                                      condition_on_previous_text=False, fp16=False)
            words = [w for s in result["segments"] for w in s["words"]]
            got, k_best, ratio_best = "", 0, 0.0
            for k, w in enumerate(words, 1):
                got += letters(w["word"], lang, aliases)
                ratio = difflib.SequenceMatcher(None, want, got, autojunk=False).ratio()
                if ratio > ratio_best:
                    k_best, ratio_best = k, ratio
            if not k_best:
                continue
            last_end = float(words[k_best - 1]["end"])
            extra = words[k_best:]
            gap = float(extra[0]["start"] - last_end) if extra else None
            audio = load(take)
            cut = float(min(sound_end(audio, last_end) + a.tail, len(audio) / 48000))
            if gap is not None:
                cut = min(cut, float(extra[0]["start"]) - 0.05)
            # sound between the words that Whisper did not write down (a hum, a laugh, mumbling)
            hop = 480
            n = len(audio) // hop
            level = 20 * np.log10(np.sqrt((audio[: n * hop].reshape(n, hop) ** 2).mean(axis=1)) + 1e-9)
            mumble = 0.0
            for w0, w1 in zip(words[: k_best - 1], words[1:k_best]):
                lo, hi = int((float(w0["end"]) + 0.15) * 100), int((float(w1["start"]) - 0.15) * 100)
                if hi > lo:
                    mumble = max(mumble, float((level[lo:hi] > -30).sum()) / 100)
            ok = bool(ratio_best >= 0.9 and (gap is None or gap >= 0.25) and mumble <= 0.4)
            said = " ".join(w["word"].strip() for w in words[:k_best])
            spans = [(float(w["start"]), float(w["end"])) for w in words[:k_best]]
            cand = {"take": take.name, "ratio": round(ratio_best, 3), "cut": round(cut, 2), "said": said, "spans": spans,
                    "extra": " ".join(w["word"].strip() for w in extra)[:80], "gap": None if gap is None else round(gap, 2),
                    "ok": ok, "length": round(len(audio) / 48000, 2), "mumble": round(mumble, 2)}
            print(f"  {line['id']} {take.name:22} ratio {ratio_best:.2f} cut {cut:5.2f}/{cand['length']:5.2f} s "
                  f"{'ok ' if ok else 'BAD'} | {said}" + (f" [mumble {mumble:.1f} s]" if mumble > 0.4 else "") + (f" || extra: {cand['extra']}" if extra else ""))
            # the script's end punctuation heard in the take (Whisper writes "?" for a rising question)
            end_mark = line["text"].rstrip()[-1:]
            heard = said.rstrip()[-1:]
            cand["score"] = ratio_best + (0.03 if end_mark in "?!" and heard == end_mark else 0) \
                - (0.03 if end_mark == "." and heard == "?" else 0) + (0.01 if not extra else 0)
            if ok and (best is None or cand["score"] > best["score"]):
                best = cand
        if best is None:
            print(f"{line['id']}: FAILED, reseed")
            report[line["id"]] = {"ok": False, "language": lang}
            (out / f"{line['id']}.wav").unlink(missing_ok=True)
            temporary = report_path.with_suffix('.json.tmp')
            temporary.write_text(json.dumps(report, ensure_ascii=False, indent=1))
            temporary.replace(report_path)
            continue
        src = Path(a.voice_dir) / best["take"]
        dst = out / f"{line['id']}.wav"
        audio = load(src)[: int(best["cut"] * 48000)].copy()
        fade = int(0.04 * 48000)
        audio[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
        audio, removed = shorten_pauses(audio, best.pop("spans"), a.max_pause)
        audio = np.concatenate([np.zeros(int(a.lead * 48000), np.float32), audio])
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", "48000", "-ac", "1", "-i", "-",
                        str(dst)], input=audio.tobytes(), check=True)
        best["pauses_removed"] = round(removed, 2)
        best["file"] = dst.name
        best["language"] = lang
        best["seconds"] = round(len(audio) / 48000, 2)
        report[line["id"]] = best
        temporary = report_path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=1))
        temporary.replace(report_path)
        print(f"{line['id']}: {best['take']} -> {dst.name} ({best['seconds']} s"
              + (f", {removed:.2f} s of pause removed" if removed else "") + ")")
    temporary = report_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(report, indent=1, ensure_ascii=False))
    temporary.replace(report_path)
    if any(not report.get(line['id'], {}).get('ok') for line in lines):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
