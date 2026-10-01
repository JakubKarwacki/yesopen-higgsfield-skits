---
name: yesopen-higgsfield-skits
description: Make short, funny YesOpen video skits for TikTok, Reels and Shorts with Higgsfield. Watch a reference video, take its comedy mechanics, write a skit where YesOpen is only the punchline, cast the characters with Soul 2, generate talking, lip-synced takes with Seedance 2.5 image-to-video, cut them with scripted ffmpeg (captions, YesOpen notification banners, end card) and deliver 9:16, 4:5, 1:1 and 16:9 files. Use this skill whenever the user shares a YouTube, TikTok or Instagram link and asks for "taką scenkę", "coś takiego dla YesOpen", a funny video, short, reel, skit, sketch, filmik or ad for YesOpen or for local business owners (gyms, restaurants, salons, shops), or wants to re-cut, reformat, continue or make a sequel to the gym breakup skit ("It's not you. It's your invoices."), even when Higgsfield is not named. Not for product demos, screen recordings or feature explainers.
---

# YesOpen skits with Higgsfield

This skill turns "make something like this for YesOpen" plus a link into a finished, funny vertical video and its
other formats. It was built from the first skit, "It's not you. It's your invoices." (2026-10-01): a gym owner
breaks up with his marketing agency, every "I don't know" is answered by a YesOpen notification on his phone,
and YesOpen only appears as the punchline and the end card. That skit is kept complete in `examples/gym-breakup/`
(script, every prompt and parameter, every request id, all takes with transcripts, the edit, QA and the finals)
and told step by step in `references/case-study-gym-breakup.md`. Read the case study before your first skit.

`SK` below is this skill's folder (for example `<localesto>/.agents/skills/yesopen-higgsfield-skits` or
`~/.agents/skills/yesopen-higgsfield-skits`). Talk to Marcin in Polish; the dialogue of the video is English
unless he asks otherwise.

## Non-negotiables

1. **A comedy skit, not a product presentation.** Marcin: "to nie jest prezentacja produktu". People share
   a joke, not a feature tour. The product is the reason for the laugh (a notification, one honest line), and
   the brand closes the video on the end card. If YesOpen could be cut out without losing a joke, it is an ad.
2. **No video credits before an explicit yes to the script.** Stills cost cents and may be made while the script
   is discussed; takes cost dollars and wait for approval.
3. **Only true claims.** Every product punchline must point to the product copy in
   `business-card/messages/en/*.json` (file and line), or come from Marcin. Unknown features stay out.
4. **Mechanics from the reference, never its content.** Reuse form, rhythm and editing. Never reuse its lines,
   names, characters or signature jokes. Its frames and transcript stay in the project's `reference/private/`:
   never commit, publish, upload or paste them, and never retell its dialogue, even in other words.
5. **Keys stay in the Keychain.** `scripts/hf-job` reads the Higgsfield key from the macOS Keychain (or `HF_KEY`)
   and never prints it. Never write a key into args, logs, scripts, commits, memory or chat. If a key is pasted
   into a chat, store it with `security add-generic-password -U -s higgsfield -a api-key -w` and tell the owner
   to rotate it in Higgsfield.
6. **No generated text on screen.** Banners, captions and the end card are drawn in the edit, so the text is
   exact and on brand. Take prompts always end with "no subtitles, no text on screen".
7. **Nothing is posted anywhere without an explicit request for that post.** Deliver files; links to the local
   files come first.

## What you need

| Need | Details |
| --- | --- |
| `ffmpeg`, `ffprobe` | 8.x; no `drawtext` or `libass` needed (all text is drawn with Pillow) |
| Python 3.11 | `pip install pillow numpy openai-whisper` (`large-v3-turbo` downloads on first use) |
| Higgsfield | an account with credit and an API key `<key-id>:<secret>` in the Keychain (service `higgsfield`, account `api-key`); `hf-job` finds or creates a venv with `higgsfield-client` |
| Ego Browser | for capturing the reference (global skill `ego-browser`) |
| Localesto checkout | optional: product copy for claims and the default project root; `LOCALESTO_ROOT` if it is not a parent folder |
| Manrope | bundled in `assets/brand/fonts/` (SIL OFL); `YESOPEN_FONT` overrides it |

Environment variables: `YESOPEN_SHORTS_ROOT` (where projects go; default `<localesto>/output/yesopen-shorts`,
else `./yesopen-shorts`), `LOCALESTO_ROOT`, `YESOPEN_FONT`, `HF_PYTHON`, `HF_KEY`.

