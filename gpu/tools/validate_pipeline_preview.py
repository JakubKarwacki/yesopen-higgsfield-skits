"""Validate the saved production graph on dev; optionally run only its closed-gate preview."""
import json
from pathlib import Path
import shlex
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'client'))
import nebius_session as n

state = n.load_state()
assert state.get('disk_id') == 'computedisk-e00ybjw8kgzj9ye54g'
def request(path, payload=None):
    command = 'curl -sf http://127.0.0.1:8188' + path
    if payload is not None:
        command += ' -H ' + shlex.quote('Content-Type: application/json') + ' -d ' + shlex.quote(json.dumps(payload))
    result = n.ssh(state['ip'], command, timeout=30)
    if not result.stdout:
        raise RuntimeError(result.stderr or 'ComfyUI not ready')
    return json.loads(result.stdout)

info = request('/object_info')
graph = json.loads((Path(__file__).resolve().parents[1] / 'workflows/pipeline/yesopen-skit-pipeline.json').read_text())
edges = {link[0]: link for link in graph['links']}
prompt = {}
for node in graph['nodes']:
    kind = node['type']
    if kind in ('Note', 'MarkdownNote'):
        continue
    definition = info[kind]['input']
    sockets = {inp['name']: inp for inp in node.get('inputs', [])}
    widgets, cursor, values = node.get('widgets_values', []), 0, {}
    for name, entry in {**definition.get('required', {}), **definition.get('optional', {})}.items():
        typ = entry[0]
        options = entry[1] if len(entry) > 1 else {}
        is_widget = isinstance(typ, list) or typ in ('STRING', 'INT', 'FLOAT', 'BOOLEAN', 'COMBO')
        if options.get('forceInput'):
            is_widget = False
        if is_widget:
            values[name] = widgets[cursor] if cursor < len(widgets) else options.get('default', typ[0] if isinstance(typ, list) else '' if typ == 'STRING' else False if typ == 'BOOLEAN' else 0)
            cursor += 1
            if name in ('seed', 'noise_seed') and cursor < len(widgets) and widgets[cursor] in ('fixed', 'randomize', 'increment', 'decrement'):
                cursor += 1
        inp = sockets.get(name, {})
        if inp.get('link') is not None:
            link = edges[inp['link']]
            values[name] = [str(link[1]), link[2]]
    prompt[str(node['id'])] = {'class_type': kind, 'inputs': values}

assert all(node['inputs'].get('approved') is False for node in prompt.values() if node['class_type'] == 'YesOpenGate')
assert all(node['inputs'].get('enabled') is False for node in prompt.values() if node['class_type'] == 'YesOpenSceneVariant')
assert all(node['inputs'].get('generate') is False for node in prompt.values() if node['class_type'] == 'YesOpenCast')
if '--queue-preview' not in sys.argv:
    print(json.dumps({'classes': len(prompt), 'missing': sorted({x['class_type'] for x in prompt.values()} - set(info))}))
    sys.exit(0)
queue = request('/queue')
assert not queue['queue_running'] and not queue['queue_pending'], 'Dev preview is busy'
result = request('/prompt', {'prompt': prompt, 'client_id': 'yesopen-regression-preview'})
print(json.dumps(result))
assert 'prompt_id' in result, result
for _ in range(30):
    history = request('/history/' + result['prompt_id'])
    if history:
        status = history[result['prompt_id']]['status']
        print(json.dumps(status))
        assert status['status_str'] == 'success', status
        break
    time.sleep(1)
else:
    raise RuntimeError('Closed-gate preview timeout')
