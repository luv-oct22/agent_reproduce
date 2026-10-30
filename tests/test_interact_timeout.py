from copy import deepcopy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx
from openai import APITimeoutError, AuthenticationError

from src.envs.drag_lab import DragLabEnv
from src.harness.openai import OpenAIHarness
from src.harness.types import ChatResponse, ToolCall
from src.interact import InteractionRecord, run_interaction
from src.tasks.identify_drag import IdentifyDragTask


def timeout():
    return APITimeoutError(request=httpx.Request('POST', 'https://example.invalid'))


class InteractTimeoutTests(unittest.TestCase):
    def test_preserves_completed_measurement_and_continues_after_skipped_turn(self):
        task = IdentifyDragTask(DragLabEnv())
        snapshots = []
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'interaction.json'
            class Harness:
                model_name = 'offline-test'
                def generate(self, messages, tools=None):
                    snapshots.append(deepcopy(messages))
                    if len(snapshots) == 1:
                        action = dict(operation='bounce', specimen_id='sample_A', surface_id='surface_1', release_height_m=1)
                        return ChatResponse(tool_calls=[ToolCall('measure', 'submit_action', json.dumps(action))])
                    if len(snapshots) == 2:
                        raise timeout()
                    saved = InteractionRecord.load(str(path))
                    self_outer.assertEqual(saved.skipped_turns[0]['turn'], 2)
                    return ChatResponse(tool_calls=[ToolCall('done', 'finish', '{}')])
            self_outer = self
            record = run_interaction(task, 'identify_drag', Harness(), max_turns=3, output_dir=directory)
            self.assertTrue(record.finished)
            self.assertEqual(task.env.observe()['experiments_used'], 1)
            self.assertEqual(len(record.skipped_turns), 1)
            self.assertFalse(record.skipped_turns[0]['action_executed'])
            self.assertEqual(snapshots[2][:-1], snapshots[1])
            self.assertIn('turn 2', snapshots[2][-1].content)
            self.assertEqual(sum(m['role'] == 'assistant' for m in record.messages), 2)
            self.assertEqual(InteractionRecord.load(str(path)), record)
            self.assertTrue((Path(directory)/'private_evaluation.json').exists())

    def test_all_timeouts_are_bounded_and_last_skip_is_saved(self):
        task = IdentifyDragTask(DragLabEnv())
        class Harness:
            model_name = 'offline-test'
            calls = 0
            def generate(self, *args, **kwargs):
                self.calls += 1
                raise timeout()
        harness = Harness()
        with tempfile.TemporaryDirectory() as directory:
            record = run_interaction(task, 'identify_drag', harness, max_turns=3, output_dir=directory)
            self.assertEqual(harness.calls, 3)
            self.assertFalse(record.finished)
            self.assertEqual([r['turn'] for r in record.skipped_turns], [1, 2, 3])
            self.assertEqual(task.env.observe()['experiments_used'], 0)
            self.assertEqual(InteractionRecord.load(str(Path(directory)/'interaction.json')), record)
            self.assertTrue((Path(directory)/'private_evaluation.json').exists())

    def test_real_harness_exhausts_retry_budget_before_skipping(self):
        finish = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='', tool_calls=[
            SimpleNamespace(id='done', function=SimpleNamespace(name='finish', arguments='{}'))]))], usage=None)
        with patch.dict('os.environ', {'OPENAI_MAX_RETRIES': '2'}, clear=True), \
                patch('src.harness.openai.OpenAI') as client, patch('src.harness.openai.time.sleep') as sleep:
            create = client.return_value.chat.completions.create
            create.side_effect = [timeout(), timeout(), timeout(), finish]
            record = run_interaction(IdentifyDragTask(DragLabEnv()), 'identify_drag',
                                     OpenAIHarness('offline-test', api_key='test'), max_turns=2)
            self.assertTrue(record.finished)
            self.assertEqual(create.call_count, 4)
            self.assertEqual([c.args[0] for c in sleep.call_args_list], [5, 10])
            self.assertEqual(len(record.skipped_turns), 1)
            self.assertEqual(create.call_args_list[0], create.call_args_list[2])
            self.assertNotEqual(create.call_args_list[2], create.call_args_list[3])

    def test_authentication_and_programming_errors_still_raise(self):
        request = httpx.Request('POST', 'https://example.invalid')
        auth = AuthenticationError('invalid key', response=httpx.Response(401, request=request), body={})
        for error in (auth, RuntimeError('programming error')):
            class Harness:
                model_name = 'offline-test'
                def generate(self, *args, **kwargs):
                    raise error
            with self.assertRaises(type(error)):
                run_interaction(IdentifyDragTask(DragLabEnv()), 'identify_drag', Harness(), max_turns=2)

    def test_old_records_without_skip_metadata_still_load(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'interaction.json'
            path.write_text(json.dumps(dict(task_name='identify_drag', model='old-model', messages=[], finished=True)))
            record = InteractionRecord.load(str(path))
            self.assertEqual(record.skipped_turns, [])
            self.assertTrue(record.finished)


if __name__ == '__main__':
    unittest.main()
