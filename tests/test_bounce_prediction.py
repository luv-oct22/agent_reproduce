from collections import Counter
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.envs.bounce_lab import BounceLabEnv
from src.worlds import UniformGravityWorld
from src.worlds.contact_registry import ContactRegistry
from src.worlds.bounce_motion import advance_bouncing
from src.simulation.bounce_scene import prepare_batch, scene_digest, IMAGES
from src.simulation.balance_batch import question_complete, render_experiment
from src.bounce_evaluate import validate_inputs, evaluate_bounce
from src.interact import InteractionRecord
from src.evaluation.visual import build_image_choice_content
from src.harness.types import ChatResponse


class BouncePredictionTests(unittest.TestCase):
    def test_exact_impacts_rebounds_and_finite_time_settling(self):
        world = UniformGravityWorld(2)
        contacts = ContactRegistry(world.world_id, 'test', 'surface_1', (('A', .5), ('B', 0), ('C', 1)))
        def sample(t, key='A'):
            return advance_bouncing(world, contacts, key, [0, 0, 1.1], [1, 0, 0], t, .1, 0)
        self.assertAlmostEqual(sample(.5)['position_m'][2], .85)
        self.assertEqual(sample(1)['impacts'], 1)
        self.assertAlmostEqual(sample(1)['velocity_m_s'][2], 1)
        self.assertAlmostEqual(sample(1.25)['position_m'][2], .2875)
        self.assertAlmostEqual(sample(1.5)['velocity_m_s'][2], 0)
        self.assertAlmostEqual(sample(2)['velocity_m_s'][2], .5)
        self.assertTrue(sample(3)['settled'])
        self.assertAlmostEqual(sample(3)['position_m'][2], .1)
        self.assertEqual(sample(3)['position_m'][0], 3)
        self.assertTrue(sample(1, 'B')['settled'])
        self.assertAlmostEqual(sample(3, 'C')['velocity_m_s'][2], 2)
        self.assertAlmostEqual(sample(2, 'C')['position_m'][2], 1.1)
        with self.assertRaises(ValueError):
            advance_bouncing(world, contacts, 'A', [0, 0, 0], [0, 0, 0], 1, .1, 0)

    def prepare(self, root):
        source = root/'source'
        env = BounceLabEnv(restitution_by_specimen={'sample_A': .6, 'sample_B': .85, 'sample_C': .35, 'sample_D': .75})
        env.export_private_artifacts(source)
        record = InteractionRecord('identify_bounce', 'offline-test',
                                   messages=[{'role': 'assistant', 'content': 'PUBLIC_EVIDENCE_MARKER: inferred gravity from drop experiments.'}], finished=True)
        record.save(str(source/'interaction.json'))
        output = root/'images'
        batch = prepare_batch(source, output)
        return source, output, batch

    def fake_renders(self, output, batch):
        for entry in batch['questions']:
            folder = output/entry['folder']
            manifest = json.loads((folder/'scene.json').read_text())
            for filename in IMAGES.values():
                (folder/filename).write_bytes(b'\x89PNG\r\n\x1a\nfixture')
                (folder/(Path(filename).stem+'_parameters.md')).write_text('test fixture')
            (folder/'scene.blend').write_bytes(b'fixture')
            (folder/'build_report.json').write_text(json.dumps({'images_rendered': True, 'scene_digest': scene_digest(manifest)}))

    def test_batch_physics_answers_public_text_and_stale_detection(self):
        with tempfile.TemporaryDirectory() as d:
            source, output, batch = self.prepare(Path(d))
            questions = json.loads((output/'questions.json').read_text())
            self.assertEqual(Counter(q['answer'] for q in questions), dict.fromkeys('ABCD', 2))
            self.assertEqual(len(questions), 8)
            for q, entry in zip(questions, batch['questions']):
                manifest = json.loads((output/entry['folder']/'scene.json').read_text())
                self.assertEqual(manifest['choices'][q['answer']]['hypothesis'], 'recorded_physics')
                self.assertGreaterEqual(manifest['minimum_candidate_separation_m'], .08)
                for color in ('blue', 'orange', 'green', 'purple', 'sample_A'):
                    self.assertNotIn(color, q['question'])
                for choice in manifest['choices'].values():
                    for obj, state in zip(manifest['objects'], choice['objects']):
                        self.assertGreaterEqual(state['position_m'][2]-obj['radius_m'], manifest['surface_z_m']-1e-9)
                self.assertFalse(question_complete(output/entry['folder']))
            with self.assertRaises(FileNotFoundError):
                validate_inputs(source/'interaction.json', output)
            self.fake_renders(output, batch)
            validate_inputs(source/'interaction.json', output)
            content = build_image_choice_content(questions[0], output)
            self.assertEqual(sum(p['type'] == 'image_url' for p in content), 5)
            text = ' '.join(p['text'] for p in content if p['type'] == 'text')
            self.assertNotIn('recorded_physics', text)
            self.assertNotIn('sha256:', text)
            folder = output/batch['questions'][0]['folder']
            scene = json.loads((folder/'scene.json').read_text())
            scene['elapsed_s'] += .01
            (folder/'scene.json').write_text(json.dumps(scene))
            self.assertFalse(question_complete(folder))
            with self.assertRaises(FileExistsError):
                prepare_batch(source, output)

    def test_render_dispatch_and_record_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            source, output, batch = self.prepare(Path(d))
            with patch('src.simulation.balance_batch.subprocess.run') as run:
                render_experiment(output)
            self.assertEqual(run.call_count, 8)
            self.assertIn('blender_bounce.py', ' '.join(run.call_args.args[0]))
            self.fake_renders(output, batch)
            data = json.loads((output/'batch.json').read_text())
            data['world_id'] = 'wrong'
            (output/'batch.json').write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'differs'):
                validate_inputs(source/'interaction.json', output)

    def test_evaluator_shares_history_records_responses_and_keeps_truth_private(self):
        with tempfile.TemporaryDirectory() as d:
            source, output, batch = self.prepare(Path(d))
            self.fake_renders(output, batch)
            outer = self
            class Harness:
                model_name = 'vision-test'
                def __init__(self, model):
                    self.index = 0
                def supports_tools(self):
                    return True
                def generate(self, messages, tools=None, **kwargs):
                    text = json.dumps([m.content for m in messages])
                    outer.assertIn('PUBLIC_EVIDENCE_MARKER', text)
                    outer.assertNotIn('ground_truth', text)
                    outer.assertNotIn('contact_registry_id', text)
                    result = ChatResponse(content='ABCD'[self.index%4])
                    self.index += 1
                    return result
            results = evaluate_bounce('vision-test', source/'interaction.json', output, Path(d)/'results', harness_factory=Harness)
            summary = json.loads((results/'summary.json').read_text())
            self.assertEqual(summary['image_score'], 1)
            self.assertEqual(len((results/'model_responses.jsonl').read_text().splitlines()), 8)
            self.assertTrue((results/'parameters.md').exists())
            self.assertTrue((results/'bounce_prediction/questions/q001/context.png').exists())


if __name__ == '__main__':
    unittest.main()
