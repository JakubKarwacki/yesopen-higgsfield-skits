"""Regressions for the 14 context audit findings; no model inference."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('contracts_test', ROOT / 'gpu/server/yesopen_pipeline/contracts.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
sys.path.insert(0, str(ROOT / 'scripts'))
import make_edl
import gpu_batches


class Contracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.write('project.json', {})
    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
    def test_disabled_music_does_not_require_file_or_tempo(self):
        self.write('project.json', {'music': {'enabled': False, 'file': 'old.flac'}})
        self.assertEqual(c.music_plan(self.root)[0], 'off')
    def test_existing_music_is_preserved_and_missing_bpm_rejected(self):
        (self.root / 'bed.flac').write_bytes(b'bed')
        self.write('project.json', {'music': {'file': 'bed.flac'}})
        with self.assertRaisesRegex(RuntimeError, 'BPM'):
            c.music_plan(self.root)
        self.write('project.json', {'music': {'file': 'bed.flac', 'bpm': 80}})
        self.assertEqual(c.music_plan(self.root)[0], 'existing')
    def test_generated_music_uses_edit_length_and_project_spec(self):
        self.write('edit/edl.json', {'_dialogue_seconds': 140, 'endcard': {'dur': 3}})
        music = {'enabled': True, 'mode': 'generate', 'tags': 'piano', 'bpm': 80,
                 'seed': 7, 'keyscale': 'C major', 'timesignature': '4', 'language': 'pl'}
        self.write('project.json', {'music': music})
        mode, values = c.music_plan(self.root)
        self.assertEqual(mode, 'generate')
        self.assertEqual(values['seconds'], 153)
        self.assertEqual(values['lyrics'], '[Instrumental]')
        self.assertEqual(values['bpm'], 80)
        self.assertIn('instrumental', values['tags'])
        music['lyrics'] = 'unwanted song'
        self.write('project.json', {'music': music})
        with self.assertRaisesRegex(RuntimeError, 'lyrics'):
            c.music_plan(self.root)
    def test_caption_decision_survives_edl(self):
        cfg = {'takes': {}, 'captions': {'enabled': False}}
        result = make_edl.build(self.root, cfg, {'cuts': []})
        self.assertFalse(result['captions_enabled'])
        self.assertEqual(result['caption_words'], [])
    def test_disabled_music_excluded_from_edl(self):
        cfg = {'takes': {}, 'music': {'enabled': False, 'file': 'old.flac'}}
        self.assertNotIn('music', make_edl.build(self.root, cfg, {'cuts': []}))
    def test_api_and_screen_have_identical_frame_rules(self):
        work = ROOT / 'gpu/workflows'
        for template, values in [('h3-talk', {'image': 'x.png', 'audio': 'x.wav', 'prompt': 'our scene', 'seconds': 5.27, 'seed': 12}),
                                 ('talk', {'image': 'x.png', 'audio': 'x.wav', 'prompt': 'our scene', 'seconds': 5.27, 'seed': 12,
                                           'enhance_prompt': False, 'negative_prompt': 'no subtitles', 'cfg_first': 2})]:
            graph, out, resolved, grid = c.prepare_template(work, template, values)
            shared = c.client(work)
            spec = json.loads((work / 'params' / (template + '.json')).read_text())
            copy = shared.resolve_values(spec, values, __import__('random').Random(0))
            self.assertEqual(grid, shared.frame_grid(spec, copy))
            self.assertEqual(resolved, copy)
            self.assertGreaterEqual(grid['seconds'], 5.27)
            if template == 'talk':
                self.assertFalse(resolved['enhance_prompt'])
                self.assertEqual(graph['340:314']['inputs']['text'], 'no subtitles')
                self.assertEqual(graph['340:315']['inputs']['cfg'], 2)
            else:
                self.assertIn('902', graph)
                self.assertNotIn('119', graph)  # orphan demo scaler
    def test_formats_and_paths_are_explicit(self):
        self.write('project.json', {'formats': ['1:1']})
        self.assertEqual(c.formats(self.root), ['1:1'])
        self.write('project.json', {'formats': ['1:1', '1:1']})
        with self.assertRaises(RuntimeError): c.formats(self.root)
        with self.assertRaises(RuntimeError): c.safe_file(self.root, '../escape.wav')
    def test_h3_is_default_and_line_options_override_take(self):
        from types import SimpleNamespace
        doc = {'characters': {'a': {'still': 'a.png', 'who': 'woman', 'where': 'room'}},
               'take': {'fast': False, 'megapixels': .4},
               'lines': [{'id': 'l01', 'who': 'a', 'text': 'Hello', 'fast': True, 'megapixels': .98}]}
        with patch.object(gpu_batches, 'line_seconds', return_value=3):
            gpu_batches.cmd_takes(self.root, doc, SimpleNamespace(only=None, out=None))
        job = json.loads((self.root / 'takes/batch.json').read_text())['jobs'][0]
        self.assertEqual(job['template'], 'h3-talk')
        self.assertTrue(job['set']['fast'])
        self.assertEqual(job['set']['megapixels'], .98)
    def test_main_graph_has_no_demo_or_forced_postprocessing(self):
        graph = json.loads((ROOT / 'gpu/workflows/pipeline/yesopen-skit-pipeline.json').read_text())
        types = {node['type'] for node in graph['nodes']}
        self.assertIn('YesOpenGenerateTake', types)
        self.assertIn('YesOpenMusic', types)
        self.assertIn('YesOpenCast', types)
        self.assertNotIn('TextEncodeAceStepAudio1.5', types)
        self.assertNotIn('YesOpenCropFormats', types)
        self.assertNotIn('late night trap', json.dumps(graph).lower())

    def test_fitter_excludes_old_seed_and_preserves_intentional_pause(self):
        import numpy as np
        import speech
        import fit_lines
        self.write('lines.json', {'language': 'en', 'lines': [{'id': 'l01', 'text': 'Hello world'}]})
        self.write('project.json', {'speech': {'fit': {'lead': .1, 'tail': .2, 'min_ratio': 1, 'max_pause': None}}})
        voice = self.root / 'voice'
        voice.mkdir()
        for seed in (1, 2): (voice / f'l01-s{seed}.audio.flac').write_bytes(b'fixture')
        wave = np.zeros(3 * 48000, dtype=np.float32)
        wave[:int(.3 * 48000)] = .1
        wave[int(2.2 * 48000):int(2.5 * 48000)] = .1
        result = {'segments': [{'words': [{'word': 'Hello', 'start': 0, 'end': .3},
                                         {'word': 'world', 'start': 2.2, 'end': 2.5}]}]}
        args = ['fit_lines', str(self.root/'lines.json'), str(voice), str(self.root/'lines'), '--candidate', 'l01-s2.audio.flac']
        with patch.object(speech, 'load_model') as load, patch.object(fit_lines, 'load', return_value=wave), patch.object(sys, 'argv', args):
            load.return_value.transcribe.return_value = result
            fit_lines.main()
        self.assertEqual(load.return_value.transcribe.call_count, 1)
        self.assertTrue(load.return_value.transcribe.call_args.args[0].endswith('l01-s2.audio.flac'))
        fitted = json.loads((self.root/'lines/fit.json').read_text())['l01']
        self.assertEqual(fitted['pauses_removed'], 0)
        self.assertGreaterEqual(fitted['seconds'], 2.6)
        self.assertEqual(fitted['policy']['lead'], .1)


if __name__ == '__main__': unittest.main()