Related global skills: `ego-browser` (capture), `higgsfield-generate` (model catalog and one-shot `hf-api`),
`higgsfield-soul-id` (a recurring character across many videos), `higgsfield-seedance` (Seedance API setup in code).

Quick check, free:

```bash
ffmpeg -version | head -1
python3 -c "import PIL, numpy, whisper; print('python ok')"
$SK/scripts/hf-job cost bytedance/seedance-2.5/image-to-video $SK/templates/args/take.json
security find-generic-password -s higgsfield -a api-key >/dev/null && echo "key ok"
```

## Project layout

```text
<root>/<date>-<slug>/
  project.json             cast, takes, speech threshold, caption style and fixes, banner texts, end card
  script.md                the script document (Polish), dialogue in the video's language
  reference/analysis.md    our analysis of the reference; reference/private/ is git-ignored
  args/                    every Soul and Seedance request body, one JSON per request
  stills/                  Soul candidates, sheets, picked.json, jobs.jsonl
  takes/                   Seedance takes, <take>.words.json, jobs.jsonl
  edit/cuts.json           the edit, one entry per shot
  edit/edl.json            generated by make_edl.py
  edit/assets/<fmt>/       banners, end card, caption sample per format; edit/assets/ding.wav
  edit/frames/             sheets for QA
  final/                   <name>-<fmt>.mp4 masters, -share.mp4, web/ copies and posters
```

Start one with `python3 $SK/scripts/new_project.py <slug> --title "<end-card line>"`.

## The workflow

Every phase ends with a gate from `references/qa-checklist.md`. A failed gate stops the next paid step.

### Phase 0: Start

1. Create the project (above). Put the link into `project.json` → `reference.url`.
2. If the brief is unclear only in ways that change the joke (who the audience is, the language, the length),
   ask once. Otherwise state your assumption and go.

### Phase 1: Reference (about 5 min)

Read `references/reference-analysis.md`.

```bash
$SK/scripts/capture-reference "<link>" reference/private
python3 $SK/scripts/contact_sheet.py reference/private/frames -o reference/private/sheet.jpg --cols 5 --per-sheet 10
```

Fill `reference/analysis.md` in your own words: form, beat structure, the engine of the joke, editing grammar,
what we take and what we do not. Gate 1.

### Phase 2: Script (about 10 min, then Marcin's yes)

Read `references/scriptwriting.md`. Build the joke in this order:

1. A frame everyone knows (breakup, intervention, job interview, therapy, parent-teacher meeting).
2. The business owner as the straight man; the old way of doing things (agency, nephew, sticky notes) as
   the other side.
3. An engine with a gap between what is said and what is seen, so the audience is ahead of a character.
4. Three or four escalation steps with the same shape, then a turn, one honest product line, a button.
5. The end-card line = the best line of the script.

Check every claim (`rg` in `business-card/messages/en`) and write the claims table. Write `script.md` from the
template. Present it in chat, in Polish and short: the idea in two sentences, the line table, what is borrowed
(mechanics only), the claims, open decisions each with a recommendation, the cost estimate
(`hf-job cost` for each planned take). Wait for an explicit yes, and record it in `script.md`. Gate 2.

### Phase 3: Cast (about 5 min, cents)

Read `references/casting-soul.md`. One `args/still-<character>.json` per character, from `templates/args/still.json`:
point of view, concrete looks, wardrobe without logos, the prop the joke needs, a plain local set, daylight,
eye contact with a neutral face and lips closed, mid-thigh framing, "No text, no logos, no watermark."
Parameters: `aspect_ratio` 9:16, `resolution` 1080p, `batch_size` 4, `enhance_prompt` false.

```bash
$SK/scripts/hf-job submit still-owner higgsfield-ai/soul/v2/standard args/still-owner.json stills
python3 $SK/scripts/contact_sheet.py stills/still-owner-*.png -o stills/sheet-owner.jpg --cols 4 --width 400 --label index
```

Run the characters in parallel. Reject logos, readable text, broad smiles, hidden props, small faces, chain-store
sets. Write the picks to `stills/picked.json` and `project.json` → `cast`. Reuse `assets/cast/` for returning
characters. Gate 3.

### Phase 4: Takes (about 10 min, dollars)

Read `references/takes-seedance.md`. One character per take, all their lines in order with "Pause" lines between
them, 20–30 s, from `templates/args/take.json`: "Single continuous handheld vertical smartphone shot, no cuts",
"stays in place", "talks directly into the camera lens as if to the person filming", the same voice description
in every take of that character, numbered lines each with a short physical direction, the silent jokes written as
actions, and the closing negatives (no music, no other people, no subtitles, no text on screen). Numbers as words.
Model `bytedance/seedance-2.5/image-to-video`, `resolution` 720p, `generate_audio` true.

