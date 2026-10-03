"""Offline source preflight, not an audition or proof that a rights declaration is true.

Usage: python3 verify_voice_sources.py PROJECT
Reads voices/provenance.json (list of source records), lines.json and project.json.
Requires each selected speaker to have one matching source record with character,
candidate, sha256, source, rights_basis (synthetic/written_consent), evidence and
voice_description. Rejected historical records may remain in the list.
"""
import argparse
import hashlib
import json
from pathlib import Path


def validate(project):
    project = Path(project).resolve()
    lines = json.loads((project / 'lines.json').read_text())
    config = json.loads((project / 'project.json').read_text())
    speakers = sorted({line['who'] for line in lines.get('lines', [])})
    if not speakers:
        return {'ok': True, 'speakers': [], 'note': 'No dialogue sources required'}
    records = json.loads((project / 'voices/provenance.json').read_text())
    if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
        raise ValueError('voices/provenance.json must contain a list of records')
    checked = []
    for speaker in speakers:
        voice = lines['characters'][speaker]['voice']
        path = (project / voice).resolve()
        cast_voice = config.get('cast', {}).get(speaker, {}).get('voice')
        if not cast_voice or (project / cast_voice).resolve() != path:
            raise ValueError(f'{speaker}: lines.json and project.json voice selection differs')
        matches = [row for row in records if row.get('character') == speaker
                   and row.get('candidate') and (project / row['candidate']).resolve() == path]
        if len(matches) != 1:
            raise ValueError(f'{speaker}: require exactly one provenance record for selected voice')
        row = matches[0]
        state = row.get('status', '')
        if not isinstance(state, str) or state.startswith(('rejected', 'superseded')):
            raise ValueError(f'{speaker}: selected source is rejected/superseded or has invalid status')
        for key in ('source', 'evidence', 'voice_description'):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f'{speaker}: missing {key}')
        if row.get('rights_basis') not in ('synthetic', 'written_consent'):
            raise ValueError(f'{speaker}: missing supported rights basis')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if row.get('sha256') != digest:
            raise ValueError(f'{speaker}: selected voice hash differs from provenance')
        checked.append({'character': speaker, 'sha256': digest})
    return {'ok': True, 'speakers': checked,
            'note': 'Declarations and file identity checked; rights evidence needs operator verification; listening not assessed'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.project)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f'Voice source preflight failed: {error}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
