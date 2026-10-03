"""Server stages and portable plans; no heavy dependency is imported by the client."""
import contextlib
import hashlib
import json
import os
import runpy
import sys
from pathlib import Path

from .state import identifier, relative

SKILL = Path(__file__).resolve().parents[2]
SCRIPTS = SKILL / 'scripts'
FORMATS = {'9:16', '4:5', '1:1', '16:9'}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def path_in(root, value):
    p = (root / relative(value)).resolve()
    if not p.is_relative_to(root.resolve()):
        raise ValueError('path escapes project')
    relative(str(p.relative_to(root.resolve())))
    return p


def plan_project(project, project_id, revision, formats=None):
    """Produce TTS → fit → talk → inspection → approval → edit/export/QA DAG.

    Casting is a creative input: this plan requires selected stills and voice samples.
    Other templates can be submitted as explicit GPU tasks with approval gates.
    """
    doc = json.loads((project / 'lines.json').read_text())
    cfg = json.loads((project / 'project.json').read_text())
    sys.path.insert(0, str(SCRIPTS)) if str(SCRIPTS) not in sys.path else None
    from languages import project_language, language_label
    lang = project_language(cfg, doc)
    doc['language'] = language_label(lang)
    identifier(cfg['name'])
    for key in cfg.get('notifications', {}):
        identifier(key)
    selected = formats or cfg.get('formats', ['9:16'])
    if not selected or not set(selected) <= FORMATS:
        raise ValueError('unsupported formats')
    inputs = {'lines.json', 'project.json', 'edit/cuts.json'}
    for char in doc['characters'].values():
        inputs.update([char['still'], char['voice']])
    for line in doc['lines']:
        if line.get('still'):
            inputs.add(line['still'])
    if cfg.get('music'):
        inputs.add(cfg['music']['file'])
    for f in inputs:
        if not path_in(project, f).is_file():
            raise ValueError(f'missing selected production input: {f}')
    # These functions use only the standard library; no media processing here.
    sys.path.insert(0, str(SCRIPTS)) if str(SCRIPTS) not in sys.path else None
    import gpu_batches
    tasks, inspections = [], []
    for i, line in enumerate(doc['lines']):
        lid = identifier(line['id'])
        deps = []
        for seed in [100 + 2*i, 101 + 2*i]:
            job = gpu_batches.tts_job(project, doc, line, seed)
            job['set']['voice'] = doc['characters'][line['who']]['voice']
            key = identifier(job['name'])
            deps.append(key)
            tasks.append({'id': key, 'kind': 'gpu', 'template': 'tts', 'set': job['set'], 'out': 'voice', 'name': key})
        fit = f'fit-{lid}'
        tasks.append({'id': fit, 'kind': 'fit', 'line': lid, 'deps': deps})
        talk = f'talk-{lid}'
        tasks.append({'id': talk, 'kind': 'talk', 'line': lid, 'deps': [fit]})
        inspection = f'inspect-{lid}'
        inspections.append(inspection)
        tasks.append({'id': inspection, 'kind': 'inspect', 'language': lang, 'line': lid, 'deps': [talk]})
    if len({t['id'] for t in tasks}) != len(tasks) or not inspections:
        raise ValueError('duplicate/empty lines')
    if set(cfg['takes']) != {l['id'] for l in doc['lines']} or any(v != f'takes/{k}.video.mp4' for k, v in cfg['takes'].items()):
        raise ValueError('project.takes must map each line to takes/<line>.video.mp4')
    tasks.append({'id': 'approve-takes', 'kind': 'gate', 'deps': inspections})
    tasks.append({'id': 'edit', 'kind': 'edit', 'formats': selected, 'deps': ['approve-takes']})
    final = []
    for fmt in selected:
        slug = fmt.replace(':', 'x')
        tasks.append({'id': f'render-{slug}', 'kind': 'render', 'format': fmt, 'deps': ['edit']})
        tasks.append({'id': f'qa-{slug}', 'kind': 'qa', 'format': fmt, 'deps': [f'render-{slug}']})
        tasks.append({'id': f'encode-{slug}', 'kind': 'encode', 'format': fmt, 'deps': [f'qa-{slug}']})
        final.append(f'encode-{slug}')
    tasks.append({'id': 'approve-final', 'kind': 'gate', 'deps': final})
    return {'project_id': identifier(project_id), 'revision': identifier(revision), 'tasks': tasks,
            'files': {str(relative(f)): sha(path_in(project, f)) for f in sorted(inputs)}}