```bash
$SK/scripts/hf-job cost bytedance/seedance-2.5/image-to-video args/take-owner-1-720p.json
$SK/scripts/hf-job submit take-owner-1-720p bytedance/seedance-2.5/image-to-video args/take-owner-1-720p.json takes
python3 $SK/scripts/inspect_take.py takes/take-owner-1-720p-0.mp4
```

Submit the takes as parallel background commands (three at once worked); each takes 4–9 minutes. If the balance
is unknown, send a 4 s 480p probe first. A job that fails within 5 s means a low balance: ask for a top-up, do not
loop. A content-safety block can be random: resubmit the same args once. If a terminal dies, `hf-job resume` the
`request_id` from `jobs.jsonl`; never pay twice. `inspect_take.py` writes the word timestamps and a frame sheet and
prints each line, the boundaries refined against the audio, and the room tone. Check every line, the lip sync, one
voice, no music or extra people, and the silent actions. Gate 4.

### Phase 5: Edit (about 15 min)

Read `references/edit-pipeline.md`. Fill `project.json` (`takes`, `captions.fixes`, `notifications`, `endcard`)
and write `edit/cuts.json` while looking at the sheets: per shot the take, the first and last word of the line,
`head`/`tail` (or `out`, or `fixed` for silent beats), an optional punch-in (`zoom`, `cy`), events (`ding`,
`banner`, `ding_at`, `cutaway`) and a `note` with the script line.

```bash
python3 $SK/scripts/build_assets.py . --sheet
python3 $SK/scripts/make_edl.py . --upto 10 --no-endcard -o edit/edl-preview.json
python3 $SK/scripts/assemble.py . --format 9:16 --edl edit/edl-preview.json --out edit/preview/part1.mp4
```

Show the preview (SendUserFile) when the pacing is new, adjust, then build the full edit:

```bash
python3 $SK/scripts/make_edl.py .
python3 $SK/scripts/assemble.py . --format 9:16
```

Rules of thumb from the first skit: 1–4 s per shot; punch-ins 1.10–1.45 on at most every third shot; `head` 0.6–0.85
to keep a look before a line; `tail` 1.0–1.35 when a silent joke follows; banner 0.02 s after its ding. Gate 5.

### Phase 6: Formats and QA (about 5 min)

Read `references/formats-delivery.md`.

```bash
python3 $SK/scripts/assemble.py . --format all
python3 $SK/scripts/qa_report.py . --format 9:16 --whisper
python3 $SK/scripts/qa_report.py . --format 4:5     # and 1:1, 16:9
```

Required: frames actual = planned, −14 ±1 LUFS, true peak ≤ −1.0 dBTP, Whisper word match about 1.0, and the
caption sheets checked (faces framed, captions and banners clear of faces). Watch the 9:16 once with sound. Gate 6.

### Phase 7: Delivery

```bash
python3 $SK/scripts/encode_variants.py final/<name>-9x16.mp4       # -share.mp4 (25 MiB) and web/ (15 MB) + poster
```

1. Reply with clickable links to the local files first: master, share copy, web copies.
2. Send the 9:16 web copy with SendUserFile so it plays on any device.
3. A shareable page only on request (a private claude.ai Artifact with the web mp4 and poster).
4. No posting to any platform without an explicit request. Gate 7.

### Phase 8: Wrap-up

- Add "Po produkcji" to `script.md`: what changed from the approved script, the final files, the QA numbers.
- Keep reusable material: cast stills to `assets/cast/` (with the Soul args), reaction shots to `assets/broll/`
  (`python3 $SK/scripts/extract_clip.py <take> <in> <dur> <out> --native`), new banners with
  `scripts/render_asset_library.py`.
- New lesson or fix? Update this skill and publish it (last section).

## Cost and time (list prices on 2026-10-01)

| Step | Price | Time | The first skit |
| --- | --- | --- | --- |
| Soul 2 batch of 4 stills, 1080p | $0.0228 ($0.0057 per image; $0.0032 in 720p) | 1.8–2.6 min | 5 batches, $0.11 |
| Seedance 2.5 take, per second | $0.2056 in 480p, $0.4622 in 720p, $1.1372 in 1080p | 4–9 min per 20–28 s take | 96 s in 720p and 22 s in 480p, $48.90 |
| 4 s 480p probe | $0.82 | a few minutes | refused (no credit), free |
| Edit, all formats, QA | local | about 15 min the first time; 35–56 s per format re-render | |
| Link to finished master | | 1 h 25 min, with 30 min waiting for a top-up | |

