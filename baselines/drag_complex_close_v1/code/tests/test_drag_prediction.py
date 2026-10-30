from collections import Counter
import json
import math
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from src.envs.drag_lab import DragLabEnv
from src.interact import InteractionRecord
from src.harness.types import ChatResponse
from src.simulation.drag_scene import prepare_batch, frame_state
from src.simulation.bounce_scene import scene_digest, IMAGES
from src.simulation.balance_batch import question_complete, render_experiment
from src.drag_evaluate import validate_inputs, evaluate_drag
from src.worlds.layered_drag import LayeredDragWorld


class DragPredictionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = tempfile.TemporaryDirectory()
        cls.root = Path(cls.template.name)
        env = DragLabEnv()
        env.export_private_artifacts(cls.root/'source')
        InteractionRecord('identify_drag', 'offline-experiment', messages=[
            {'role': 'assistant', 'content': 'PUBLIC_DRAG_EVIDENCE: measured impact time and rebound height.'}
        ], finished=True).save(str(cls.root/'source/interaction.json'))
        cls.batch = prepare_batch(cls.root/'source', cls.root/'batch', candidate_mode='legacy')

    @classmethod
    def tearDownClass(cls):
        cls.template.cleanup()

    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.path = Path(self.work.name)
        shutil.copytree(self.root/'source', self.path/'source')
        shutil.copytree(self.root/'batch', self.path/'batch')
        self.source, self.images = self.path/'source', self.path/'batch'

    def fake_renders(self):
        for entry in self.batch['questions']:
            folder = self.images/entry['folder']
            manifest = json.loads((folder/'scene.json').read_text())
            for filename in IMAGES.values():
                (folder/filename).write_bytes(b'\x89PNG\r\n\x1a\nfixture')
                (folder/(Path(filename).stem+'_parameters.md')).write_text('test fixture')
            (folder/'scene.blend').write_bytes(b'fixture')
            (folder/'build_report.json').write_text(json.dumps({'images_rendered': True, 'scene_digest': scene_digest(manifest)}))

    def test_batch_transfer_physics_and_public_question(self):
        questions = json.loads((self.images/'questions.json').read_text())
        self.assertEqual(Counter(q['answer'] for q in questions), dict.fromkeys('ABCD', 2))
        # The user's estimated boundary differs by 2 mm; its predictions should
        # still be much closer to the correct option than any distractor.
        learned = LayeredDragWorld(boundary_height_m=.848)
        for question, entry in zip(questions, self.batch['questions']):
            manifest = json.loads((self.images/entry['folder']/'scene.json').read_text())
            for forbidden in ('blue', 'sample_A', 'boundary_height_m', 'lower_drag_kg_s', 'upper_drag_kg_s',
                              'sha256', 'recorded_physics'):
                self.assertNotIn(forbidden, question['question'])
            truth = manifest['choices'][question['answer']]
            self.assertEqual(truth['hypothesis'], 'recorded_physics')
            approximate = frame_state(learned, manifest['objects'][0], manifest['elapsed_s'], .8, manifest['surface_z_m'])
            self.assertLess(math.dist(approximate['position_m'], truth['objects'][0]['position_m']), .01)
            self.assertGreaterEqual(manifest['minimum_candidate_separation_m'], .07)
            for choice in manifest['choices'].values():
                self.assertGreaterEqual(choice['objects'][0]['position_m'][2], manifest['surface_z_m']+.03-1e-10)
            self.assertFalse(question_complete(self.images/entry['folder']))
        with self.assertRaisesRegex(FileNotFoundError, 'Render missing'):
            validate_inputs(self.source/'interaction.json', self.images)

    def test_dispatch_matching_and_stale_physics(self):
        with patch('src.simulation.balance_batch.subprocess.run') as run:
            render_experiment(self.images)
        self.assertEqual(run.call_count, 8)
        self.assertIn('blender_bounce.py', ' '.join(run.call_args.args[0]))
        self.fake_renders()
        validate_inputs(self.source/'interaction.json', self.images)
        folder = self.images/self.batch['questions'][0]['folder']
        path = folder/'scene.json'
        manifest = json.loads(path.read_text())
        manifest['choices'][manifest['answer']]['objects'][0]['position_m'][0] += .1
        path.write_text(json.dumps(manifest))
        self.assertFalse(question_complete(folder))
        with self.assertRaisesRegex(ValueError, 'inconsistent'):
            validate_inputs(self.source/'interaction.json', self.images)
        other = self.path/'other_world'
        DragLabEnv(upper_drag_kg_s=.25).export_private_artifacts(other)
        shutil.copy2(self.source/'interaction.json', other/'interaction.json')
        with self.assertRaisesRegex(ValueError, 'differs'):
            validate_inputs(other/'interaction.json', self.images)

    def test_evaluation_shares_public_history_and_logs(self):
        self.fake_renders()
        answers = [q['answer'] for q in json.loads((self.images/'questions.json').read_text())]
        outer = self
        class Harness:
            model_name = 'offline-vision'
            def __init__(self, model):
                self.i = 0
            def supports_tools(self):
                return False
            def generate(self, messages, tools=None, **kwargs):
                content = json.dumps([m.content for m in messages])
                outer.assertIn('PUBLIC_DRAG_EVIDENCE', content)
                for forbidden in ('world_id', 'host_only', 'recorded_physics', 'private_manifest', 'answer":'):
                    outer.assertNotIn(forbidden, content)
                outer.assertEqual(sum(p['type'] == 'image_url' for p in messages[-1].content), 5)
                response = ChatResponse(content=answers[self.i])
                self.i += 1
                return response
        output = evaluate_drag('offline-vision', self.source/'interaction.json', self.images,
                               self.path/'results', harness_factory=Harness)
        self.assertEqual(json.loads((output/'summary.json').read_text())['image_score'], 1)
        self.assertEqual(len((output/'model_responses.jsonl').read_text().splitlines()), 8)
        self.assertTrue((output/'drag_prediction/questions/q001/context.png').exists())
        self.assertNotIn('data:image/png;base64', (output/'model_requests.jsonl').read_text())
        parameters = json.loads((output/'run_parameters.json').read_text())
        self.assertEqual(parameters['experiment_model'], 'offline-experiment')
        self.assertEqual(parameters['evaluation_model'], 'offline-vision')
        with patch('src.drag_evaluate.OpenAIHarness') as api:
            evaluate_drag('offline-vision', self.source/'interaction.json', self.images,
                          self.path/'prepared', prepare_only=True, harness_factory=api)
            api.assert_not_called()

    def test_failure_preserves_completed_questions(self):
        self.fake_renders()
        class FailingHarness:
            model_name = 'offline-failure'
            def __init__(self, model):
                self.i = 0
            def generate(self, messages, tools=None, **kwargs):
                self.i += 1
                if self.i == 2:
                    raise TimeoutError('offline timeout')
                return ChatResponse(content='A')
        with self.assertRaises(TimeoutError):
            evaluate_drag('offline-failure', self.source/'interaction.json', self.images,
                          self.path/'failed', harness_factory=FailingHarness)
        output = next((self.path/'failed').iterdir())
        self.assertEqual(json.loads((output/'status.json').read_text())['status'], 'failed')
        self.assertEqual(len(json.loads((output/'evaluation_with_history.json').read_text())['answers']), 1)


if __name__ == '__main__':
    unittest.main()
