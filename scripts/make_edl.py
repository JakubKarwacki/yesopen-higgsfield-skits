"""Build edit/edl.json (the timeline) from edit/cuts.json, project.json and the takes' word timestamps.

Each cut names the take and the first and last word of the line, plus how much to keep
before (head) and after (tail) it. Lines are searched in order inside each take, so a
repeated word ("What", "Fine") always resolves to its next occurrence. Word times from
Whisper are widened to where the audio really starts and ends (media.refine), then every
segment is rounded to whole frames so the planned timeline equals the rendered one.

usage: python3 make_edl.py <project_dir> [--upto N] [--no-endcard] [-o edit/edl.json]

Needs takes/<take>.words.json for every take in project.json (inspect_take.py writes them).
"""
import argparse
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from media import envelope, find_project, load_project, refine  # noqa: E402


from languages import normalize, project_language


def norm(w, language='en'):
    return normalize(w, language)


class Takes:
    def __init__(self, project, cfg):
        self.paths = {k: (project / v).resolve() for k, v in cfg["takes"].items()}
        self.language = project_language(cfg)
        self.words, self.env = {}, {}
        for k, p in self.paths.items():
            wj = p.with_suffix(".words.json")
            if not wj.exists():
                raise SystemExit(f"{wj} missing: run inspect_take.py {p}")
            self.words[k] = json.loads(wj.read_text())
        self.cursor = {k: 0 for k in self.paths}
        speech = cfg.get("speech", {})
        self.thr, self.gap, self.reach = speech.get("thr", -26.0), speech.get("gap", 0.12), speech.get("reach", 0.8)

    def span(self, take, first, last):
        """Start of the next `first` word and end of the following `last` word, checked against the audio."""
        words = self.words[take]
        try:
            i = next(j for j in range(self.cursor[take], len(words)) if norm(words[j]["w"], self.language) == norm(first, self.language))
            k = next(j for j in range(i, len(words)) if norm(words[j]["w"], self.language) == norm(last, self.language))
        except StopIteration:
            raise SystemExit(f"take {take}: no '{first} … {last}' after word #{self.cursor[take]}; check the cut order and .words.json")
        self.cursor[take] = k + 1
        if take not in self.env:
            self.env[take] = envelope(self.paths[take])
        onset, offset = refine(self.env[take], words[i]["s"], words[k]["e"], self.thr, self.gap, self.reach)
        # the widened times also feed the captions, so the first and last word stay on screen
        words[i]["s"], words[k]["e"] = min(onset, words[i]["s"]), max(offset, words[k]["e"])
        return words[i]["s"], words[k]["e"]


def build(project, cfg, cuts_doc, upto=None, with_endcard=True, out_dir=None):
    takes = Takes(project, cfg)
    fps = cfg.get("fps", 30)
    default_cy = cuts_doc.get("defaults", {}).get("cy", 0.40)
    fixes_all = cfg.get("captions", {}).get("fixes", {})
    segments, cutaways, dings, banners, caption_words = [], [], [], [], []
    t = 0.0
    for n, cut in enumerate(cuts_doc["cuts"][:upto]):
        take = cut["take"]
        if "fixed" in cut:
            start, end = cut["fixed"]
            anchor = start
        else:
            s, e = takes.span(take, *cut["line"])
            start = max(s - cut.get("head", 0.1), 0.0)
            end = cut["out"] if "out" in cut else e + cut.get("tail", 0.3)
            anchor = e
        end = start + round((end - start) * fps) / fps  # whole frames at the edit's frame rate
        segments.append({"take": take, "in": round(start, 3), "out": round(end, 3),
                         "zoom": cut.get("zoom", 1.0), "cx": cut.get("cx", 0.5), "cy": cut.get("cy", default_cy),
                         "cut": n + 1})
        fixes = fixes_all.get(take, {})
        for w in (takes.words[take] if cfg.get("captions", {}).get("enabled", True) else []):
            if start <= (w["s"] + w["e"]) / 2 <= end:
                caption_words.append({"w": fixes.get(w["w"], w["w"]),
                                      "s": round(t + max(w["s"], start) - start, 3),
                                      "e": round(t + min(w["e"], end) - start, 3)})
        at_anchor = t + (anchor - start)
        for ev in cut.get("events", []):
            kind = ev["type"]
            if kind == "ding":
                dings.append(round(at_anchor + ev.get("after", 0.0), 3))
            elif kind == "banner":
                banners.append({"at": round(at_anchor + ev.get("after", 0.0), 3), "name": ev["name"], "dur": ev.get("dur", 1.9)})
            elif kind == "ding_at":
                dings.append(round(t + (ev["take_time"] - start), 3))
            elif kind == "cutaway":
                cutaways.append({"at": round(t + (ev["take_time"] - start), 3), "take": ev["take"], "in": ev["in"],
                                 "dur": ev["dur"], "zoom": ev.get("zoom", 1.0), "cx": ev.get("cx", 0.5),
                                 "cy": ev.get("cy", default_cy)})
            else:
                raise SystemExit(f"cut {n + 1}: unknown event type {kind!r}")
        t += end - start

    out_dir = out_dir or project / "edit"
    rel = lambda p: os.path.relpath(p, project)  # noqa: E731
    endcard = cfg.get("endcard") or {}
    edl = {
        "version": 2,
        "root": os.path.relpath(project, out_dir),
        "fps": fps,
        "takes": {k: rel(v) for k, v in takes.paths.items()},
        "segments": segments,
        "cutaways": cutaways,
        "banners": banners,
        "dings": dings,
        "ding": "edit/assets/ding.wav",
        "ding_volume": cfg.get("ding_volume", 0.55),
        "caption_words": caption_words,
        "language": project_language(cfg),
        "caption_fixes": fixes_all,
        "caption_style": cfg.get("captions", {}).get("style", {}),
        "endcard": {"name": "endcard", "dur": endcard.get("dur", 2.6)} if with_endcard and endcard else None,
        "_dialogue_seconds": round(t, 2),
        "_dialogue_frames": sum(round((s["out"] - s["in"]) * fps) for s in segments),
    }
    if cfg.get("music"):  # only when there is one, so an edit without music keeps its exact EDL
        edl["music"] = {"thr": cfg.get("speech", {}).get("thr", -26.0), **cfg["music"]}
    return edl


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--upto", type=int, help="only the first N cuts (a quick preview of the opening)")
    ap.add_argument("--no-endcard", action="store_true")
    ap.add_argument("-o", "--out", help="default: <project>/edit/edl.json")
    a = ap.parse_args()
    project = find_project(a.project)
    cfg = load_project(project)
    cuts_doc = json.loads((project / "edit" / "cuts.json").read_text())
    out = pathlib.Path(a.out).resolve() if a.out else project / "edit" / "edl.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    edl = build(project, cfg, cuts_doc, a.upto, not a.no_endcard, out.parent)
    out.write_text(json.dumps(edl, indent=1) + "\n")
    print(json.dumps({"edl": str(out), "segments": len(edl["segments"]), "dialogue_seconds": edl["_dialogue_seconds"],
                      "dialogue_frames": edl["_dialogue_frames"], "banners": len(edl["banners"]),
                      "dings": len(edl["dings"]), "cutaways": len(edl["cutaways"]),
                      "caption_words": len(edl["caption_words"])}))


if __name__ == "__main__":
    main()
