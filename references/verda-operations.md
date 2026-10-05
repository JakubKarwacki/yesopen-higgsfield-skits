# Verda operations: CLI/API first, preserve every disk

## Policy

After GPU use, DELETE the instance and PRESERVE ALL disks/volumes, including OS and detached volumes. This explicit standing user instruction supersedes historical stop-only and leave-running directions. Do not ask again merely because old notes disagree. Never interrupt actual active/queued shared compute. A completed film awaiting review is not active computation.

Use authenticated CLI/API before UI. Ego Browser is only a necessary bootstrap/fallback. Never use Chrome. Confirm the project and resource IDs live; stale saved IPs are not identity proof.

## Authentication

Install/use the official `verda` CLI. The bundled `scripts/verda-vault.py` loads client ID and secret from the agent-passwords encrypted vault into process environment. Default entry: `Verda API - YesOpen Video`; override entry name with `VERDA_VAULT_ENTRY`. Requires the agent-passwords helper in `~/.agents/skills/agent-passwords/scripts/vault.py`. Never print secrets, enable debug, pass secrets in command arguments or commit plaintext credential files. Credential creation/renewal may require Ego Browser. Record expiry without recording secrets. Existing project credential was created 2026-10-03 with 30-day validity.

## Operations

Run from this skill directory:

```sh
python3 scripts/verda-vault.py vm list --agent
python3 scripts/verda-vault.py volume list --agent
python3 scripts/verda-vault.py vm start INSTANCE_ID --yes --agent
python3 scripts/verda-vault.py vm shutdown INSTANCE_ID --yes --agent
python3 scripts/verda-vault.py vm delete INSTANCE_ID --yes --agent
```

`gpu/client/gpu.py` (`start`, `stop`, `up`, `down`, `status`) drives the same CLI and makes machines too (`vm create`, which this helper does not allow). It needs the CLI's own login (`verda auth login`, done by the account holder) or the two variables in its environment; `python3 gpu/client/gpu.py verda-check` says which is missing, and the session commands refuse to run until it passes.

`shutdown` is a temporary operational pause and continues instance billing. Retirement uses `delete`, NEVER `--with-volumes`. Deleted compute must be recreated for a future authorized session using retained disks; `start` only starts an existing instance.

Before deletion: download and verify required artifacts; record all disk IDs; verify project/instance; drain coordinator if deployed; check native queues and CPU/GPU/export/transfer processes across projects. Resident models or historical CPU averages do not establish active work. Unknown live state requires reconciliation, not an invented active job.

After deletion: query VM and volume lists; confirm target absent and every original volume retained. Save UTC timestamp, project/instance IDs, before/after disk inventories and provider evidence in checkpoint. Report storage charges honestly. List/read authentication was verified live on 2026-10-03; start/shutdown syntax was checked without creating a paid test instance. The helper is credential transport, not an automatic workload/retirement controller.
