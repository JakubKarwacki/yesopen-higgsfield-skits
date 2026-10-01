"""Cut the takes into the dialogue edit, add cutaways, captions, notification banners, dings and the end card.

usage: python3 assemble.py edl.json out.mp4 [--no-captions]
"""
import json
import pathlib
import subprocess
import sys

from brand import caption

FF = ["ffmpeg", "-v", "error", "-y"]
W, H, FPS = 1080, 1920, 30
CAPTION_Y = 1240
BANNER_TOP = 70


def run(args):
    subprocess.run(FF + args, check=True)


def size(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height", "-of", "csv=p=0", str(path)]).decode().strip()
    w, h = out.split(",")
    return int(w), int(h)


def duration(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(path)]).decode().strip())


def vf_for(src, zoom=1.0, cx=0.5, cy=0.4):
    sw, sh = size(src)
    target = W / H
    # crop the source to 9:16 first, then zoom around (cx, cy)
    bw, bh = (sh * target, sh) if sw / sh > target else (sw, sw / target)
    cw, ch = bw / zoom, bh / zoom
    x = min(max(cx * sw - cw / 2, 0), sw - cw)
    y = min(max(cy * sh - ch / 2, 0), sh - ch)
    return f"crop={int(cw) // 2 * 2}:{int(ch) // 2 * 2}:{int(x)}:{int(y)},scale={W}:{H}:flags=lanczos,setsar=1,fps={FPS}:start_time=0"


