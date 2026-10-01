# Case study: "It's not you. It's your invoices." (the first skit, 2026-10-01)

The complete record of how the first YesOpen skit was made, from Marcin's link to the delivered files: what
was asked, what was decided and why, every prompt and parameter, every Higgsfield request, what the
takes actually said, every cut, every bug and its fix, the costs and the lessons. All project files are in
`examples/gym-breakup/`. Times are CEST (UTC+2), as logged in `jobs.jsonl`.

## Contents

1. Result in numbers
2. Timeline
3. The brief in Marcin's words
4. The reference and what we took from it
5. From the first draft to the approved script
6. The approved script
7. Product claims behind the punchlines
8. Casting with Soul 2
9. Takes with Seedance 2.5: the four prompts
10. Generation log: every request
11. What the takes said (Whisper) and the line boundaries
12. The edit: 21 cuts, banners, dings, captions, end card
13. QA: every bug found and its fix
14. Deliverables
15. Costs and time
16. Delivery: what went wrong
17. Lessons for the next skit

## 1. Result in numbers

| Item | Value |
| --- | --- |
| Length | 73.5 s: 70.93 s of dialogue (2128 frames) + 2.6 s end card (78 frames) = 2206 frames at 30 fps |
| Lines | 21 script lines, all kept; 21 cuts; 4 notification banners; 6 dings; 1 cutaway; 59 caption chunks (119 words) |
| Formats | 9:16 master 1080x1920; 4:5, 1:1, 16:9 rendered from the same edit |
| Loudness | −14.2 LUFS integrated, LRA 6.7 LU, true peak −1.4 dBTP (all four formats) |
| QA | frames planned = actual in every format; Whisper on the 9:16 master matches the captions word for word (1.0, no differences) |
| Higgsfield | 5 Soul batches (20 stills), 5 completed Seedance takes (118 s of video), 9 failed or refused requests |
| Cost | about $24.65 at list price (section 15) |
| Time | 1 h 25 min from the link (18:44) to the master (20:09), of which about 30 min was waiting for credits |
| Reproducible | re-rendering the example gives a byte-identical 9:16 master (MD5 `095ffdca450db823b26fd76fa89a1204`) |

## 2. Timeline

| Time | What happened |
| --- | --- |
| 18:44 | Marcin sends the Shorts link and the brief (section 3). |
| 18:45–18:51 | More steering while the agent works: YesOpen at the end; RapidAPI available for transcripts; use the Higgsfield skills; "first a script, then Higgsfield"; English is fine. |
| 18:47–18:49 | Ego Browser capture of the reference: 40 frames and the transcript from YouTube's own transcript panel. RapidAPI was not needed. The material stayed private (section 4). |
| 18:51 | Model check: Seedance 2.5 image-to-video with `generate_audio: true` gives voice and lip sync in one step. |
| 18:54 | Product claims checked in `business-card/messages/en`. |
| 18:55 | Marcin: a funny skit, not a product presentation. |
| 18:58 | First draft (v1) written to `script.md`; first Soul batches for its two characters (18:59). |
| 18:59–19:01 | Marcin proposes the agency breakup and the "who's going to …? / I don't know" engine, and asks to see the script before anything else. |
| 19:05–19:06 | v2 written and presented with four open decisions. |
| 19:07 | Marcin approves: "jest genialny". Defaults taken for the open decisions. |
| 19:08–19:13 | Soul: owner v2, agency v1, agency v2; picks made. |
| 19:14 | First take (owner 1, 1080p) fails after 5 s: credit balance too low. |
| 19:20 | Marcin sends a new test key; it goes straight into the Keychain. The retry fails after 5 s again. |
| 19:33 | "Teraz wal z tym nowym kluczem". 1080p fails again; owner 1 at 720p is accepted (done 19:38). |
| 19:39 | Owner 2, agency 1 and agency 2 at 720p fail after 5 s: balance. |
| 19:41 | Marcin is topping up. Meanwhile agency 1 at 480p is accepted (done 19:45). |
| 19:44 | "Dobra karta doładowana". |
| 19:46 | Agency 1, owner 2 and agency 2 at 720p submitted in parallel. |
| 19:47 | While waiting: banner layout fixed (a two-line text sat too low). |
| 19:50 | Agency 1 at 720p blocked by content safety after 3 min 55 s; resubmitted unchanged at 19:50:27. Agency 2 done. |
| 19:51 | Marcin: "Dobra to jak to idzie i podeślij mi link do działającego filmiku". |
| 19:53–19:54 | Preview of the first 28 s (agency 1 still at 480p) built, checked frame by frame and sent to chat. |
| 19:54 | Owner 2 and agency 1 at 720p done. Marcin asks for a private page with a shareable link. |
| 19:57 | Full cut planned: all 21 lines kept, the pauses become reaction shots. |
| 19:58–20:08 | Edit QA, bug by bug (section 13). |
| 20:09 | 9:16 master done. |
| 20:11–20:15 | Web copy (720p, 14 MB) and share copy (24 MB). |
| 20:11–20:20 | Detours: a file server, then WhatsApp; Marcin asks where the files on disk are (section 16). |
| 20:23 | Marcin asks for this skill. |

## 3. The brief in Marcin's words

