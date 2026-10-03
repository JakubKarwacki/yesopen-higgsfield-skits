"""Shutdown regressions; no GPU, network, provider or other pipeline modules required."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / 'coordinator' / 'state.py'
spec = importlib.util.spec_from_file_location('shutdown_state', module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ShutdownDrainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = module.State(Path(self.temp.name) / 'state.sqlite')

    def submit(self, project, tasks):
        return self.state.submit({'project_id': project, 'revision': 'v1',
                                  'files': {}, 'tasks': tasks}, lambda _: None)

    def finished_film(self, project='ducks'):
        run = self.submit(project, [{'id': 'encode', 'kind': 'encode'},
                                   {'id': 'approve-final', 'kind': 'gate', 'deps': ['encode']}])
        task = self.state.claim('cpu', lambda t: t['kind'] == 'encode')
        self.state.update(task, 'done', result={'artifacts': {'final.mp4': {'sha256': 'test'}}})
        return run

    def test_finished_film_review_does_not_keep_server_running_or_mutate_film(self):
        run = self.finished_film()
        before = self.state.snapshot(run)
        result = self.state.drain()
        self.assertTrue(result['safe_to_stop'])
        self.assertEqual(result['outstanding'], 0)
        self.assertEqual(result['pending_reviews'], 1)
        self.assertEqual(result['review_tasks'][0]['task'], 'approve-final')
        self.assertEqual(self.state.snapshot(run), before)
        self.assertEqual(self.state.drain(), result)
        with self.assertRaises(ValueError):
            self.submit('new', [{'id': 'encode', 'kind': 'encode'}])

    def test_other_film_queued_compute_still_blocks(self):
        self.finished_film()
        run = self.submit('salon', [{'id': 'encode', 'kind': 'encode'}])
        result = self.state.drain()
        self.assertFalse(result['safe_to_stop'])
        self.assertEqual(result['outstanding'], 1)
        self.assertEqual(result['blocking_tasks'][0]['run'], run)
        self.assertEqual(result['pending_reviews'], 1)

    def test_active_and_unknown_work_block_even_when_cancel_requested(self):
        for state in ['dispatching', 'accepted', 'running', 'unknown']:
            with self.subTest(state=state):
                self.state.resume()
                run = self.submit(state, [{'id': 'encode', 'kind': 'encode'}])
                task = self.state.claim(state, lambda t: t['kind'] == 'encode')
                self.state.update(task, state)
                self.state.cancel(run)
                self.assertFalse(self.state.drain()['safe_to_stop'])
                self.state.update(task, 'done')
                self.assertTrue(self.state.drain()['safe_to_stop'])

    def test_unfinished_compute_behind_review_is_reported_not_hidden(self):
        self.submit('pending', [{'id': 'review', 'kind': 'gate'},
                                {'id': 'render', 'kind': 'render', 'deps': ['review']}])
        result = self.state.drain()
        self.assertFalse(result['safe_to_stop'])
        self.assertEqual(result['pending_reviews'], 1)
        self.assertEqual(result['blocking_tasks'][0]['task'], 'render')

    def test_empty_queue_and_resume(self):
        self.assertTrue(self.state.drain()['safe_to_stop'])
        self.state.resume()
        self.submit('new', [{'id': 'review', 'kind': 'gate'}])
        self.assertTrue(self.state.drain()['safe_to_stop'])

    def test_unknown_gate_is_not_mistaken_for_idle_review(self):
        run = self.submit('unknown-gate', [{'id': 'review', 'kind': 'gate'}])
        with self.state.tx() as db:
            db.execute("UPDATE tasks SET state='unknown' WHERE run=?", (run,))
        self.assertFalse(self.state.drain()['safe_to_stop'])


if __name__ == '__main__':
    unittest.main()
