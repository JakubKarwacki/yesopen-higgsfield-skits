#!/usr/bin/env bash
# Prepare a GPU machine and start ComfyUI: Ubuntu 24.04 with the NVIDIA driver, Docker and the NVIDIA Container
# Toolkit (at Verda: the image ubuntu-24.04-cuda-13.0-open-docker). Run as root, from client/gpu.py start or
# bootstrap, which copy the skill's gpu/ folder to /srv/yesopen/stack and the HF token to server/.env.
#
# Safe to run again, also on a kept disk: every step checks first, models already in place are not downloaded,
# image layers come from the cache.
set -euo pipefail

ROOT=${YESOPEN_DATA:-/srv/yesopen}
STACK=$ROOT/stack
step() { printf '\n== %s\n' "$*"; }

step "1/6 GPU and Docker"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
docker compose version >/dev/null 2>&1 || { echo "docker compose plugin missing"; exit 1; }
docker run --rm --gpus all ubuntu:24.04 nvidia-smi -L >/dev/null || { echo "Docker cannot see the GPU"; exit 1; }
echo "Docker sees the GPU"

step "2/6 firewall and SSH"
# Allow SSH before denying the rest, so this session survives. ComfyUI is published on 127.0.0.1 only,
# so the firewall is a second line, not the only one (Docker's own rules bypass ufw for published ports).
if ! command -v ufw >/dev/null; then apt-get update -qq && apt-get install -y -qq ufw; fi
ufw allow OpenSSH >/dev/null
ufw default deny incoming >/dev/null
ufw default allow outgoing >/dev/null
ufw --force enable >/dev/null
ufw status | head -4
# sshd keeps the first value it reads, so this file must sort before cloud-init's 50-cloud-init.conf.
conf=/etc/ssh/sshd_config.d/01-yesopen.conf
if [ ! -f "$conf" ]; then
  cat > "$conf" <<'EOF'
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
PermitEmptyPasswords no
EOF
  if sshd -t; then systemctl reload ssh; else rm -f "$conf"; echo "sshd rejected the drop-in; removed it"; exit 1; fi
fi
sshd -T 2>/dev/null | grep -E '^(passwordauthentication|permitrootlogin|kbdinteractiveauthentication) '
sshd -T 2>/dev/null | grep -qx 'passwordauthentication no' || echo "WARNING: SSH still accepts passwords, check /etc/ssh/sshd_config.d"

step "3/6 folders"
mkdir -p "$ROOT"/{models,comfy/input,comfy/output,comfy/user,projects,skill,cache/whisper}
chmod 700 "$ROOT"
df -h "$ROOT" | tail -1

step "4/6 images (building in the background) and the models needed first"
cd "$STACK/server"
(docker compose build comfyui && docker compose --profile edit build editor) > "$ROOT/build.log" 2>&1 &
build=$!
set -a
# shellcheck source=/dev/null
[ -f .env ] && . ./.env
set +a
[ -n "${HF_TOKEN:-}" ] || echo "no HF_TOKEN: the gated LTX-2.5 files (action shots) will be skipped"
python3 fetch_models.py --models "$ROOT/models" --stage before_start --jobs 6
if ! wait "$build"; then tail -40 "$ROOT/build.log"; exit 1; fi
echo "images built"

step "5/6 ComfyUI"
docker compose up -d comfyui
for _ in $(seq 1 90); do
  curl -fsS http://127.0.0.1:8188/system_stats >/dev/null 2>&1 && break
  sleep 5
done
curl -fsS http://127.0.0.1:8188/system_stats | python3 -c '
import json, sys
d = json.load(sys.stdin)
print("ComfyUI", d["system"]["comfyui_version"], "on", ", ".join(x["name"] for x in d["devices"]))'

step "6/6 remaining models in the background"
nohup python3 fetch_models.py --models "$ROOT/models" --stage after_start --jobs 6 > "$ROOT/fetch-after-start.log" 2>&1 &
echo "follow with: tail -f $ROOT/fetch-after-start.log"
echo "ready: gpu.py start on your computer opens the tunnel and checks the server (or gpu.py tunnel, gpu.py health)"
