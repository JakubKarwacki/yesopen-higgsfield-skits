#!/usr/bin/env python3
"""Validate workflow links and a closed-gate batch prompt on the CPU preview (no model execution)."""
import json
from pathlib import Path
import time
import urllib.request

URL = 'http://127.0.0.1:8188'
ROOT = Path(__file__).resolve().parents[1]


def get(path):
    return json.load(urllib.request.urlopen(URL + path, timeout=20))


def main():
    graph = json.loads((ROOT / 'workflows/pipeline/yesopen-skit-pipeline.json').read_text())
    nodes = {n['id']: n for n in graph['nodes']}
    for lid, src, slot, dst, port, _ in graph['links']:
        assert nodes[dst]['inputs'][port]['link'] == lid
        assert lid in nodes[src]['outputs'][slot]['links']
    info = get('/object_info')
    virtual = {'Note', 'MarkdownNote', 'PrimitiveNode'} | {s['id'] for s in graph['definitions']['subgraphs']}
    assert all(n['type'] in info or n['type'] in virtual for n in graph['nodes'])
    assert info['YesOpenLine']['output_is_list'] == [True] * 9
    assert get('/system_stats')['devices'][0]['type'] == 'cpu', 'Closed-gate test is restricted to CPU preview'
    queue = get('/queue')
    assert not queue['queue_running'] and not queue['queue_pending'], 'Leave a busy server untouched'
    project = info['YesOpenProject']['input']['required']['project'][0][0]
    tts = json.loads((ROOT / 'workflows/api/tts.json').read_text())['1']
    tts['inputs'].update(text=['3', 0], audio_prompt=['3', 1], exaggeration=['3', 2],
                         cfg_weight=['3', 3], seed=['3', 4], language=['3', 8])
    prompt = {'1': {'class_type': 'YesOpenProject', 'inputs': {'project': project}},
              '2': {'class_type': 'YesOpenGate', 'inputs': {'project': ['1', 0], 'gate': '2 · Scenariusz (Twoje TAK)', 'approved': False}},
              '3': {'class_type': 'YesOpenLine', 'inputs': {'project': ['2', 0], 'line': '*', 'take': 0}},
              '4': tts,
              '5': {'class_type': 'YesOpenFitLine', 'inputs': {'project': ['2', 0], 'line': ['3', 7], 'seed': ['3', 4], 'audio': ['4', 0]}}}
    request = urllib.request.Request(URL + '/prompt', data=json.dumps({'prompt': prompt, 'client_id': 'yesopen-closed-gate-test'}).encode(),
                                     headers={'Content-Type': 'application/json'})
    try:
        result = json.load(urllib.request.urlopen(request, timeout=20))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(exc.read().decode()) from exc
    assert not result.get('node_errors'), result
    for _ in range(30):
        history = get('/history/' + result['prompt_id'])
        if result['prompt_id'] in history:
            item = history[result['prompt_id']]
            assert item['status']['status_str'] == 'success', item['status']
            assert not item['outputs'], 'The closed gate must produce no media'
            print(f'OK: {len(nodes)} root nodes, {len(graph["links"])} valid links; batch/language schema accepted; closed gate blocked model execution.')
            return
        time.sleep(1)
    raise RuntimeError('Closed-gate prompt did not complete')


if __name__ == '__main__':
    main()
