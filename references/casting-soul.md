# Casting: start stills with Soul 2

Every character starts as one still image. Seedance animates that exact picture, so the still decides the
face, the wardrobe, the set, the light and whether a stray logo appears in every second of the video.

This page is for `"engine": "higgsfield"`. The GPU engine animates its still the same way, so the prompt parts
below hold for it too: write them into `lines.json` → `characters.<name>.look`, open with the framing, and run
them through `gpu_batches.py stills` (`gpu-engine.md`, section 5).

## The prompt, part by part

Write the prompt in this order. Each part solves a problem we hit.

| Part | Example from the gym skit | Why |
| --- | --- | --- |
| Shot type and point of view | "Vertical smartphone video still, point of view of a person standing in front of him." | Seedance continues the camera it sees; a POV still gives a POV take. |
| Who, with concrete looks | "A fit gym owner in his late 30s with a short dark beard and short dark hair" | Concrete, average features act better than "handsome model". |
| Wardrobe without branding | "plain black fitted crew-neck t-shirt with no logos and a grey towel over one shoulder" | The model invents sportswear logos unless told otherwise. |
| The prop the story needs | "holding a smartphone loosely in one hand at waist height" | If the joke needs a phone later, it must be in the still; Seedance rarely adds props convincingly. |
| Set, with plain surfaces | "small independent neighborhood gym in front of a dumbbell rack. White-painted brick wall, a blank whiteboard…" | Local business, not a chain. Blank boards and walls avoid fake text. |
| Light | "warm natural daylight from big windows" | Soft daylight survives video compression and looks like a phone video. |
| Gaze and expression | "looks straight into the camera lens, direct eye contact, calm neutral expression, lips closed, about to say something awkward" | A neutral start lets the take act; a broad smile in the still stays in the video. |
| Framing and texture | "Medium shot from mid-thigh up, eye level, realistic skin texture, candid, shot on iPhone, shallow depth of field" | Room for hands and props, leaves space for captions and zoom-ins. |
| Negatives | "No text, no logos, no brand marks, no watermark." | Fewer things to fix later. |

Parameters: `aspect_ratio: "9:16"`, `resolution: "1080p"`, `batch_size: 4`, `enhance_prompt: false`.
Templates: `templates/args/still.json`. Real examples: `assets/cast/*.soul-args.json`, `examples/gym-breakup/args/still-*.json`.

## Picking a candidate

Make a sheet and look at all four side by side:

```bash
python3 $SK/scripts/contact_sheet.py stills/still-owner-0.png stills/still-owner-1.png stills/still-owner-2.png \
  stills/still-owner-3.png -o stills/sheet-owner.jpg --cols 4 --width 400 --label index
```

Reject a candidate for any of these:

- a logo, a brand mark or readable text anywhere (shirts, sleeves, laptops, cups, posters, machines);
- a broad smile or a strong expression (it sticks through the whole take);
- hands that hide the prop, or a prop that is cut off;
- the face too small for a 1.4x punch-in (the face should be at least about 1/6 of the frame height);
- a set that looks like a chain store or a studio, or that has people in the background.

Pick the one that looks like a real phone video of a real local business and fits the script: the character's
role, the place, the prop the joke needs and the variants the later shots start from. Write the pick, its URL
(`stills/picked.json`) and the reason in `script.md`, and keep the rejected ones: they show the next person what
goes wrong. The look prompt itself comes from the character table written with the script, never from a still or
a character of another skit.

## What went wrong in the gym skit and the fix

| Round | Problem | Fix that worked |
| --- | --- | --- |
| owner v1 | all four smiled broadly ("a hint of a suppressed smile" plus the enhancer) and #2 had a logo on the sleeve | v2: "calm neutral expression, lips closed, about to say something awkward", `enhance_prompt: false`, "no logos" in the wardrobe line, phone in hand |
| agency v1 | the "closed silver laptop" came out with apple-style logos | v2: "a thick plain black ring binder with no text", "plain white front desk", "no signs, no posters", "no brand marks" |
| member v1 (later dropped) | 3 of 4 tank tops had sportswear logos | candidate #1 was clean; it is kept as `assets/cast/gym-member.jpg` |

## Reusing a character

- `assets/cast/` has the three cast stills of the first skit at full size with their exact Soul args.
  Reuse them as `image_url` for new takes so the same owner or account manager can come back
  ("the agency is back" sequels work only if it is the same face).
- Upload a local still with `hf-job upload <file>` or put the relative path in the take args; `hf-job submit`
  uploads it for you.
- For a recurring character across many videos and outfits, consider a Soul ID (global skill
  `higgsfield-soul-id`) and pass `custom_reference_id` and `custom_reference_strength` to Soul.

## Two characters in one shot

The first skit never shows both characters together: each speaks to the camera from their own still,
and the edit makes it a conversation. That is cheaper and safer (lip sync is per face). If a scene really
needs both in frame, generate a still with both and use `reference-to-video` or image-to-video with a
prompt that says who speaks which line; expect more retries.