Marcin dictates by voice, so the quotes keep the dictation errors: "jest open" is YesOpen, "Fix Field",
"hixfield" and "higsfield" are Higgsfield, "IS Open" is YesOpen, "cnot you is your in Voices" is
"It's not you. It's your invoices."

- 18:44, the request (link shortened to the video id):
  > https://youtube.com/shorts/NvKrK5S0yS4 Potrzebuję żebyś obejrzał ten filmik i zrobił właśnie taką scenkę
  > bardzo podobną tylko dla jest open dla właścicieli biznesów ale żeby była właśnie taka humorystyczna taka
  > fajna i niech na przykład reklamuje na koncu siłownię lokalną.

  *Watch this video and make a very similar skit for YesOpen, for business owners, humorous and fun, and let it
  advertise, say, a local gym at the end.*
- 18:45: "Chodzi o to żeby to było właśnie na końcu jest open" (*YesOpen goes at the end*).
- 18:50: "Tylko najpierw jakiś scenariusz tej scenki weź wybierz i potem zrób higsfield ai" (*first pick a
  script, then do Higgsfield*).
- 18:51: "…chodzi właśnie żeby to było takie humorystyczne śmieszne i skierowane do właścicieli siłowni"
  (*humorous, funny, aimed at gym owners*). And: "Możesz też zrobić po angielsku też jest okej".
- 18:55, the most important rule:
  > Pamiętaj że to ma być scenka śmieszna humorystyczna ona ma nie prezentować produktu O to nie jest
  > prezentacja produktu […] to jest po prostu zwykła humorystyczna scenka właśnie taka jak tutaj lekka
  > powiewna i przyjemna […]
  > Zrób jak uważasz ale pamiętaj żeby nie zamknąć się w scenariuszu prezentacja funkcjonalności produktu bo to
  > zupełnie nie o to chodzi

  *It is a funny, light skit like this one, not a product presentation; do not get locked into a
  feature-presentation script.*
- 18:59–19:01, the idea that became the skit:
  > Wydaje mi się że też dobry był ten scenariusz że właściciel siłowni zrywa z agencją marketingową […]
  > Mogłoby to być tak że […] Agencja marketingowa coś tam mówi A kto będzie ci odpowiadał na pytania a on o to
  > No nie wiem nie wiem i potem A kto będzie odpowiadał na rewiusy a nie wiem i tak dalej […]
  > te funkcje czyli pozycja na mapie odpowiedzi na opinię publikowanie postów w mediach społecznościowych
  > promocja w lokalnym w lokalnych artykułów […] Przedstaw mi tutaj ten scenariusz zanim go gdzieś dalej wyśle
  > […] cały czas zachowujemy takie humorystyczne fajne ujęcia jakie właśnie są w tym filmiku

  *The gym owner breaks up with his marketing agency; the agency asks "who will answer your questions?", he
  says "I don't know", "who will reply to reviews?", "no idea"… Weave in the features (Maps position, review
  replies, social posts, local articles). Show me the script before sending it anywhere; keep the fun shots of
  the reference.*
- 19:07, approval: "Ten scenariusz i cnot you is your in Voices jest genialny".

## 4. The reference and what we took from it

- **Video:** "How to breakup with your girlfriend #shorts", channel Content Machine,
  https://www.youtube.com/watch?v=NvKrK5S0yS4. 49 s, 10.2 M views, category Comedy, published 2025-10-10.
- **Captured** with `scripts/capture_reference.mjs` in Ego Browser: metadata, 40 frames (every 1.25 s), the
  transcript from the player's "Show transcript" panel. The material stayed on Marcin's Mac and is not in this
  repository: frames and dialogue belong to the channel. Only the link and our own analysis are kept
  (`examples/gym-breakup/reference/analysis.md`).
- **Taken (mechanics only):** two people speak straight into the lens in turn, so the viewer stands in for
  the other person; a cut on every line, 1–2 s per shot; punch-ins of about 1.25–1.45x on reactions; short
  silent reaction shots; yellow captions with a black outline, 2–4 words; a breakup played straight with
  exaggerated, reluctant faces; an ending where one side storms off and the other protests for show, then
  shows relief. The reference also places its sponsor only once, in passing, inside the joke.
- **Ours:** the situation, both characters, every line, the phone-notification payoffs, the product line,
  the end card. Two short exclamations of fake protest near the end echo the reference's ending.

## 5. From the first draft to the approved script

**v1, "How to break up with your gym" (18:58, never presented).** A regular breaks up with his local gym,
with YesOpen mentioned once in passing. It took the reference's premise (one partner leaving the other)
almost one to one and changed only the costume. Its two characters were cast in the first Soul batches
(`stills/still-owner-*`, `stills/still-member-*`). It had no engine of its own and no honest place for the
product, so the product could only be "mentioned".

**Marcin's idea (19:00).** The owner leaves his marketing agency. The old way of doing things becomes the
partner who is dumped, and the agency's job list becomes the escalation: "who's going to answer your
questions?" "I don't know."

**v2, what the agent added to the idea:**

- the gap between words and picture: every "I don't know" is followed by a YesOpen notification proving
  that it is already done, so the audience is ahead of the agency;
