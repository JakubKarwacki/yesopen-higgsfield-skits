#!/usr/bin/env python3
"""Sync pipeline sources and workflows to the existing machine; never provisions compute.

Run through scripts/skill.ps1 python3 gpu/tools/deploy_pipeline.py [--cpu] [--test].
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'client'))
import nebius_session as session


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cpu', action='store_true')
    ap.add_argument('--test', action='store_true')
    args = ap.parse_args()
    state = session.load_state()
    ip = state.get('ip')
    if not ip:
        raise SystemExit('No running machine recorded; this command does not create one.')
    def remote(command, timeout=180):
        result = session.ssh(ip, command, timeout)
        if result.stdout:
            print(result.stdout, flush=True)
        if result.stderr and result.returncode == 0:
            print(result.stderr, flush=True)
        if result.returncode:
            raise SystemExit(result.stderr or f'Failed: {command}')
        return result.stdout
    queue = json.loads(remote('curl -fsS -m 8 http://127.0.0.1:8188/queue'))
    if queue.get('queue_running') or queue.get('queue_pending'):
        raise SystemExit('ComfyUI is busy; no files were changed.')
    keyopts = ['-i', str(session.KEY), '-o', f'UserKnownHostsFile={session.KNOWN_HOSTS}',
               '-o', 'StrictHostKeyChecking=accept-new']
    user = state.get('ssh_user') or 'nebius'
    def copy(source, destination):
        session.run(['scp', *keyopts, str(source), f'{user}@{ip}:/tmp/yesopen-pipeline-upload'])
        remote(f'sudo cp /tmp/yesopen-pipeline-upload {destination}')
    root = Path(__file__).resolve().parents[2]
    remote('sudo mkdir -p /srv/yesopen/comfy/yesopen_pipeline /srv/yesopen/stack/server')
    for name in ['__init__.py', 'runtime.py']:
        copy(root / 'gpu/server/yesopen_pipeline' / name, '/srv/yesopen/comfy/yesopen_pipeline/' + name)
    copy(root / 'gpu/workflows/pipeline/yesopen-skit-pipeline.json',
         '/srv/yesopen/comfy/user/default/workflows/yesopen-skit-pipeline.json')
    if args.test:
        copy(root / 'gpu/tests/test_pipeline_nodes.py', '/tmp/yesopen-pipeline-tests.py')
        remote('docker cp /tmp/yesopen-pipeline-tests.py yesopen-comfyui-1:/tmp/yesopen-pipeline-tests.py')
        remote('docker exec -e YESOPEN_NODE_DIR=/opt/ComfyUI/custom_nodes/yesopen_pipeline yesopen-comfyui-1 python /tmp/yesopen-pipeline-tests.py')
    copy(root / 'gpu/server/compose.yaml', '/srv/yesopen/stack/server/compose.yaml')
    command = 'docker compose -f /srv/yesopen/stack/server/compose.yaml'
    if args.cpu:
        copy(root / 'gpu/server/compose.cpu.yaml', '/srv/yesopen/stack/server/compose.cpu.yaml')
        command += ' -f /srv/yesopen/stack/server/compose.cpu.yaml'
    # Recheck after tests/copying: never restart another operator's active work.
    queue = json.loads(remote('curl -fsS -m 8 http://127.0.0.1:8188/queue'))
    if queue.get('queue_running') or queue.get('queue_pending'):
        raise SystemExit('A job arrived; files synced but restart deferred.')
    remote(command + ' restart comfyui')
    print('Synced; ComfyUI is restarting. No generation submitted.')


if __name__ == '__main__':
    main()
