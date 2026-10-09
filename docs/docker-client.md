# The Docker client as a Claude Code skill (Windows)

On Windows the skill's tools (`ffmpeg`, `rsync`, `ssh` with ControlMaster, `pkill`, Python with Pillow and numpy, the
Verda CLI) are not installed. This repo ships them as one Docker image, and `scripts\skill.ps1` runs any command of the
skill inside it. Claude Code then uses the skill as usual; only the way commands are started changes.

## 1. Install the skill

Claude Code reads a skill from a folder that holds `SKILL.md`. Clone this repo into your skills folder:

```powershell
git clone https://github.com/behavio1/yesopen-higgsfield-skits.git "$env:USERPROFILE\.claude\skills\yesopen-higgsfield-skits"
```

(For one project only, clone into `<project>\.claude\skills\yesopen-higgsfield-skits` instead.) Start a new Claude
Code session so it picks the skill up.

## 2. Get the image

Docker Desktop must be running. The image is not published anywhere: the first `skill.ps1` call builds it locally from
`docker/Dockerfile` (a few minutes, then cached). Whisper is included (CPU only); its models download on first use
into the `whisper-cache` volume.

```powershell
cd "$env:USERPROFILE\.claude\skills\yesopen-higgsfield-skits"
scripts\skill.ps1 build
scripts\skill.ps1 unlock
scripts\skill.ps1 gpu status
```

## 3. Credentials

The image holds no secrets. The Verda credentials and the GPU SSH key live only in GitHub Secrets of a separate
PRIVATE repo of your team (`<owner>/<secrets-repo>`), never in a local file, in `.env`, or in an image layer.

One-time setup of that repo (an admin does it):

1. Create the private repo, copy `docker/secrets/broker.yml` into it as `.github/workflows/broker.yml`.
2. In Settings -> Environments create `broker` (limit it to the `main` branch) and add the secrets
   `VERDA_CLIENT_ID`, `VERDA_CLIENT_SECRET`, `YESOPEN_GPU_SSH_KEY` (base64 of the private key file) and
   `YESOPEN_GPU_SSH_KEY_PUB` there.
3. Add the team as collaborators. Access to the secrets is exactly access to that repo.
4. Everyone sets the repo name once: `$env:SECRETS_REPO = "<owner>/<secrets-repo>"` (or in the user environment).

Local runs get the keys from a sidecar container that keeps them in memory only. They are pulled with your own GitHub
account from that repo; you must be a collaborator there.
The first command asks you to sign in to GitHub (a one-time code in the browser); nothing is written to disk:

```powershell
scripts\skill.ps1 unlock        # pull the secrets into the sidecar (also done automatically before gpu/shell/other commands)
scripts\skill.ps1 lock          # wipe them
scripts\skill.ps1 secret list                 # names and update times of the secrets
scripts\skill.ps1 secret set VERDA_CLIENT_SECRET   # change one (typed hidden, straight to GitHub; needs write access to the secrets repo)
scripts\skill.ps1 secret rotate-ssh           # new GPU SSH key made in memory; prints the public key to add in Verda
```

Updates reach everyone: before every command the script compares the secrets' update times in the secrets repo with
what is loaded, and pulls them again when somebody changed or rotated one. Removing a collaborator cuts their access at
their next pull.

Under the hood the `broker` workflow of the secrets repo encrypts the secrets to a one-time key made in the sidecar and
hands them over as a one-day artifact. Add or remove a collaborator of that repo to grant or cut access; rotate a secret
with `gh secret set <NAME> --env broker --repo <owner>/<secrets-repo>`.


Check it (nothing is ordered):

```powershell
scripts\skill.ps1 gpu verda-check
```

The GPU settings (`config.json`, `state.json`) live in the Docker volume `<folder>_gpu-home` and survive between
runs. The first run makes `config.json` from the example.

## 4. How commands run

`SKILL.md` and the references write commands as `python3 $SK/scripts/...` and `$G` (= `python3 $SK/gpu/client/gpu.py`).
With the Docker client every such command is started through the wrapper, and `$SK` is `/skill` inside the container:

| In the skill | With Docker |
|---|---|
| `python3 $SK/gpu/client/gpu.py status` | `scripts\skill.ps1 gpu status` |
| `python3 $SK/scripts/gpu_batches.py voice` | `scripts\skill.ps1 python3 scripts/gpu_batches.py voice` |
| `ffmpeg ...` | `scripts\skill.ps1 ffmpeg ...` |
| a shell in the environment | `scripts\skill.ps1 shell` |
| the client's tests | `scripts\skill.ps1 test` |

The skill folder is mounted at `/skill`, and commands start there. The Windows **Videos** folder is mounted at
`/videos`, and `YESOPEN_SHORTS_ROOT=/videos/yesopen-skits`, so every skit gets its own project folder in the
subfolder `yesopen-skits` (`%USERPROFILE%\Videos\yesopen-skits\<date>-<slug>`, made by `new_project.py`) and the finals land where you look for videos.
Paths in a command are the container's: `/videos/yesopen-skits/<date>-<slug>/...`, with forward slashes. Put your own input
files (references, clips) in a project folder in Videos so the container can see them.

