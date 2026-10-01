"""Build edl.json from the takes' word timestamps.

Each cut names the take, the first and last word of the line, and how much
to keep before and after it. Lines are searched in order inside each take,
so a repeated word ("What", "Fine") always resolves to the next occurrence.

usage: python3 make_edl.py [config.json-string] > edl.json
config: {"takes": {"a1": "../takes/other.mp4"}, "upto": 10, "endcard": false}
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent
TAKES = {
    "o1": HERE / "../takes/take-owner-1-720p-0.mp4",
    "a1": HERE / "../takes/take-agency-1-720p-0.mp4",
    "o2": HERE / "../takes/take-owner-2-720p-0.mp4",
    "a2": HERE / "../takes/take-agency-2-720p-0.mp4",
}
WORDS = {}
cursor = {k: 0 for k in TAKES}


def norm(w):
    return re.sub(r"[^a-z0-9#]", "", w.lower())


ENV = {}
HOP = 0.01


def envelope(take):
    """Loudness of the take in dB, one value per 10 ms."""
    if take not in ENV:
        import numpy as np
        import subprocess
        raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(TAKES[take]), "-vn", "-ac", "1",
                                       "-ar", "16000", "-f", "s16le", "-"])
        a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        n = len(a) // 160
        ENV[take] = 20 * np.log10(np.sqrt((a[: n * 160].reshape(n, 160) ** 2).mean(axis=1)) + 1e-9)
    return ENV[take]


def refine(take, s, e, thr=-26.0, gap=0.12, reach=0.8):
    """Whisper's word times can be off by a few hundred ms; extend them to where the speech really starts and ends."""
    env = envelope(take)

    def loud(t):
        i = int(round(t / HOP))
        return 0 <= i < len(env) and env[i] > thr

    onset, t, quiet = s, s, 0.0
    while t > max(0.0, s - reach):
        t -= HOP
        if loud(t):
            onset, quiet = t, 0.0
        else:
            quiet += HOP
            if quiet >= gap:
                break
    offset, t, quiet = e, e, 0.0
    while t < e + reach:
        t += HOP
        if loud(t):
            offset, quiet = t + HOP, 0.0
        else:
            quiet += HOP
            if quiet >= gap:
                break
    return round(onset, 2), round(offset, 2)


def span(take, first, last):
    """Start of the next `first` word and end of the following `last` word in a take, checked against the audio."""
    if take not in WORDS:
        WORDS[take] = json.loads(TAKES[take].with_suffix(".words.json").read_text())
    words = WORDS[take]
    i = next(j for j in range(cursor[take], len(words)) if norm(words[j]["w"]) == norm(first))
    k = next(j for j in range(i, len(words)) if norm(words[j]["w"]) == norm(last))
    cursor[take] = k + 1
    onset, offset = refine(take, words[i]["s"], words[k]["e"])
    words[i]["s"], words[k]["e"] = min(onset, words[i]["s"]), max(offset, words[k]["e"])
    return words[i]["s"], words[k]["e"]


FACE = 0.33
# A cut is either a spoken line (take, first word, last word, head, tail) or a
# fixed span (take, None, None, in, out). Optional keys: zoom, cy and events.
# Events, timed from the end of the line (or the segment start for fixed spans):
#   ("ding", delay)
#   ("banner", png, delay, dur)
#   ("ding_at", take_time)                       a ding at an absolute time of the take
#   ("cutaway", take_time, src, src_in, dur, zoom, cy)  silent reaction shot over this cut
CUTS = [
    dict(take="o1", line=("Hey", "up"), head=0.30, tail=0.20),
    dict(take="a1", line=("You're", "agency"), head=0.10, tail=0.30, zoom=1.25, cy=FACE),
    dict(take="o1", line=("It's", "invoices"), head=0.15, tail=0.30, zoom=1.10, cy=0.38),
    dict(take="a1", line=("Wow", "Wow"), head=0.30, tail=1.15, zoom=1.40, cy=FACE),
    dict(take="a1", line=("Fine", "questions"), head=0.10, tail=0.25),
    dict(take="o1", line=("I", "know"), head=0.12, tail=1.35,
         events=[("ding", 0.20), ("banner", "assets/notif-1.png", 0.22, 1.9)]),
    dict(take="a1", line=("Who's", "reviews"), head=0.85, tail=0.25),
    dict(take="o1", line=("No", "idea"), head=0.15, tail=1.00,
         events=[("ding", 0.15), ("banner", "assets/notif-2.png", 0.17, 1.9)]),
    dict(take="a1", line=("Who's", "Instagram"), head=0.85, tail=0.30),
    dict(take="o1", line=("Not", "clue"), head=0.15, tail=1.15,
         events=[("ding", 0.15), ("banner", "assets/notif-3.png", 0.17, 2.1)]),
    dict(take="a2", line=("Who's", "Maps"), head=0.10, tail=0.30, zoom=1.15, cy=0.36),
    dict(take="o2", line=("Honestly", "idea"), head=0.10, tail=1.30,
         events=[("ding", 0.15), ("ding", 0.42), ("banner", "assets/notif-4.png", 0.17, 2.1)]),
    dict(take="a2", line=("Wait", "else"), head=0.85, tail=0.35, zoom=1.30, cy=FACE),
    dict(take="o2", line=("What", "No"), head=0.10, tail=0.30, zoom=1.45, cy=FACE),
    dict(take="a2", line=("Then", "you"), head=0.10, tail=0.30),
    dict(take="o2", line=("It's", "app"), head=0.60, tail=0.40),
    dict(take="a2", line=("You're", "app"), head=0.10, tail=0.40, zoom=1.30, cy=FACE),
    dict(take="o2", line=("It", "days"), head=0.10, tail=0.15),
    dict(take="a2", line=("Fine", "me"), head=0.10, out=25.3,
         events=[("cutaway", 19.95, "o2", 10.05, 0.6, 1.0, 0.40)]),
    dict(take="o2", line=("What", "back"), head=0.08, tail=1.00),
    dict(take="o2", fixed=(22.7, 28.0), events=[("ding_at", 25.55)]),
]


