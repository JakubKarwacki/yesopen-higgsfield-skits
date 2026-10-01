# Reference analysis: watch a short and take its mechanics

The user usually starts with a link: "zrób coś takiego dla YesOpen". The goal of this phase is to understand
why the reference works (form, engine, rhythm) so the YesOpen skit can reuse the mechanics with its own
situation, characters and lines.

## Rules

- **Mechanics, not content.** Reuse form, structure, pacing and editing grammar. Never reuse the reference's
  lines, names, characters or signature jokes. Describe the reference in your own words.
- **Private material stays private.** Frames, transcript and metadata go to `<project>/reference/private/`,
  which `new_project.py` git-ignores. Never commit, publish, attach or upload them anywhere, and never paste
  the reference's transcript into chat or documents; summarise it instead.
- **Link, not copy.** `project.json` and `reference/analysis.md` keep only the URL, the factual metadata
  (title, channel, length, views, date) and our analysis.

## Capture (Ego Browser)

```bash
$SK/scripts/capture-reference "https://www.youtube.com/watch?v=<id>" reference/private   # [--step 1.25] [--start 0.2] [--space ID]
```

`capture-reference` writes the parameters into the script text (`const REF = {...};` followed by
`capture_reference.mjs`) and pipes it to `ego-browser nodejs`: Ego's embedded Node runtime does not see the
shell's environment variables and runs with the working directory `/`, so environment variables and relative
paths do not reach it.

What the script does (all inside one Ego TaskSpace, which it finishes at the end):

1. Focus emulation and an "active" lifecycle state, so the background tab decodes video.
2. A page script that mutes every `<video>` before it plays (no sound on the user's speakers).
3. Opens the watch page (Shorts URLs are rewritten to `watch?v=`).
4. Reads `window.ytInitialPlayerResponse`: title, channel, length, views, keywords, description, publish date,
   category, caption tracks -> `metadata.json`.
5. Waits out a pre-roll ad (clicks "Skip" when it appears).
6. Frames: for t = 0.2 s, then every `--step` (1.25 s): `seekTo(t)`, wait for `seeked` and `readyState >= 2`,
   two animation frames, draw the `<video>` to a canvas, save `frames/f_<centiseconds>.jpg`. The first gym
   reference switched from 360x640 to 480x854 mid-video; that is normal.
7. Transcript: expands the description and clicks "Show transcript", reads the segments; if there is no panel,
   turns captions on and scrapes `.ytp-caption-segment` every 0.5 s. (The direct `timedtext` URL returned an
   empty body, so it is not used.)

Then look at it:

```bash
python3 $SK/scripts/contact_sheet.py reference/private/frames -o reference/private/sheet.jpg --cols 5 --per-sheet 10
```

Read the sheets (5x2 frames each, labelled with seconds) next to the transcript.

## What to write down (`templates/analysis.md`)

1. **Form.** Who talks to whom, where the camera is, how many characters and places, average shot length.
2. **Beat map.** One row per beat, our own words, with its function: hook, setup, escalation, turn, button.
3. **Engine.** Why people laugh: the gap between words and picture, escalation, role reversal,
   repetition with variation, a callback.
4. **Editing grammar.** Cut rhythm, punch-ins (how strong, on what), reaction shots, captions (colour,
   outline, words per chunk, position), sound (music, effects, silence as a beat), the ending.
5. **Transplant plan.** Which mechanics go into the YesOpen skit, our situation and cast, where each
   product payoff lands.
6. **Not taken.** The reference's own lines, names, characters and signature jokes.

## Worked example: the gym skit's reference

- **Video:** "How to breakup with your girlfriend #shorts", channel Content Machine,
  https://www.youtube.com/watch?v=NvKrK5S0yS4 (49 s, 10.2 M views, Comedy, published 2025-10-10).
- **Form we saw:** a two-person conversation filmed as POV: each person speaks straight into the lens, the
  edit alternates them every 1–2 s, so the viewer stands in for the other person.
- **Engine we took:** a breakup played straight, with exaggerated, reluctant reactions; the comedy sits in the
  faces and the timing more than in the words.
- **Editing grammar we took:** hard cuts on every line, punch-ins of roughly 1.25–1.45x on reactions, short
  reaction shots between lines, yellow captions with a black outline, 2–4 words per chunk; an ending where
  one side storms off, the other protests for show and then shows relief.
- **What became ours:** the situation (a gym owner leaving his marketing agency) and the escalating
  "who's going to …?" questions met with "I don't know" (both Marcin's idea), the phone notifications that
  keep proving him wrong, both characters, every line, the product payoffs and the end card. Two short exclamations of fake protest at the end echo the reference's ending;
  everything else is new.
- **First draft lesson:** v1 kept the reference's premise almost one to one (a gym member dumping his gym)
  and had no honest place for the product; Marcin's agency idea replaced it before it was shown. See
  `case-study-gym-breakup.md`, section 5.
