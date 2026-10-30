import json
from pathlib import Path
import tempfile
import unittest

from src.density_pipeline import run_pipeline
from src.harness.types import ChatResponse, ToolCall
from src.objects.registry import ObjectRegistry
from src.objects.specimen import generate_specimens
from src.simulation.balance_batch import prepare_experiment
from src.simulation.balance_scene import IMAGES
from src.simulation.balance_challenge import prepare_challenge
from src.simulation.liquid_scene import prepare_liquid_batch, liquid_visual_settings


class PipelineTests(unittest.TestCase):
    def test_liquid_pipeline_reuses_experiments_and_saves_liquid_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = ObjectRegistry(tuple(generate_specimens(7)), seed=7).save(root/'registry.json')
            batch = root/'liquid'
            definition = prepare_liquid_batch(source, batch)
            for entry in definition['questions']:
                folder = batch/entry['folder']
                for filename in IMAGES.values():
                    (folder/filename).write_bytes(b'\x89PNG\r\n\x1a\nfixture')
                    (folder/f'{Path(filename).stem}_parameters.md').write_text('render parameters')
                (folder/'scene.blend').write_bytes(b'fixture')
                (folder/'build_report.json').write_text(json.dumps({
                    'images_rendered': True,
                    'visual_settings': liquid_visual_settings(json.loads((folder/'scene.json').read_text()))}))
            run = run_pipeline('experiment-test', 'vision-test', batch_dir=batch,
                               output_dir=root/'results', harness_factory=self.factory(batch))
            self.assertEqual(json.loads((run/'summary.json').read_text())['image_questions_answered'], 8)
            self.assertTrue((run/'liquid_equilibrium/questions.json').is_file())
            self.assertFalse((run/'density_balance').exists())
            requests = (run/'model_requests.jsonl').read_text()
            self.assertNotIn('liquid_density_kg_m3', requests)
            self.assertNotIn('submerged_fraction', requests)

    def setup_batch(self, root):
        source = ObjectRegistry(tuple(generate_specimens(23)), seed=23).save(root/'registry.json')
        batch = root/'batch'
        definition = prepare_experiment(source, batch)
        for entry in definition['questions']:
            folder = batch/entry['folder']
            for filename in IMAGES.values():
                (folder/filename).write_bytes(b'\x89PNG\r\n\x1a\nfixture')
                (folder/f'{Path(filename).stem}_parameters.md').write_text('render parameters')
            (folder/'scene.blend').write_bytes(b'large scene not needed in snapshot')
        return batch

    def factory(self, batch, fail_evaluation=False):
        answers = [q['answer'] for q in json.loads((batch/'questions.json').read_text())]
        class Harness:
            def __init__(self, model):
                self.model_name = model
                self.calls = 0
            def supports_tools(self):
                return True
            def generate(self, messages, tools=None, **kwargs):
                self.calls += 1
                if self.model_name == 'experiment-test':
                    if self.calls == 1:
                        return ChatResponse(content='Measure sample A.', tool_calls=[ToolCall(
                            'measure', 'submit_action', '{"operation":"displace","specimen_id":"sample_A"}')])
                    return ChatResponse(tool_calls=[ToolCall('done', 'finish', '{}')])
                if fail_evaluation and self.calls == 2:
                    raise RuntimeError('simulated interrupted evaluation')
                return ChatResponse(content=answers[self.calls-1])
        return Harness

    def test_combined_run_snapshots_inputs_and_records_both_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            batch = self.setup_batch(root)
            run = run_pipeline('experiment-test', 'vision-test', batch_dir=batch,
                               output_dir=root/'results', max_turns=3, harness_factory=self.factory(batch))
            summary = json.loads((run/'summary.json').read_text())
            self.assertEqual(summary['status'], 'complete')
            self.assertEqual(summary['image_score'], 1)
            self.assertEqual(summary['experiments_used'], 1)
            self.assertEqual(summary['experiment_score'], 0)  # Fixture did not submit any estimates.
            self.assertTrue(summary['interaction_finished'])
            registry = ObjectRegistry.load(run/'object_registry.json')
            self.assertEqual(registry.registry_id, ObjectRegistry.load(batch/'object_registry.json').registry_id)
            self.assertEqual(registry.seed, 23)  # Must override config's seed 7 using image registry.
            self.assertEqual(len(list((run/'density_balance').rglob('*.png'))), 30)
            self.assertFalse(list((run/'density_balance').rglob('*.blend')))
            responses = [json.loads(line) for line in (run/'model_responses.jsonl').read_text().splitlines()]
            self.assertEqual(len(responses), 8)
            self.assertEqual({r['stage'] for r in responses}, {'experiments', 'image_evaluation'})
            requests = (run/'model_requests.jsonl').read_text()
            self.assertIn('saved-image-data-uri:sha256:', requests)
            self.assertNotIn('data:image/png;base64,', requests)
            self.assertNotIn(registry.registry_id, requests)
            self.assertTrue((run/'parameters.md').exists())
            self.assertTrue((run/'evaluation_with_history.json').exists())

    def test_failed_second_stage_retains_first_stage_and_completed_answers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            batch = self.setup_batch(root)
            with self.assertRaisesRegex(RuntimeError, 'interrupted evaluation'):
                run_pipeline('experiment-test', 'vision-test', batch_dir=batch,
                             output_dir=root/'results', harness_factory=self.factory(batch, True))
            run = next((root/'results').iterdir())
            self.assertEqual(json.loads((run/'status.json').read_text())['status'], 'failed')
            self.assertTrue(json.loads((run/'interaction.json').read_text())['finished'])
            self.assertEqual(len(json.loads((run/'evaluation_with_history.json').read_text())['answers']), 1)
            self.assertTrue((run/'private_evaluation.json').exists())
            last_response = json.loads((run/'model_responses.jsonl').read_text().splitlines()[-1])
            self.assertEqual(last_response['error_type'], 'RuntimeError')

    def test_registry_mismatch_rejected_before_model_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            batch = self.setup_batch(root)
            q = json.loads((batch/'questions.json').read_text())
            q[0]['object_registry_id'] = 'different episode'
            (batch/'questions.json').write_text(json.dumps(q))
            def factory(model):
                self.fail('Must not call a model with mismatched registries')
            with self.assertRaisesRegex(ValueError, 'same object registry'):
                run_pipeline('test', batch_dir=batch, output_dir=root/'results', harness_factory=factory)

    def test_hard_pipeline_does_not_expose_evaluation_only_objects_to_experiment_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = ObjectRegistry(tuple(generate_specimens(7)), seed=7).save(root/'registry.json')
            batch = root/'hard'
            definition = prepare_challenge(source, batch)
            for entry in definition['questions']:
                folder = batch/entry['folder']
                for filename in IMAGES.values():
                    (folder/filename).write_bytes(b'\x89PNG\r\n\x1a\nfixture')
                    (folder/f'{Path(filename).stem}_parameters.md').write_text('render parameters')
                (folder/'scene.blend').write_bytes(b'fixture')
            run = run_pipeline('experiment-test', 'vision-test', batch_dir=batch,
                               output_dir=root/'results', harness_factory=self.factory(batch))
            self.assertEqual(json.loads((run/'summary.json').read_text())['image_questions_answered'], 32)
            self.assertEqual(len(ObjectRegistry.load(run/'object_registry.json').specimens), 4)
            self.assertEqual(len(ObjectRegistry.load(run/'density_balance/evaluation_registry.json').specimens), 6)
            requests = [json.loads(line) for line in (run/'model_requests.jsonl').read_text().splitlines()]
            self.assertNotIn('unseen_1', json.dumps(requests))
            self.assertNotIn('unseen_2', json.dumps(requests))


if __name__ == '__main__':
    unittest.main()
