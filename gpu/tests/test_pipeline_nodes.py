"""Regression checks for project orchestration; run in the ComfyUI image (no GPU jobs)."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PACKAGE = Path(os.environ.get('YESOPEN_NODE_DIR', Path(__file__).resolve().parents[1] / 'server/yesopen_pipeline'))
spec = importlib.util.spec_from_file_location('yesopen_pipeline_test', PACKAGE / '__init__.py',
                                             submodule_search_locations=[str(PACKAGE)])
p = importlib.util.module_from_spec(spec)
HAS_COMFY = importlib.util.find_spec('comfy_execution') is not None
sys.modules[spec.name] = p
try:
    spec.loader.exec_module(p)
except ModuleNotFoundError as exc:
    if exc.name not in {'torch', 'numpy', 'PIL'}:
        raise
    p = None


@unittest.skipIf(p is None, 'Run node regressions in the ComfyUI image (torch/numpy/Pillow required).')
class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'demo'
        self.root.mkdir()
        self.scope = patch.object(p, 'WORK', self.root.parent)
        self.scope.start()
        self.addCleanup(self.scope.stop)
        self.doc = {'language': 'Polish (pl)', 'characters': {'a': {'voice': 'voices/a.wav', 'still': 'stills/a.png'}},
                    'lines': [{'id': 'l01', 'who': 'a', 'text': 'Raz'}, {'id': 'l02', 'who': 'a', 'text': 'Dwa'}]}
        p.write_json(self.root / 'lines.json', self.doc)
        p.write_json(self.root / 'project.json', {'takes': {'l01': 'takes/l01.video.mp4', 'l02': 'takes/l02.video.mp4'}})
        for name in ['voices/a.wav', 'stills/a.png', 'lines/l01.wav']:
            path = self.root / name
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(b'first')

    def test_batch_keeps_line_seed_language_alignment(self):
        jobs = {'jobs': [{'name': f'l0{i+1}-s{100+2*i}', 'set': {'text': text, 'voice': '../voices/a.wav',
                         'exaggeration': .5, 'cfg_weight': .5, 'seed': 100+2*i, 'language': 'Polish (pl)'}}
                        for i, text in enumerate(['Raz', 'Dwa'])]}
        p.write_json(self.root / 'voice/batch.json', jobs)
        with patch.object(p, 'editor', return_value='OK'), patch.object(p, 'load_audio', side_effect=lambda path: str(path)):
            result = p.Line().run('demo', '*', 0)
        self.assertEqual(result[0], ['Raz', 'Dwa'])
        self.assertEqual(result[4], [100, 102])
        self.assertEqual(result[7], ['l01', 'l02'])
        self.assertEqual(result[8], ['Polish (pl)', 'Polish (pl)'])

    def test_resume_does_not_request_gpu_video_and_rejects_changed_source(self):
        video = self.root / 'takes/l01.video.mp4'
        video.parent.mkdir()
        video.write_bytes(b'video')
        expected = p.signature(self.root, 'l01', input_name='video')
        words = video.with_suffix('.words.json')
        words.write_text('[]')
        p.checkpoint(self.root, 'take/l01', [video, words])
        p.write_json(self.root / 'takes/l01.source.json', {'signature': expected, 'video_sha256': p.digest(video)})
        self.assertEqual(p.SaveTake().check_lazy_status('demo', 'l01'), [])
        self.assertEqual(p.SaveTake().run('demo', 'l01')['result'][0], 'demo')
        (self.root / 'stills/a.png').write_bytes(b'changed')
        self.assertEqual(p.SaveTake().check_lazy_status('demo', 'l01'), ['video'])

    def test_missing_transcript_resumes_inspection_without_regeneration(self):
        video = self.root / 'takes/l01.video.mp4'
        video.parent.mkdir()
        video.write_bytes(b'video')
        expected = p.signature(self.root, 'l01', input_name='video')
        p.write_json(self.root / 'takes/l01.source.json', {'signature': expected, 'video_sha256': p.digest(video)})
        self.assertEqual(p.SaveTake().check_lazy_status('demo', 'l01'), [])
        def inspect(*args, **kw):
            video.with_suffix('.words.json').write_text('[]')
            return 'inspected'
        with patch.object(p, 'editor', side_effect=inspect):
            p.SaveTake().run('demo', 'l01')
        self.assertTrue(p.cached(self.root, 'take/l01'))
        video.with_suffix('.words.json').write_text('["changed"]')
        self.assertFalse(p.cached(self.root, 'take/l01'))

    def test_voice_approval_does_not_include_other_lines(self):
        import torch
        audio = {'sample_rate': 48000, 'waveform': torch.zeros(1, 1, 8)}
        (self.root / 'lines/l02.wav').write_bytes(b'other')
        with patch.object(p, 'load_audio', return_value=audio):
            p.VoiceApproval().run(['demo'], [audio], [True], ['l01'])
        saved = json.loads((self.root / 'edit/pipeline-state.json').read_text())['approved-voices']
        self.assertEqual(set(saved), {'lines/l01.wav'})

    def test_render_respects_music_captions_and_formats(self):
        p.write_json(self.root / 'project.json', {'formats': ['1:1'], 'captions': {'enabled': False}, 'music': {'enabled': False}})
        from yesopen_pipeline_test.generation import RenderFormats
        with patch.object(p, 'editor', return_value='OK') as edit:
            RenderFormats().run('demo')
        self.assertEqual(edit.call_args.args[2], ['.', '--format', '1:1', '--no-captions', '--no-music'])

    @unittest.skipUnless(HAS_COMFY, 'ComfyUI graph runtime required; tested on dev')
    def test_h3_expansion_anchors_audio_and_optional_postprocess(self):
        from yesopen_pipeline_test.generation import GenerateTake
        self.doc['take'] = {'postprocess': {'upscale': {'enabled': True, 'multiplier': 1.5},
                                          'interpolate': {'enabled': True, 'multiplier': 2, 'multiply_fps': True}}}
        p.write_json(self.root / 'lines.json', self.doc)
        p.write_json(self.root / 'takes/batch-l01.json', {'jobs': [{'template': 'h3-talk', 'set': {
            'image': '../stills/a.png', 'audio': '../lines/l01.wav', 'prompt': 'Approved scene', 'seconds': 5.27, 'seed': 42}}]})
        graph = GenerateTake().run('demo', 'l01', None)['expand']
        types = [n['class_type'] for n in graph.values()]
        self.assertIn('MiniMaxH3AddGuide', types)
        self.assertEqual(types.count('YesOpenVideoPass'), 2)
        audio = next(n for n in graph.values() if n['class_type'] == 'YesOpenProjectMedia' and n['inputs']['kind'] == 'LoadAudio')
        self.assertGreaterEqual(audio['inputs']['seconds'], 5.27)
        record = json.loads((self.root / 'takes/l01/h3-talk.task.json').read_text())
        self.assertEqual(record['values']['prompt'], 'Approved scene')

    @unittest.skipUnless(HAS_COMFY, 'ComfyUI graph runtime required; tested on dev')
    def test_h3_without_postprocess_does_not_load_upscale_or_film(self):
        from yesopen_pipeline_test.generation import GenerateTake
        p.write_json(self.root / 'takes/batch-l01.json', {'jobs': [{'template': 'h3-talk', 'set': {
            'image': '../stills/a.png', 'audio': '../lines/l01.wav', 'prompt': 'Approved scene', 'seconds': 6, 'seed': 42}}]})
        graph = GenerateTake().run('demo', 'l01', None)['expand']
        self.assertFalse(any(n['class_type'].startswith(('SeedVR', 'FrameInterpolation')) for n in graph.values()))

    @unittest.skipUnless(HAS_COMFY, 'ComfyUI graph runtime required; tested on dev')
    def test_cast_uses_unique_characters_and_actual_seed(self):
        from yesopen_pipeline_test.generation import Cast
        self.doc['characters']['a'].update(still='', look='The approved character', seed=17)
        p.write_json(self.root / 'lines.json', self.doc)
        graph = Cast().run('demo', 2, True)['expand']
        savers = [n for n in graph.values() if n['class_type'] == 'YesOpenSaveStill']
        self.assertEqual(len(savers), 1)
        self.assertEqual(savers[0]['inputs']['seed'], 19)
        self.assertTrue(any(n['inputs'].get('seed') == 19 for n in graph.values() if n['class_type'] == 'KSampler'))

    @unittest.skipUnless(HAS_COMFY, 'ComfyUI graph runtime required; tested on dev')
    def test_project_media_pads_audio_without_truncating(self):
        from yesopen_pipeline_test.generation import ProjectMedia
        import torch
        audio = {'sample_rate': 10, 'waveform': torch.ones(1, 1, 5)}
        with patch.object(p, 'load_audio', return_value=audio):
            padded = ProjectMedia().run('demo', 'lines/l01.wav', 'LoadAudio', 1)[1]
        self.assertEqual(padded['waveform'].shape[-1], 10)
        self.assertEqual(padded['waveform'][..., 5:].sum(), 0)
        with patch.object(p, 'load_audio', return_value=audio):
            with self.assertRaisesRegex(RuntimeError, 'truncate'):
                ProjectMedia().run('demo', 'lines/l01.wav', 'LoadAudio', .2)

    def test_failed_qa_blocks_even_when_editor_returns_success(self):
        p.write_json(self.root / 'edit/qa-9x16.json', {'frames': {'ok': True}, 'loudness': {'ok': False}, 'whisper': {'ok': True}})
        with patch.object(p, 'editor', return_value='exit code zero'):
            with self.assertRaisesRegex(RuntimeError, 'loudness'):
                p.QAReport().run('demo', '9:16', True)

    def test_audio_approval_is_invalidated_by_audio_change(self):
        import torch
        audio = {'sample_rate': 48000, 'waveform': torch.zeros(1, 1, 8)}
        with patch.object(p, 'load_audio', return_value=audio):
            p.VoiceApproval().run(['demo'], [audio], [True], ['l01'])
            (self.root / 'lines/l01.wav').write_bytes(b'new recording')
            with self.assertRaisesRegex(RuntimeError, 'Audio zmieniło'):
                p.VoiceApproval().run(['demo'], [audio], [True], ['l01'])

    def test_join_checks_all_cut_takes_not_only_current_batch(self):
        p.write_json(self.root / 'edit/cuts.json', {'cuts': [{'take': 'l01'}, {'take': 'l02'}]})
        with self.assertRaisesRegex(RuntimeError, 'l02.video.mp4'):
            p.JoinProduction().run(['demo'], [])

    def test_join_returns_one_project_after_all_mapped_takes(self):
        p.write_json(self.root / 'edit/cuts.json', {'cuts': [{'take': 'l01'}, {'take': 'l02'}]})
        for line in ['l01', 'l02']:
            for suffix in ['video.mp4', 'video.words.json']:
                path = self.root / f'takes/{line}.{suffix}'
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(b'asset')
        music = self.root / 'music/bed.flac'
        music.parent.mkdir()
        music.write_bytes(b'bed')
        self.assertEqual(p.JoinProduction().run(['demo', 'demo'], [str(music)])[0], 'demo')

    def test_voice_seed_selection_changes_video_resume_signature(self):
        prompt = {'1': {'class_type': 'YesOpenLine', 'inputs': {'line': '*', 'take': 0}},
                  '2': {'class_type': 'YesOpenFitLine', 'inputs': {'seed': ['1', 4]}},
                  '3': {'class_type': 'CreateVideo', 'inputs': {'audio': ['2', 0]}},
                  '4': {'class_type': 'YesOpenSaveTake', 'inputs': {'video': ['3', 0]}}}
        before = p.signature(self.root, 'l01', prompt=prompt, unique_id='4', input_name='video')
        prompt['1']['inputs']['take'] = 1
        after = p.signature(self.root, 'l01', prompt=prompt, unique_id='4', input_name='video')
        self.assertNotEqual(before, after)

    def test_manifest_and_qa_hash_detect_replaced_master(self):
        video = self.root / 'final/demo-9x16.mp4'
        video.parent.mkdir()
        video.write_bytes(b'finished')
        report = {'video': str(video), 'video_sha256': p.digest(video),
                  'frames': {'ok': True}, 'loudness': {'ok': True}, 'whisper': {'ok': True}}
        p.write_json(self.root / 'edit/qa-9x16.json', report)
        p.verify_qa_files(self.root, ['9:16'])
        self.assertEqual(p.manifest(self.root)['files'][0]['sha256'], p.digest(video))
        video.write_bytes(b'replaced')
        with self.assertRaisesRegex(RuntimeError, 'nieaktualne'):
            p.verify_qa_files(self.root, ['9:16'])

    def test_cache_scope_follows_only_selected_project(self):
        prompt = {'1': {'class_type': 'YesOpenProject', 'inputs': {'project': 'demo'}},
                  '2': {'class_type': 'YesOpenGate', 'inputs': {'project': ['1', 0]}},
                  '3': {'class_type': 'YesOpenMakeEDL', 'inputs': {'project': ['2', 0]}},
                  '4': {'class_type': 'YesOpenProject', 'inputs': {'project': 'other'}}}
        self.assertEqual(p.selected_project(None, prompt, '3'), 'demo')


if __name__ == '__main__':
    unittest.main()