- denials that get less convincing each time ("I don't know…" -> "No idea." -> "Not a clue." ->
  "Honestly? Absolutely no idea."), with a silent physical joke after each (phone flip, cough, whistle,
  shake and a smile);
- the turn: the agency notices the phone ("Wait… are you seeing someone else?"), the owner gets caught and
  admits it in four words ("It's… just an app.");
- the one honest product line inside the joke: "It replies at 2 a.m. You reply in five business days.";
- the button: an exit, a fake protest, a silent celebration, and a whisper to the phone ("Hey, you.").

**Presented at 19:06 with four decisions:**

| Decision | Options given | Taken |
| --- | --- | --- |
| Who plays the agency | a woman in a blazer (closer to the reference, "Babe" sounds natural) or an "agency bro" in a vest with a laptop | the account manager in a blazer |
| End-card line | "The one that always replies.", "It's not you. It's your invoices.", "Every gym deserves a glow-up." | "It's not you. It's your invoices." (the line Marcin called "genialny") |
| Local articles | not found in the product copy or the designs, so left out; a fifth question offered if it exists | left out |
| Number of questions | three (faster) or four (shows more) | four |

## 6. The approved script

| # | Who | Line | Acting and shot |
| --- | --- | --- | --- |
| 1 | OWNER | Hey… I think we should break up. | serious, a little nervous |
| 2 | AGENCY | You're breaking up… with your marketing agency? | shock, punch-in |
| 3 | OWNER | It's not you. It's your invoices. | calm, sympathetic |
| 4 | AGENCY | …Wow. | offended, slow blink |
| 5 | AGENCY | Fine. But who's going to answer all your questions? | confidence back, a threat |
| 6 | OWNER | I don't know… | fake worry. DING, banner 1; flips the phone face down |
| 7 | AGENCY | Who's going to reply to your reviews? | |
| 8 | OWNER | No idea. | DING, banner 2; small cough |
| 9 | AGENCY | Who's going to post on your Instagram? | glances at his phone |
| 10 | OWNER | Not a clue. | DING, banner 3; whistles, looks away |
| 11 | AGENCY | Who's going to get you to the top of Google Maps? | her last card |
| 12 | OWNER | Honestly? Absolutely no idea. | DING DING, banner 4; the smile breaks through |
| 13 | AGENCY | Wait… are you seeing someone else? | squint, punch-in |
| 14 | OWNER | What? …What? No. | fake offended, tightest punch-in |
| 15 | AGENCY | Then who keeps texting you? | |
| 16 | OWNER | It's… just an app. | sheepish, shows the phone |
| 17 | AGENCY | You're leaving us… for an app?! | outrage, punch-in |
| 18 | OWNER | It replies at 2 a.m. You reply in five business days. | shrug, matter-of-fact |
| 19 | AGENCY | Fine. You'll come crawling back. Don't even think about calling me. | points, leans into the lens, walks out |
| 20 | OWNER | What? Babe, no! Come back! | fake despair |
| 21 | OWNER | (silence) | a beat, then joy: head back, arms wide. DING, he looks at the phone and whispers "Hey, you." |
| 22 | end card | YesOpen · It's not you. It's your invoices. · yesopens.com | 2.6 s |

The full script document, as approved, is `examples/gym-breakup/script.md`.

Banner texts as rendered (slightly reworded from the script table during the edit):

| Banner | Text (app "YesOpen", time "now") | Script feature |
| --- | --- | --- |
| notif-1 | Answered your question. Anything else? | the assistant answers questions |
| notif-2 | 12 new reviews answered | review replies |
| notif-3 | Your post is live on Instagram and Facebook | posts through Meta |
| notif-4 | You're #1 for "gym near me" | Google Maps position |

## 7. Product claims behind the punchlines

Every punchline points to product copy in `business-card/messages/en` (checked 2026-10-01; line numbers and
quotes in `scriptwriting.md`, section 4):

| Punchline | Source |
| --- | --- |
| "Answered your question. Anything else?" | `nav.json:36`, the agent: "I can reply to reviews, prepare a post and help improve your profile." |
| "12 new reviews answered" | `marketing.json:240` "AI replies to every review, in your voice" |
| "Your post is live on Instagram and Facebook" | `app.json:1239–1263`, campaign publishing through one Meta login |
| "You're #1 for 'gym near me'" | the hero "Be the #1 business on Google Maps"; `marketing.json:243` "Daily Google Maps ranking tracking" |
| "It replies at 2 a.m." | `marketing.json:227` "AI runs your Google profile 24/7"; `:164` "even while you're closed" |

Local articles: not found, not used. The number 12 and the ranking are illustrative, as in any ad.

## 8. Casting with Soul 2

Model `higgsfield-ai/soul/v2/standard`, `aspect_ratio` 9:16, `resolution` 1080p (output 1152x2048 PNG),
`batch_size` 4. The prompts are in `examples/gym-breakup/args/still-*.json`; the sheets are
`stills/sheet-*.jpg`, the final pair is `stills/cast.jpg`, and `stills/cmp-owner.jpg` compares owner v1 and v2.

