"""Install the project's active workflows and archive obsolete previews on the kept disk."""
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1] / 'workflows'
SSH = ['ssh', '-i', str(Path.home() / '.ssh/id_ed25519_yesopen_gpu'),
       '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new',
       '-o', 'UserKnownHostsFile=/dev/null', '-o', 'ConnectTimeout=10']


def main():
    host = sys.argv[1]
    payload = io.BytesIO()
    with tarfile.open(fileobj=payload, mode='w:gz') as archive:
        for path in sorted((ROOT / 'ui').glob('*.json')):
            if path.name != 'index.json':
                archive.add(path, arcname='templates/' + path.name)
        archive.add(ROOT / 'pipeline/yesopen-skit-pipeline.json', arcname='yesopen-skit-pipeline.json')
        api_types = set()
        for path in (ROOT / 'api').glob('*.json'):
            graph = json.loads(path.read_text(encoding='utf-8'))
            api_types.update(node['class_type'] for node in graph.values()
                             if isinstance(node, dict) and 'class_type' in node)
        data = json.dumps(sorted(api_types)).encode()
        info = tarfile.TarInfo('node-types.txt')
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    remote = '/tmp/yesopen-workflows-install.tar.gz'
    subprocess.run(SSH + [host, 'cat > ' + remote], input=payload.getvalue(), check=True)
    script = r'''
from datetime import datetime, timezone
from pathlib import Path
import shutil
import tarfile
import tempfile
root = Path('/srv/yesopen/comfy/user/default/workflows')
backup = Path('/srv/yesopen/comfy/workflow-archive') / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
root.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='yesopen-workflows-') as temp:
    with tarfile.open('/tmp/yesopen-workflows-install.tar.gz') as archive:
        archive.extractall(temp, filter='data')
    staging = Path(temp)
    desired = {p.relative_to(staging) for p in staging.rglob('*.json')}
    archived = 0
    for existing in list(root.rglob('*.json')):
        rel = existing.relative_to(root)
        source = staging / rel
        obsolete = rel not in desired
        changed = source.exists() and existing.read_bytes() != source.read_bytes()
        if obsolete or changed:
            destination = backup / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(existing), str(destination))
            archived += 1
    for rel in desired:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != (staging / rel).read_bytes():
            shutil.copyfile(staging / rel, target)
    shutil.copyfile(staging / 'node-types.txt', root.parent / 'yesopen-node-types.json')
    print(f'Installed {len(desired)} project workflows; archived {archived} previous files at {backup}')
Path('/tmp/yesopen-workflows-install.tar.gz').unlink()
'''
    subprocess.run(SSH + [host, 'sudo python3 -'], input=script.encode(), check=True)


if __name__ == '__main__':
    main()