The first skit cost $49.01 at list price, which matches the account spend. The price per second depends on the
resolution, so a 1080p take costs about 2.5 times as much as the same take in 720p. `hf-job cost <model>
<args.json>` prints the estimate for any args file from its resolution, duration and batch size. The API
returns no cost and there is no balance endpoint.

## Scripts

| Script | What it does |
| --- | --- |
| `new_project.py` | new project folder from the templates |
| `capture-reference` (`capture_reference.mjs`) | Ego Browser: metadata, frames, transcript of a reference into `reference/private/` |
| `contact_sheet.py` | labelled grid of images or frames |
| `hf-job` (`hf_job.py`) | Higgsfield: `submit`, `resume`, `status`, `upload`, `cost`; checkpoints in `jobs.jsonl` |
| `inspect_take.py` | Whisper words, frame sheet, refined line times, room tone of a take |
| `build_assets.py` | ding, banners, end card, caption sample for each format |
| `make_edl.py` | `cuts.json` + transcripts -> `edl.json` (frame-exact segments, events, caption words) |
| `assemble.py` | renders one or all formats from the EDL |
| `qa_report.py` | frames, loudness, caption sheet, Whisper diff |
| `qa_sheet.py` | frame sheet of any video |
| `encode_variants.py` | share copy, web copy, poster |
| `extract_clip.py` | cut a B-roll clip from a take, in any format |
| `render_asset_library.py` | brand pack and the reusable banners, end cards and caption samples |
| `brand.py`, `media.py` | shared drawing (YesOpen look) and media helpers |

## References

| File | Read when |
| --- | --- |
| `references/case-study-gym-breakup.md` | before the first skit, and whenever you need a worked example of any step |
| `references/reference-analysis.md` | Phase 1 |
| `references/scriptwriting.md` | Phase 2: joke structure, verified claims, ideas for the next skits |
| `references/casting-soul.md` | Phase 3 |
| `references/takes-seedance.md` | Phase 4 |
| `references/higgsfield-api.md` | anything about the key, `hf-job`, models, parameters, prices, failures |
| `references/edit-pipeline.md` | Phase 5: every field of `project.json`, `cuts.json`, `edl.json`, the filters, known traps |
| `references/formats-delivery.md` | Phases 6–7 |
| `references/qa-checklist.md` | the gates |
| `references/asset-catalog.md` | logo, icon, fonts, banners, end cards, sound, cast, B-roll, product graphics |

## Lessons that cost time or money

- v1 copied the reference's premise and had no place for the product; the approved idea made the product the
  engine of the joke.
- 1080p takes failed on balance while 720p went through; 720p is enough for the 1080x1920 master.
- The first take request failed in 5 s for lack of credit; a 4 s probe would have shown it for under a dollar.
- Whisper's word times can be 0.4 s late; the edit refines every line against the audio, with a threshold above
  the take's room tone (−26 dB).
- Rounding each segment separately drifted captions by 0.34 s; lengths are whole frames now.
- Delivery detours cost 25 minutes and Marcin's patience: links to the files on disk come first.

## Updating this skill and the public repository

This folder is its own Git repository, published at https://github.com/behavio1/yesopen-higgsfield-skits
(public; Marcin shares it with colleagues). The parent Localesto repository excludes the folder locally
(`.git/info/exclude`).

1. Change the skill; run the scripts you touched on `examples/gym-breakup` (the 9:16 render must stay
   byte-identical unless you meant to change the edit).
2. Scan before every commit; all of these must print nothing:

   ```bash
   cd $SK
   git ls-files -co --exclude-standard | grep -E '(^|/)(\.env|.*\.pem|.*\.key)$|reference/private/'
   git ls-files -co --exclude-standard -z | xargs -0 grep -I -l -E '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:[0-9a-fA-F]{16,}|HF_KEY=[^"$ []|(sk|pk|rk)_(live|test)_[0-9A-Za-z]{8,}|gh[pousr]_[0-9A-Za-z]{20,}|postgres(ql)?://'
   K="$(security find-generic-password -s higgsfield -a api-key -w)"; git ls-files -co --exclude-standard -z | xargs -0 grep -I -l -F -e "${K#*:}"; unset K
   ```

3. Commit as `behavio1` and push:

   ```bash
   git -C $SK add -A
   git -C $SK commit -m "<what changed and why>"
   git -C $SK push
   ```

The remote is `git@github.com-behavio1:behavio1/yesopen-higgsfield-skits.git` (SSH alias for the behavio1 key).
Never push keys, a reference's frames or transcript, `edit/work/` or `.venv/`.