def render_segments(edl, work):
    parts = []
    for i, seg in enumerate(edl["segments"]):
        src = edl["takes"][seg["take"]]
        # a whole number of frames, with audio cut to exactly the same length,
        # so the edit's timeline matches the times make_edl.py computed
        frames = round((seg["out"] - seg["in"]) * FPS)
        dur = frames / FPS
        out = work / f"seg_{i:03d}.mkv"
        fade = min(0.03, dur / 4)
        run(["-ss", f"{seg['in']:.3f}", "-i", src, "-t", f"{dur:.6f}", "-frames:v", str(frames),
             "-vf", vf_for(src, seg.get("zoom", 1.0), seg.get("cx", 0.5), seg.get("cy", 0.4)) + ",tpad=stop_mode=clone:stop_duration=0.2",
             "-af", f"aresample=48000,aformat=channel_layouts=stereo,apad,atrim=0:{dur:.6f},afade=t=in:d={fade},afade=t=out:st={dur - fade:.6f}:d={fade}",
             "-c:v", "libx264", "-preset", "fast", "-crf", "15", "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", str(out)])
        parts.append(out)
    listing = work / "segments.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts))
    dialogue = work / "dialogue.mkv"
    run(["-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(dialogue)])
    return dialogue


def words_of(audio_src, work):
    """Word timestamps from Whisper (cached large-v3-turbo model)."""
    import whisper
    wav = work / "dialogue.wav"
    run(["-i", str(audio_src), "-vn", "-ac", "1", "-ar", "16000", str(wav)])
    model = whisper.load_model("large-v3-turbo")
    result = model.transcribe(str(wav), language="en", word_timestamps=True, condition_on_previous_text=False)
    words = [{"w": w["word"].strip(), "s": w["start"], "e": w["end"]} for seg in result["segments"] for w in seg["words"]]
    (work / "dialogue-words.json").write_text(json.dumps(words, indent=1))
    return words


def words_from_takes(edl):
    """Caption words taken from each take's own transcript and shifted onto the edit's timeline."""
    words, t = [], 0.0
    for seg in edl["segments"]:
        src = pathlib.Path(edl["takes"][seg["take"]])
        fixes = edl.get("caption_fixes", {}).get(seg["take"], {})
        for w in json.loads(src.with_suffix(".words.json").read_text()):
            if seg["in"] <= (w["s"] + w["e"]) / 2 <= seg["out"]:
                words.append({"w": fixes.get(w["w"], w["w"]),
                              "s": round(t + max(w["s"], seg["in"]) - seg["in"], 3),
                              "e": round(t + min(w["e"], seg["out"]) - seg["in"], 3)})
        t += seg["out"] - seg["in"]
    return words


def chunks_of(words, max_words=3, max_chars=18, gap=0.35):
    chunks, cur = [], []
    for i, w in enumerate(words):
        if cur and (len(cur) >= max_words or len(" ".join(x["w"] for x in cur + [w])) > max_chars
                    or cur[-1]["w"][-1:] in ".?!,…" or w["s"] - cur[-1]["e"] > gap):
            chunks.append(cur)
            cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    out = []
    for i, c in enumerate(chunks):
        start = c[0]["s"]
        end = c[-1]["e"] + 0.12
        if i + 1 < len(chunks):
            end = min(max(end, start + 0.35), chunks[i + 1][0]["s"])
        out.append({"text": " ".join(x["w"] for x in c), "s": start, "e": end})
    return out


def main():
    edl_path, out_path = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    edl = json.loads(edl_path.read_text())
    work = edl_path.parent / "work"
    work.mkdir(exist_ok=True)
    dialogue = render_segments(edl, work)
    total = duration(dialogue)

    inputs, filters, last = ["-i", str(dialogue)], [], "[0:v]"
    n = 1
    for k, cut in enumerate(edl.get("cutaways", [])):
        src = edl["takes"][cut["take"]]
        clip = work / f"cut_{k:02d}.mkv"
        run(["-ss", f"{cut['in']:.3f}", "-t", f"{cut['dur']:.3f}", "-i", src, "-an",
             "-vf", vf_for(src, cut.get("zoom", 1.0), cut.get("cx", 0.5), cut.get("cy", 0.4)),
             "-c:v", "libx264", "-preset", "fast", "-crf", "15", "-pix_fmt", "yuv420p", str(clip)])
        inputs += ["-i", str(clip)]
        filters.append(f"[{n}:v]setpts=PTS-STARTPTS+{cut['at']}/TB[c{k}]")
        filters.append(f"{last}[c{k}]overlay=eof_action=pass:enable='between(t,{cut['at']},{cut['at'] + cut['dur']})'[v{n}]")
        last, n = f"[v{n}]", n + 1

    for k, b in enumerate(edl.get("banners", [])):
        at, dur, slide = b["at"], b.get("dur", 1.7), 0.22
        inputs += ["-loop", "1", "-t", f"{dur:.3f}", "-i", b["png"]]
        y = (f"if(lt(t-{at},{slide}),-h+(h+{BANNER_TOP})*(t-{at})/{slide},"
             f"if(gt(t-{at},{dur - slide}),{BANNER_TOP}-(h+{BANNER_TOP})*(t-{at}-{dur - slide})/{slide},{BANNER_TOP}))")
        filters.append(f"[{n}:v]format=rgba,setpts=PTS-STARTPTS+{at}/TB[b{k}]")
        filters.append(f"{last}[b{k}]overlay=x=(W-w)/2:y='{y}':eof_action=pass:enable='between(t,{at},{at + dur})'[v{n}]")
        last, n = f"[v{n}]", n + 1

    if "--no-captions" not in sys.argv:
        if "caption_words" in edl:
            words = edl["caption_words"]
        elif edl.get("captions") == "takes":
            words = words_from_takes(edl)
        else:
            words = words_of(dialogue, work)
        (work / "caption-words.json").write_text(json.dumps(words, indent=1))
        for k, ch in enumerate(chunks_of(words)):
            png = work / f"cap_{k:03d}.png"
            caption(ch["text"]).save(png)
            dur = ch["e"] - ch["s"]
            inputs += ["-loop", "1", "-t", f"{dur:.3f}", "-i", str(png)]
            filters.append(f"[{n}:v]format=rgba,setpts=PTS-STARTPTS+{ch['s']:.3f}/TB[t{k}]")
            filters.append(f"{last}[t{k}]overlay=x=0:y={CAPTION_Y}:eof_action=pass:enable='between(t,{ch['s']:.3f},{ch['e']:.3f})'[v{n}]")
            last, n = f"[v{n}]", n + 1

    dings = edl.get("dings", [])
    audio = "[0:a]"
    if dings:
        inputs += ["-i", edl["ding"]]
        filters.append(f"[{n}:a]asplit={len(dings)}" + "".join(f"[d{k}]" for k in range(len(dings))))
        for k, t in enumerate(dings):
            ms = int(t * 1000)
            filters.append(f"[d{k}]adelay={ms}|{ms},volume={edl.get('ding_volume', 0.55)}[dd{k}]")
        filters.append(f"[0:a]" + "".join(f"[dd{k}]" for k in range(len(dings))) + f"amix=inputs={len(dings) + 1}:normalize=0:duration=first[a]")
        audio, n = "[a]", n + 1
    filters.append(f"{last}format=yuv420p[vout]")
    main_mp4 = work / "main.mkv"
    run(inputs + ["-filter_complex", ";".join(filters), "-map", "[vout]", "-map", audio, "-t", f"{total:.3f}",
                  "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-c:a", "pcm_s16le", str(main_mp4)])

    end = edl.get("endcard")
    parts = [main_mp4]
    if end:
        end_mp4 = work / "endcard.mkv"
        frames = int(end["dur"] * FPS)
        run(["-loop", "1", "-framerate", str(FPS), "-t", f"{end['dur']}", "-i", end["png"], "-i", edl["ding"],
             "-filter_complex",
             f"[0:v]scale={W * 2}:{H * 2},zoompan=z='1+0.035*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS},"
             f"fade=t=in:st=0:d=0.18:color=white,format=yuv420p[v];[1:a]volume=0.5,apad[a]",
             "-map", "[v]", "-map", "[a]", "-t", f"{end['dur']}", "-ar", "48000", "-ac", "2",
             "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-c:a", "pcm_s16le", str(end_mp4)])
        parts.append(end_mp4)
    listing = work / "final.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts))
    run(["-f", "concat", "-safe", "0", "-i", str(listing), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000",
         "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-profile:v", "high",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out_path)])
    print(json.dumps({"out": str(out_path), "duration": round(duration(out_path), 2)}))


if __name__ == "__main__":
    main()
