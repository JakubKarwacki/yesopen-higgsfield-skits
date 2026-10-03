# Scriptwriting: humor first, YesOpen as the punchline

## Contents

1. What the owner asked for (and rejected)
2. Building the joke
3. Where YesOpen goes
4. Claims you may use (verified 2026-10-01)
5. Writing for the engines
6. The script document and the approval gate
7. Ideas for the next skits

## 1. What the owner asked for (and rejected)

These rules come from Marcin's feedback on the first skit (2026-10-01):

- **A comedy skit, not a product presentation.** Marcin said it as soon as he heard that product claims were
  being checked: "to nie jest prezentacja produktu", "nie zamknąć się w scenariuszu prezentacja
  funkcjonalności produktu". Viewers share a joke, not a feature tour.
- **A situation everyone knows, played by a local business.** The approved idea came from Marcin himself:
  the gym owner breaks up with his marketing agency; the agency asks "and who is going to …?" and he answers
  "I don't know". The script added the phone notifications that show YesOpen already did it.
- **Features only as punchlines.** Every feature lands as a visible payoff (a notification, a phone screen,
  a line like "It replies at 2 a.m.") right after a setup, never as an explanation.
- **YesOpen appears at the end.** The brand closes the video (end card), it does not open it.
- **The script is approved before any video credits are spent.** Stills are cheap; takes are not.

## 2. Building the joke

1. **Pick a frame everyone knows**: a breakup, an intervention, a job interview, a dating profile,
   couples therapy, a parent-teacher meeting, a heist. The reference video usually supplies it.
2. **Cast the business owner as the "normal" person** and give the opposing role to the old way of doing
   things (an agency, a nephew who "does the Instagram", a pile of sticky notes, a competitor).
3. **Find the engine**: a gap between what is said and what is seen. In the gym skit the owner says "I don't
   know" while the phone keeps proving he does. The audience is ahead of the agency, which is the fun.
4. **Escalate in steps of three or four.** Same question shape, bigger stakes each time (questions ->
   reviews -> Instagram -> top of Google Maps), and the denial gets less convincing each time
   ("I don't know…" -> "No idea." -> "Not a clue." -> "Honestly? Absolutely no idea.").
5. **Turn it.** The opponent notices ("Wait… are you seeing someone else?"), the owner gets caught,
   and admits it in the smallest possible words ("It's… just an app.").
