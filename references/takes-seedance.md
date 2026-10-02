# Takes: dialogue with Seedance 2.5 image-to-video

A take is one continuous Seedance clip in which one character says several script lines to the camera,
with pauses in between. The edit later interleaves the takes into a conversation.

This page is for `"engine": "higgsfield"`. The GPU engine records every line first and makes one take per line
to that sound (`gpu-engine.md`, section 6); the rules on silent jokes, phones and on-screen text below hold for it
too.

## Why long takes per character

- **Voice consistency.** Seedance invents the voice in each generation. One 20–28 s take carries one voice;
  ten 3 s clips would carry ten slightly different voices.
- **Free reaction shots.** The pauses where the character "listens" become reaction shots and cutaways.
- **Cost.** One 22 s take costs the same per second as short clips but needs one prompt and one QA pass.

Split a character's lines over two takes when they do not fit into 30 s (the maximum) or when the acting
changes a lot (calm denials vs. a big celebration). The gym skit used 2 takes per character:

| Take | Lines (script #) | Duration asked | Resolution | Generation time |
| --- | --- | --- | --- | --- |
| owner 1 | 1, 3, 6, 8, 10 | 20 s | 720p | 3.9 min |
| agency 1 | 2, 4, 5, 7, 9 | 22 s | 720p (a 480p copy too) | 4.0 min (4.2 min at 480p) |
| owner 2 | 12, 14, 16, 18, 20, 21 | 28 s | 720p | 8.4 min |
| agency 2 | 11, 13, 15, 17, 19 | 26 s | 720p | 4.5 min |

## Sizing the duration

Per line: about 0.35 s per spoken word + 0.5 s, then 1.5–2.5 s of pause (listening) after it. Add 1 s at
the start and 1–2 s at the end. Silent actions (a celebration, walking out) need 3–5 s of their own.
Over-asking a little is fine: the edit cuts. Under-asking makes the model rush and swallow lines.

## The prompt

Template (also in `templates/args/take.json`):

```text
Single continuous handheld vertical smartphone shot, no cuts, camera at eye level facing him, slight natural
handheld movement. The <who, as in the still> from the image stays in place in his <place> and talks directly
into the camera lens as if to the person filming him, with natural, understated comedic acting and accurate
lip sync. He speaks English in a <voice>. In this exact order, with real pauses where he silently listens:
1) <Acting direction>: "<Line.>" <Optional silent action.>
Pause, he listens.
2) <Acting direction>: "<Line.>"
Pause.
…
Only his voice and quiet <place> room tone. No music, no background music, no other people, no subtitles,
no text on screen.
```

What each piece does:

- **"Single continuous … no cuts"** stops the model from inventing its own edit.
- **"stays in place"** keeps the framing stable for crops in other formats. Leave it out only when the
  character must move (the agency walking out was written as an action inside the line).
- **"as if to the person filming him"** gives POV eye contact; the other character "is" the camera.
- **Voice description, same in every take of that character.** Owner: "calm, warm, slightly deep American
  male voice". Agency: "crisp, confident American female voice with a slightly sassy tone".
- **Numbered lines, each with an acting direction before the quote.** Directions are short and physical:
  "Shocked, eyebrows up", "Offended, a slow blink", "Fake offended, leaning back", "Shrugging, matter-of-fact".
- **Silent business after the quote** plants the visual jokes: "the phone in his hands lights up, he glances down
  at it and quickly flips it face down against his chest, then looks back up innocently", "clears his throat with
  a small cough and looks away innocently", "purses his lips and whistles quietly, looking to the side",
  "points her finger at the camera and leans in close … then she turns around and walks out of the frame".
- **"Pause." lines** create the listening gaps. "Pause, she hears something and glances suspiciously down at
  his phone below the camera" makes the pause act.
- **The closing negatives** ("No music … no subtitles, no text on screen") keep the audio clean for the edit
  (dings and loudness are added later) and keep the picture free of fake captions.

Writing lines for the model:

- Write numbers and times as words in the prompt ("two a.m.", "five business days"). Captions can show
  digits later through `captions.fixes` ("2am," became "2 a.m.").
- Ellipses make real hesitations ("Hey... I think we should break up.", "It's... just an app.").
- Keep each line under about 12 words. Long sentences lose lip sync.
- Expect small changes. The model said "Honestly, absolutely no idea" for "Honestly? Absolutely no idea."
  and "You're leaving us? For an app?" for "You're leaving us... for an app?!". Fix punctuation in captions,
  regenerate only if a word is wrong.

## Generating

```bash
SK=<skill folder>
$SK/scripts/hf-job cost bytedance/seedance-2.5/image-to-video args/take-owner-1-720p.json
$SK/scripts/hf-job submit take-owner-1-720p bytedance/seedance-2.5/image-to-video args/take-owner-1-720p.json takes
```

Run the takes in parallel (three at once worked) as background commands. Each lands as
`takes/<label>-0.mp4`. Probe a new character or voice first with a 4 s, 480p job (`args/probe-owner-4s.json`
in the example) when the cost of a full take is a concern.

## Checking a take

```bash
python3 $SK/scripts/inspect_take.py takes/take-owner-1-720p-0.mp4
```

This writes `takes/<take>.words.json` (Whisper large-v3-turbo, word timestamps) and
`edit/frames/<take>_sheet.jpg` (a frame every 0.5 s), and prints each line with Whisper's times and the
times refined against the audio, plus the room tone. Check:

- every scripted line is there, in order, with the right words (compare with the script table);
- lip sync holds on every line (look at the sheet around each line);
- one voice per character, no music, no second person, no on-screen text;
- the silent business happened (phone flip, cough, whistle, walk-out) where the joke needs it;
- the take did not end mid-word.

Regenerate only a take that fails. A missing silent action can often be covered in the edit with a cutaway
or a banner instead of paying for a new take.