What does not run in the container: `scripts/capture-reference` (it needs Ego Browser on the host) and anything that
opens a window. Do those on Windows and put the result in the project folder.

## 5. Tell Claude to use it

The skill already points here from `SKILL.md`. If Claude tries bare `python3` or `ffmpeg` on Windows, say once:
"run the skill's commands through `scripts\skill.ps1`".

Ordering a GPU bills from that moment. `gpu up` (and `start`) without `--yes` only shows the plan; with `--yes` it
orders the machine and, if a kept disk named `yesopen-gpu-disk` exists, waits for a free card in the disk's location.

## ComfyUI of the GPU machine in your browser

With a machine running (`scripts\skill.ps1 nebius-up`, or `gpu start --yes` on Verda) and the secrets unlocked:

```powershell
docker compose --profile link up -d comfy-link      # open http://127.0.0.1:8188
docker compose rm -sf comfy-link                    # stop the tunnel
```

The `comfy-link` service reads the machine's address from `state.json`, keeps an SSH tunnel to its ComfyUI and copies
the 15 workflows of `gpu/workflows/ui` into the machine's ComfyUI (panel Workflows, key `W`). It follows a new address
by itself after the next session. It orders and deletes nothing: the machine is ended with `nebius-down` / `gpu stop`.
**Live refresh.** Every browser showing a workflow reloads it when its saved file changes on the machine (a toast says
"Workflow odświeżony", the viewer's zoom and position stay). A tab with unsaved changes of its own is never
overwritten: it only gets a message. This is the small extension in `gpu/server/live_refresh` (it watches the
workflows folder and sends the event `yesopen.workflow_changed`); `comfy-link` copies it to the machine and
`gpu/server/compose.yaml` mounts it, so it is active from ComfyUI's next start. Edit a workflow in the repo, rebuild
it with `python3 gpu/tools/build_pipeline_graph.py` and restart `comfy-link` (it syncs the files): all open screens
update by themselves. Saving in the ComfyUI UI (`Ctrl+S`) refreshes the other open tabs the same way.
**Busy badge.** A badge at the top of every tab (`gpu/server/live_refresh/web/busy_indicator.js`) reads ComfyUI's queue: green "Wolne" = nobody generates, amber = you do, red = another browser does (your Run would queue behind it). Alt+R reloads the open workflow from the server. One "Run" runs the whole GPU pipeline of `yesopen-skit-pipeline` (MiniMax H3 is muted: it needs the vendor's written consent).

**Theme and layout.** `theme.js` installs the One Dark colour palette (VS Code) and selects it on this server, and sets JetBrains Mono (the Nerd Font build when installed, else the web font) with bold node titles and brighter labels. In the pipeline the talking take speaks the Chatterbox line, or the two-voice dialog when "Rozmowa zamiast kwestii" is on in the settings panel; "5a · Podgląd ujęcia z muzyką" mixes the finished take with the music bed (cut to the take, 12 dB down) for a quick listen. The graph's layout and orthogonal wiring come from `gpu/tools/build_pipeline_graph.py` + `graph_layout.py`, using node and socket positions measured in the browser (`gpu/tools/measure_geometry.js` → `comfy_geometry.json`); measure again after changing node sizes, templates or the theme. Links draw at right angles only with the link render mode "Straight" (Settings → Lite Graph → Link Render Mode).

The skill's own commands use the same tunnel from inside the Docker network when you point them at it, for example
`docker compose run --rm --no-deps -T -e GPU_COMFY_URL=http://comfy-link:8188 skill python3 gpu/client/gpu.py health`
(also `batch` and `run`); without it, `gpu start` opens its own tunnel as before.
ComfyUI has no login, so the port is published on 127.0.0.1 only. A colleague on the same network opens it at your
computer's address: start the service with `COMFY_LINK_BIND` set to your LAN address (not `0.0.0.0`, which would also
open every other adapter), for example

```powershell
$env:COMFY_LINK_BIND = '192.168.1.84'     # ipconfig: the IPv4 address of your Ethernet / Wi-Fi
docker compose --profile link up -d comfy-link      # colleague: http://192.168.1.84:8188
```

Windows Firewall must allow Docker Desktop's inbound connection on a private network (a network marked Public blocks it),
and the colleague can then run jobs on the machine you pay for: share the address only with people you trust, and stop
the service (`docker compose rm -sf comfy-link`) when you are done. Over SSH, with his own key on the machine, still works:
`ssh -N -L 8188:127.0.0.1:8188 <user>@<address>`.

## 6. Update

```powershell
git pull                          # new code of the skill (the repo is mounted, so no rebuild is needed)
scripts\skill.ps1 build           # a local image
```

The image is linux/amd64 only and holds no secrets. To rotate a secret, set it again in GitHub Secrets
(`gh secret set VERDA_CLIENT_SECRET`); no image rebuild is needed.
