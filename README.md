# YesOpen skits with Higgsfield

An agent skill that turns "make something like this for YesOpen" plus a link to a short video into a finished,
funny skit, delivered in 9:16, 4:5, 1:1 and 16:9. Characters are cast with Higgsfield Soul 2, the talking,
lip-synced takes come from Seedance 2.5 image-to-video, and the edit (cuts, punch-ins, captions, YesOpen
notification banners, end card, loudness) is a scripted ffmpeg pipeline driven by one JSON file.

<p>
  <img src="examples/gym-breakup/final/web/its-not-you-its-your-invoices-9x16-poster.jpg" height="240" alt="9:16">
  <img src="examples/gym-breakup/final/web/its-not-you-its-your-invoices-4x5-poster.jpg" height="240" alt="4:5">
  <img src="examples/gym-breakup/final/web/its-not-you-its-your-invoices-16x9-poster.jpg" height="240" alt="16:9">
</p>

The first skit, **"It's not you. It's your invoices."**: a gym owner breaks up with his marketing agency, and
every "I don't know" is answered by a YesOpen notification on his phone.
[Watch the 9:16 version](examples/gym-breakup/final/web/its-not-you-its-your-invoices-9x16.mp4) ·
[4:5](examples/gym-breakup/final/web/its-not-you-its-your-invoices-4x5.mp4) ·
[1:1](examples/gym-breakup/final/web/its-not-you-its-your-invoices-1x1.mp4) ·
[16:9](examples/gym-breakup/final/web/its-not-you-its-your-invoices-16x9.mp4) ·
[how it was made](references/case-study-gym-breakup.md)

## Po polsku

Skill dla agenta (Claude Code, Codex i inne czytające `SKILL.md`), który robi śmieszne scenki wideo dla
YesOpen. Pokazujesz filmik, który ci się podoba, a agent wykonuje kolejne kroki:

1. Analizuje mechanikę wzoru.
2. Pisze scenariusz, w którym YesOpen jest tylko puentą, nie prezentacją produktu, i czeka na akceptację.
3. Generuje postacie i ujęcia z mową w Higgsfield.
4. Składa montaż w czterech formatach.

Wszystko z pierwszej scenki jest w `examples/gym-breakup/`: scenariusz, każdy prompt i parametr, identyfikatory
zleceń, ujęcia z transkrypcjami, montaż, QA i gotowe pliki. Opis krok po kroku znajdziesz w
`references/case-study-gym-breakup.md`. Instrukcja instalacji jest niżej. Potrzebny jest własny klucz Higgsfield
w Pęku kluczy.

## What is inside

```text
SKILL.md                 the workflow the agent follows: rules, phases 0–8, commands, gates, costs
references/              how-to for each phase, the Higgsfield API, the edit pipeline, QA, the full case study
scripts/                 project setup, reference capture, Higgsfield jobs, take inspection, edit, QA, delivery
templates/               project.json, cuts.json, script and analysis documents, request templates
assets/brand/            YesOpen icon (PNG, SVG), wordmarks and lockups, palette, Manrope font
assets/overlays/         ready notification banners, end cards and caption samples for all four formats
assets/sfx/              the notification ding
assets/cast/             the cast stills of the first skit with their Soul prompts, ready for sequels
assets/broll/            20 reaction shots cut from the first skit's takes
assets/graphics/         YesOpen product illustrations
assets/product-clips/    four short YesOpen product clips
examples/gym-breakup/    the complete first skit
agents/openai.yaml       display metadata for agents that read it
```

## Requirements

- macOS (the key is read from the Keychain; on Linux export `HF_KEY` instead).
- `ffmpeg` and `ffprobe` 8.x. No `drawtext` or `libass` is needed.
- Python 3.11 with `pip install pillow numpy openai-whisper`.
- A Higgsfield account with credit and an API key. `scripts/hf-job` creates its own virtualenv with
  `higgsfield-client` on first use.
- Ego Browser (Ego Lite) with its `ego-browser` command and agent skill, only to capture a reference video.
  Without it, watch the reference yourself and write the analysis by hand.

## Install

Clone into your Agent Skills folder (or a project's `.agents/skills/`):

```bash
git clone https://github.com/behavio1/yesopen-higgsfield-skits.git ~/.agents/skills/yesopen-higgsfield-skits
```

Store your Higgsfield key once. The command asks for the value and does not echo it:

```bash
security add-generic-password -U -s higgsfield -a api-key -w
```

Check the setup (free, nothing is sent):

```bash
SK=~/.agents/skills/yesopen-higgsfield-skits
python3 -c "import PIL, numpy, whisper; print('python ok')"
$SK/scripts/hf-job cost bytedance/seedance-2.5/image-to-video $SK/templates/args/take.json
```

## Use it

Ask your agent, for example:

> Zrób taką scenkę dla YesOpen dla właścicieli restauracji: https://youtube.com/shorts/…

The agent captures and analyses the reference, writes the script with a claims table and a cost estimate, and
waits for your yes before it spends money on video. Then it casts, generates, edits, checks and hands over the
files with local links.

By hand, the core commands are:

```bash
python3 $SK/scripts/new_project.py my-skit --title "The end-card line"
$SK/scripts/hf-job submit still-owner higgsfield-ai/soul/v2/standard args/still-owner.json stills
$SK/scripts/hf-job submit take-owner-1-720p bytedance/seedance-2.5/image-to-video args/take-owner-1-720p.json takes
python3 $SK/scripts/inspect_take.py takes/take-owner-1-720p-0.mp4
python3 $SK/scripts/make_edl.py .
python3 $SK/scripts/assemble.py . --format all
python3 $SK/scripts/qa_report.py . --format 9:16 --whisper
python3 $SK/scripts/encode_variants.py final/<name>-9x16.mp4
```

Every step, parameter and decision is explained in [SKILL.md](SKILL.md) and the [references](references/).

## Reproduce the example

```bash
cd $SK
python3 scripts/assemble.py examples/gym-breakup --format 9:16
md5 -q examples/gym-breakup/final/its-not-you-its-your-invoices-9x16.mp4    # 095ffdca450db823b26fd76fa89a1204
```

## The first skit in numbers

| | |
| --- | --- |
| Length | 73.5 s (70.9 s dialogue + 2.6 s end card), 21 lines, 21 cuts |
| Higgsfield | 5 Soul batches (20 stills), 5 Seedance 2.5 takes (118 s of video) |
| Cost | $49.01 at list price, matching the account spend |
| Time | 1 h 25 min from the link to the master, including 30 min waiting for a top-up |
| QA | frames as planned in all four formats, −14.2 LUFS, true peak −1.4 dBTP, captions match the audio word for word |

## What is not in this repository

- **No keys of any kind.** The Higgsfield key lives in each person's Keychain.
- **No material from the reference video.** Its frames and transcript belong to its authors and were kept
  local; the example keeps only the link and our own analysis.

## Rights

- The scripts and documents were written for YesOpen by Behavio.one with Claude Code. No open-source licence has
  been chosen yet, so ask before reusing them outside YesOpen.
- The YesOpen name, logo, icon, product illustrations, product clips and the example videos belong to YesOpen
  / Behavio.one. Use them for YesOpen content only.
- Manrope is licensed under the SIL Open Font License 1.1 (`assets/brand/fonts/OFL.txt`).
- The cast stills and takes were generated with Higgsfield (Soul 2, Seedance 2.5) under the account owner's
  Higgsfield terms.
