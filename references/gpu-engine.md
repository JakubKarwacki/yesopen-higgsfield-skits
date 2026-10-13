# GPU engine: MiniMax H3 on the project server

The primary video engine is **MiniMax H3**, hosted on the project GPU server.
**Locally hosted Wan 3.0** is an alternative to evaluate after confirming official
weights and a local runtime. Model selection, terms and implementation status:
[video-models.md](video-models.md).

`project.json.engine: "gpu"` selects the server workflow. Stills use Z-Image,
image variants use Qwen-Image-Edit, dialogue uses the selected voice and TTS,
and video uses the explicit H3 batch. The editor produces montage, QA and delivery.

```bash
SK=<the skill folder>
G="python3 $SK/gpu/client/gpu.py"
```

## 1. Session, access and model terms

Start and retire compute according to the user's current session instruction.
Preserve persistent disks. On a shared host, inspect the queue and outstanding
work before stopping or deleting an instance. Keep ComfyUI on localhost behind
an SSH tunnel, and credentials outside projects and Git.

Use traceable synthetic voices or appropriately authorized recordings.
MiniMax's current terms and the local Wan availability check are linked in
[video-models.md](video-models.md). A selected model is not proof of authorization.

## 2. The server and kept disks

Nebius preparation: [nebius-operations.md](nebius-operations.md).
Windows client: [../docs/docker-client.md](../docs/docker-client.md).
Use the production disk for employee video generation and a separate clone
for development. The prepared project disk has Ubuntu, Docker, ComfyUI, the
editor images, model weights and project data on a 600 GiB persistent volume.

Verda and manually provisioned servers remain supported by `gpu.py`.
Configure `gpu/client/config.example.json` locally; run `gpu.py verda-check`
for Verda. For another provider, use `provider: "other"` and `gpu.py use <address>`.
Choose a GPU after an H3 pilot confirms memory and performance requirements.

## 3. A session

```bash
$G start --yes
$G fetch h3-talk,h3-i2v,h3-r2v --variant-b
$G health
# submit the explicit H3 batches from section 6
```

`--variant-b` is the current downloader flag for H3 files. The production graph
now supports H3; fetch its weights explicitly when preparing a fresh machine.
Confirm H3 node classes and files are ready before submitting a job.

For Nebius, use individual credentials and explicitly select the dev or
production disk. The current session wrapper rejects any already-listed
instance; parallel dev/production requires targeted instance and disk selection
before using that wrapper for both environments.

## 4. The templates

| Template | Role | Inputs |
| --- | --- | --- |
| `still` | Z-Image cast candidates | `prompt`, `seed` |
| `still-edit` | Qwen image variant | `image`, `prompt`, `fast` |
| `tts` | Chatterbox multilingual dialogue | text, language, voice sample |
| `tts-dialog` | Chatterbox dialogue experiment | dialog, speaker samples |
| `h3-talk` | MiniMax shot with approved input audio | image, audio, prompt, seconds, fast, megapixels |
| `h3-i2v` | MiniMax shot with native audio | image, prompt, seconds |
| `h3-r2v` | MiniMax reference-based shot | reference images, prompt, seconds |
| `music` | Optional ACE-Step bed | instrumental brief, duration, BPM |
| `upscale` | Optional SeedVR2 finish | video, scale |
| `interpolate` | Optional interpolation | video, multiplier |

`two-shot` uses an older Wan model; it is not the planned Wan 3.0 integration.
Implemented parameters: `gpu/workflows/params/<template>.json`.

## 5. Cast stills

Each character needs a look, a picked still and a traceable voice selection.
Each shot's still must match its START state. A variant changes only the
specified pose, prop or framing, preserving identity, clothing and the set.

```bash
python3 $SK/scripts/gpu_batches.py stills
$G batch stills/batch.json
```

Write selected stills into `lines.json` and record voice provenance in the project.

## 6. Audio first, then MiniMax pictures

Set `lines.json.take.model` to `"h3"`; inspect every per-line override.
Runtime defaults have not been changed by this documentation migration.

```bash
python3 $SK/scripts/gpu_batches.py voice
$G batch voice/batch.json
python3 $SK/scripts/fit_lines.py lines.json voice lines
python3 $SK/scripts/gpu_batches.py takes --model h3
$G batch takes/batch.json
python3 $SK/scripts/inspect_take.py takes/l01.video.mp4
```

`h3-talk` uses the picked still, fitted audio and a shot-specific prompt.
Use `take.h3_template` or `lines[].h3_prompt`: `<Picture 1>`, `SHOT 1`, dialogue
and the audio policy. Include START, action order, END and HOLD. Do not ask
the generator to draw captions.

The current H3 adapter rounds video to `17k+5` frames at 24 fps and prepares
audio for that duration. Its trained shot range is approximately 5.2–15 s.
Split longer dialogue; trim short shots in montage. `take.fast` and
`take.megapixels` select the implemented H3 quality and size settings.

Silent reactions use an explicitly specified native-audio H3 shot with soundtrack
inspection. A generic phone reaction is not the script's scene specification.
An experimental graphical branch is not a replacement for approved dialogue.

Retakes: preserve old output and submit a specific new batch using `--only <id>
--model h3`; use `--force` when reusing a job name. Record inputs and provenance.

## 7. Optional music

Choose whether the project has music before generation and montage. Specify
the source or generation brief, duration and actual BPM. Leave lyrics empty
for an instrumental bed. The file and BPM must reach `project.json.music`;
no-music projects remain valid.

The current graphical branch has known demo-content and metadata defects:
[context audit](../docs/reviews/2026-10-13-pipeline-context-audit.md).
Use a project-specific brief and verify the saved configuration.

## 8. Editing on the server

Record selected takes in `project.json.takes` and `edit/cuts.json`, inspect
each take and verify action completion. Preserve caption and music decisions
through EDL creation, montage and QA.

```bash
python3 $SK/scripts/build_assets.py . --sheet
python3 $SK/scripts/make_edl.py .
python3 $SK/scripts/assemble.py . --format all
python3 $SK/scripts/qa_report.py . --format 9:16 --whisper
```

Use the formats approved for the project. The graphical format chain currently
hardcodes four formats and needs migration. Retire compute only under the
current session instruction, accounting for shared work and persistent disks.

## 9. Time and cost

Measure MiniMax H3 on the dev disk: GPU time, model loading, VRAM, retries and
accepted outputs per shot. Historical pilot throughput is not an H3 estimate.
The existing estimator has no measured H3 timing entry.

## 10. Migration and Wan tests

The H3 runtime defaults, graphical audio-conditioned path and checkpoint
contracts are implemented. The graph uses the client's API parameter maps and
frame rules. MVP quality checks on GPU remain pending.

Track local Wan 3.0 testing in [video-models.md](video-models.md) and
[../docs/TODO.md](../docs/TODO.md). Official weights and a reproducible local
runtime are the first prerequisites.

Previous guide: [historical archive](../docs/archive/pre-minimax/gpu-engine.md).