6. **Give the product its one honest line** inside the joke ("It replies at 2 a.m. You reply in five
   business days.").
7. **End on a button**: an exit, a fake protest, then the real feeling ("What? Babe, no! Come back!" ->
   silent celebration -> "Hey, you." to the phone).
8. **End card line = the best line of the script** ("It's not you. It's your invoices."). If the line works
   without the video, it is the right one.

Length: 40–50 s of dialogue plus a 2.6 s end card. 20–22 lines, 1–2 s per shot.

## 3. Where YesOpen goes

- In **notification banners** added in the edit (exact text, real brand, no model-generated text).
- In **one honest line** of dialogue at most.
- On the **end card**: icon, wordmark, tagline, `yesopens.com`.
- Never in the opening line, never as a list, never with claims we cannot point to in the product copy.

## 4. Claims you may use (verified 2026-10-01)

Check every claim again in `business-card/messages/en/*.json` before a new script; the product copy changes.

| Punchline type | Source (business-card/messages/en, line numbers on 2026-10-01) |
| --- | --- |
| The assistant answers your questions | `nav.json:36` "I can reply to reviews, prepare a post and help improve your profile." |
| Replies to reviews | `marketing.json:240` "AI replies to every review, in your voice"; `:157` "We reply to every review in your voice…" |
| Works 24/7 ("It replies at 2 a.m.") | `marketing.json:227` "One plan. AI runs your Google profile 24/7 — replies to reviews, publishes posts, and keeps your ranking climbing." |
| Posts even while you are closed | `marketing.json:164` "AI writes posts and offers that sound like your business and publishes them on schedule — even while you’re closed." |
| Posts on Instagram and Facebook | `app.json:1239–1263` campaign publishing through Meta: "Connect Facebook and Instagram with one secure Meta login." |
| Google Maps position | `marketing.json` hero "Be the #1 business on Google Maps"; `:243` "Daily Google Maps ranking tracking"; `:130` "Track your ranking rise…" |

Not found on 2026-10-01, so not used: promotion in local articles or local news. If a feature is not in the
copy, leave it out or ask the owner first.

Commands:

```bash
cd <localesto>/business-card/messages/en
rg -n -i "review|reply|24/7|closed|instagram|facebook|ranking|#1|post" marketing.json app.json nav.json
```

## 5. Writing for the engines

Both engines:

- Lines under 12 words; numbers as words ("two a.m.", "five business days"), because the voice reads them.
- Put the visual jokes into the takes as silent actions (phone flip, cough, whistle, walk-out).
- Phones show their back to the camera: a screen facing the lens gets an invented app.
- On-screen text (banners, captions, end card) is never generated; it is added in the edit.

GPU engine (`gpu-engine.md`, section 6): one take per line, so every line is also one shot.

- Write the line table straight into `lines.json`: per line `text`, `exaggeration` (0.5 neutral, up to 0.85 for
  shouting), `acting`, and `action`, the one sentence the take prompt gets ("right after the line he clears his
  throat with a small cough and looks away").
- A silent joke after a line goes into that line's `action` plus a longer `tail` (1.3–2.6 s in the gym skit).
  A silent beat before a line: `silence_before` and a whole `prompt` for that take.
- Mark the lines that carry the joke in `key_shots`; they are the ones to listen to before the takes.
- `python3 $SK/scripts/gpu_batches.py estimate` gives the GPU minutes for the cost line of the script.

Higgsfield engine (`takes-seedance.md`):

- One character per take, all their lines in order, 20–30 s.
- Numbers as words in the prompt, the silent jokes as numbered actions between the lines.

## 6. The script document and the approval gate

Create the project with `scripts/new_project.py` and fill `script.md` from `templates/script.md`
(in Polish, dialogue in the video's language). Then present it in chat, in the user's language, short:

- the idea in two sentences;
- the full line table (who, line, acting/shot);
- what is borrowed from the reference (mechanics only) and what is ours;
- the claims table with sources;
- open decisions with a recommendation each (e.g. who the opponent is, the end-card line, how many questions);
- cost and time estimate for the takes (GPU: the GPU minutes and the session's hours at the machine's price;
  Higgsfield: `hf-job cost` per take).

Wait for an explicit yes; with the GPU engine it also covers starting the machine for the session. Changes to lines after approval go back to the owner if they change a joke or a claim.
Mark the approval in `script.md` (`Status: zaakceptowany przez … <date>`).

## 7. Ideas for the next skits (not produced yet)

Each keeps the same engine: a familiar frame, the owner as the straight man, YesOpen as the payoff.

- **The intervention.** Friends stage an intervention because the bakery owner answers reviews at 3 a.m.
  Twist: he doesn't anymore; the phone did it. Payoff: review-reply banners pop up during the intervention.
- **Job interview.** The owner interviews a "social media manager" candidate who asks for a 4-day week, a
  ring light and a budget; each answer is followed by a YesOpen banner doing the job. End: "We'll call you."
- **Couples therapy with the Google profile.** The owner and his neglected Google profile (a person in a
  "Google Maps pin" costume) at therapy; the profile complains nobody answers it.
- **The nephew.** "My nephew does our Instagram." Cut to the nephew asleep; the post is live anyway.
- **Parent-teacher meeting.** The teacher reports the restaurant's ranking "could try harder"; the owner shows
  the phone: "#1 for pizza near me".
- **Breakup, part 2.** The agency account manager comes back with a new offer; she is now the one
  with the phone (sequel with the same cast from `assets/cast/`).


## 8. Complete shot endings and continuity (required)

User feedback, 2026-10-03: clips feel cut off when only the starting frame and the action are described.
Define the ending before generating the starting still. For **each edit shot**, including silent beats,
write START, ACTION / DIALOGUE, END, HOLD and NEXT. A dialogue beat containing two speakers is two shots
unless it is explicitly staged as one continuous two-person shot.

END must be an observable result: not "gets up", but "stands fully upright beside the now empty chair,
holding the same cup in the same hand; movement has settled". Include pose, gaze, expression, framing,
hand/prop positions and off-screen state. HOLD is a deliberate settling/listening beat after the last word
and completed movement; plan its duration, allow enough generated footage, then choose the actual cut visually.
Do not shorten away the payoff to hit an estimated runtime. Time the recorded dialogue plus actions and
holds before committing to the final duration; report a conflict with an approved runtime.

For each NEXT link compare the outgoing state with the incoming state. A reverse shot changes viewpoint,
not elapsed action, prop hand, character position or wardrobe. Resume a recurring character in their last
established state, including movements explicitly performed off screen. Avoid crossing the dialogue axis.
Do not reset every shot to the original portrait. Same-view continuation may start with the accepted last
frame; reverse views require a matching reference in that angle. Keep references consistent in face,
wardrobe, lighting and set. Do not infer support for an end-frame parameter from the phrase "last frame".

Transfer the full shot contract into the actual generation prompt. GPU uses the existing `prompt` or
`action` fields; generation `tail` must cover post-speech action plus hold, while edit `cut.tail` / `out`
independently retains it. Inspect the resulting batch prompt before submission. For long Higgsfield takes,
apply an ending/listening state after each numbered line, not only to the last frame of the entire take.
No model-generated transitions, fades, captions or spontaneous new actions after the scripted ending.

Example: START seated, cup on the table. ACTION picks the cup up with the right hand, stands, steps beside
the chair. END upright, cup steady in right hand, chair completely clear. HOLD the settled state visibly.
NEXT a wide shot preserves that state. Reject a take ending with bent knees or a half-lifted cup.
