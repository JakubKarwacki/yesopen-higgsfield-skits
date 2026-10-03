"""Review findings: independent QA, audio provenance, parallel results and setup."""
import concurrent.futures
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import fit_lines
import gpu_batches
import make_edl
import qa_report

class ReviewRegressions(unittest.TestCase):
    def test_qa_does_not_accept_audio_just_because_captions_repeat_its_error(self):
        edl={'caption_words':[{'w':'wrong'}],'segments':[{'take':'u01'}]}
        expected,source=qa_report.expected_dialogue({},edl,{'lines':[{'id':'u01','text':'approved'}]})
        self.assertEqual(expected,'approved')
        self.assertEqual(source,'approved_lines_in_edit_order')

    def test_ambiguous_and_silent_edits_require_explicit_reference(self):
        edl={'caption_words':[],'segments':[{'take':'action'}]}
        with self.assertRaises(ValueError):qa_report.expected_dialogue({},edl,{})
        self.assertEqual(qa_report.expected_dialogue({'speech':{'expected_text':''}},edl,{}),('', 'speech.expected_text'))
        self.assertEqual(qa_report.expected_dialogue({'speech':{'expected_text':'selected words'}},edl,{})[0],'selected words')

    def test_parallel_line_checkpoints_do_not_lose_other_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
                futures=[pool.submit(fit_lines.save_fit_result,root,f'u{i}',{'ok':True,'language':'pl'}) for i in range(20)]
                for future in futures:future.result()
            report=json.loads((root/'fit.json').read_text())
            self.assertEqual(set(report),{f'u{i}' for i in range(20)})
            for key in report:self.assertEqual(json.loads((root/f'{key}.fit.json').read_text())[key],report[key])

    def test_changed_voice_with_same_duration_invalidates_padded_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'lines').mkdir();src=root/'lines/u01.wav';src.write_bytes(b'first')
            def render(args,**kwargs):Path(args[-1]).write_bytes(b'padded')
            with patch.object(gpu_batches,'duration',side_effect=lambda p:2.0 if '-pad' in str(p) else 1.0),patch.object(gpu_batches.subprocess,'run',side_effect=render) as run:
                gpu_batches.pad_line(root,'u01',1.0)
                gpu_batches.pad_line(root,'u01',1.0)
                self.assertEqual(run.call_count,1)
                src.write_bytes(b'other')
                gpu_batches.pad_line(root,'u01',1.0)
                self.assertEqual(run.call_count,2)

    def test_edit_inherits_language_and_checks_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'lines.json').write_text('{"language":"tr"}')
            self.assertEqual(make_edl.Takes(root,{'takes':{}}).language,'tr')
            with self.assertRaises(ValueError):make_edl.Takes(root,{'takes':{},'language':'en'})

if __name__=='__main__':unittest.main()
