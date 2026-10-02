# GPU engine: the whole skit on your own ComfyUI server

`project.json` → `"engine": "gpu"` (the default for new projects) makes the cast stills, the voices, the talking
takes and the music on a GPU server you rent or own: ComfyUI 0.35 with the official ComfyUI workflow templates and
open models. Phases 0–2 and 5–8 are the same for both engines: the takes land in `takes/`, `inspect_take.py`
transcribes them, and the edit, formats, QA and delivery run on your computer. Higgsfield stays the other engine
(`"engine": "higgsfield"`, `casting-soul.md`, `takes-seedance.md`).

Everything the server needs is in this skill: `$SK/gpu/` holds the client (`gpu/client/gpu.py`), the server setup
(`gpu/server/`), the editor container (`gpu/editor/`) and the 15 workflows (`gpu/workflows/`). `gpu/README.md`
describes the server itself: models, licences, security, measured times, updating the templates. The worked example
is `examples/gym-breakup-gpu/`, the gym skit made again on one H200 on 2 October 2026.

```bash
SK=<the skill folder>
G="python3 $SK/gpu/client/gpu.py"
```

## Contents

1. Money and safety rules
2. The server: what it needs and where to get it
3. A session
4. The templates
5. Phase 3 on GPU: stills
6. Phase 4 on GPU: audio first, then pictures
7. Music bed
8. Editing on the server
9. Time and cost
10. What went wrong in the pilot, and the fix

## 1. Money and safety rules

- **The machine bills by the hour, from the moment it exists until it is deleted.** Make it (`gpu.py start --yes`,
  `gpu.py up --yes`, or by hand at the provider) only after the script is approved (Gate 2) and after an
  explicit yes from the user for that session. Without `--yes` the client only shows what it would order.
- **Always end the session.** `gpu.py stop --yes` as soon as the GPU work is done, also after a failure. It closes
  the tunnel, deletes the machine and keeps the disk with the models and images; the disk bills on its own
  (Verda: $0.20 per GB a month, $60 for 300 GB) until it is deleted at the provider. A machine that is only shut
  down still bills at Verda.
- **ComfyUI listens on 127.0.0.1 only** and has no login. Reach it only through `gpu.py tunnel` (`start` opens it);
  never publish the port.
- **Tokens stay in the Keychain or the environment.** The Hugging Face token (Keychain service `huggingface`,
  account `token`, or `HF_TOKEN`) goes to the server through SSH stdin into a file only root can read; never as an
  argument, never printed, never in a project file.
