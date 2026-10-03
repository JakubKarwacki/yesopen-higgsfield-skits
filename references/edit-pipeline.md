# Edit pipeline: from takes to a finished skit

The whole edit is data: `project.json` + `edit/cuts.json` -> `make_edl.py` -> `edit/edl.json` ->
`assemble.py` per format. Nothing is cut by hand in an editor, so a fix is one changed number and a re-run,
and the result is exactly reproducible: re-running the gym example gives a byte-identical master
(MD5 `095ffdca450db823b26fd76fa89a1204`).

## Contents

1. Tools and setup
2. Step by step
3. `project.json` reference
4. `edit/cuts.json` reference, with how to choose each number
5. `edit/edl.json` reference
6. What `assemble.py` does, filter by filter
7. Known traps and their fixes
8. Music bed

## 1. Tools and setup

- `ffmpeg`/`ffprobe` (8.x used; no `drawtext`/`libass` needed: all text is drawn with Pillow and overlaid).
- Python 3.11 with `pillow`, `numpy`, and `openai-whisper` for `inspect_take.py` and `qa_report.py --whisper`
  (`pip install pillow numpy openai-whisper`; the `large-v3-turbo` model downloads on first use).
- Manrope comes with the skill (`assets/brand/fonts/Manrope-Variable.ttf`, SIL OFL). `YESOPEN_FONT` overrides it.

## 2. Step by step

```bash
SK=<skill folder>; cd <project folder>
python3 $SK/scripts/inspect_take.py takes/take-owner-1-720p-0.mp4     # every take: words + sheet + boundaries
# write edit/cuts.json (section 4) while looking at the sheets and the printed lines
python3 $SK/scripts/build_assets.py . --sheet                         # banners, end card, ding, per format
python3 $SK/scripts/make_edl.py . --upto 10 --no-endcard -o edit/edl-preview.json
python3 $SK/scripts/assemble.py . --format 9:16 --edl edit/edl-preview.json --out edit/preview/part1.mp4
# show the preview, adjust cuts.json, repeat
python3 $SK/scripts/make_edl.py .
python3 $SK/scripts/assemble.py . --format all
python3 $SK/scripts/qa_report.py . --format 9:16 --whisper
python3 $SK/scripts/encode_variants.py final/<name>-9x16.mp4
```

Render times on an M-series Mac for the 73.6 s gym skit: 9:16 53 s, 4:5 41 s, 1:1 35 s, 16:9 56 s.

## 3. `project.json`

| Key | Meaning | Gym value |
| --- | --- | --- |
| `slug`, `date`, `name`, `title` | ids; `name` names the outputs (`final/<name>-<format>.mp4`) | `its-not-you-its-your-invoices` |
| `language` | Whisper language for transcripts and QA | `en` |
| `fps` | edit frame rate (takes are 24 fps; the edit resamples to 30) | `30` |
| `formats` | formats to deliver | `["9:16","4:5","1:1","16:9"]` |
| `reference` | link to the reference video (no frames, no transcript) | YouTube URL |
| `cast` | per character: still, its URL and Soul args (Higgsfield), voice: the description used in Seedance prompts or the voice sample (GPU) | owner, agency |
| `takes` | short id -> take file; ids are used in `cuts.json` | `o1`, `a1`, `o2`, `a2`; GPU: `l01` … `l21`, one per line |
| `speech.thr/gap/reach` | speech detection for line boundaries (dB, s, s) | `-26`, `0.12`, `0.8` |
| `captions.style` | `max_words`, `max_chars`, `gap` for caption chunks | `3`, `18`, `0.35` |
| `captions.fixes` | per take: Whisper token -> caption text | `"2am,": "2 a.m."` |
| `captions.sample` | text for the caption sample image | `It's not you.` |
| `notification_app`, `notification_when` | banner title and time label | `YesOpen`, `now` |
| `notifications` | banner name -> text (or `{body, when}`) | `notif-1` … `notif-4` |
| `endcard.tagline` | lines of `[text, colour]` parts; colours `ink`, `blue`, `muted`, hex or RGB | see example |
| `endcard.url`, `endcard.dur` | URL under the tagline; card length in s | `yesopens.com`, `2.6` |
| `ding_volume` | volume of each ding under dialogue | `0.55` |
| `engine` | who makes the stills and takes: `gpu` (the default for new projects, `gpu-engine.md`) or `higgsfield`; it tells the agent which Phases 3–4 to follow, no script reads it | `higgsfield`; `gpu` in `gym-breakup-gpu` |
| `music` | optional music bed, section 8; without it the render is exactly as before | not set (no music) |

