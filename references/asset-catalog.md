# Asset catalog

Everything under `assets/` can be reused in new skits. Brand material (logo, icon, product illustrations,
product clips) belongs to YesOpen / Behavio.one: use it for YesOpen content only. Manrope is under the SIL Open
Font License (`assets/brand/fonts/OFL.txt`).

## `assets/brand/`

| File | What it is |
| --- | --- |
| `yesopen-icon-512.png` | app icon: white rounded square with the blue gradient "Y" (from `business-card/public/icons/icon-512.png`) |
| `yesopen-icon-maskable-512.png` | maskable variant (safe zone padding) |
| `yesopen-icon-rounded-1024.png` | the icon at 1024 px with rounded corners, transparent outside |
| `yesopen-icon.svg` | vector "Y" mark, gradient `#0050C1 -> #0064F1 -> #99C1F9`, with a dark-mode variant (from `business-card/app/icon.svg`) |
| `yesopen-wordmark-on-light.png` / `-on-dark.png` | "YesOpen" wordmark, Manrope 500, tracking −0.05 em; "Yes" ink `#0f172a` (white on dark) + "Open" blue `#0877ff` |
| `yesopen-lockup-horizontal-on-light.png` / `-on-dark.png` | icon + wordmark side by side |
| `yesopen-lockup-stacked-on-light.png` / `-on-dark.png` | icon above the wordmark |
| `palette.json` | ink, blue, muted, caption yellow, icon gradient, font notes |
| `fonts/Manrope-Variable.ttf`, `fonts/OFL.txt` | Manrope variable (wght 200–800), Latin + Latin Extended (Polish and German letters) |

Re-render the PNGs with `python3 scripts/brand.py --render-brand-pack` (or `render_asset_library.py`).
The wordmark matches `business-card/components/marketing/common/Logo.tsx` ("Yes" + `<span class="text-[#0877ff]">Open</span>`, `font-medium`, `tracking-[-0.05em]`).

## `assets/overlays/`

| Folder | Files | Notes |
| --- | --- | --- |
| `notifications/` | `notif-question-answered`, `notif-reviews-answered`, `notif-review-reply`, `notif-post-live-meta`, `notif-google-post`, `notif-rank-gym`, `notif-ranking-up` (PNG, 1040 px wide, 9:16 scale) | iOS-style YesOpen banners; every text is a verified claim (see `render_asset_library.py`). For a project, put the texts in `project.json` and let `build_assets.py` render them per format. |
| `endcards/` | `endcard-its-your-invoices-<fmt>.png`, `endcard-be-number-one-<fmt>.png` for 9x16, 4x5, 1x1, 16x9 | "Be the #1 business on Google Maps." is the site's hero line, a safe default tagline |
| `captions/` | `caption-sample-<fmt>.png` | caption style per format (Manrope 800, yellow, black outline) |

## `assets/sfx/`

- `ding.wav`: the two-tone notification sound (E6 then B6, soft decay, 0.9 s, 48 kHz stereo). Made with
  ffmpeg `aevalsrc`; the expression is in `scripts/build_assets.py` (`DING_EXPR`).

## `assets/cast/`

Full-size Soul 2 stills (1152x2048, JPG q92) with the exact Soul args next to each (`*.soul-args.json`).
Use them as `image_url` to bring a character back.

| File | Character | Used in |
| --- | --- | --- |
| `gym-owner.jpg` | gym owner, late 30s, short beard, black tee, grey towel, phone in hand, small gym | the first skit (takes o1, o2) |
| `agency-manager.jpg` | marketing agency account manager, early 30s, navy suit, black binder, iced latte, gym front desk | the first skit (takes a1, a2) |
| `gym-member.jpg` | gym regular, mid 20s, stringer tank, backwards cap, headphones, shaker | cast for the rejected v1, never animated |

## `assets/broll/`

Silent or short reaction shots cut from the first skit's takes (720x1280, 30 fps, H.264 crf 20, AAC 128k).
Cut more with `scripts/extract_clip.py <take> <in> <dur> <out> --native`.

| File | Take, in–out (s) | Content |
| --- | --- | --- |
| `owner-listening.mp4` | o1 4.0–6.0 | listens, slightly worried, silent |
| `owner-phone-flip.mp4` | o1 11.2–14.0 | phone lights up blue, he looks down and presses it to his chest |
| `owner-cough-look-away.mp4` | o1 14.7–16.9 | small cough, looks to the side innocently |
| `owner-whistle.mp4` | o1 17.8–20.05 | glances at the phone, whistles, looks away |
| `owner-smirk.mp4` | o2 0.0–1.85 | can't hide a smile, silent |
| `owner-shows-phone.mp4` | o2 11.2–13.8 | lifts the phone, says "It's… just an app" |
| `owner-babe-no.mp4` | o2 17.7–20.0 | reaches to the camera, "What? Babe, no! Come back!" |
| `owner-fake-sad.mp4` | o2 20.0–22.6 | fake-sad face turning into a grin, silent |
| `owner-celebration.mp4` | o2 22.8–26.0 | head back laughing, arms wide, fists up |
| `owner-hey-you.mp4` | o2 25.9–28.0 | looks at the phone, smiles, "Hey, you." |
| `agency-shocked.mp4` | a1 4.6–6.8 | wide-eyed shock, silent |
| `agency-wow-pout.mp4` | a1 6.7–8.9 | "Wow." and a big pout |
| `agency-glances-at-phone.mp4` | a1 11.7–13.6 | suspicious glance down at his phone, silent |
| `agency-eye-roll.mp4` | a1 15.3–17.2 | closes her eyes, unimpressed, silent |
| `agency-waiting.mp4` | a1 19.6–22.0 | stands with the binder and latte, waiting, silent |
| `agency-unimpressed.mp4` | a2 2.9–5.0 | unimpressed look, silent |
| `agency-squint.mp4` | a2 7.9–9.9 | suspicious squint, silent |
| `agency-point-lean-in.mp4` | a2 17.2–22.7 | "Fine. You'll come crawling back…", points and leans into the lens |
| `agency-walk-out.mp4` | a2 22.7–25.0 | turns and walks out of frame |
| `empty-gym.mp4` | a2 24.9–26.0 | the empty front desk after she left |

## `assets/graphics/`

YesOpen product illustrations copied from `business-card/public/product-visuals/` (3D clay style, mostly
1254x1254 PNG/WebP with transparency): `modules/` (agent adviser, audit, campaigns megaphone, details, health,
map position, reviews, subscription, activity), `account/` (blog, businesses, settings, social channels),
`reviews/monitoring/` (notification envelope, reviewer, care checklist, YesOpen adviser), `reviews/tones/`,
`chat-starters/`, `profile-information/`, `status/`, `states/`, `nav/`, `newsletter/`, `ui/`.
Use them for end cards, thumbnails or a phone-screen insert.

## `assets/product-clips/`

Four 5 s product clips from `business-card/public/videos/` (1280x720): `content-campaigns.mp4`,
`customer-welcome.mp4`, `profile-optimization.mp4`, `reviews-autopilot.mp4`. Good for 16:9 cutaways or a
"what the app did" insert.

## The full example project

`examples/gym-breakup/` is the complete first skit: script, args, all Soul candidates, the four takes with
word timestamps and job logs, `cuts.json`, `edl.json`, the overlays per format, QA sheets, the original edit
scripts, and the finals (9:16 master and share copy, web copies of all four formats with posters).