| Batch | Request | Submitted -> done | Problem / result |
| --- | --- | --- | --- |
| still-owner (v1) | `67c2c98e-0352-4df5-bad0-902386bbd09c` | 18:59:20 -> 19:01:54 | all four smile broadly (the prompt said "a hint of a suppressed smile" and the enhancer was on), #2 has a logo on the sleeve; no phone |
| still-member (v1 cast) | `01ba9a19-2c0b-4413-9a95-37927656fa07` | 18:59:20 -> 19:01:54 | 3 of 4 tank tops with sportswear logos; #1 clean, kept as `assets/cast/gym-member.jpg`; never animated |
| still-owner-v2 | `3b8b8087-21cc-44ec-9b1e-8160feac4271` | 19:08:55 -> 19:10:43 | picked #3: neutral face, lips closed, phone in hand |
| still-agency (v1) | `466c7409-cc87-4448-b26a-f200833b7556` | 19:08:55 -> 19:10:43 | the "closed silver laptop" came out with apple-style logos |
| still-agency-v2 | `bf016617-19f2-471f-83a0-170f50e8d164` | 19:11:14 -> 19:13:33 | picked #1: plain black binder, plain desk, composed and a little smug |

Picked URLs (`stills/picked.json`; the PNG originals are `stills/still-owner-v2-3.png` and
`stills/still-agency-v2-1.png`):

- owner: `https://d3u0tzju9qaucj.cloudfront.net/1afd69d3-f0b3-4fa7-b234-55e0d71ae71d/74ee542d-c9ef-4096-8576-8b1ddcc56a47.png`
- agency: `https://d3u0tzju9qaucj.cloudfront.net/1afd69d3-f0b3-4fa7-b234-55e0d71ae71d/00cbe575-8127-4b6a-89a4-ca135f4d4cf9.png`

The owner v2 prompt (`enhance_prompt: false`):

```text
Vertical smartphone video still, point of view of a person standing in front of him. A fit gym owner in his
late 30s with a short dark beard and short dark hair, wearing a plain black fitted crew-neck t-shirt with no
logos and a grey towel over one shoulder, holding a smartphone loosely in one hand at waist height, stands in
his small independent neighborhood gym in front of a dumbbell rack. White-painted brick wall, a blank
whiteboard, slightly worn black rubber floor, a few older machines, warm natural daylight from big windows.
He looks straight into the camera lens, direct eye contact, calm neutral expression, lips closed, about to
say something awkward. Medium shot from mid-thigh up, eye level, realistic skin texture, candid, shot on
iPhone, shallow depth of field. No text, no logos, no watermark.
```

The agency v2 prompt (`enhance_prompt: false`):

```text
Vertical smartphone video still, point of view of a person standing in front of her. A confident marketing
agency account manager in her early 30s, sleek low ponytail, small gold hoop earrings, navy blazer over a
white top and tailored navy trousers, holding a thick plain black ring binder with no text under one arm and
an iced latte in a clear cup in the other hand, stands near the plain white front desk of a small independent
neighborhood gym. White-painted brick wall, a dumbbell rack softly out of focus behind her, slightly worn
black rubber floor, natural daylight, no signs, no posters. She looks straight into the camera lens, direct
eye contact, composed, slightly smug expression, lips closed. Medium shot from mid-thigh up, eye level,
realistic skin texture, candid, shot on iPhone, shallow depth of field. No text, no logos, no brand marks,
no watermark.
```

What changed from v1 to v2 and why: "a hint of a suppressed smile" -> "calm neutral expression, lips closed,
about to say something awkward" (a smile in the still stays in the whole take); "no logo" moved into the
wardrobe line; the phone added (the joke needs it in his hand from the first frame); the laptop replaced by
"a thick plain black ring binder with no text"; "plain white front desk", "no signs, no posters", "no brand
marks" added; `enhance_prompt: false` (the enhancer brought the smiles and logos back).

## 9. Takes with Seedance 2.5: the four prompts

Model `bytedance/seedance-2.5/image-to-video`, `generate_audio: true`. Each character speaks all their lines
in order in two long takes, with "Pause" lines that become the listening and reaction shots.

| Take | Script lines | `duration` | File | Picture, sound |
| --- | --- | --- | --- | --- |
| o1 `take-owner-1-720p` | 1, 3, 6, 8, 10 | 20 | 20.06 s | 720x1280, 24 fps, AAC 32 kHz |
| a1 `take-agency-1-720p` | 2, 4, 5, 7, 9 | 22 | 22.05 s | same |
| o2 `take-owner-2-720p` | 12, 14, 16, 18, 20, 21 | 28 | 28.04 s | same |
| a2 `take-agency-2-720p` | 11, 13, 15, 17, 19 | 26 | 26.05 s | same |

All four use `image_url` = the picked still of the character and `resolution` 720p. The same prompts exist at
1080p (`args/take-*.json`, all refused for balance) and at 480p (`args/take-*-480p.json`).

**o1, owner take 1** (`args/take-owner-1-720p.json`):

