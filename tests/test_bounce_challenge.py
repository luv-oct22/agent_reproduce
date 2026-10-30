from collections import Counter
import json
import math
from pathlib import Path
import tempfile
import unittest

from src.envs.bounce_lab import BounceLabEnv
from src.harness.types import ChatResponse, ToolCall
from src.interact import InteractionRecord
from src.simulation.bounce_challenge import prepare_hard_batch
from src.simulation.bounce_scene import scene_digest, IMAGES
from src.bounce_evaluate import evaluate_bounce, validate_inputs
from src.worlds.bounce_motion import advance_bouncing


class BounceChallengeTests(unittest.TestCase):
    def prepare(self, root):
        source, output = root/'source', root/'images'
        env = BounceLabEnv(max_experiments=16, restitution_by_specimen={
            'sample_A': .6, 'sample_B': .85, 'sample_C': .35, 'sample_D': .75})
        env.export_private_artifacts(source)
        InteractionRecord('identify_bounce', 'experiment-test',
            messages=[{'role': 'assistant', 'content': 'FIRST_WORLD_EVIDENCE'}], finished=True).save(str(source/'interaction.json'))
        batch = prepare_hard_batch(source, output)
        return source, output, batch

    def rendered_fixtures(self, root, batch):
        for entry in batch['questions']:
            folder = root/entry['folder']
            scene = json.loads((folder/'scene.json').read_text())
            for filename in IMAGES.values():
                (folder/filename).write_bytes(b'\x89PNG\r\n\x1a\nfixture')
                (folder/(Path(filename).stem+'_parameters.md')).write_text('fixture')
            (folder/'scene.blend').write_bytes(b'fixture')
            (folder/'build_report.json').write_text(json.dumps({'images_rendered': True, 'scene_digest': scene_digest(scene)}))

    def test_same_pixels_different_answers_both_objects_required_and_physical_truth(self):
        with tempfile.TemporaryDirectory() as d:
            source, root, batch = self.prepare(Path(d))
            scenes = [json.loads((root/e['folder']/'scene.json').read_text()) for e in batch['questions']]
            self.assertEqual(len(scenes), 16)
            self.assertEqual(Counter(s['answer'] for s in scenes), dict.fromkeys('ABCD', 4))
            worlds = {e['key']: BounceLabEnv.from_private_manifest(json.loads((root/e['folder']/'private_manifest.json').read_text()))
                      for e in batch['worlds']}
            for a, b in zip(scenes[::2], scenes[1::2]):
                for key in ('objects', 'choices', 'scene', 'elapsed_s', 'surface_id'):
                    self.assertEqual(a[key], b[key], key)
                self.assertNotEqual(a['answer'], b['answer'])
                self.assertNotEqual(a['world_id'], b['world_id'])
            impacts = set()
            for s in scenes:
                env = worlds[s['experiment_world']]
                good = s['choices'][s['answer']]['objects']
                intersections = set('ABCD')
                for i, o in enumerate(s['objects']):
                    expected = advance_bouncing(env._world, env._contacts, o['source_specimen_id'], o['position_m'],
                                                o['velocity_m_s'], s['elapsed_s'], o['radius_m'], s['surface_z_m'])
                    self.assertEqual(good[i]['position_m'], expected['position_m'])
                    impacts.add(expected['impacts'])
                    compatible = {k for k, c in s['choices'].items() if c['objects'][i]['position_m'] == good[i]['position_m']}
                    self.assertEqual(len(compatible), 2)
                    intersections &= compatible
                    alternative = next(c['objects'][i]['position_m'] for c in s['choices'].values()
                                       if c['objects'][i]['position_m'] != good[i]['position_m'])
                    gap = math.dist(good[i]['position_m'], alternative)
                    self.assertGreaterEqual(gap, .045)
                    self.assertLessEqual(gap, .12)
                self.assertEqual(intersections, {s['answer']})
            self.assertTrue({0, 1, 2, 3}.issubset(impacts))
            questions = json.loads((root/'questions.json').read_text())
            for q in questions:
                for word in ('blue', 'orange', 'green', 'purple', 'sample_A', 'world_001', 'bottom clearance 0.'):
                    self.assertNotIn(word, q['question'])
            self.assertNotEqual([s['answer'] for s in scenes[::2]], list('ABCDABCD'))

    def test_replace_archives_existing_outputs_without_mutating_them(self):
        with tempfile.TemporaryDirectory() as d:
            source, root, batch = self.prepare(Path(d))
            old = (root/'questions.json').read_bytes()
            (root/'original.png').write_bytes(b'preserve')
            with self.assertRaises(FileExistsError):
                prepare_hard_batch(source, root)
            prepare_hard_batch(source, root, seed=922, replace=True)
            archives = list(root.parent.glob('images_archive_*'))
            self.assertEqual(len(archives), 1)
            self.assertEqual((archives[0]/'questions.json').read_bytes(), old)
            self.assertEqual((archives[0]/'original.png').read_bytes(), b'preserve')
            self.assertFalse((root/'original.png').exists())

    def test_world_histories_are_acquired_separately_and_do_not_cross(self):
        with tempfile.TemporaryDirectory() as d:
            source, root, batch = self.prepare(Path(d))
            self.rendered_fixtures(root, batch)
            validate_inputs(source/'interaction.json', root)
            questions = json.loads((root/'questions.json').read_text())
            answers = {key: [q['answer'] for q, e in zip(questions, batch['questions']) if e['experiment_world'] == key]
                       for key in ('world_001', 'world_002')}
            outer = self
            calls = {'experiments': 0, 'world_001': 0, 'world_002': 0}
            class Harness:
                def __init__(self, model):
                    self.model_name = model
                def supports_tools(self):
                    return True
                def generate(self, messages, tools=None, **kwargs):
                    text = json.dumps([m.content for m in messages])
                    if tools:
                        outer.assertNotIn('FIRST_WORLD_EVIDENCE', text)
                        calls['experiments'] += 1
                        return ChatResponse(content='SECOND_WORLD_EVIDENCE', tool_calls=[ToolCall('done', 'finish', '{}')])
                    first = 'FIRST_WORLD_EVIDENCE' in text
                    second = 'SECOND_WORLD_EVIDENCE' in text
                    outer.assertNotEqual(first, second)
                    outer.assertNotIn('contact_registry_id', text)
                    outer.assertNotIn('paired_world_components', text)
                    key = 'world_001' if first else 'world_002'
                    answer = answers[key][calls[key]]
                    calls[key] += 1
                    return ChatResponse(content=answer)
            result = evaluate_bounce('vision-test', source/'interaction.json', root, Path(d)/'results', harness_factory=Harness)
            self.assertEqual(calls, {'experiments': 1, 'world_001': 8, 'world_002': 8})
            summary = json.loads((result/'summary.json').read_text())
            self.assertEqual(summary['image_score'], 1)
            self.assertEqual(summary['paired_world_score'], 1)
            saved = json.loads((result/'evaluation_with_history.json').read_text())
            self.assertEqual([a['question_id'] for a in saved['answers']], [q['id'] for q in questions])
            self.assertTrue((result/'world_runs/world_002/interaction.json').exists())
            # Reusing an interaction from the wrong physical world must fail before model calls.
            with self.assertRaises(ValueError):
                evaluate_bounce('vision-test', source/'interaction.json', root, Path(d)/'results',
                                world_records={'world_002': str(source/'interaction.json')}, harness_factory=Harness)
            prepared = evaluate_bounce('vision-test', source/'interaction.json', root, Path(d)/'results', prepare_only=True,
                                       world_records={'world_002': str(result/'world_runs/world_002/interaction.json')}, harness_factory=Harness)
            self.assertEqual(json.loads((prepared/'status.json').read_text())['model_calls'], 0)
            self.assertEqual(calls['experiments'], 1)

    def test_fresh_pipeline_validates_then_learns_each_world_with_separate_models(self):
        with tempfile.TemporaryDirectory() as d:
            _, root, batch = self.prepare(Path(d))
            calls = {'experiments': 0, 'world_001': 0, 'world_002': 0}
            outer = self
            questions = json.loads((root/'questions.json').read_text())
            answers = {key: [q['answer'] for q, entry in zip(questions, batch['questions'])
                             if entry['experiment_world'] == key]
                       for key in ('world_001', 'world_002')}

            class Harness:
                def __init__(self, model):
                    self.model_name = model

                def supports_tools(self):
                    return True

                def generate(self, messages, tools=None, **kwargs):
                    text = json.dumps([m.content for m in messages])
                    outer.assertNotIn('FIRST_WORLD_EVIDENCE', text)
                    outer.assertNotIn('contact_registry_id', text)
                    if tools:
                        outer.assertEqual(self.model_name, 'experiment-test')
                        calls['experiments'] += 1
                        marker = f'FRESH_EVIDENCE_{calls["experiments"]}'
                        outer.assertNotIn('FRESH_EVIDENCE_', text)
                        return ChatResponse(content=marker, tool_calls=[ToolCall('done', 'finish', '{}')])
                    outer.assertEqual(self.model_name, 'vision-test')
                    first, second = 'FRESH_EVIDENCE_1' in text, 'FRESH_EVIDENCE_2' in text
                    outer.assertNotEqual(first, second)
                    key = 'world_001' if first else 'world_002'
                    answer = answers[key][calls[key]]
                    calls[key] += 1
                    return ChatResponse(content=answer)

            with self.assertRaises(FileNotFoundError):
                evaluate_bounce('vision-test', batch_dir=root, output_dir=Path(d)/'results',
                                experiment_model='experiment-test', harness_factory=Harness)
            self.assertEqual(calls['experiments'], 0)
            self.rendered_fixtures(root, batch)
            prepared = evaluate_bounce('vision-test', batch_dir=root, output_dir=Path(d)/'results',
                                      prepare_only=True, harness_factory=Harness)
            params = json.loads((prepared/'run_parameters.json').read_text())
            self.assertEqual(params['experiment_model'], 'vision-test')
            self.assertEqual(params['worlds_requiring_interaction'], ['world_001', 'world_002'])
            self.assertIsNone(params['primary_record_source'])
            self.assertEqual(calls['experiments'], 0)
            result = evaluate_bounce('vision-test', batch_dir=root, output_dir=Path(d)/'results',
                                    experiment_model='experiment-test', harness_factory=Harness)
            self.assertEqual(calls, {'experiments': 2, 'world_001': 8, 'world_002': 8})
            self.assertEqual(json.loads((result/'summary.json').read_text())['paired_world_score'], 1)
            for key in ('world_001', 'world_002'):
                target = result/'world_runs'/key
                self.assertTrue((target/'interaction.json').exists())
                self.assertTrue((target/'private_evaluation.json').exists())


if __name__ == '__main__':
    unittest.main()
