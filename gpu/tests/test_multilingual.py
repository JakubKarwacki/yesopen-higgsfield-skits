"""Portable language and V3 integration regressions; no GPU or downloaded models."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'gpu')]
from languages import LANGUAGES, normalize, project_language, language_label, language_code, verify_whisper_model
from coordinator import pipeline
import gpu_batches
import fit_lines
import inspect_take
import qa_report
import make_edl

SAMPLES = {'pl':'Zażółć gęślą jaźń.', 'de':'Grüße für die Straße.', 'es':'Mañana está abierto.',
 'fr':'Écoutez, déjà ouvert.', 'tr':'Işık için İSTANBUL.', 'ru':'Салон уже открыт.',
 'el':'Το κομμωτήριο είναι ανοιχτό.', 'ar':'الصالون مفتوح الآن', 'he':'המספרה פתוחה',
 'hi':'सैलून खुला है', 'ja':'美容室は営業中です。', 'zh':'理发店现在营业。', 'ko':'미용실이 열려 있어요.'}

class LanguageTests(unittest.TestCase):
    def test_all_23_model_languages_and_legacy_labels(self):
        self.assertEqual(len(LANGUAGES), 23)
        for code in LANGUAGES:
            self.assertEqual(language_code(language_label(code)), code)
            self.assertEqual(project_language({'language':code},{'language':language_label(code)}),code)
        self.assertEqual(project_language({},{}),'en')
        self.assertEqual(project_language({}, {'language':'pl'}),'pl')

    def test_conflicting_unknown_and_region_codes_fail_instead_of_silent_fallback(self):
        for value in ['', None, 'xx', 'pl-PL', 'Polish (de)']:
            with self.assertRaises(ValueError): language_code(value)
        with self.assertRaises(ValueError): project_language({'language':'pl'},{'language':'en'})
        with self.assertRaises(ValueError): verify_whisper_model('small.en','pl')

    def test_unicode_is_preserved_and_different_scripts_never_both_become_empty(self):
        for code, text in SAMPLES.items():
            result=normalize(text,code)
            self.assertTrue(result,code)
            self.assertEqual(result,fit_lines.letters(text,code))
            self.assertEqual(''.join(qa_report.norm_words(text,code)),result)
            self.assertNotEqual(result,normalize('Other words',code))
        self.assertEqual(normalize('E\u0301cole','fr'),normalize('École','fr'))
        self.assertNotEqual(normalize('łaska','pl'),normalize('laska','pl'))
        self.assertEqual(normalize('İSTANBUL','tr'),normalize('istanbul','tr'))
        self.assertEqual(normalize('今日は 晴れ','ja'),normalize('今日は晴れ','ja'))
        self.assertNotEqual(make_edl.norm('你好'), make_edl.norm('再见'))

    def test_numbers_are_not_erased_or_assumed_english(self):
        self.assertNotEqual(normalize('15','pl'),normalize('16','pl'))
        self.assertNotEqual(normalize('1','pl'),normalize('one','pl'))
        self.assertEqual(normalize('O 15.','pl',{'15':'piętnastej'}),normalize('O piętnastej','pl'))
        with self.assertRaises(ValueError):normalize('15','pl',{'15':''})

    def test_project_creation_sets_both_language_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc=subprocess.run([sys.executable,str(ROOT/'scripts/new_project.py'),'demo','--root',tmp,'--language','pl'],capture_output=True,text=True,check=True)
            root=Path(proc.stdout.strip())
            self.assertTrue((root/'voice-validation.md').is_file())
            self.assertEqual(project_language(json.loads((root/'project.json').read_text()),json.loads((root/'lines.json').read_text())),'pl')

    def test_all_languages_reach_tts_and_inspection_in_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'edit').mkdir();(root/'edit/cuts.json').write_text('{}')
            (root/'still.png').write_bytes(b'image');(root/'voice.wav').write_bytes(b'audio')
            for code in LANGUAGES:
                doc={'characters':{'actor':{'still':'still.png','voice':'voice.wav'}},'lines':[{'id':'u01','who':'actor','text':SAMPLES.get(code,'Test')} ]}
                cfg={'name':'demo','language':code,'takes':{'u01':'takes/u01.video.mp4'}}
                (root/'project.json').write_text(json.dumps(cfg));(root/'lines.json').write_text(json.dumps(doc))
                plan=pipeline.plan_project(root,'demo','v1')
                self.assertTrue(all(t['set']['language']==language_label(code) for t in plan['tasks'] if t.get('template')=='tts'))
                self.assertEqual(next(t for t in plan['tasks'] if t['kind']=='inspect')['language'],code)

    def test_inspection_passes_target_language_to_whisper(self):
        import speech
        with patch('inspect_take.subprocess.run'), patch.object(speech,'load_model') as load:
            load.return_value.transcribe.return_value={'segments':[]}
            inspect_take.transcribe('fake.mp4','Polish (pl)','large-v3-turbo')
            self.assertEqual(load.return_value.transcribe.call_args.kwargs['language'],'pl')

    def test_failed_speech_qa_blocks_export_even_if_technical_checks_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'edit').mkdir();(root/'project.json').write_text('{"name":"demo"}')
            def fake(name,args):
                Path(args[-1]).write_text(json.dumps({'frames':{'ok':True},'loudness':{'ok':True},'whisper':{'ok':False}}))
            with patch.object(pipeline,'run_script',side_effect=fake), self.assertRaises(RuntimeError):
                pipeline.execute_stage(root,{'kind':'qa','format':'9:16'},root/'qa.log')

class V3Tests(unittest.TestCase):
    def test_manifest_selects_verified_v3_and_not_v2(self):
        manifest=json.loads((ROOT/'gpu/server/manifest.json').read_text())
        weights=[f for f in manifest['files'] if 'tts' in f.get('templates',[]) and f['name'].startswith('t3_')]
        self.assertEqual([f['name'] for f in weights],['t3_mtl23ls_v3.safetensors'])
        self.assertEqual(weights[0]['sha256'],'5abca8321ede76f8e61f1cc0d19aea6c946b28871017ce8726f8a69203f05953')
        templates=json.loads((ROOT/'gpu/workflows/templates.json').read_text())
        self.assertIn(weights[0]['name'],templates['extra_models']['tts']['files'])
        self.assertIn('patch_chatterbox_v3.py',(ROOT/'gpu/server/Dockerfile').read_text())

    def test_patch_refuses_unknown_source_without_writing(self):
        spec=importlib.util.spec_from_file_location('v3patch',ROOT/'gpu/server/patch_chatterbox_v3.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'chatterbox_node.py';p.write_text('changed upstream')
            with self.assertRaises(ValueError):mod.patched_sources(tmp)
            self.assertEqual(p.read_text(),'changed upstream')


class FittedAudioTests(unittest.TestCase):
    def test_fitter_uses_language_and_writes_real_wav_for_non_english_text(self):
        import numpy as np
        import speech
        for lang, text in [('pl','Cześć!'),('de','Grüße!'),('ja','こんにちは。')]:
            with self.subTest(lang=lang), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);(root/'voice').mkdir()
                (root/'voice/u01-s1.audio.flac').write_bytes(b'ASR fixture')
                (root/'lines.json').write_text(json.dumps({'language':lang,'lines':[{'id':'u01','text':text}]}))
                result={'segments':[{'words':[{'word':text,'start':0.0,'end':0.3}]}]}
                audio=np.ones(24000,dtype=np.float32)*0.1
                with patch.object(speech,'load_model') as load, patch.object(fit_lines,'load',return_value=audio), patch.object(sys,'argv',['fit_lines',str(root/'lines.json'),str(root/'voice'),str(root/'lines')]):
                    load.return_value.transcribe.return_value=result
                    fit_lines.main()
                    self.assertEqual(load.return_value.transcribe.call_args.kwargs['language'],lang)
                report=json.loads((root/'lines/fit.json').read_text())['u01']
                self.assertTrue(report['ok']);self.assertEqual(report['language'],lang)
                self.assertGreater((root/'lines/u01.wav').stat().st_size,100)

    def test_failed_fit_invalidates_old_audio_and_returns_failure(self):
        import speech
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'voice').mkdir();(root/'lines').mkdir()
            (root/'lines/u01.wav').write_bytes(b'previous successful voice')
            (root/'lines.json').write_text('{"language":"pl","lines":[{"id":"u01","text":"Cześć"}]}')
            with patch.object(speech,'load_model'), patch.object(sys,'argv',['fit_lines',str(root/'lines.json'),str(root/'voice'),str(root/'lines')]), self.assertRaises(SystemExit):
                fit_lines.main()
            self.assertFalse((root/'lines/u01.wav').exists())
            self.assertFalse(json.loads((root/'lines/fit.json').read_text())['u01']['ok'])

    def test_caption_font_rejects_missing_glyph_instead_of_exporting_tofu(self):
        import brand
        with self.assertRaises(ValueError):brand.validate_caption_glyphs(chr(0x10ffff))
        brand.validate_caption_glyphs('Zażółć gęślą jaźń')

    def test_cjk_caption_chunks_do_not_insert_spaces(self):
        from media import chunks_of
        words=[{'w':'你好','s':0,'e':0.3},{'w':'世界','s':0.3,'e':0.6}]
        self.assertEqual(chunks_of(words,language='zh')[0]['text'],'你好世界')

if __name__=='__main__':unittest.main()