```text
Single continuous handheld vertical smartphone shot, no cuts, camera at eye level facing him, slight natural
handheld movement. The bearded gym owner from the image stays in place in his gym and talks directly into the
camera lens as if to the person filming him, with natural, understated comedic acting and accurate lip sync.
He speaks English in a calm, warm, slightly deep American male voice. In this exact order, with real pauses
where he silently listens:
1) Serious and a little nervous: "Hey... I think we should break up."
Pause, he listens and nods slightly.
2) Calm and sympathetic, tilting his head: "It's not you. It's your invoices."
Pause, he listens.
3) Faking worry with a shrug: "I don't know..." Then the phone in his hands lights up, he glances down at it
and quickly flips it face down against his chest, then looks back up innocently.
Pause.
4) "No idea." Then he clears his throat with a small cough and looks away innocently.
Pause.
5) "Not a clue." Then he glances at his phone, purses his lips and whistles quietly, looking to the side.
Only his voice and quiet gym room tone. No music, no background music, no other people, no subtitles, no
text on screen.
```

**a1, agency take 1** (`args/take-agency-1-720p.json`):

```text
Single continuous handheld vertical smartphone shot, no cuts, camera at eye level facing her, slight natural
handheld movement. The marketing agency account manager from the image (navy suit, black binder, iced latte)
stays in place near the gym's front desk and talks directly into the camera lens as if to the gym owner who is
filming her, with natural, expressive comedic acting and accurate lip sync. She speaks English in a crisp,
confident American female voice with a slightly sassy tone. In this exact order, with real pauses where she
silently listens:
1) Shocked, eyebrows up: "You're breaking up... with your marketing agency?"
Pause, she listens.
2) Offended, a slow blink: "...Wow."
Pause.
3) Regaining her confidence, chin up, a little threatening: "Fine. But who's going to answer all your
questions?"
Pause, she hears something and glances suspiciously down at his phone below the camera.
4) "Who's going to reply to your reviews?"
Pause, she glances down again, eyes narrowing.
5) "Who's going to post on your Instagram?"
Pause, she waits for his answer.
Only her voice and quiet gym room tone. No music, no background music, no other people, no subtitles, no
text on screen.
```

**o2, owner take 2** (`args/take-owner-2-720p.json`), same opening paragraph as o1, then:

```text
1) Trying hard and failing to hide a smile: "Honestly? Absolutely no idea." He glances at his phone and the
smile breaks through.
Pause.
2) Fake offended, leaning back: "What? ... What? No."
Pause.
3) Sheepish, he raises his phone and briefly shows the screen to the camera: "It's... just an app."
Pause.
4) Shrugging, matter-of-fact: "It replies at two a.m. You reply in five business days."
Pause.
5) Fake desperate, reaching one hand toward the camera: "What? Babe, no! Come back!"
6) A one-second beat, then he bursts into silent joyful celebration: throws his head back laughing, arms
spread wide, a fist pump. Then he looks down at his phone with a tender smile and whispers: "Hey, you."
Only his voice and quiet gym room tone. No music, no background music, no other people, no subtitles, no
text on screen.
```

**a2, agency take 2** (`args/take-agency-2-720p.json`), same opening paragraph as a1, then:

```text
1) Smug, playing her last card: "Who's going to get you to the top of Google Maps?"
Pause, her eyes dart down to his phone, then narrow.
2) Suspicious, slowly: "Wait... are you seeing someone else?"
Pause.
3) Accusing: "Then who keeps texting you?"
Pause.
4) Outraged, loud: "You're leaving us... for an app?!"
Pause.
5) Furious, she points her finger at the camera and leans in close: "Fine. You'll come crawling back. Don't
even think about calling me." Then she turns around and walks out of the frame.
Only her voice and quiet gym room tone. No music, no background music, no other people, no subtitles, no
text on screen.
```

Every planted silent action happened on screen: the phone flip, the cough, the whistle, the smile breaking
through, the phone shown to the camera, the lean-in with the pointed finger, the walk-out, the celebration
and the whisper. They are now reusable B-roll in `assets/broll/`.

## 10. Generation log: every request

From `examples/gym-breakup/takes/jobs.jsonl` (the Soul batches are in section 8).

| Label | Request | Submitted -> result | Outcome |
| --- | --- | --- | --- |
| take-owner-1 (1080p) | `84c6e69d-b745-487b-90cf-46b42e59c0e1` | 19:14:25 -> 19:14:30 | Failed: credit balance too low |
| take-owner-1 (1080p) | `fc5fc50c-c358-465b-9bf9-dc78f7ca2b4c` | 19:20:31 -> 19:20:36 | Failed: balance (new test key) |
| probe-owner-4s (480p, 4 s) | none | about 19:2x | submit refused `not_enough_credits` |
| take-owner-1 (1080p) | `5b88a7b5-6f92-4967-8b93-0c04e126986c` | 19:33:52 -> 19:33:57 | Failed: balance |
| take-agency-1 (1080p) | `78b80df4-81c3-4555-81e8-770ffbe7d08a` | 19:33:54 -> 19:33:59 | Failed: balance |
| take-owner-1-720p | `fb8823dd-8616-4eed-b7ac-1affa9efcc2f` | 19:34:20 -> 19:38:12 | completed (3 min 52 s) |
| take-owner-2-720p | `2cef0c39-c807-4711-b603-dc7faafcdb5c` | 19:39:11 -> 19:39:16 | Failed: balance |
| take-agency-1-720p | `ab807dd2-5711-4930-be84-18fe680ed2a8` | 19:39:12 -> 19:39:18 | Failed: balance |
| take-agency-2-720p | `faf203a8-3330-4671-91ab-715342457c6e` | 19:39:14 -> 19:39:20 | Failed: balance |
| take-agency-1-480p | `402016fe-0de4-4c5d-905e-80d17416729b` | 19:41:33 -> 19:45:43 | completed (4 min 10 s); used in the preview only |
| take-agency-1-720p | `be324560-fb82-4df4-9c65-d1012259be6a` | 19:46:05 -> 19:50:00 | Failed: "The generated result was blocked by content safety checks." |
| take-owner-2-720p | `7b2d1f2a-9111-4062-a2e6-108a0737e06f` | 19:46:07 -> 19:54:32 | completed (8 min 25 s) |
| take-agency-2-720p | `b09e5cde-bc80-40c5-a591-403bb24f6e9f` | 19:46:09 -> 19:50:40 | completed (4 min 31 s) |
| take-agency-1-720p (same args) | `aecaf313-a9ae-4925-a508-bdbbff75fc91` | 19:50:27 -> 19:54:27 | completed (4 min) |

