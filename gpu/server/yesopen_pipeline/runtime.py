"""Project checkpoints and validation shared by the ComfyUI nodes (stdlib only)."""
import hashlib
import json
import threading
from pathlib import Path

LOCK = threading.RLock()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    if path.is_file() and path.read_text() == body:
        return
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(body)
    tmp.replace(path)


def checkpoint(root, stage, files):
    with LOCK:
        path = root / 'edit' / 'pipeline-state.json'
        data = json.loads(path.read_text()) if path.exists() else {}
        data[stage] = {str(p.relative_to(root)): digest(p) for p in files}
        write_json(path, data)


def cached(root, stage):
    path = root / 'edit/pipeline-state.json'
    data = json.loads(path.read_text()) if path.exists() else {}
    files = data.get(stage, {})
    return bool(files) and all((root / p).is_file() and digest(root / p) == h for p, h in files.items())


def signature(root, line, seed=None, prompt=None, unique_id=None, input_name=None):
    doc = json.loads((root / 'lines.json').read_text())
    entry = next(item for item in doc['lines'] if item['id'] == line) if line else {}
    char = doc['characters'][entry['who']] if line else {}
    values = {'line': entry, 'character': char, 'language': doc.get('language'), 'take': doc.get('take'), 'seed': seed}
    cfg = json.loads((root / 'project.json').read_text())
    values['policy'] = {'speech': cfg.get('speech'), 'language': cfg.get('language')}
    if line is None:
        values['policy']['music'] = cfg.get('music')
    values['fit'] = doc.get('fit')
    names = [char.get('voice'), entry.get('still') or char.get('still')]
    if input_name == 'video':
        names.append(f'lines/{line}.wav')
        for variant in entry.get('variants', {}).values():
            names.extend(value for key, value in variant.get('set', {}).items()
                         if key in ('image', 'audio', 'video', 'first_frame', 'last_frame') and isinstance(value, str))
        from .generation import workflows
        assets = workflows()
        take = doc.get('take', {})
        templates = {'h3-talk' if entry.get('model', take.get('model', 'h3')) == 'h3' else 'talk'}
        post = {**take.get('postprocess', {}), **entry.get('postprocess', {})}
        templates.update(key for key, settings in post.items() if settings.get('enabled'))
        templates.update(v.get('template') for v in entry.get('variants', {}).values())
        values['templates'] = {str(p.relative_to(assets)): digest(p) for template in templates if template
                               for p in (assets / 'api' / f'{template}.json', assets / 'params' / f'{template}.json') if p.is_file()}
        values['contract'] = {p.name: digest(p) for p in [Path(__file__), Path(__file__).with_name('generation.py'), Path(__file__).with_name('contracts.py')]}
    values['files'] = {name: digest(root / name) for name in names if name and (root / name).is_file()}
    if input_name and prompt and unique_id:
        edge = prompt.get(str(unique_id), {}).get('inputs', {}).get(input_name)
        todo, seen, graph = [str(edge[0])] if isinstance(edge, list) else [], set(), {}
        while todo:
            nid = todo.pop()
            if nid in seen:
                continue
            seen.add(nid)
            node = prompt.get(nid, {})
            kind = node.get('class_type', '')
            if kind.startswith('YesOpen'):
                # Keep voice seed/line selection without approval/cache/UI switches.
                if kind == 'YesOpenLine':
                    graph[nid] = {'class_type': kind, 'inputs': {k: v for k, v in node.get('inputs', {}).items() if k in ('line', 'take')}}
                elif kind not in {'YesOpenVoiceApproval', 'YesOpenFitLine', 'YesOpenGenerateTake'}:
                    continue
            else:
                graph[nid] = node
            for value in node.get('inputs', {}).values():
                if isinstance(value, list) and len(value) == 2:
                    todo.append(str(value[0]))
        values['graph'] = graph
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def reusable(root, stage, source_file, expected):
    path = root / source_file
    return cached(root, stage) and path.is_file() and json.loads(path.read_text()).get('signature') == expected


def require_files(root, names):
    missing = [name for name in names if not (root / name).is_file()]
    if missing:
        raise RuntimeError('Brak plików: ' + ', '.join(missing))


def require_takes(root):
    require_files(root, ['project.json', 'lines.json', 'edit/cuts.json'])
    cuts = json.loads((root / 'edit/cuts.json').read_text()).get('cuts', [])
    if not cuts:
        raise RuntimeError('edit/cuts.json: brak ujęć do montażu.')
    cfg = json.loads((root / 'project.json').read_text())
    doc = json.loads((root / 'lines.json').read_text())
    known = {line['id'] for line in doc['lines']}
    ids = {c['take'] for c in cuts}
    ids.update(e['take'] for c in cuts for e in c.get('events', []) if e['type'] == 'cutaway')
    covered = {line for line in known if line in ids or any(take.startswith(line + '-') for take in ids)}
    omitted = set(cfg.get('edit', {}).get('omitted_lines', []))
    if known - covered - omitted:
        raise RuntimeError('cuts.json pomija kwestie bez jawnej decyzji edit.omitted_lines: ' + ', '.join(sorted(known - covered - omitted)))
    mapping = cfg.get('takes', {})
    required = []
    for take in sorted(ids):
        if take not in mapping:
            raise RuntimeError(f'project.takes: brak wybranego ujęcia {take}')
        if take not in known and not any(take.startswith(k + '-') for k in known):
            raise RuntimeError(f'cuts.json: ujęcie {take} nie pochodzi z lines.json')
        path = Path(mapping[take])
        if (root / path).resolve().is_relative_to(root.resolve()) is False:
            raise RuntimeError('Ujęcie poza projektem')
        required.extend([str(path), str(path.with_suffix('.words.json'))])
    require_files(root, required)


def require_qa(report, whisper=False):
    checks = ['frames', 'loudness'] + (['whisper'] if whisper else [])
    failed = [key for key in checks if report.get(key, {}).get('ok') is not True]
    if failed:
        raise RuntimeError('QA nie przeszło: ' + ', '.join(failed))


def manifest(root, formats=None):
    files = sorted(p for p in (root / 'final').rglob('*') if p.is_file() and p.name != 'manifest.json')
    if formats is not None:
        cfg = json.loads((root / 'project.json').read_text())
        stems = {cfg.get('name', root.name) + '-' + f.replace(':', 'x') for f in formats}
        files = [p for p in files if any(p.stem in (s, s + '-share', s + '-poster') for s in stems)]
    if not files:
        raise RuntimeError('Brak plików końcowych.')
    data = {'project': root.name, 'files': [
        {'path': str(p.relative_to(root)), 'bytes': p.stat().st_size, 'sha256': digest(p)} for p in files],
        'download_verified': False, 'compute_retired': False}
    write_json(root / 'final/manifest.json', data)
    return data


def verify_qa_files(root, formats):
    for fmt in formats:
        tag = fmt.replace(':', 'x')
        path = root / f'edit/qa-{tag}.json'
        require_files(root, [str(path.relative_to(root))])
        report = json.loads(path.read_text())
        require_qa(report, whisper=True)
        video = Path(report['video'])
        if not video.is_absolute():
            video = root / video
        if report.get('video_sha256') != digest(video):
            raise RuntimeError(f'QA {fmt} jest nieaktualne: film zmienił się po sprawdzeniu.')
