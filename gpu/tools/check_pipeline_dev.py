"""Read-only model checks and regressions on the explicitly selected dev server; no generations."""
import io
import shlex
import subprocess
import sys
import tarfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'client'))
import nebius_session as n

root = Path(__file__).resolve().parents[2]
state = n.load_state()
assert state.get('disk_id') == 'computedisk-e00ybjw8kgzj9ye54g', 'Select the dev disk first'
payload = io.BytesIO()
with tarfile.open(fileobj=payload, mode='w:gz') as archive:
    for name in ['gpu/tests', 'gpu/client', 'gpu/workflows', 'gpu/server/yesopen_pipeline', 'scripts', 'templates']:
        archive.add(root / name, arcname=name, filter=lambda member: None if '__pycache__' in member.name else member)
target = '/srv/yesopen/projects/.pipeline-regressions'
command = ['ssh', '-i', str(n.KEY), '-o', 'IdentitiesOnly=yes', '-o', f'UserKnownHostsFile={n.KNOWN_HOSTS}',
           '-o', 'StrictHostKeyChecking=accept-new', f'nebius@{state["ip"]}', f'sudo mkdir -p {target} && sudo tar -C {target} -xzf -']
upload = subprocess.run(command, input=payload.getvalue(), capture_output=True)
assert upload.returncode == 0, upload.stderr.decode()
cmd = 'docker exec -e YESOPEN_NODE_DIR=/work/.pipeline-regressions/gpu/server/yesopen_pipeline yesopen-comfyui-1 python -m unittest discover -s /work/.pipeline-regressions/gpu/tests -p test_pipeline_nodes.py'
result = n.ssh(state['ip'], cmd, timeout=120)
print(result.stdout)
print(result.stderr)
sys.exit(result.returncode)
