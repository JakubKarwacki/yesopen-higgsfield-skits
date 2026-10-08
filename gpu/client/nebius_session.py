#!/usr/bin/env python3
"""A GPU session on Nebius: one H200/H100 machine on the kept disk, made and deleted with the Nebius CLI.

  nebius_session.py up [--dry-run]    make the machine, start ComfyUI, record its address in state.json
  nebius_session.py down [--force]    stop ComfyUI, DELETE the machine, check the kept disk is still READY

Run it through `scripts\\skill.ps1 nebius-up` / `nebius-down` (needs the profile from `skill.ps1 nebius-config` and the
SSH key from the secrets sidecar). After `up`, open a shell (`skill.ps1 shell`) and run `gpu.py tunnel`.
The disk is never deleted. A stopped machine is billed too, so `down` always deletes.
"""
import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

HOME = Path(os.environ.get("YESOPEN_GPU_HOME", "~/.config/yesopen-gpu")).expanduser()
SETTINGS = HOME / "nebius" / "nebius.json"
STATE = HOME / "state.json"
KNOWN_HOSTS = Path("~/.ssh/known_hosts_yesopen_gpu").expanduser()
KEY = Path("~/.ssh/id_ed25519_yesopen_gpu").expanduser()
COMPOSE = "/srv/yesopen/stack/server/compose.yaml"
SSH_USER = "nebius"

# tried in this order until one has a free card: H200, H200 at spot prices (for short sessions), H100
VARIANTS = [
    ("H200", "gpu-h200-sxm", "1gpu-16vcpu-200gb", False),
    ("H200 preemptible", "gpu-h200-sxm", "1gpu-16vcpu-200gb", True),
    ("H100", "gpu-h100-sxm", "1gpu-16vcpu-200gb", False),
]


def run(cmd, check=True, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, check=check, **kw)


def nebius(*args, check=True):
    return run(["nebius", *args], check=check)


def nebius_json(*args):
    result = nebius(*args, "--format", "json")
    return json.loads(result.stdout) if result.stdout.strip() else {}


def settings() -> dict:
    if not SETTINGS.exists():
        sys.exit("no Nebius settings: run scripts\\skill.ps1 nebius-config <nebius-name.json> <publickey-id>")
    return json.loads(SETTINGS.read_text(encoding="utf-8-sig"))


def instance_name(cfg) -> str:
    return "yesopen-gpu-" + cfg["vault_entry"].rsplit("-", 1)[-1].strip().lower()


def load_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save_state(state: dict):
    STATE.write_text(json.dumps(state, indent=2) + "\n")


def instances() -> list:
    return nebius_json("compute", "instance", "list").get("items", [])


def ssh(ip: str, command: str, timeout=60):
    return run(["ssh", "-i", str(KEY), "-o", "IdentitiesOnly=yes", "-o", f"UserKnownHostsFile={KNOWN_HOSTS}",
                "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=8", f"{SSH_USER}@{ip}", command],
               check=False, timeout=timeout)


def public_ip(instance: dict):
    for nic in instance.get("status", {}).get("network_interfaces", []):
        address = (nic.get("public_ip_address") or {}).get("address")
        if address:
            return address.split("/")[0]