# Whisper transcribed the takes correctly; these only match the script's punctuation and spelling.
CAPTION_FIXES = {
    "o1": {"you,": "you.", "it's": "It's"},
    "o2": {"Honestly,": "Honestly?", "absolutely": "Absolutely", "come": "Come", "2am,": "2 a.m.", "you": "You", "5": "five", "no,": "no!"},
    "a2": {"us?": "us...", "For": "for", "app?": "app?!"},
}


def build(upto=None, with_endcard=True):
    segments, cutaways, dings, banners, caption_words = [], [], [], [], []
    t = 0.0
    for cut in CUTS[:upto]:
        take = cut["take"]
        if "fixed" in cut:
            start, end = cut["fixed"]
            anchor = start
        else:
            s, e = span(take, *cut["line"])
            start = max(s - cut["head"], 0.0)
            end = cut["out"] if "out" in cut else e + cut["tail"]
            anchor = e
        end = start + round((end - start) * 30) / 30  # whole frames at the edit's 30 fps
        segments.append({"take": take, "in": round(start, 3), "out": round(end, 3),
                         "zoom": cut.get("zoom", 1.0), "cx": 0.5, "cy": cut.get("cy", 0.40)})
        fixes = CAPTION_FIXES.get(take, {})
        for w in WORDS[take]:
            if start <= (w["s"] + w["e"]) / 2 <= end:
                caption_words.append({"w": fixes.get(w["w"], w["w"]),
                                      "s": round(t + max(w["s"], start) - start, 3),
                                      "e": round(t + min(w["e"], end) - start, 3)})
        at_anchor = t + (anchor - start)
        for ev in cut.get("events", []):
            kind = ev[0]
            if kind == "ding":
                dings.append(round(at_anchor + ev[1], 3))
            elif kind == "banner":
                banners.append({"at": round(at_anchor + ev[2], 3), "png": str((HERE / ev[1]).resolve()), "dur": ev[3]})
            elif kind == "ding_at":
                dings.append(round(t + (ev[1] - start), 3))
            elif kind == "cutaway":
                _, take_time, src, src_in, dur, zoom, cy = ev
                cutaways.append({"at": round(t + (take_time - start), 3), "take": src, "in": src_in,
                                 "dur": dur, "zoom": zoom, "cx": 0.5, "cy": cy})
        t += end - start
    return {
        "takes": {k: str(v.resolve()) for k, v in TAKES.items()},
        "segments": segments,
        "cutaways": cutaways,
        "banners": banners,
        "dings": dings,
        "ding": str((HERE / "assets/ding.wav").resolve()),
        "ding_volume": 0.55,
        "caption_words": caption_words,
        "caption_fixes": CAPTION_FIXES,
        "endcard": {"png": str((HERE / "assets/endcard.png").resolve()), "dur": 2.6} if with_endcard else None,
        "_dialogue_seconds": round(t, 2),
    }


if __name__ == "__main__":
    cfg = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    for k, v in cfg.get("takes", {}).items():
        TAKES[k] = HERE / v
    print(json.dumps(build(cfg.get("upto"), cfg.get("endcard", True)), indent=1))