Output URLs of the completed jobs are in the `urls` field of each line. The jobs were run with an earlier
version of `hf-job`; today's version also logs `args_file`, `seconds` and the failure reason.

## 11. What the takes said (Whisper) and the line boundaries

Whisper large-v3-turbo, word timestamps, take time in seconds (`takes/*.words.json`). Re-running
`inspect_take.py` on o1 on 2026-10-01 gave the identical word list in 17 s.

**o1:** 1.24–3.74 "Hey, I think we should break up." · 5.72–8.36 "It's not you, it's your invoices." ·
10.12–11.08 "I don't know." · 13.62–14.56 "No idea." · 16.70–17.64 "Not a clue."

**a1:** 1.32–4.46 "You're breaking up with your marketing agency?" · 6.48–7.16 "Wow." · 8.62–9.30 "Fine." ·
9.72–11.70 "But who's going to answer all your questions?" · 13.20–15.08 "Who's going to reply to your
reviews?" · 16.78–18.50 "Who's going to post on your Instagram?"

**o2:** 2.30–4.14 "Honestly, absolutely no idea." · 6.32–6.94 "What?" · 7.92–9.20 "What? No." ·
11.96–13.70 "It's just an app." · 14.44–17.60 "It replies at 2am, you reply in 5 business days." ·
17.88–19.84 "What? Babe, no, come back!" · 26.80–27.70 "Hey, you."

**a2:** 0.00–2.80 "Who's going to get you to the top of Google Maps?" · 5.36–7.86 "Wait, are you seeing
someone else?" · 9.40–11.16 "Then who keeps texting you?" · 11.98–14.78 "You're leaving us? For an app?" ·
16.92–17.62 "Fine." · 18.20–19.84 "You'll come crawling back." · 20.62–22.58 "Don't even think about calling
me."

The 480p agency take said the same lines with different timing (1.16–4.14 … 19.08–20.76).

Every word of the script came out; only punctuation, case and number formatting differed. Those became
caption fixes (`project.json`, `captions.fixes`):

| Take | Whisper token -> caption |
| --- | --- |
| o1 | `you,` -> `you.`, `it's` -> `It's` |
| o2 | `Honestly,` -> `Honestly?`, `absolutely` -> `Absolutely`, `come` -> `Come`, `2am,` -> `2 a.m.`, `you` -> `You`, `5` -> `five`, `no,` -> `no!` |
| a2 | `us?` -> `us...`, `For` -> `for`, `app?` -> `app?!` |

Room tone and boundaries from `inspect_take.py` (threshold −26 dB):

| Take | Room tone median / p90 | Boundaries the audio envelope moved |
| --- | --- | --- |
| o1 | −48.1 / −31.7 dB | "No idea." and "Not a clue." end 0.03–0.05 s later |
| a1 | −45.7 / −31.8 dB | "You're breaking up…" starts 0.05 s earlier; "…Instagram?" ends 0.18 s later |
| o2 | −47.3 / −34.2 dB | "Honestly" starts at 1.93, not 2.30 (Whisper was 0.37 s late and the cut clipped "Ho-"); "What? No." ends 0.21 s later |
| a2 | −45.1 / −37.7 dB | "Wait…" starts 0.25 s earlier |

## 12. The edit: 21 cuts, banners, dings, captions, end card

`examples/gym-breakup/edit/cuts.json` is the edit; `make_edl.py` turns it into `edit/edl.json`. Defaults:
`cy` 0.40, `speech.thr` −26 dB, `gap` 0.12 s, `reach` 0.8 s. Timeline at 30 fps; every length is whole frames.

