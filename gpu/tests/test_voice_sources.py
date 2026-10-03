import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from verify_voice_sources import validate


class VoiceSources(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root/'voices').mkdir()
        (self.root/'voices/a.wav').write_bytes(b'synthetic fixture')
        self.lines = {'characters': {'a': {'voice': 'voices/a.wav'}}, 'lines': [{'who': 'a'}]}
        self.config = {'cast': {'a': {'voice': 'voices/a.wav'}}}
        self.records = [{'character': 'a', 'candidate': 'voices/a.wav',
                         'sha256': hashlib.sha256(b'synthetic fixture').hexdigest(),
                         'source': 'synthetic catalog fixture', 'rights_basis': 'synthetic',
                         'evidence': 'catalog fixture entry', 'voice_description': 'intended character voice',
                         'human_listening': 'not_reviewed'}]

    def tearDown(self):
        self.tmp.cleanup()

    def check(self):
        for name, value in [('lines.json', self.lines), ('project.json', self.config),
                            ('voices/provenance.json', self.records)]:
            (self.root/name).write_text(json.dumps(value))
        return validate(self.root)

    def test_deferred_listening_does_not_fake_approval_or_block_source_check(self):
        result = self.check()
        self.assertTrue(result['ok'])
        self.assertIn('listening not assessed', result['note'])
        self.assertNotIn('accepted', result)

    def test_changed_bytes_even_at_same_path_are_rejected(self):
        (self.root/'voices/a.wav').write_bytes(b'different fixture')
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            self.check()

    def test_cast_selection_mismatch_is_rejected(self):
        self.config['cast']['a']['voice'] = 'voices/old.wav'
        with self.assertRaisesRegex(ValueError, 'selection differs'):
            self.check()

    def test_filename_without_rights_evidence_is_rejected(self):
        del self.records[0]['evidence']
        with self.assertRaisesRegex(ValueError, 'missing evidence'):
            self.check()

    def test_ambiguous_selected_source_is_rejected(self):
        self.records.append(dict(self.records[0]))
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            self.check()

    def test_rejected_old_source_does_not_override_selected_source(self):
        self.records.insert(0, {'character': 'a', 'candidate': 'voices/old.wav'})
        self.assertTrue(self.check()['ok'])

    def test_selected_rejected_source_is_blocked(self):
        self.records[0]['status'] = 'rejected_and_not_used_in_final'
        with self.assertRaisesRegex(ValueError, 'rejected/superseded'):
            self.check()

    def test_rights_basis_is_required(self):
        self.records[0]['rights_basis'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'rights basis'):
            self.check()

    def test_malformed_records_fail_with_actionable_error(self):
        self.records = ['not a record']
        with self.assertRaisesRegex(ValueError, 'list of records'):
            self.check()

    def test_silent_project_requires_no_voice_manifest(self):
        self.lines['lines'] = []
        self.assertEqual(self.check()['speakers'], [])


if __name__ == '__main__':
    unittest.main()