## 4. `edit/cuts.json`

One entry per shot, in timeline order:

```json
{"take": "o1", "line": ["I", "know"], "head": 0.12, "tail": 1.35,
 "events": [{"type": "ding", "after": 0.20}, {"type": "banner", "name": "notif-1", "after": 0.22, "dur": 1.9}],
 "note": "6 OWNER: I don't know... DING + banner 1; he flips the phone face down."}
```

| Field | Meaning | How to choose |
| --- | --- | --- |
| `take` | take id from `project.json` | |
| `line` | first and last word of the line as Whisper wrote them; punctuation and case are ignored | the search starts after the previous cut's last word in the same take, so repeated words ("What", "Fine") resolve in order |
| `head` | seconds kept before the first word | 0.08–0.15 for a snappy cut; 0.3 for the opening; 0.6–0.85 to keep a reaction before the line (the agency's suspicious look before "Who's going to reply…") |
| `tail` | seconds kept after the last word | 0.15–0.4 normally; 1.0–1.35 when a banner or a silent joke plays after the line (phone flip, cough, whistle) |
| `out` | absolute take time to end at, instead of `tail` | use when an action runs long after the words (the agency walking out: `25.3`) |
| `fixed` | `[in, out]` in take time, no line search | silent beats (the celebration `[22.7, 28.0]`) |
| `zoom` | punch-in factor around (`cx`, `cy`) | 1.10–1.15 for emphasis, 1.25–1.30 for shock, 1.40–1.45 for the biggest beats; at most every third shot |
| `cx`, `cy` | zoom centre as a fraction of the source frame | `cy` 0.33 = face height in these takes (`FACE`); 0.36–0.40 for chest-up |
| `note` | free text: the script line and the reason | always write it; it is the edit's documentation |

Events, timed from the end of the line (`after`), or from the segment start for `fixed` spans:

| Event | Fields | Use |
| --- | --- | --- |
| `ding` | `after` | notification sound; two dings 0.27 s apart for the biggest one |
| `banner` | `name`, `after`, `dur` | slides in over 0.22 s from the top, holds, slides out; `after` 0.02 s later than the ding feels right |
| `ding_at` | `take_time` | a ding at an absolute time of the take (the "Hey, you." phone ding at 25.55) |
| `cutaway` | `take_time`, `take`, `in`, `dur`, `zoom`, `cy` | a silent shot from another take over this segment (the owner's face for 0.6 s while the agency rants) |

## 5. `edit/edl.json` (written by `make_edl.py`)

| Key | Content |
| --- | --- |
| `root` | the project folder relative to the EDL file |
| `fps`, `takes` | from `project.json`, take paths relative to the project |
| `segments[]` | `take`, `in`, `out` (seconds in the take, whole frames), `zoom`, `cx`, `cy`, `cut` (index in cuts.json) |
| `cutaways[]` | `at` (timeline seconds), `take`, `in`, `dur`, `zoom`, `cx`, `cy` |
| `banners[]` | `at`, `name`, `dur` |
| `dings[]` | timeline seconds |
| `ding`, `ding_volume` | sound file and level |
| `caption_words[]` | `w`, `s`, `e` on the edit timeline, already fixed by `captions.fixes` |
| `caption_style`, `caption_fixes` | copied for reference |
| `endcard` | `{name, dur}` or `null` |
| `music` | only when `project.json` has one: its `music` block plus `thr` from `speech.thr` |
| `_dialogue_seconds`, `_dialogue_frames` | planned length without the end card (gym: 70.93 s, 2128 frames) |

How a line becomes a segment:

1. Find `first`…`last` in the take's words after that take's cursor.
2. Widen the span with the audio envelope (`media.refine`): 10 ms RMS in dB; walk out from Whisper's times
   while the level is above `speech.thr`, tolerating dips shorter than `gap`, at most `reach` seconds. Whisper's
   word starts were off by up to 0.4 s ("Honestly" 2.30 -> real 1.93) and clipped first syllables.
3. `in = start - head`, `out = end + tail` (or `out`), then the length is rounded to whole frames.
4. Caption words whose midpoint lies inside the segment are moved onto the timeline.
5. Events are converted to timeline times.

## 6. What `assemble.py` does

1. **Segments.** Each segment is cut with `-ss in -frames:v N` (N = frames of the segment) and
   `crop -> scale (lanczos) -> setsar=1 -> fps=30:start_time=0 -> tpad (clone 0.2 s)`; audio `aresample 48000,
   stereo, apad, atrim to exactly N/30 s` with 30 ms fades. Every segment is exactly as long as planned.
   16:9 uses the pillarbox graph instead of the crop (formats-delivery.md).
2. **Concat** with stream copy into `dialogue.mkv`.
3. **Cutaways** are rendered the same way without audio and overlaid with `enable='between(t,at,at+dur)'`.
4. **Banners**: PNG looped for `dur`, `overlay x=(W-w)/2` with a piecewise `y` expression: slide in from `-h` to
   `banner_top` in 0.22 s, hold, slide out in 0.22 s.
5. **Captions**: words grouped into chunks (`max_words` 3, `max_chars` 18, break on punctuation or a pause over
   0.35 s; shown until 0.12 s after the last word, at least 0.35 s, never past the next chunk); each chunk is a
   PNG (Manrope 800, yellow `#ffe04b`, black outline 8 px at 66 px) overlaid at `caption_y`.
6. **Dings**: one `asplit` of the ding, each `adelay`ed and at `ding_volume`, `amix normalize=0 duration=first`.
7. **Main render**: libx264 crf 16, PCM audio, cut to the dialogue length.
8. **End card**: the format's `endcard.png`, `-loop 1 -framerate 30`, scaled to 2x and `zoompan` from 1.0 to
   1.035, white fade-in 0.18 s, a ding at 0.5.
9. **Final**: concat, `loudnorm=I=-14:TP=-1.5:LRA=11`, 48 kHz, libx264 medium crf 17 high profile yuv420p,
   AAC 192k, `+faststart`.
10. **With a music bed** (section 8) only the final step changes: `music.py` writes the placed, ducked and faded
    bed (`edit/work/<fmt>/music-bed.wav`, with its decisions in `music.json`), `amix` adds it under the concat,
    and a static gain plus a 4x oversampled peak limiter bring the mix to −14 LUFS instead of `loudnorm`. The
    video stream is bit-identical to the render without music.

## 7. Known traps

| Symptom | Cause | Fix (already in the scripts) |
| --- | --- | --- |
| captions and dings drift later and later (+0.34 s by the end) | each segment rounded its own length | lengths in whole frames, `-frames:v`, audio `apad,atrim` to the same length |
| 66 ms offset at every cut | first frame at 0.033 s after resampling 24 -> 30 fps | `fps=30:start_time=0` |
| end card 65 frames instead of 78 | a looped PNG defaults to 25 fps | `-loop 1 -framerate 30` |
| first syllable cut ("…onestly") | Whisper's word start 0.37 s late | envelope refinement |
| a line runs into room tone and the next breath | threshold below the room tone (agency take: room tone −30 to −28 dB, threshold was −33) | `speech.thr` −26; `inspect_take.py` prints the room tone and warns |
| captions with "absolutely no", lowercase "you", "2 a .m" | Whisper on the cut mix | caption words come from each take's own transcript + `captions.fixes` |
| invented UI on a phone screen (a precaution; not seen in the gym skit, where the owner showed the back of the phone) | video models draw pseudo text | keep screens away from the lens or under a banner; never rely on generated text |
| `ffmpeg` has no `drawtext` | build without libfreetype/libass | all text is drawn with Pillow and overlaid as PNG |
| a two-line banner sits too low | a fixed card height | the card grows 48 px per extra line (`brand.notification`) |
| music swells in every pause after `loudnorm` | `loudnorm`'s dynamic mode rides quiet passages up | the music mix gets one static gain (measured twice) and a peak limiter |
| a peaky track pushed the mix to −0.2 dBTP after AAC | white-noise hats, crest factor 17 dB | the bed goes through a 4x oversampled limiter at 12 dB above its loudness, the mix through one at −2 dBFS |
| the downbeat came 15 ms after the cut to the end card | the dialogue's audio runs a few ms past its last frame | the anchor is the segments' frame count / fps, the moment the picture cuts |

## 8. Music bed

Optional. `project.json` → `music`, copied into the EDL by `make_edl.py`; `assemble.py --no-music` leaves it out.

```json
"music": {"file": "music/bed.flac", "bpm": 100}
```

| Key | Default | Meaning |
| --- | --- | --- |
| `file` | required | the track, relative to the project (`gpu.py run music`, or a licensed library track) |
| `bpm` | required for an anchor | the tempo it was made at; the real tempo is searched within 3 % of it |
| `beats_per_bar` | `4` | as the track's time signature (ACE-Step `timesignature`) |
| `first_downbeat` | `"auto"` | seconds into the file of the first downbeat; `auto` finds it |
| `anchor` | `"endcard"` | where a downbeat lands: `endcard` (the cut to the card), `start`, a timeline second, or `null` |
| `offset` | none | seconds into the file where the bed starts; overrides `anchor` |
| `start` | `0` | timeline second where the bed comes in |
| `level_db` | `-9` | bed loudness against the dialogue's integrated loudness, between lines |
| `duck_db` | `-12` | extra level under speech (so −21 dB against the dialogue) |
| `attack`, `release` | `0.15`, `0.5` | the dip starts 0.15 s before a line and recovers over 0.5 s after it |
| `hold` | `0.6` | pauses shorter than this stay ducked, so the bed does not pump between words |
| `thr` | `speech.thr` | dB above which the cut dialogue counts as speech |
| `fade_in`, `fade_out` | `0.4`, `1.5` | at the bed's start and the end of the video |

What `music.py` does:

1. **Beat grid.** Spectral flux of the track (16 kHz, 5 ms steps) folded on a beat comb: the tempo within ±3 % of
   `bpm` (0.05 % then 0.005 % steps) and the phase with the strongest hits; the downbeat is the beat of the bar
   with the strongest average hit. `python3 $SK/scripts/music.py <file> --bpm 100` prints it: `tempo_bpm`,
   `first_downbeat`, `beat_clarity` (about 1: no beat; the test tracks 13–25), `downbeat_contrast`.
2. **Placement.** The bed starts `offset = first_downbeat + k·bar − (anchor − start)` seconds into the file,
   with the smallest `k` that keeps the offset ≥ 0, so a downbeat lands on the anchor. A track too short for the
   edit stops with the length it needs.
3. **Level.** The segment goes to −23 LUFS through a 4x oversampled lookahead limiter at −11 dBFS (12 dB above
   its loudness; `latency` compensated, so the beat does not move), then to the dialogue's loudness +
   `level_db`.
4. **Ducking.** Speech spans come from the cut dialogue's 10 ms envelope above `thr`, with pauses under `hold`
   filled. The gain is `duck_db` inside a span, ramps down over `attack` before it and back up over `release`
   after it. The edit is offline, so the dip anticipates the line, which a compressor cannot do; `sidechaincompress`
   was not used because its depth would follow the dialogue's level and it pumps between words.
5. **Fades and stem.** Fade in at `start`, fade out over the last `fade_out` seconds, exactly the timeline's
   length, 48 kHz 24-bit: `edit/work/<fmt>/music-bed.wav`; `music.json` next to it records the grid, the offset,
   the gains and the speech spans.

Measured on the gym skit with a synthetic 101.3 bpm track (`bpm` given as 100), 9:16 and 1:1:

| Check | Result |
| --- | --- |
| tempo and first downbeat on six test tracks (97.2–102.9 bpm, with 0–8 ms timing jitter) | tempo within 0.005 bpm, downbeat within 2.2 ms |
| downbeat against the first frame of the end card | −0.3 ms (a frame is 33.3 ms) |
| ducking depth on the track's pad tone, speech against the end card | −12.02 dB (set −12) |
| final loudness and true peak | −14.4 LUFS, −1.5 dBTP (without music −14.2 LUFS, −1.4 dBTP) |
| video stream against the render without music | bit-identical |
| render without `music`, and with `--no-music` | MD5 `095ffdca450db823b26fd76fa89a1204`, unchanged |

## Reuse typography and locked dialogue

Use `brand.font(size, weight)` and the existing caption/asset renderers in custom integrations. The bundled
variable Manrope defaults to weight 200 when opened directly with Pillow; omitting its weight produced thin,
hard-to-read subtitles in the Polish salon film. Render a representative long, accented caption at phone-sized
preview before the full export; check weight, clipping, face clearance and platform overlays. Do not regenerate
video to fix typography. Retain the earlier export, rerender the overlay, and recheck the delivered file.

For audio-first talk shots, the selected fitted WAV is the dialogue source of truth. Preserve its timing and
lead-in when replacing generated video audio; never mix both copies of the dialogue. Recheck final ASR,
complete word boundaries, loudness and visible lip sync after assembly. An ASR score or frame sheet alone is
not proof of perceived lip sync or voice naturalness.
