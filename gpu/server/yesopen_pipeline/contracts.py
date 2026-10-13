"""Project contracts used by orchestration and regression tests (no GPU imports)."""
import copy
import json
import math
import importlib.util
import random
from functools import lru_cache
from pathlib import Path

FORMATS = ('9:16', '4:5', '1:1', '16:9')


def formats(root):
    cfg = json.loads((root / 'project.json').read_text())
    selected = cfg.get('formats', list(FORMATS))
    if not selected or len(set(selected)) != len(selected) or set(selected) - set(FORMATS):
        raise RuntimeError('project.formats: select unique supported formats')
    return selected


def safe_file(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise RuntimeError('Media path escapes project: ' + str(name))
    return path


@lru_cache(maxsize=2)
def client(workflows):
    spec = importlib.util.spec_from_file_location('yesopen_template_client', workflows.parent / 'client/gpu.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare_template(workflows, template, values):
    """Resolve exactly the same API parameter map used by gpu.py, prune disconnected demo nodes."""
    spec = json.loads((workflows / 'params' / (template + '.json')).read_text())
    graph = json.loads((workflows / 'api' / (template + '.json')).read_text())
    shared = client(workflows)
    values = shared.resolve_values(spec, copy.deepcopy(values), random.Random(0))
    grid = shared.frame_grid(spec, values)
    if grid.get('seconds', 0) <= 0 and grid:
        raise RuntimeError('Shot duration must be positive')
    for name, value in values.items():
        for node, key in spec['params'][name]['targets']:
            graph[node]['inputs'][key] = value
    # A saver is an output root in the API; the screen graph receives its source instead.
    output = next(iter(spec['outputs'].values()))
    output_node = graph[output]
    source = next(v for k, v in output_node['inputs'].items()
                  if k in ('video', 'audio', 'images') and isinstance(v, list))
    keep, todo = set(), [source[0]]
    while todo:
        node = todo.pop()
        if node in keep:
            continue
        keep.add(node)
        todo.extend(v[0] for v in graph[node]['inputs'].values()
                    if isinstance(v, list) and len(v) == 2 and v[0] in graph)
    return {k: graph[k] for k in graph if k in keep}, source, values, grid


def music_plan(root):
    cfg = json.loads((root / 'project.json').read_text())
    music = cfg.get('music') or {}
    if not music.get('enabled', bool(music)):
        return 'off', music
    if music.get('file') and music.get('mode', 'existing') == 'existing':
        if not safe_file(root, music['file']).is_file() or not music.get('bpm'):
            raise RuntimeError('Existing music requires an existing file and BPM')
        return 'existing', music
    if music.get('mode') != 'generate':
        raise RuntimeError('music.mode must be existing or generate')
    required = ('tags', 'bpm', 'seed', 'keyscale', 'timesignature', 'language')
    if any(key not in music for key in required):
        raise RuntimeError('Generated music requires tags, bpm, seed, keyscale, timesignature, language')
    if music.get('instrumental', True) and music.get('lyrics', '[Instrumental]') != '[Instrumental]':
        raise RuntimeError('Instrumental music cannot contain lyrics')
    edl = json.loads((root / 'edit/edl.json').read_text())
    duration = edl['_dialogue_seconds'] + (edl.get('endcard') or {}).get('dur', 0)
    values = {key: music[key] for key in required}
    values['tags'] = ('instrumental, ' if music.get('instrumental', True) else '') + music['tags']
    values['lyrics'] = music.get('lyrics', '[Instrumental]')
    values['seconds'] = max(float(music.get('seconds', 0)), duration + float(music.get('tail', 10)))
    if 'steps' in music:
        values['steps'] = music['steps']
    return 'generate', values