| # | Take | In–out (take s) | Length | Starts at | Zoom / cy | Line and reason |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | o1 | 0.940–3.940 | 3.00 s / 90 f | 0.00 | – | "Hey… I think we should break up." head 0.3 for the opening |
| 2 | a1 | 1.170–4.803 | 3.63 / 109 | 3.00 | 1.25 / 0.33 | "You're breaking up…" shock punch-in |
| 3 | o1 | 5.570–8.670 | 3.10 / 93 | 6.63 | 1.10 / 0.38 | "It's not you. It's your invoices." slight push-in for the title line |
| 4 | a1 | 6.180–8.313 | 2.13 / 64 | 9.73 | 1.40 / 0.33 | "…Wow." tight, the pout held 1.15 s |
| 5 | a1 | 8.520–11.953 | 3.43 / 103 | 11.87 | – | "Fine. But who's going to answer…" |
| 6 | o1 | 10.000–12.433 | 2.43 / 73 | 15.30 | – | "I don't know…" ding + banner 1; tail 1.35 for the phone flip |
| 7 | a1 | 12.350–15.317 | 2.97 / 89 | 17.73 | – | "…reply to your reviews?" head 0.85 keeps her suspicious look |
| 8 | o1 | 13.470–15.603 | 2.13 / 64 | 20.70 | – | "No idea." ding + banner 2; the cough |
| 9 | a1 | 15.930–18.963 | 3.03 / 91 | 22.83 | – | "…post on your Instagram?" head 0.85 |
| 10 | o1 | 16.550–18.850 | 2.30 / 69 | 25.87 | – | "Not a clue." ding + banner 3; the whistle |
| 11 | a2 | 0.000–3.100 | 3.10 / 93 | 28.17 | 1.15 / 0.36 | "…top of Google Maps?" her last card |
| 12 | o2 | 1.830–5.530 | 3.70 / 111 | 31.27 | – | "Honestly? Absolutely no idea." two dings + banner 4 |
| 13 | a2 | 4.260–8.193 | 3.93 / 118 | 34.97 | 1.30 / 0.33 | "Wait… are you seeing someone else?" squint |
| 14 | o2 | 6.220–9.720 | 3.50 / 105 | 38.90 | 1.45 / 0.33 | "What? …What? No." the tightest punch-in |
| 15 | a2 | 9.300–11.467 | 2.17 / 65 | 42.40 | – | "Then who keeps texting you?" |
| 16 | o2 | 11.360–14.093 | 2.73 / 82 | 44.57 | – | "It's… just an app." head 0.6, shows the phone |
| 17 | a2 | 11.880–15.180 | 3.30 / 99 | 47.30 | 1.30 / 0.33 | "You're leaving us… for an app?!" outrage |
| 18 | o2 | 14.340–17.773 | 3.43 / 103 | 50.60 | – | "It replies at 2 a.m. …" |
| 19 | a2 | 16.820–25.287 | 8.47 / 254 | 54.03 | – | "Fine. You'll come crawling back…" runs to 25.3 for the lean-in and the walk-out |
| 20 | o2 | 17.770–20.903 | 3.13 / 94 | 62.50 | – | "What? Babe, no! Come back!" |
| 21 | o2 | 22.700–28.000 | 5.30 / 159 | 65.63 | – | silent celebration, then "Hey, you." (fixed span) |

Dialogue ends at 70.93 s (2128 frames). Then the end card, 2.6 s (78 frames).

Events on the timeline:

- **Banners** (slide in over 0.22 s from the top, hold, slide out): notif-1 at 16.60 s for 1.9 s, notif-2 at
  21.99 for 1.9, notif-3 at 27.177 for 2.1, notif-4 at 33.827 for 2.1.
- **Dings** (`ding_volume` 0.55): 16.58, 21.97, 27.157, 33.807 and 34.077 (the double ding on "Honestly"),
  68.483 (the phone before "Hey, you.", take time 25.55). The end card adds its own ding 0.5 s in.
- **Cutaway**: at 57.163 s, 0.6 s of the owner's face (o2 from 10.05 s, no zoom) over the agency's rant.
- **Captions**: 119 words in 59 chunks, at most 3 words or 18 characters, a new chunk after a pause over
  0.35 s; Manrope 800, yellow `#ffe04b`, black outline 8 px at 66 px, at 64.6% of the height in 9:16.
- **End card**: the YesOpen icon, the wordmark, "It's not you." / "It's your **invoices.**" ("invoices." in
  YesOpen blue `#0877ff`), `yesopens.com`; a white fade-in of 0.18 s and a slow zoom from 1.0 to 1.035.
- **Sound**: the takes' own voice and room tone, the ding, `loudnorm` to −14 LUFS. No music: the jokes live
  in the timing, and the take prompts asked for clean voice tracks.

## 13. QA: every bug found and its fix

In the order they were found; all fixes are built into today's scripts.

| Time | Symptom | Cause | Fix |
| --- | --- | --- | --- |
| 19:47 | a two-line banner text sat too low, against the bottom edge of the card | the card had a fixed height of 200 px | the card grows by 48 px per extra line and the text wraps by its measured width (`brand.notification`) |
| 19:58 | captions "absolutely no", lowercase "you", "2 a .m" | Whisper run on the cut mix | caption words come from each take's own transcript, plus `captions.fixes` |
| 20:00 | captions, dings and banners drift later and later, +0.34 s by the end | each segment rounded its own length up to a frame | lengths in whole frames, `-frames:v N`, audio `apad,atrim` to the same length |
| 20:02 | a 66 ms offset at every cut | 24 -> 30 fps resampling put the first frame at 0.033 s | `fps=30:start_time=0`; planned and actual timelines then matched to the frame |
| 20:05–20:07 | the first syllable of "Honestly" cut off | Whisper's word start 0.37 s late | refine every line against the audio envelope (10 ms RMS) |
| 20:07–20:08 | a line ran into room tone and a breath before "You're breaking up" | the first threshold (−33 dB) was below the agency take's room tone peaks | `speech.thr` −26 dB; `inspect_take.py` now prints the room tone and warns |
| 20:04 | end card 65 frames instead of 78 | a looped PNG defaults to 25 fps | `-loop 1 -framerate 30` |

