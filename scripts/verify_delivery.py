#!/usr/bin/env python3
"""Verify a downloaded project's final/manifest.json against every delivered file.

Run on the downloaded project, after gpu.py pull: verify_delivery.py PROJECT.
No provider operations or network requests are performed.
"""
import argparse
import hashlib
import json
from pathlib import Path


def verify(root):
    root = Path(root).resolve()
    data = json.loads((root / 'final/manifest.json').read_text())
    if not data.get('files'):
        raise RuntimeError('Manifest is empty.')
    failed = []
    for item in data['files']:
        path = (root / item['path']).resolve()
        if not path.is_relative_to(root / 'final'):
            raise RuntimeError('Manifest path escapes final/: ' + item['path'])
        if not path.is_file() or path.stat().st_size != item['bytes']:
            failed.append(item['path'])
            continue
        h = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(chunk)
        if h.hexdigest() != item['sha256']:
            failed.append(item['path'])
    if failed:
        raise RuntimeError('Missing or changed delivery files: ' + ', '.join(failed))
    return {'verified_files': len(data['files']), 'project': str(root)}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('project')
    args = ap.parse_args()
    print(json.dumps(verify(args.project), ensure_ascii=False))