def run_script(name, args):
    old = sys.argv
    sys.argv = [str(SCRIPTS / name), *map(str, args)]
    try:
        runpy.run_path(str(SCRIPTS / name), run_name='__main__')
    except SystemExit as e:
        if e.code not in (None, 0):
            raise RuntimeError(f'{name} failed: {e.code}') from e
    finally:
        sys.argv = old


def receipt_files(root, paths):
    return {str(p.relative_to(root)): {'sha256': sha(p), 'bytes': p.stat().st_size}
            for p in paths if p.is_file() and not p.is_symlink()}


def execute_stage(root, spec, log_path):
    """Runs in a persistent worker process, so speech.load_model caches one Whisper instance."""
    root = Path(root).resolve()
    os.environ.setdefault('YESOPEN_WHISPER_DEVICE', 'cpu')
    os.environ.setdefault('YESOPEN_CPU_THREADS', '4')
    sys.path.insert(0, str(SCRIPTS)) if str(SCRIPTS) not in sys.path else None
    from media import load_project
    outputs = []
    with open(log_path, 'a') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        kind = spec['kind']
        if kind == 'fit':
            lid = identifier(spec['line'])
            run_script('fit_lines.py', [root/'lines.json', root/'voice', root/'lines', '--only', lid])
            fit = json.loads((root/f'lines/{lid}.fit.json').read_text())
            outputs = [root/f'lines/{lid}.wav', root/f'lines/{lid}.fit.json']
            if not fit[lid].get('ok'):
                raise RuntimeError('audio QA rejected; no automatic extra paid attempt')
        elif kind == 'inspect':
            lid = identifier(spec['line'])
            from languages import language_for_path
            lang = language_for_path(root/f'takes/{lid}.video.mp4')
            run_script('inspect_take.py', [root/f'takes/{lid}.video.mp4', '--lang', lang])
            outputs = [root/f'takes/{lid}.video.words.json', root/f'takes/{lid}.video.words.meta.json', root/f'edit/frames/{lid}.video_sheet.jpg']
        elif kind == 'edit':
            run_script('build_assets.py', [root, '--formats', ','.join(spec['formats']), '--sheet'])
            run_script('make_edl.py', [root])
            outputs = [root/'edit/edl.json', *[p for p in (root/'edit/frames').glob('assets-*.jpg')], *[p for p in (root/'edit/assets').rglob('*') if p.is_file()]]
        elif kind in {'render', 'qa', 'encode'}:
            fmt = spec['format']
            if fmt not in FORMATS:
                raise ValueError('unsupported format')
            name = identifier(load_project(root)['name'])
            master = root/f"final/{name}-{fmt.replace(':','x')}.mp4"
            if kind == 'render':
                render_args = [root, '--format', fmt]
                if not load_project(root).get('captions', {}).get('enabled', True):
                    render_args.append('--no-captions')
                run_script('assemble.py', render_args)
                outputs = [master]
            elif kind == 'qa':
                qa_path=root/f"edit/qa-{fmt.replace(':','x')}.json"
                run_script('qa_report.py', [root, '--format', fmt, '--whisper','--out',qa_path])
                outputs = [qa_path]
                report=json.loads(qa_path.read_text())
                if report.get('caption_sheet'):
                    outputs.append(Path(report['caption_sheet']))
                if not report['frames']['ok'] or not report['loudness']['ok'] or not report.get('whisper', {}).get('ok'):
                    raise RuntimeError('final technical QA failed; inspect report before acceptance')
            else:
                run_script('encode_variants.py', [master])
                outputs = [master.with_name(master.stem+'-share.mp4'),master.parent/'web'/master.name,master.parent/'web'/(master.stem+'-poster.jpg')]
        else:
            raise ValueError('unsupported CPU stage')
    if not outputs or any(not p.is_file() or p.stat().st_size == 0 for p in outputs):
        raise RuntimeError('required stage artifacts missing or empty')
    return {'artifacts': receipt_files(root, outputs)}
