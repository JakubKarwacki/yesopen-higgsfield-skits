# Higgsfield platform API: keys, jobs, models, prices

How the skits talk to Higgsfield (`"engine": "higgsfield"`). Everything here was used for the first skit on
2026-10-01. The GPU engine needs none of it: `gpu-engine.md`.

## Contents

1. Access and the key
2. `hf-job`: submit, resume, status, upload, cost
3. Models and every parameter we pass
4. Prices and credits
5. Statuses, failures and what to do
6. Running several jobs and watching them
7. Where the official docs are

## 1. Access and the key

- There is no Higgsfield MCP connector and no Higgsfield CLI in these sessions. Everything goes through
  the Python package `higgsfield-client` (0.2.0 at the time of writing) against `https://platform.higgsfield.ai`.
- The key has the form `<key-id>:<secret>` and is read from the environment variable `HF_KEY` by the client.
- On the Mac it lives in the macOS Keychain, service `higgsfield`, account `api-key`. The owner stores it once
  in Terminal (the command asks for the value without echoing it):

  ```bash
  security add-generic-password -U -s higgsfield -a api-key -w
  ```

- `scripts/hf-job` reads the Keychain entry (or an existing `HF_KEY`), exports it only into the child Python
  process and never prints it. Never ask for the key in chat, never write it into args files, logs, commits,
  scripts or memory. If a key ever lands in a transcript or a file, tell the owner to rotate it in Higgsfield.
- Colleagues on other machines: export `HF_KEY` in the shell for the session, or store it in their own
  Keychain with the same command. Each person uses their own key.

## 2. `hf-job`

`scripts/hf-job` is a bash launcher for `scripts/hf_job.py`. Python is taken from `$HF_PYTHON`, the skill's
own `.venv`, or `~/.agents/skills/higgsfield-generate/.venv`; if none exists, it creates `.venv` next to the
skill and installs `higgsfield-client`.

| Command | What it does | Costs money |
| --- | --- | --- |
| `hf-job submit <label> <model> <args.json> <outdir>` | uploads local media named in args, submits, polls every 5 s, downloads outputs to `<outdir>/<label>-<i>.<ext>`, logs to `<outdir>/jobs.jsonl` | yes |
| `hf-job resume <label> <request_id> <outdir>` | waits for an already submitted request and downloads it | no (already paid) |
| `hf-job status <request_id>` | prints the raw status JSON | no |
| `hf-job upload <file>` | uploads a local image/video/audio, prints `{"file", "url"}` | no |
| `hf-job cost <model> <args.json>` | list-price estimate from the resolution, duration and batch size in the args; no key needed, nothing sent | no |

Conventions:

- Label = file stem: `still-owner-v2` gives `still-owner-v2-0.png … -3.png`; `take-agency-1-720p` gives
  `take-agency-1-720p-0.mp4`. Put the resolution in the label when you try several.
- `jobs.jsonl` is the checkpoint. Each line has `label`, `model`, `request_id`, `status` (`submitted`,
  `completed`, `Failed`, `NSFW`, `Cancelled`, `submit_failed`, `no_output`), `args` without the prompt,
  `args_file`, `urls`, `files`, `seconds` and `ts`. If a terminal dies mid-job, read the `request_id`
  there and `resume`; never resubmit a paid job just because the terminal lost it.
- Args files may name local media relative to the args file, e.g. `"image_url": "../stills/still-owner-v2-3.png"`.
  `submit` uploads it and logs the resulting URL. A URL from an earlier upload or from a Soul output also works.

Examples (run from the project folder; `SK` is the skill folder):

```bash
SK=~/.agents/skills/yesopen-higgsfield-skits   # or <localesto>/.agents/skills/yesopen-higgsfield-skits
$SK/scripts/hf-job cost higgsfield-ai/soul/v2/standard args/still-owner.json
$SK/scripts/hf-job submit still-owner higgsfield-ai/soul/v2/standard args/still-owner.json stills
$SK/scripts/hf-job cost bytedance/seedance-2.5/image-to-video args/take-owner-1-720p.json
$SK/scripts/hf-job submit take-owner-1-720p bytedance/seedance-2.5/image-to-video args/take-owner-1-720p.json takes
$SK/scripts/hf-job status 7b2d1f2a-9111-4062-a2e6-108a0737e06f
$SK/scripts/hf-job upload stills/still-owner-v2-3.png
```

## 3. Models and parameters

### Soul 2 stills: `higgsfield-ai/soul/v2/standard`

| Parameter | Values | We used |
| --- | --- | --- |
| `prompt` | text, required | the cast prompt (see `casting-soul.md`) |
| `aspect_ratio` | `9:16`, `16:9`, `4:3` (default), `3:4`, `1:1`, `2:3`, `3:2` | `9:16` |
| `resolution` | `720p`, `1080p` | `1080p` (output 1152x2048 PNG) |
| `batch_size` | `1` or `4` | `4`: four candidates per call |
| `enhance_prompt` | bool, default `true` | `false` from round 2: the enhancer added smiles and logos |
| `seed` | 1–1,000,000 | not set |
| `style_id` | a Soul style | not set |
| `custom_reference_id`, `custom_reference_strength` (0–1) | a Soul ID character | not set; see `casting-soul.md` for recurring characters |

Output: `images` array of URLs. Time: 1.8–2.6 min per batch of 4.

### Seedance 2.5 image-to-video: `bytedance/seedance-2.5/image-to-video`

