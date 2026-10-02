"""Render the edit in edit/edl.json in one output format: cut the takes, add cutaways, captions,
notification banners, dings and the end card, lay the music bed under it when the EDL has one,
then normalise the loudness.

usage: python3 assemble.py <project_dir> [--format 9:16|4:5|1:1|16:9] [--edl PATH] [--out PATH]
                           [--no-captions] [--whisper-captions] [--no-music]

Default output: <project>/final/<name>-<format>.mp4, e.g. final/its-not-you-its-your-invoices-9x16.mp4.
Intermediate files go to <project>/edit/work/<format>/. Overlays come from edit/assets/<format>/
and are rendered by build_assets.py when missing.
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from brand import caption, get_format  # noqa: E402
from media import chunks_of, find_project, load_project, probe_duration, run, video_filter  # noqa: E402


def render_segments(edl, root, layout, work, fps):
    parts = []
    for i, seg in enumerate(edl["segments"]):
        src = root / edl["takes"][seg["take"]]
        # a whole number of frames, with the audio cut to exactly the same length,
        # so the rendered timeline matches the times make_edl.py computed
        frames = round((seg["out"] - seg["in"]) * fps)
        dur = frames / fps
        out = work / f"seg_{i:03d}.mkv"
        fade = min(0.03, dur / 4)
        vf = video_filter(src, layout, seg.get("zoom", 1.0), seg.get("cx", 0.5), seg.get("cy", 0.4), fps)
        run(["-ss", f"{seg['in']:.3f}", "-i", src, "-t", f"{dur:.6f}", "-frames:v", str(frames),
             "-vf", vf + ",tpad=stop_mode=clone:stop_duration=0.2",
             "-af", f"aresample=48000,aformat=channel_layouts=stereo,apad,atrim=0:{dur:.6f},afade=t=in:d={fade},afade=t=out:st={dur - fade:.6f}:d={fade}",
             "-c:v", "libx264", "-preset", "fast", "-crf", "15", "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", out])
        parts.append(out)
    listing = work / "segments.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts))
    dialogue = work / "dialogue.mkv"
    run(["-f", "concat", "-safe", "0", "-i", listing, "-c", "copy", dialogue])
    return dialogue


def whisper_words(audio_src, work, language="en"):
    """Fallback when the EDL has no caption words: transcribe the cut dialogue."""
    import whisper
    wav = work / "dialogue.wav"
    run(["-i", audio_src, "-vn", "-ac", "1", "-ar", "16000", wav])
    model = whisper.load_model("large-v3-turbo")
    result = model.transcribe(str(wav), language=language, word_timestamps=True, condition_on_previous_text=False)
    return [{"w": w["word"].strip(), "s": w["start"], "e": w["end"]} for seg in result["segments"] for w in seg["words"]]


def assemble(project, layout, edl_path=None, out_path=None, captions=True, whisper_captions=False, music=True):
    cfg = load_project(project)
    edl_path = pathlib.Path(edl_path or project / "edit" / "edl.json").resolve()
    edl = json.loads(edl_path.read_text())
    root = (edl_path.parent / edl.get("root", "..")).resolve()
    fps = edl.get("fps", 30)
    W, H = layout["size"]
    slug = layout["slug"]
    assets = project / "edit" / "assets" / slug
    needed = [assets / f"{b['name']}.png" for b in edl.get("banners", [])]
    if edl.get("endcard"):
        needed.append(assets / f"{edl['endcard']['name']}.png")
    if not all(p.exists() for p in needed) or not (root / edl["ding"]).exists():
        import build_assets
        build_assets.build(project, [layout["name"]])
    work = project / "edit" / "work" / slug
    work.mkdir(parents=True, exist_ok=True)
    out_path = pathlib.Path(out_path) if out_path else project / "final" / f"{cfg.get('name', project.name)}-{slug}.mp4"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    dialogue = render_segments(edl, root, layout, work, fps)
    total = probe_duration(dialogue)

    inputs, filters, last, n = ["-i", dialogue], [], "[0:v]", 1
    for k, cut in enumerate(edl.get("cutaways", [])):
        src = root / edl["takes"][cut["take"]]
        clip = work / f"cut_{k:02d}.mkv"
        run(["-ss", f"{cut['in']:.3f}", "-t", f"{cut['dur']:.3f}", "-i", src, "-an",
             "-vf", video_filter(src, layout, cut.get("zoom", 1.0), cut.get("cx", 0.5), cut.get("cy", 0.4), fps),
             "-c:v", "libx264", "-preset", "fast", "-crf", "15", "-pix_fmt", "yuv420p", clip])
        inputs += ["-i", clip]
        filters.append(f"[{n}:v]setpts=PTS-STARTPTS+{cut['at']}/TB[c{k}]")
        filters.append(f"{last}[c{k}]overlay=eof_action=pass:enable='between(t,{cut['at']},{cut['at'] + cut['dur']})'[v{n}]")
        last, n = f"[v{n}]", n + 1

    top = layout["banner_top"]
    for k, b in enumerate(edl.get("banners", [])):
        at, dur, slide = b["at"], b.get("dur", 1.7), 0.22
        inputs += ["-loop", "1", "-t", f"{dur:.3f}", "-i", assets / f"{b['name']}.png"]
        y = (f"if(lt(t-{at},{slide}),-h+(h+{top})*(t-{at})/{slide},"
             f"if(gt(t-{at},{dur - slide}),{top}-(h+{top})*(t-{at}-{dur - slide})/{slide},{top}))")
        filters.append(f"[{n}:v]format=rgba,setpts=PTS-STARTPTS+{at}/TB[b{k}]")
        filters.append(f"{last}[b{k}]overlay=x=(W-w)/2:y='{y}':eof_action=pass:enable='between(t,{at},{at + dur})'[v{n}]")
        last, n = f"[v{n}]", n + 1

    if captions:
        words = edl.get("caption_words")
        if not words or whisper_captions:
            words = whisper_words(dialogue, work, cfg.get("language", "en"))
        (work / "caption-words.json").write_text(json.dumps(words, indent=1))
        style = {**cfg.get("captions", {}).get("style", {}), **edl.get("caption_style", {})}
        chunks = chunks_of(words, **style)
        (work / "caption-chunks.json").write_text(json.dumps(chunks, indent=1))
        cap_y = round(layout["caption_y"] * H)
        for k, ch in enumerate(chunks):
            png = work / f"cap_{k:03d}.png"
            caption(ch["text"], width=W, size=layout["caption_size"]).save(png)
            dur = ch["e"] - ch["s"]
            inputs += ["-loop", "1", "-t", f"{dur:.3f}", "-i", png]
            filters.append(f"[{n}:v]format=rgba,setpts=PTS-STARTPTS+{ch['s']:.3f}/TB[t{k}]")
            filters.append(f"{last}[t{k}]overlay=x=0:y={cap_y}:eof_action=pass:enable='between(t,{ch['s']:.3f},{ch['e']:.3f})'[v{n}]")
            last, n = f"[v{n}]", n + 1

    ding = root / edl["ding"]
    dings = edl.get("dings", [])
    audio = "[0:a]"
    if dings:
        inputs += ["-i", ding]
        filters.append(f"[{n}:a]asplit={len(dings)}" + "".join(f"[d{k}]" for k in range(len(dings))))
        for k, t in enumerate(dings):
            ms = int(t * 1000)
            filters.append(f"[d{k}]adelay={ms}|{ms},volume={edl.get('ding_volume', 0.55)}[dd{k}]")
        filters.append("[0:a]" + "".join(f"[dd{k}]" for k in range(len(dings))) + f"amix=inputs={len(dings) + 1}:normalize=0:duration=first[a]")
        audio, n = "[a]", n + 1
    filters.append(f"{last}format=yuv420p[vout]")
    main_mkv = work / "main.mkv"
    run(inputs + ["-filter_complex", ";".join(filters), "-map", "[vout]", "-map", audio, "-t", f"{total:.3f}",
                  "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-c:a", "pcm_s16le", main_mkv])

    parts = [main_mkv]
    end = edl.get("endcard")
    if end:
        end_mkv = work / "endcard.mkv"
        frames = int(end["dur"] * fps)
        # -framerate matters: a looped PNG defaults to 25 fps and the card would come out short
        run(["-loop", "1", "-framerate", str(fps), "-t", f"{end['dur']}", "-i", assets / f"{end['name']}.png", "-i", ding,
             "-filter_complex",
             f"[0:v]scale={W * 2}:{H * 2},zoompan=z='1+0.035*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={fps},"
             f"fade=t=in:st=0:d=0.18:color=white,format=yuv420p[v];[1:a]volume=0.5,apad[a]",
             "-map", "[v]", "-map", "[a]", "-t", f"{end['dur']}", "-ar", "48000", "-ac", "2",
             "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-c:a", "pcm_s16le", end_mkv])
        parts.append(end_mkv)
    listing = work / "final.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts))
    loud = "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000"
    encode = ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-profile:v", "high",
              "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out_path]
    if music and edl.get("music"):
        from music import build_bed, master
        timeline = sum(probe_duration(p) for p in parts)
        # the picture cuts to the end card after the segments' whole frames (the audio runs a few ms longer)
        cut_at = sum(round((s["out"] - s["in"]) * fps) for s in edl["segments"]) / fps
        bed, bed_info = build_bed(edl["music"], root, dialogue, timeline, cut_at if end else None, work)
        # the bed comes placed, ducked and faded (music.py); the mix gets a static gain and a peak limiter
        graph, bed_info["master_gain_db"] = master(listing, bed, work)
        print(json.dumps({"format": layout["name"], "music": bed_info}))
        run(["-f", "concat", "-safe", "0", "-i", listing, "-i", bed, "-filter_complex", graph,
             "-map", "0:v", "-map", "[a]"] + encode)
    else:
        run(["-f", "concat", "-safe", "0", "-i", listing, "-af", loud] + encode)
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--format", default="9:16", help="9:16, 4:5, 1:1 or 16:9 (or several, comma-separated, or 'all')")
    ap.add_argument("--edl")
    ap.add_argument("--out", help="output file (only with a single format)")
    ap.add_argument("--no-captions", action="store_true")
    ap.add_argument("--whisper-captions", action="store_true", help="caption from Whisper on the cut dialogue instead of the EDL words")
    ap.add_argument("--no-music", action="store_true", help="leave out the music bed even if the EDL has one")
    a = ap.parse_args()
    project = find_project(a.project)
    names = list(__import__("brand").FORMATS) if a.format == "all" else a.format.split(",")
    if a.out and len(names) > 1:
        raise SystemExit("--out works with one format only")
    for name in names:
        layout = get_format(name)
        out = assemble(project, layout, a.edl, a.out, not a.no_captions, a.whisper_captions, not a.no_music)
        print(json.dumps({"format": layout["name"], "out": str(out), "duration": round(probe_duration(out), 3)}))


if __name__ == "__main__":
    main()
