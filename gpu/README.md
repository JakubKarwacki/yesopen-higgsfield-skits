# MiniMax H3 server and development environment

The project's primary video engine is locally hosted **MiniMax H3**.
Locally hosted **Wan 3.0** is an alternative to evaluate. The model policy,
current terms, local-weight availability and migration state are documented in
[video-models.md](../references/video-models.md).

## Current support

The repository contains H3 API workflows:
- `h3-talk`: a still plus approved recorded dialogue, anchored as the soundtrack;
- `h3-i2v`: image-to-video with native sound;
- `h3-r2v`: reference-based generation with native sound.

New projects default to `take.model: "h3"`. The production graph expands
the same audio-conditioned API template used by the client and passes approved
audio, project prompts and parameters into it. Existing explicit model overrides
are respected. Upscale/interpolation are opt-in. Full generation quality remains
to be validated on GPU; the CPU preview does not prove model quality.

## Machine and disk

Use a VM with Ubuntu, Docker, NVIDIA Container Toolkit and a GPU that passes
the H3 pilot's memory check. The prepared Nebius disk is 600 GiB. Keep employee
production on the production disk and test changes on a separate dev clone.
Never delete persistent disks when retiring compute.

Individual Nebius access and disk preparation:
[nebius-operations.md](../references/nebius-operations.md).
Windows Docker client and browser tunnel:
[docker-client.md](../docs/docker-client.md).

Verda remains supported: configure `client/config.example.json` outside Git,
add the operator's SSH key and run `gpu.py verda-check`. A manually provisioned
server uses `provider: "other"` and `gpu.py use <address>`.

## Commands

```bash
SK=<the skill folder>
G="python3 $SK/gpu/client/gpu.py"
$G start --yes
$G fetch h3-talk,h3-i2v,h3-r2v --variant-b
$G templates
$G health
python3 $SK/scripts/gpu_batches.py takes --model h3
$G batch takes/batch.json
python3 $SK/scripts/inspect_take.py takes/l01.video.mp4
```

`--variant-b` remains the downloader's H3 flag. It is a compatibility name,
not the project's model preference. Every job records parameters, file hashes,
prompt ID, outputs and execution time in `jobs.jsonl`.

Shared-host retirement follows the user's current instruction after accounting
for real queued work. Keep ComfyUI on localhost and use an SSH tunnel.

## Supporting stages

| Stage | Implemented workflow |
| --- | --- |
| Cast candidates | Z-Image `still` |
| Still variants | Qwen `still-edit` |
| Selected dialogue voice | Chatterbox `tts` |
| Dialogue experiment | `tts-dialog` |
| Approved-audio video | MiniMax `h3-talk` |
| Native-audio video | MiniMax `h3-i2v` / `h3-r2v` |
| Optional music | ACE-Step `music` |
| Optional upscale | SeedVR2 `upscale` |
| Optional interpolation | `interpolate` |
| Montage and QA | `editor-api` and skill scripts |

The older `two-shot` workflow is not Wan 3.0 support. Check
`workflows/params/<id>.json` for the actual implemented contract and
`server/manifest.json` for the current installed model inventory.

## Validation and performance

H3 templates are present in API format. End-to-end graphical H3 production,
its quality, GPU latency and memory use need MVP validation on the dev disk.
Use the same approved audio, reference images and scene plan for every comparison.
Historical timings from the gym pilot cannot be used as H3 performance claims.

Previous server measurements and template inventory:
[historical archive](../docs/archive/pre-minimax/gpu-server.md).
Current implementation audit:
[pipeline context audit](../docs/reviews/2026-10-13-pipeline-context-audit.md).

## Wan 3.0 local experiment

First verify official downloadable weights, licence and a reproducible local
runtime. Then implement the shared generation contract and compare lipsync,
identity, props, scene completion, VRAM, time and cost with H3. An API wrapper
does not satisfy the local-hosting requirement.

## Repository structure

- `client/`: GPU/provider client and session helpers.
- `server/`: images, compose files, model manifest and project nodes.
- `editor/`: montage and QA service.
- `workflows/ui/`, `workflows/api/`, `workflows/params/`: workflow sources and contracts.
- `workflows/pipeline/`: generated ComfyUI project graph.
- `tools/`: conversion, graph generation and workspace installation.
- `tests/`: client, workflow and runtime checks.

Settings, credentials, disk IDs and instance state stay outside Git.