Final checks of the master at 20:09: frames planned = actual, −14.2 LUFS, true peak −1.4 dBTP, captions
checked at every change of speaker on a sheet (`edit/frames/final_caption_starts.jpg`,
`edit/frames/final_checkpoints.jpg`).

When the skill's scripts were written afterwards, the whole edit was redone from `cuts.json` and compared:
the new EDL equals the original (`edit/original-scripts/edl-original.json`), the 9:16 overlays are
pixel-identical, the 9:16 master is byte-identical, and 4:5, 1:1 and 16:9 passed `qa_report.py`
(`edit/qa-summary.json`, sheets `edit/frames/qa-*-captions.jpg` and `edit/frames/checkpoints-*.jpg`).

## 14. Deliverables

| File | What it is |
| --- | --- |
| `final/its-not-you-its-your-invoices-9x16.mp4` | master: 1080x1920, 73.5 s, H.264 crf 17, AAC 192k, 58.9 MB |
| `final/its-not-you-its-your-invoices-9x16-share.mp4` | the same at 2450k two-pass, 24.1 MB (under 25 MiB for mail and chat) |
| `final/web/its-not-you-its-your-invoices-{9x16,4x5,1x1,16x9}.mp4` | web copies: shorter side 720, 1350k two-pass, about 13.6 MB each (under the 15 MB Artifact limit) |
| `final/web/*-poster.jpg` | a frame at 3.3 s for each format |

The 4:5, 1:1 and 16:9 masters are not stored; render them in about 40 s each:
`python3 scripts/assemble.py examples/gym-breakup --format all`.

## 15. Costs and time

| Item | Quantity | List price | Cost |
| --- | --- | --- | --- |
| Soul 2 stills | 5 batches x 4 = 20 images | about $0.0126 per image | about $0.25 |
| Seedance 2.5 takes, completed | 20 + 22 (480p) + 26 + 22 + 28 = 118 s | $0.2068 per second | about $24.40 |
| Requests refused for balance | 8 | not charged (they never ran) | $0 |
| The take blocked by content safety | 22 s | unknown: there is no balance endpoint to check | $0–4.55 |

Generation time: Soul 1.8–2.6 min per batch; takes 3.9–8.4 min, three in parallel. The edit, with all the
fixes in section 13, took about 16 minutes from the first preview (19:53) to the master (20:09). With today's scripts a re-render takes 35–56 s per
format.

## 16. Delivery: what went wrong

At 19:54 Marcin asked for a private page with a working link to share. Instead of first handing over the
files, the agent spent the next 25 minutes on side routes: a private page was started but not published,
then a file server (files.behavio.news) was investigated, then WhatsApp. Marcin, increasingly frustrated,
asked for "pliki na dysku, linki na dysku" (*the files on disk, links on disk*). At 20:24 he got three
clickable local links.

The rule now in `formats-delivery.md`: clickable local links to the master, share and web files come first,
in the first reply after the render. A preview in chat and a page to share come after that, and only through
the tools that exist for it.

## 17. Lessons for the next skit

1. **The engine is the product.** v2 works because the phone keeps contradicting the owner: the product is
   the reason for the laugh, not a mention. A script where YesOpen could be removed without losing a joke is
   an ad with a skit around it.
2. **Take the mechanics, not the premise.** v1 changed only the costume of the reference. Marcin's idea kept
   the mechanics (a breakup played straight, POV, quick alternation) on a new situation from the owner's life.
3. **Show the script before spending.** Stills are cents; takes are dollars. The approval took one message.
4. **Plant every visual joke in the take prompt.** Every planted action was acted where it was asked for.
   Pauses with a direction ("she glances suspiciously down at his phone") give usable reaction shots.
   Asked to show the screen, the owner showed the back of the phone: safer, as there is no generated UI to check.
5. **Same voice, same take.** Each character's lines in one or two long takes kept one voice per character.
6. **Check the balance with a cheap probe first.** A 4 s 480p probe (`args/probe-owner-4s.json`, about $0.83)
   tells you whether the key has credit and what the voice sounds like. Refused jobs are free; ask for a top-up
   rather than retrying.
7. **720p is enough.** The edit scales to 1080x1920 with lanczos; 1080p takes cost more and failed first.
8. **A content-safety block can be random.** The same args passed on the retry. Resubmit once, then soften
   the wording.
9. **Estimate the length from the takes, not from the script.** 21 lines with reactions became 70.9 s, not
   the planned 45 s. For a hard limit, cut lines in the script.
10. **Captions from each take, fixed by hand.** The per-take transcript plus `captions.fixes` gave a word
    match of 1.0 on the final master.
11. **Trust the audio over Whisper's word times.** Envelope refinement and a threshold above the room tone
    keep first syllables and drop breaths.
12. **Everything is data.** Because the edit is `cuts.json`, a fix is one number and a re-run, the result is
    byte-identical, and every format comes from the same edit.
13. **Local links first.** Hand over the files on disk before anything else (section 16).