| Parameter | Values | We used |
| --- | --- | --- |
| `image_url` | URL or local path (hf-job uploads it), required | the picked Soul still of the character |
| `prompt` | text | numbered lines with acting directions and pauses (see `takes-seedance.md`) |
| `duration` | 4–30 s, default 5 | 20, 22, 26, 28 |
| `resolution` | `480p`, `720p` (default), `1080p` | `720p` (1080p failed on balance, see 4) |
| `generate_audio` | bool, default `true` | `true`: voice, lip sync and room tone come from the model |
| `end_image_url` | URL | not used |
| `output_format` | `mp4`, `mov` | default mp4 |

Output: `video` URL. 720p is 720x1280, 480p is 480x854, 24 fps, AAC 32 kHz. Time: 3.9–8.4 min per take.

### Other Seedance 2.5 endpoints (not used yet)

- `bytedance/seedance-2.5/reference-to-video`: `image_urls`, `video_urls`, `audio_urls`, `prompt`, `aspect_ratio`,
  `duration`, `resolution`, `generate_audio`, `output_format`. Useful when one shot must show two characters
  together, or to keep a voice with an audio reference.
- `bytedance/seedance-2.5/text-to-video`: `prompt`, `duration`, `resolution`, `aspect_ratio`, `output_format`,
  `generate_audio`. Useful for establishing shots without a character still.

## 4. Prices and credits

List prices from the Pricing section of each model page on open.higgsfield.ai, read on 2026-10-01 (the pages
render only in a browser; open them in Ego Browser):

| Model | Price |
| --- | --- |
| Seedance 2.5 text-to-video, image-to-video, reference-to-video | video tokens = ceil(height x width x (input video s + generated s) x 24 / 1024), at $0.0214 per 1,000 in 480p and 720p and $0.0234 in 1080p. For 9:16 or 16:9 that is about $0.2056 per second in 480p, $0.4622 in 720p and $1.1372 in 1080p. |
| Seedance 2.5 with video inputs (reference-to-video) | the token price is multiplied by 0.6, and the input videos' seconds are billed too. Image and audio references are free. |
| Seedance 2.0 (not used) | from $0.1408 per second; the price rises with resolution, so check its model page first |
| Soul 2 | $0.0032 per image in 720p (the default), $0.0057 in 1080p |

`hf-job cost` applies these prices. Top-up tiers start at $25, $100 and $1,000.

The API returns no cost and there is no balance endpoint, so compute a skit's cost from the args in
`jobs.jsonl`. The first skit cost $49.01 at list price:

- four 720p takes, 96 s: $44.38;
- one 480p take used only in the preview, 22 s: $4.52;
- five Soul batches of 4 in 1080p: $0.11.

The account spend Marcin saw, about $50, matches this total, so the 720p take blocked by content safety (22 s,
$10.17 at list price) was most likely not charged. Jobs refused for balance never run and cost nothing.

A low balance shows up in two free ways:

- the submit itself is refused with `not_enough_credits`;
- the job is accepted and fails within about 5 s with "Your credit balance is too low to complete this request".

On 2026-10-01 the 1080p takes failed this way while the same takes at 720p went through; after a top-up,
three 720p takes ran in parallel. Ask the owner to top up; do not retry in a loop.

## 5. Statuses and failures

The client yields `Queued`, `InProgress`, then one of `Completed`, `Failed`, `NSFW`, `Cancelled`.

| Symptom | Cause | Action |
| --- | --- | --- |
| `Failed` after ~5 s | credit balance too low | ask for a top-up, or lower `resolution`; nothing was charged |
| submit refused `not_enough_credits` | same | same |
| `Failed` after ~4 min: "The generated result was blocked by content safety checks. Try a different prompt or reference media." | the safety filter on the generated video (agency take 1 at 720p) | resubmit the same args once; it passed on the retry. If it fails twice, soften the wording ("furious" -> "annoyed") |
| `NSFW` | input or output flagged | change the still or the prompt |
| terminal closed mid-poll | nothing wrong with the job | `hf-job resume <label> <request_id> <outdir>` from `jobs.jsonl` |

## 6. Several jobs at once

Run each take as its own background command (the agent harness notifies when each ends), or watch them with
one loop that prints a line only when something changes:

```bash
labels="take-owner-1-720p take-agency-1-720p take-owner-2-720p take-agency-2-720p"
while true; do
  done_all=1
  for l in $labels; do
    if [ -f "takes/$l-0.mp4" ]; then s=ready
    else s=$(grep "\"label\": \"$l\"" takes/jobs.jsonl 2>/dev/null | tail -1 | sed 's/.*"status": "\([^"]*\)".*/\1/'); fi
    case "$s" in ready|Failed|Cancelled|NSFW) ;; *) done_all=0 ;; esac
    [ "$s" != "$(cat /tmp/hf-$l 2>/dev/null)" ] && { echo "$l: $s"; echo "$s" > /tmp/hf-$l; }
  done
  [ $done_all = 1 ] && break
  sleep 10
done
```

Three 720p takes in parallel were fine. Do not poll faster than every 5 s.

## 7. Official docs

- The API docs moved from `console.higgsfield.ai` to `open.higgsfield.ai` (model pages list every parameter).
- The global skill `higgsfield-generate` (`~/.agents/skills/higgsfield-generate/`) has the model catalog and
  the one-shot `hf-api` script; this skill's `hf-job` adds checkpoints, resume, upload and cost.
