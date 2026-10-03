import json
import random
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'gpu/client'))
import gpu_batches
import gpu

class TalkNegativeConditioning(unittest.TestCase):
    def test_optional_negative_prompt_preserves_default_graph(self):
        graph, spec = gpu.load_template('talk')
        before = graph['340:314']['inputs']['text']
        values = gpu.resolve_values(spec, {'image': 'fixture.png', 'audio': 'fixture.wav',
                                          'prompt': 'A woman speaks', 'seconds': 3}, random.Random(1))
        self.assertNotIn('negative_prompt', values)
        for name, value in values.items():
            gpu.set_targets(graph, spec['params'][name], value)
        self.assertEqual(graph['340:314']['inputs']['text'], before)
        self.assertEqual(graph['340:315']['inputs']['cfg'], 1.0)
        self.assertEqual(graph['340:290']['inputs']['cfg'], 1)
        gpu.set_targets(graph, spec['params']['negative_prompt'], 'subtitles, extra person')
        conditioning = graph[graph['340:315']['inputs']['negative'][0]]['inputs']
        negative_encoder = conditioning['negative'][0]
        self.assertEqual(graph[negative_encoder]['inputs']['text'], 'subtitles, extra person')

    def test_line_negative_prompt_overrides_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc = {'characters': {'a': {'still': 'a.png', 'who': 'Woman', 'where': 'salon'}},
                   'take': {'negative_prompt': 'subtitles'},
                   'lines': [{'id': 'l01', 'who': 'a', 'text': 'Hello',
                              'negative_prompt': 'subtitles, foreground person'}]}
            with patch.object(gpu_batches, 'line_seconds', return_value=2):
                gpu_batches.cmd_takes(root, doc, SimpleNamespace(only=None, out=None))
            job = json.loads((root/'takes/batch.json').read_text())['jobs'][0]
            self.assertEqual(job['set']['negative_prompt'], 'subtitles, foreground person')



class TalkFirstStage(unittest.TestCase):
    def test_first_cfg_reaches_initial_sampler_only(self):
        graph, spec = gpu.load_template('talk')
        gpu.set_targets(graph, spec['params']['cfg_first'], 2.0)
        first = graph['340:291']['inputs']
        second = graph['340:310']['inputs']
        self.assertEqual(graph[first['guider'][0]]['inputs']['cfg'], 2.0)
        self.assertEqual(graph[second['guider'][0]]['inputs']['cfg'], 1)
        self.assertTrue(graph[first['sigmas'][0]]['inputs']['sigmas'].startswith('1.0,'))

if __name__ == '__main__': unittest.main()