- **Voices and faces.** Clone only synthetic voices (our own takes, Chatterbox's voices) or a person who agreed in
  writing. Never a real person's voice or face from the reference. The reference's frames and transcript stay on
  your computer; they never go to the server.
- **Model licences.** The LTX-2 Community License covers `talk`, `talk-voice` and `action*`: free for a company with
  less than $10 million a year in revenue, no deepfakes of real people without their consent, and content made with
  it must be marked as generated. Every model's licence is listed in `gpu/README.md`.
- **Variant B (MiniMax H3)** stays off until MiniMax confirms the licence in writing (`--variant-b` downloads it).

## 2. The server: what it needs and where to get it

**What it needs.** One NVIDIA GPU with 80 GB of memory or more (Hopper or Blackwell: H100, H200, B200). Measured on
an H200: peaks of 13–49 GiB per job, with models from earlier jobs still loaded. A VM, not a container, with
Ubuntu 24.04, the NVIDIA driver, Docker with the compose plugin and the NVIDIA Container Toolkit, root login by SSH
key, and a 300 GB disk. Tested: 1× H200 at Verda (`1H200.141S.44V`). Planned: 1× B200 (`1B200.30V`), about twice
as fast, not measured yet.

**One-time setup on your computer:**

1. An SSH key for the server: `ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_yesopen_gpu -C yesopen-gpu`.
2. The settings: `mkdir -p ~/.config/yesopen-gpu && cp $SK/gpu/client/config.example.json ~/.config/yesopen-gpu/config.json`
   (another folder: `YESOPEN_GPU_HOME`). Settings and the machine's address stay there, outside the skill, so
   updating the skill keeps them.
3. Optional, for silent action shots (`action*`, LTX-2.5): accept the licence on the Hugging Face page
   `Lightricks/LTX-2.5`, create a read token and store it: `security add-generic-password -U -s huggingface -a token -w`
   (macOS; on Linux export `HF_TOKEN` before `start`). Without it everything else works.
4. For editing in Docker (optional): `docker build -t yesopen-editor:latest $SK/gpu/editor`.

**Where to get the machine.** Pick one:

| Way | Setup | Start and end of a session |
| --- | --- | --- |
| Verda, from this computer (recommended) | a Verda account with a prepaid balance (top-ups from $20 plus VAT); `brew install verda-cloud/tap/verda-cli`; API credentials from the Verda console (Project → Credentials) and `verda auth login`; `verda ssh-key add --name yesopen-gpu --public-key "$(cat ~/.ssh/id_ed25519_yesopen_gpu.pub)"`; then `verda.ssh_key_id` (`verda ssh-key list`), `verda.instance_type` and `verda.location` (a location with a free card: `verda availability --type <type>`) in the config | `gpu.py start --yes` finds the machine or orders it, boots the kept disk, installs what is missing and connects; `gpu.py stop --yes` deletes it and keeps the disk |
| Verda console, without API credentials | the SSH key added in the console (Deploy → "Add new key") | deploy by hand: the GPU type, the image "Ubuntu 24.04 + CUDA 13.0 Open + Docker" (later: the kept disk as its OS disk), 300 GB, your key; then `gpu.py use <address>` and `gpu.py start`. At the end `gpu.py stop`, delete the machine in the console with the disk kept, `gpu.py use --clear` |
| Another provider, or a machine in your office | a VM that meets the list above; your public key for root | `gpu.py use <address>`, `gpu.py start`; at the end `gpu.py stop`, delete or free the machine, `gpu.py use --clear`. The install turns on the firewall (only SSH comes in) and turns off SSH passwords, so give it a machine of its own |

**A team on one machine.** Everyone works in the same Verda project with the same `verda.hostname`,
`instance_type` and `location`. Each person adds their own public key to the project (`verda ssh-key add`), and
`verda.ssh_key_id` lists every member's key id (`["id-1", "id-2"]`), so the machine accepts all of them whoever
orders it. The first `start --yes` orders the machine; anyone else's `start` finds it running and connects. To
boot the team's kept disk rather than install from scratch, put its id into your own `state.json` once:
`{"os_volume_id": "<disk id>"}` (`verda volume list`). `stop --yes` deletes the machine for everyone, so agree
who ends the session.

## 3. A session

```bash
$G start              # is there a machine? yes: connect to it. no: show the order and stop
$G start --yes        # after the user's yes for this session: order it if there is none (billing starts)
...                   # the work (sections 5-8)
$G stop --yes         # always: close the tunnel, delete the machine, keep the disk
```

`start` does every step that is still missing and skips the rest:

1. **The machine.** With Verda set up: the machine called `verda.hostname` if it exists (it waits while Verda
   starts it), otherwise a new order with `--yes`, booting the kept disk when there is one. Without Verda: the
   address from `gpu.py use`, `host` in the config, or `GPU_HOST`.
2. **Login.** It waits until SSH answers (a new machine needs a minute or two).
3. **The stack.** It installs it (`bootstrap`) when the server has none or has one from other server files:
   firewall, SSH settings, the images, 61.5 GB of models, ComfyUI; the remaining 101 GB download in the background
   (`tail -f /srv/yesopen/fetch-after-start.log` on the server). A new disk takes about 11 minutes; a kept disk
   from the same stack only starts ComfyUI. `start --bootstrap` installs again on purpose.
4. **The tunnel and the check.** `localhost:8188` → the server's ComfyUI, then `health` for `still`, `tts` and `talk`.
   `$G health` checks all templates; right after a first install the background ones are still downloading.

The single steps exist too: `up`, `down`, `status` (Verda), `use`, `bootstrap`, `tunnel` / `tunnel --close`,
`health`. An order that ends as `no_capacity` (no free card in that location) must be removed with
`gpu.py down --yes` before the next try. A failed or timed-out order may still leave a billed machine: check
`gpu.py status`. Every job writes a `jobs.jsonl` line next to its outputs: template, ComfyUI prompt id, every value,
input files with SHA-256, outputs and time.

## 4. The templates

`$G templates` prints every parameter. Outputs are named `<name>.<output>.<ext>` in the output folder.

| Template | Model (licence) | Use | Key parameters |
| --- | --- | --- | --- |
| `still` | Z-Image Turbo (Apache 2.0) | cast stills, 1088×1920 | `prompt`, `seed` |
| `still-edit` | Qwen-Image-Edit 2511 (Apache 2.0) | the same person in another pose, prop or framing | `image`, `prompt`, `fast` |
| `tts` | Chatterbox Multilingual (MIT) | one line, 23 languages, voice cloned from a sample | `text`, `language` (always set it: `English (en)`, `Polish (pl)`, `German (de)`), `voice`, `exaggeration` |
| `tts-dialog` | Chatterbox (MIT) | a whole English conversation, plus one track per speaker | `dialog` (`SPEAKER A: …`), `voice_a`, `voice_b` |
| `talk` | LTX-2.3 IA2V (LTX-2 Community) | lip-synced take from a still and a recorded line | `image`, `audio`, `prompt`, `seconds` |
| `talk-voice` | LTX-2.3 ID-LoRA | voice and lips in one pass from a still and a voice sample | `image`, `voice`, `prompt` with `[VISUAL]:` and `[SPEECH]:`, `seconds` |
| `action` | LTX-2.5 I2V (LTX-2.x Community, gated) | silent reactions and B-roll from a still, with room sound | `image`, `prompt`, `seconds` (whole) |
| `action-t2v`, `action-flf` | LTX-2.5 | establishing shot from text; a move between two frames | `prompt` / `first`, `last` |
| `music` | ACE-Step 1.5 XL Turbo (Apache 2.0) | instrumental bed of a set length, tempo and key | `tags`, `seconds`, `bpm`, `timesignature`, `keyscale` |
| `upscale` | SeedVR2 3B (Apache 2.0) | 704×1280 → 1056×1920, restores detail | `video`, `multiplier` |
| `interpolate` | FILM (MIT, Apache 2.0) | 24 → 48 fps, smoother than the edit's 24 → 30 | `video`, `multiplier` |
| `two-shot` | InfiniteTalk on Wan 2.1, 480p | two people talking in one frame; downloaded on request, the repackaged files state no licence | `image`, `audio_a`, `audio_b`, `mask_a`, `mask_b` |
| `h3-i2v`, `h3-r2v` | MiniMax H3 | variant B, see section 1 | |

LTX makes 8n+1 frames: the client rounds `seconds` up to whole groups of 8 frames and pads the audio with silence
to exactly that length, so picture, sound and latent agree. Takes come out at 704×1280 and 24 fps; the edit
resamples to 30.

## 5. Phase 3 on GPU: stills

Write each new character's still prompt into `lines.json` → `characters.<name>.look`, as for Soul
(`casting-soul.md`: point of view, concrete looks, wardrobe without logos, the prop, a plain local set, daylight,
eye contact, neutral face, lips closed, no text), but **open with the framing**: "Vertical smartphone photo,
medium shot from mid-thigh up, eye level, …". With a prompt written for Soul, Z-Image frames wider and shows the
whole figure. A still takes about 3 s on the H200.

```bash
python3 $SK/scripts/gpu_batches.py stills          # stills/batch.json: 4 seeds per character without a still
$G batch stills/batch.json                         # -> stills/still-<name>-<k>.image.png
python3 $SK/scripts/contact_sheet.py stills/still-owner-*.image.png -o stills/sheet-owner.jpg --cols 4 --width 400 --label index
```

Pick as in Gate 3 and write the pick into `characters.<name>.still`. Returning characters need no new still:
`assets/cast/` has the gym skit's cast with their voice samples.

A variant of a picked still (a protein shaker at the chin, the phone in hand, another expression): `still-edit`
with the still, a one-sentence change and `fast=true` (4 steps, about 5 s), which keeps the face, the clothes and
the set. Name the variant in the line that needs it (`"still": "stills/owner-shake.png"`). **Show phones from the
back**: a screen facing the camera gets an invented interface (a camera app in the pilot), in the still and again
in the take.

```bash
$G run still-edit -s image=stills/owner.png -s fast=true -s prompt="He holds a plain black protein shaker bottle near his chin with one hand, about to take a sip. Keep his face, clothes and the gym the same." -o stills --name owner-shake
```

## 6. Phase 4 on GPU: audio first, then pictures

The dialogue is recorded first and sets the length of every shot. The picture is then generated to the finished
line, so the lips follow the sound and the edit never hunts for word boundaries. One take per line.

1. **Voice samples.** `voices/<character>.wav`, 5–15 s of one clean speaker, 48 kHz. A returning character:
   `assets/cast/<character>.voice.wav`. A new one: cut it from our own earlier take
   (`ffmpeg -ss 1.0 -t 8.6 -i takes/take-owner-1-720p-0.mp4 -vn -ac 1 -ar 48000 voices/owner.wav`), or record a
   Chatterbox line in one of its own voices first.
2. **`lines.json`.** The script as the engine reads it (template: `templates/lines.json`; the full example:
   `examples/gym-breakup-gpu/lines.json`). Per character: `voice`, `still`, and how the take prompt names them
   (`who`, `where`, `him`). Per line, in timeline order: `id`, `who`, `text` (numbers as words: "five",
   "two a.m."), `exaggeration` (0.5 neutral, 0.6–0.85 for a bigger performance), `acting`, and `action` = what we
   see in the take ("glancing down suspiciously at his phone, then back at the camera"). Exceptions per line:
   `still`, `tail`, `seed`, `silence_before`, a whole `prompt`, `seconds`.
3. **Record every line twice.** `python3 $SK/scripts/gpu_batches.py voice` writes `voice/batch.json` (two seeds per
   line), then `$G batch voice/batch.json`. With the voice model kept loaded a line takes 3–5 s of GPU time.
4. **Fit every line before any picture is made:** `python3 $SK/scripts/fit_lines.py lines.json voice lines`.
   Chatterbox often keeps talking after the line (invented words up to its 1000-token limit) and sometimes hums or
   mumbles in a pause. The script keeps a take only when the script's words come first and nothing untranscribed
   sounds between them, cuts it after the last word, shortens pauses over 0.75 s, puts 0.3 s of silence in front
   (a take's first frame is the still, so the face starts still) and writes `lines/<id>.wav` and `lines/fit.json`.
   A take that ends with the script's "?" or "!" wins; one that asks "No?" where the script says "No." loses.
   A line that fails or says a word wrong (the pilot's "two AMA"): `gpu_batches.py reseed <id>` (4 new seeds,
   optionally `--text "It replies at 2 AM. …"` or `--exaggeration 0.5`), `$G batch voice/batch-<id>.json`,
   `fit_lines.py lines.json voice lines --only <id>`. In the pilot 2 of 21 lines needed that. Listen to the lines
   that carry the joke.
5. **Talking takes.** `python3 $SK/scripts/gpu_batches.py takes` writes one `talk` job per fitted line into
   `takes/batch.json`: the character's still, `lines/<id>.wav`, `seconds` = the line + `tail` (0.6 s of acting after
   the line by default; more where the edit holds a reaction, 1.3–2.6 s in the pilot) and the prompt from
   `take.template`:
   "Single continuous handheld vertical smartphone shot, no cuts, camera at eye level facing him, slight natural
   handheld movement, the framing stays the same with no zoom and no push-in. The bearded gym owner stays in place
   in his small gym and talks directly into the camera lens as if to the person filming him, serious and a little
   nervous, he takes a small breath before speaking. Natural, understated comedic acting. No other people, no text
   on screen."
   The framing sentence matters: LTX-2.3 likes to push in at the end of a take. Then `$G batch takes/batch.json`:
   13 s of GPU time per take on the H200. One seed per line was enough in the pilot.
6. **Silent beats.** `action` from the still needs LTX-2.5 (the Hugging Face token; not tested yet): the action as a
   short sentence ("he flips the phone face down and looks away, whistling"), `seconds` 3–5. Without it a `talk`
   take with silence before its line carries the beat: `"silence_before": 3.3` and a whole `prompt` that says what
   happens before the line (the pilot's last shot: 3.3 s of silent joy, then "Hey, you." to the phone). A short
   reaction can also come from the tail of another take (`cutaway` in `cuts.json`).
7. **Into the edit.** Name the takes in `project.json` → `takes` (`"l01": "takes/l01.video.mp4"`), run
   `inspect_take.py` on every take (words, sheet, boundaries) and check Gate 4 on the sheets: lips on every word,
   no push-in, no screen facing the camera, no extra people, the action where the joke needs it. Whisper puts the
   first word at 0.00; when the take is silent before it, `inspect_take.py` moves it to where the sound starts. In
   `cuts.json` a line is usually its whole take: `{"take": "l01", "line": ["Hey", "up"], "head": 0.28,
   "tail": 0.2}`; keep `head` under the 0.3 s of silence.
8. **A retake.** Change the line in `lines.json`, move the old files to `takes/old/`, write a batch of that line
   alone and run it even though its name is in `jobs.jsonl`:
   `gpu_batches.py takes --only l16 --out takes/batch-l16.json`, `$G batch takes/batch-l16.json --force`.
   `gpu_batches.py` warns whenever a changed job would otherwise be skipped.
9. **Optional finish per take:** `upscale` for a sharper 1056×1920 master (63 s for a 4.4 s take on the H200);
   `interpolate` when the motion judders.

`talk-voice` makes voice and lips in one job (`[VISUAL]: <what we see>. [SPEECH]: <the exact line>`, plus a voice
sample), like Seedance. On the first server day it was 5 times slower than `talk`, pushed in on the face and matched
the lips worse, and its sound cannot be checked before the picture. Use `talk`.

## 7. Music bed

```bash
$G run music -s tags="instrumental, light comedic underscore, pizzicato strings, soft percussion" \
   -s seconds=90 -s bpm=100 -s timesignature=4 -o music --name bed
python3 $SK/scripts/music.py music/bed.audio.flac --bpm 100     # the beat grid it will use
```

Make the track at least 10 s longer than the edit, and listen to it: Whisper cannot tell whether a bed has vocals.
Then `project.json` → `"music": {"file": "music/bed.audio.flac", "bpm": 100}` and `make_edl.py` + `assemble.py` as
usual: a downbeat lands on the cut to the end card, the bed ducks under every line and comes up between them. All
keys and the measurements are in `edit-pipeline.md`, section 8. ACE-Step does not hit the asked tempo exactly
(110 bpm for 112); `music.py` uses the measured grid. `beat_clarity` under about 3 means no clear beat: set
`"anchor": null`. A licensed library track works the same way with its own BPM.

## 8. Editing on the server

The edit normally runs on your computer and needs no GPU, so the machine can be deleted as soon as the takes and
the music are in. The same scripts also run in the `yesopen-editor` container (Python 3.12, Pillow, numpy, Whisper,
static ffmpeg 8.1):

```bash
$G edit . -- assemble.py --format 9:16                 # in the container on your computer
$G edit . --remote -- assemble.py --format all         # on the server: push the project, render, pull it back
```

Neither the B200 nor the H200 has a video encoder (NVENC), so encoding is libx264 on the CPU either way; the server's
30 cores (B200) or 44 (H200) help with `--format all`. The container's render of the gym skit matches the macOS
render: same frames, PSNR 47.9 dB, SSIM 0.990, −14.2 LUFS. Its ffmpeg and x264 are another build, so the MD5
differs; the byte-identical checks of the examples hold for renders with the same ffmpeg build.

## 9. Time and cost

Measured on the first server day (2 October 2026, 1× H200 at Verda, GPU time from ComfyUI's own history):

| Step | GPU time per job | The pilot skit (21 lines) |
| --- | --- | --- |
| `still` | 2.8 s (9.6 s with the model load) | not needed: the cast came from the Higgsfield skit |
| `still-edit`, 4 steps | about 5 s (15.7 s first) | 3 jobs, 0.6 min |
| `tts`, one line | 3–5 s (10.8 s first) | 50 jobs, 5.2 min, most of them before the voice model stayed loaded |
| `talk`, a 3–5 s take | 13.4 s on average (35.4 s first) | 21 takes, 4.7 min |
| `music`, 45 s | 17.8 s | |
| `upscale`, a 4.4 s take | 63.2 s | |

- The pilot skit took 10.4 min of GPU time. The whole session, with the first install (10 min 40 s), a test of every
  template and the skit, took about 1 h and cost $4.86 on an H200 at $4.78 an hour.
- `python3 $SK/scripts/gpu_batches.py estimate` prints the jobs and GPU minutes of a new skit for Gate 2.
- Prices at Verda on 2 October 2026, per hour on demand (spot is half and can be stopped at any time): 1× B200
  (`1B200.30V`, 180 GB) $6.99, 1× H200 (`1H200.141S.44V`) $4.78. Check before starting.
- The kept disk: 300 GB, $60 a month. Verda disks only grow; enlarge it to 400 GB before variant B.
- First install: about 61.5 GB of models before ComfyUI starts, 101 GB more in the background (variant A: 162.5 GB
  automatic, 94.6 GB more on request).

## 10. What went wrong in the pilot, and the fix

| Problem | Fix, now in the skill |
| --- | --- |
| Chatterbox kept talking after most lines, up to its token limit, and sometimes mumbled in a pause | `fit_lines.py` cuts after the script's last word and rejects takes with mumbling |
| TTS loaded the voice model again for every line: 7 s more per 3 s line | `keep_model_loaded` in `gpu/workflows/patches.json` |
| LTX-2.3 pushed in on the face at the end of takes | the framing sentence in the take template |
| A phone held towards the camera got an invented camera app on its screen | phones with their back to the camera, in the still and the prompt |
| Whisper put each take's first word at 0.00 although speech starts after 0.3 s of silence | `inspect_take.py` moves the first word to the first sound |
| "two a.m." came out as "two AMA" | `gpu_batches.py reseed` with 4 seeds; listen to the key lines |
| "No." came out as a question | `fit_lines.py` prefers takes whose last word carries the script's mark |
| A Soul prompt gave Z-Image a full-figure picture | the framing goes first in the prompt |
| `gpu.py tunnel --close` hung once the machine was deleted | `stop` closes the tunnel first; `tunnel --close` gives up after 15 s |
