#!/usr/bin/env bash
# Keeps an SSH tunnel from this computer to the ComfyUI of the running GPU machine (Verda or Nebius) and puts the
# skill's ComfyUI workflows into it, so the browser at http://127.0.0.1:8188 shows the pipeline.
#
#   docker compose --profile link up -d comfy-link      (scripts\skill.ps1 comfy-link up)
#
# Reads the machine from $YESOPEN_GPU_HOME/state.json after every drop, so a new session needs no change here:
# `nebius-up` / `gpu start` write the address, this script follows it. Orders nothing and deletes nothing.
# ComfyUI has no login: the port is published on 127.0.0.1 only (docker-compose.yml) and never beyond it.
set -uo pipefail

KEY="$HOME/.ssh/id_ed25519_yesopen_gpu"
STATE="${YESOPEN_GPU_HOME:-$HOME/.config/yesopen-gpu}/state.json"
REMOTE_LIVE=/srv/yesopen/comfy/live_refresh
SSH_OPTS=(-i "$KEY" -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/dev/null
          -o ConnectTimeout=10 -o ServerAliveInterval=30 -o ServerAliveCountMax=3)

[ -s "$KEY" ] || { echo "no SSH key in the container: run scripts\\skill.ps1 unlock first" >&2; exit 1; }

target() {  # prints "<user>@<ip>" for the machine in state.json, or nothing
  python3 - "$STATE" <<'PY'
import json, sys
try:
    s = json.load(open(sys.argv[1]))
except (OSError, ValueError):
    sys.exit(0)
ip = s.get("ip")
if ip:
    print(f"{s.get('ssh_user') or 'root'}@{ip}")
PY
}

sync_workflows() {  # install the active project graphs; obsolete versions are recoverable in an archive
  local host="$1"
  # One main graph, related templates in their own folder, obsolete previews outside the workflow browser.
  python3 "${SKILL_DIR:-/skill}/gpu/tools/install_comfy_workspace.py" "$host" || return 1
  echo "workflows synced to $host"
}

sync_live_refresh() {  # the live-refresh extension (gpu/server/live_refresh): picked up by ComfyUI at its next start
  local host="$1" tmp="/tmp/live-$(date +%s)"
  ssh "${SSH_OPTS[@]}" "$host" "mkdir -p $tmp/web" || return 1
  scp -q "${SSH_OPTS[@]}" "${SKILL_DIR:-/skill}/gpu/server/live_refresh/__init__.py" "$host:$tmp/" || return 1
  scp -q "${SSH_OPTS[@]}" "${SKILL_DIR:-/skill}"/gpu/server/live_refresh/web/*.js "$host:$tmp/web/" || return 1
  ssh "${SSH_OPTS[@]}" "$host" "sudo mkdir -p $REMOTE_LIVE/web && sudo cp $tmp/__init__.py $REMOTE_LIVE/ && sudo cp $tmp/web/*.js $REMOTE_LIVE/web/" || return 1
  echo "live-refresh extension synced to $host"
}

sync_pipeline() {  # the YesOpen pipeline nodes, the editor service and the skill's scripts the service runs
  local host="$1" skill="${SKILL_DIR:-/skill}"
  tar -C "$skill/gpu/server" --exclude=__pycache__ -czf - yesopen_pipeline \
    | ssh "${SSH_OPTS[@]}" "$host" "sudo mkdir -p /srv/yesopen/comfy && sudo tar -C /srv/yesopen/comfy -xzf -" || return 1
  tar -C "$skill/gpu" -czf - editor/api.py \
    | ssh "${SSH_OPTS[@]}" "$host" "sudo mkdir -p /srv/yesopen/stack && sudo tar -C /srv/yesopen/stack -xzf -" || return 1
  # what the editor needs: scripts, brand assets, templates (not the examples, the GPU stack or the Git history)
  tar -C "$skill" --exclude=__pycache__ --exclude='*.pyc' -czf - scripts assets templates SKILL.md \
    | ssh "${SSH_OPTS[@]}" "$host" "sudo mkdir -p /srv/yesopen/skill && sudo tar -C /srv/yesopen/skill -xzf -" || return 1
  echo "pipeline nodes, editor service and skill scripts synced to $host"
}

last=""
while true; do
  host="$(target)"
  if [ -z "$host" ]; then
    echo "no machine in state.json; waiting (start one with nebius-up or gpu start --yes)"
    sleep 15; continue
  fi
  if ! ssh "${SSH_OPTS[@]}" "$host" true 2>/dev/null; then
    echo "$host does not answer on SSH; retrying"
    sleep 10; continue
  fi
  if [ "$host" != "$last" ]; then
    sync_workflows "$host" || echo "workflow sync failed (the tunnel still comes up)"
    sync_live_refresh "$host" || echo "live-refresh sync failed (the tunnel still comes up)"
    sync_pipeline "$host" || echo "pipeline sync failed (the tunnel still comes up)"
    last="$host"
  fi
  echo "tunnel: 127.0.0.1:8188 -> $host:8188"
  ssh -N "${SSH_OPTS[@]}" -o ExitOnForwardFailure=yes -L 0.0.0.0:8188:127.0.0.1:8188 "$host"
  echo "tunnel dropped; checking the machine again"
  sleep 5
done
