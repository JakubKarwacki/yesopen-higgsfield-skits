# Nebius access with an individual service account

Each operator uses their own Nebius service account, authorized key and vault entry. This repository contains no shared account, private key, token, project ID or disk ID.

## Setup

1. Install the native Nebius CLI at `~/.local/lib/nebius/nebius` and the local Agent KeePassXC vault helper at `~/.agents/skills/agent-passwords/scripts/vault.py`.
2. Create your own service account and authorized key in Nebius. Grant only the required project-scoped role (the farm uses project editor); do not grant tenant administrator access for routine operations.
3. Store the account in your own vault entry: username = service account ID, password = base64-encoded private PEM key. Transfer secrets through stdin/process memory, never command arguments, logs or committed files. Base64 is transport encoding, not encryption.
4. Copy `gpu/client/nebius.example.json` to `~/.config/yesopen-gpu/nebius.json` and replace the placeholders with your own non-secret identifiers and vault entry name. `YESOPEN_NEBIUS_CONFIG` may select another local settings file. Keep that file outside Git.
5. Prevent native CLI plaintext credential caching: on a fresh setup point `~/.nebius/credentials.yaml` to `/dev/null`. If an existing cache is present, securely migrate/remove it first; do not overwrite an existing user's setup blindly. The wrapper supplies configuration through an anonymous pipe; the native CLI requests fresh short-lived tokens using your service-account key.
6. Run `python3 scripts/nebius-vault.py iam whoami --format json`, then `python3 scripts/nebius-vault.py compute instance list --all --format json` to verify identity and project access.

The wrapper has no fallback to another operator's account. The supplied vault username must match the configured service account. Each operator is responsible for their own key rotation/revocation and project access.

## Persistent disks and SSH

Create standalone protected disks and attach them as `existing_disk`, never as managed disks that would be deleted with the instance. Preserve every disk on retirement; inspect the instance specification before Delete and verify all disks afterwards. The wrapper blocks direct disk deletion, but is not a complete policy enforcement boundary.

Use a non-root SSH user (for example `nebius`) with `/bin/bash`, an authorized public key and the required sudo policy. Nebius prohibits SSH login as `root` and `admin`. Keep private SSH keys local.

## Installation and current scope

The same `gpu/server` and `gpu/editor` sources and model manifest can prepare a Nebius disk. A CPU preparation VM can build both Docker images and download models; do not run `bootstrap.sh` unchanged on CPU because it requires a GPU. Pass any required Hugging Face token only in process memory. Keep ComfyUI ports bound to localhost and access them through SSH tunnels.

Verified on a 600 GiB disk: 50 model files including LTX and MiniMax H3, both images, ComfyUI 0.35.0 CPU API, all node classes required by the 16 API workflows, editor imports/FFmpeg and Whisper cache. GPU generation has not been tested on Nebius. Model weights and operational checkpoints do not belong in this Git repository.

This is manual Nebius access and preparation support. Automatic Verda-first/Nebius fallback is not implemented in `gpu.py` yet.