def wait_for(what, test, timeout, step=5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if test():
                return
        except subprocess.TimeoutExpired:
            pass
        time.sleep(step)
    sys.exit(f"timed out waiting for {what}. The machine is still running: finish with `nebius-down`")


def cmd_up(args):
    cfg = settings()
    if cfg["public_key_id"].startswith("PUBLICKEY_ID"):
        sys.exit("the settings still hold the placeholder key id")
    pub_key = "ssh-ed25519 DRY-RUN"
    if not args.dry_run:
        if not KEY.exists():
            sys.exit(f"no SSH key in {KEY}: run scripts\\skill.ps1 unlock first")
        pub = Path(str(KEY) + ".pub")
        pub_key = pub.read_text().strip() if pub.exists() else run(["ssh-keygen", "-y", "-f", str(KEY)]).stdout.strip()

    running = instances()
    if running:
        names = ", ".join(f"{i['metadata']['name']} ({i['metadata']['id']})" for i in running)
        sys.exit(f"the disk is in use, instance list is not empty: {names}\nAsk on Slack, do not start a second one.")
    disks = nebius_json("compute", "disk", "list").get("items", [])
    disk = next((d for d in disks if d["metadata"]["id"] == cfg["disk_id"]), None)
    if not disk or disk.get("status", {}).get("state") != "READY":
        sys.exit(f"disk {cfg['disk_id']} is not READY: {disk and disk.get('status', {}).get('state')}")

    user_data = ("#cloud-config\nusers:\n  - name: nebius\n    sudo: ALL=(ALL) NOPASSWD:ALL\n    shell: /bin/bash\n"
                 f"    groups: [docker]\n    ssh_authorized_keys:\n      - {pub_key}\n")
    nics = json.dumps([{"subnet_id": cfg["subnet_id"], "name": "eth0", "ip_address": {}, "public_ip_address": {}}])
    name = instance_name(cfg)

    instance = None
    for label, platform, preset, spot in VARIANTS:
        cmd = ["compute", "instance", "create", "--name", name, "--parent-id", cfg["project_id"],
               "--resources-platform", platform, "--resources-preset", preset,
               "--boot-disk-attach-mode", "READ_WRITE", "--boot-disk-existing-disk-id", cfg["disk_id"],
               "--network-interfaces", nics, "--cloud-init-user-data", user_data, "--format", "json"]
        if spot:
            cmd += ["--preemptible-on-preemption", "STOP"]
        if args.dry_run:
            print(f"[{label}] nebius " + " ".join(shlex.quote(c) for c in cmd[:14]) + " ...")
            continue
        print(f"trying {label} ({platform}) ...", flush=True)
        result = nebius(*cmd, check=False)
        if result.returncode == 0:
            instance = json.loads(result.stdout)
            print(f"{label}: created")
            break
        print(f"{label}: no ({(result.stderr or result.stdout).strip().splitlines()[-1][:200] if (result.stderr or result.stdout).strip() else 'failed'})")
        # a failed attempt must not leave a machine holding the disk
        for leftover in instances():
            print(f"removing the leftover {leftover['metadata']['id']}")
            nebius("compute", "instance", "delete", "--id", leftover["metadata"]["id"], check=False)
    if args.dry_run:
        return 0
    if not instance:
        sys.exit("no H200 / H200 preemptible / H100 available now. Try again later or use Verda.")

    instance_id = instance["metadata"]["id"]
    ip = public_ip(instance) or public_ip(nebius_json("compute", "instance", "get", "--id", instance_id))
    state = load_state()
    state.update({"instance_id": None, "nebius_instance_id": instance_id, "ip": ip, "ssh_user": SSH_USER,
                  "provider": "nebius"})
    save_state(state)   # first, so that `down` finds the machine whatever fails next
    if not ip:
        sys.exit(f"instance {instance_id} has no public address; delete it with nebius-down")
    run(["ssh-keygen", "-R", ip, "-f", str(KNOWN_HOSTS)], check=False)
    print(f"instance {instance_id} at {ip}; waiting for SSH ...", flush=True)
    wait_for("SSH", lambda: ssh(ip, "true").returncode == 0, 300)
    # ComfyUI wakes after about 40 s; the compose file is on the kept disk
    result = ssh(ip, f"docker compose -f {COMPOSE} up -d comfyui", 300)
    if result.returncode != 0:
        sys.exit(f"ComfyUI did not start: {result.stderr.strip()[-400:]}\nThe machine is running: nebius-down deletes it.")
    wait_for("ComfyUI", lambda: ssh(ip, "curl -fsS -m 5 http://127.0.0.1:8188/system_stats >/dev/null").returncode == 0,
             240)
    print(f"ready: {SSH_USER}@{ip}. Next, in `scripts\\skill.ps1 shell`: python3 gpu/client/gpu.py tunnel")
    print("When done: scripts\\skill.ps1 nebius-down   (a forgotten H200 is about $85 a day)")
    return 0


def cmd_down(args):
    cfg = settings()
    state = load_state()
    ip = state.get("ip")
    found = instances()
    mine = [i for i in found if i["metadata"]["id"] == state.get("nebius_instance_id")] \
        or [i for i in found if i["metadata"]["name"] == instance_name(cfg)]
    if not mine:
        print("no instance of yours" + (f" (others exist: {[i['metadata']['name'] for i in found]})" if found else ""))
    for inst in mine:
        ip = ip or public_ip(inst)
        if ip and not args.force:
            queue = ssh(ip, "curl -s -m 8 http://127.0.0.1:8188/queue")
            try:
                q = json.loads(queue.stdout)
                busy = len(q.get("queue_running", [])) + len(q.get("queue_pending", []))
            except ValueError:
                busy = 0   # ComfyUI not answering: nothing to protect
            if busy:
                sys.exit(f"ComfyUI has {busy} job(s) in the queue (maybe someone else's). Wait, or use --force.")
            ssh(ip, f"docker compose -f {COMPOSE} stop comfyui", 120)
        run(["pkill", "-f", "ssh.*-L 8188"], check=False)
        print(f"deleting {inst['metadata']['id']} ...", flush=True)
        nebius("compute", "instance", "delete", "--id", inst["metadata"]["id"])
    state.update({"nebius_instance_id": None, "ip": None, "ssh_user": None, "provider": None})
    save_state(state)

    left = instances()
    disks = nebius_json("compute", "disk", "list").get("items", [])
    disk_state = next((d.get("status", {}).get("state") for d in disks if d["metadata"]["id"] == cfg["disk_id"]), None)
    print(f"instances left in the project: {len(left)}; disk yesopen-gpu-disk: {disk_state}")
    if any(i["metadata"]["name"] == instance_name(cfg) for i in left):
        sys.exit("YOUR INSTANCE IS STILL LISTED. Check it in the Nebius console and delete it.")
    if disk_state != "READY":
        sys.exit("the disk is not READY: check the console, do not delete it")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    up = sub.add_parser("up")
    up.add_argument("--dry-run", action="store_true", help="show the create commands, change nothing")
    up.set_defaults(fn=cmd_up)
    down = sub.add_parser("down")
    down.add_argument("--force", action="store_true", help="delete even with jobs in the ComfyUI queue")
    down.set_defaults(fn=cmd_down)
    args = parser.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
