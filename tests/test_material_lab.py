from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from src.envs.material_lab import MaterialLabEnv
from src.envs.material_lab.demo import run_demo
from src.harness.base import ModelHarness
from src.harness.types import ChatResponse, ToolCall
from src.interact import build_action_tool, run_interaction
from src.tasks.identify_material import IdentifyMaterialTask
from src.tasks.shoot_ball import ShootBallTask


def specimen(key, mass_g, volume_ml):
    return {'id': key, 'mass_kg': mass_g/1000, 'volume_m3': volume_ml*1e-6, 'color': 'blue'}


class ScriptedHarness(ModelHarness):
    model_name = 'offline-test'

    def __init__(self, batches):
        self.batches = iter(batches)
        self.requests = []

    def generate(self, messages, tools=None, **kwargs):
        self.requests.append(deepcopy(messages))
        return ChatResponse(tool_calls=next(self.batches))


class MaterialLabTests(unittest.TestCase):
    def setUp(self):
        self.env = MaterialLabEnv(specimens=[specimen('A', 60, 80), specimen('B', 40, 80)])

    def test_initial_public_views_are_independent_of_hidden_properties(self):
        other = MaterialLabEnv(specimens=[specimen('A', 175, 51), specimen('B', 13, 120)])
        self.assertEqual(self.env.observe(), other.observe())
        self.assertEqual(self.env.get_state(), other.get_state())
        self.assertEqual(self.env.description(), other.description())
        self.assertEqual(self.env.objects, other.objects)
        self.assertEqual(self.env.get_object('A'), other.get_object('A'))
        self.assertEqual(IdentifyMaterialTask(self.env).get_prompt(), IdentifyMaterialTask(other).get_prompt())
        for item in self.env.objects.values():
            self.assertEqual(set(item), {'id', 'color', 'shape'})
        self.assertNotIn('seed', self.env.observe())

    def test_balance_measures_comparisons_without_numeric_unknown_mass(self):
        cases = [(['A'], ['B'], 'left_down'), (['B'], ['A'], 'right_down'),
                 (['A'], ['weight_50g', 'weight_10g'], 'level'),
                 (['A', 'B'], ['weight_100g'], 'level'), ([], [], 'level')]
        for left, right, expected in cases:
            result = self.env.experiment({'operation': 'balance', 'left_pan': left, 'right_pan': right})
            self.assertEqual(result['observation']['reading'], expected)
            self.assertEqual(set(result['observation']), {'instrument', 'left_pan', 'right_pan', 'reading'})

    def test_duplicate_items_unknown_ids_and_malformed_actions_do_not_spend_budget(self):
        actions = [None, [], {'operation': 'reveal'}, {'operation': ['balance']},
                   {'operation': 'balance', 'left_pan': ['A'], 'right_pan': ['A']},
                   {'operation': 'balance', 'left_pan': ['weight_1g', 'weight_1g'], 'right_pan': []},
                   {'operation': 'balance', 'left_pan': ['missing'], 'right_pan': []},
                   {'operation': 'balance', 'left_pan': 'A', 'right_pan': []},
                   {'operation': 'displace', 'specimen_id': ['A']},
                   {'operation': 'displace', 'specimen_id': 'A', 'mass_g': 1}]
        for action in actions:
            self.assertFalse(self.env.experiment(action)['success'], action)
        self.assertEqual(self.env.observe()['experiments_used'], 0)

    def test_displacement_does_not_depend_on_density_or_reveal_float_state(self):
        env = MaterialLabEnv(specimens=[specimen('light', 40, 80), specimen('heavy', 160, 80)])
        observations = []
        for key in ('light', 'heavy'):
            result = env.experiment({'operation': 'displace', 'specimen_id': key})['observation']
            self.assertEqual(result['water_level_before_ml'], 100)
            self.assertEqual(result['water_level_after_ml'], 180)
            self.assertTrue(result['fully_submerged_by_holder'])
            self.assertNotIn('density', result)
            self.assertNotIn('floating', result)
            observations.append({k: v for k, v in result.items() if k != 'specimen_id'})
        self.assertEqual(*observations)

    def test_instrument_resolution_and_tolerance(self):
        env = MaterialLabEnv(specimens=[specimen('A', 60.4, 80.4), specimen('B', 60.6, 80.6)])
        for key, expected in [('A', 'level'), ('B', 'left_down')]:
            result = env.experiment({'operation': 'balance', 'left_pan': [key],
                                     'right_pan': ['weight_50g', 'weight_10g']})
            self.assertEqual(result['observation']['reading'], expected)
        for key, expected in [('A', 180), ('B', 181)]:
            self.assertEqual(env.experiment({'operation': 'displace', 'specimen_id': key})['observation']['water_level_after_ml'], expected)

    def test_budget_overload_overflow_and_reset_preserve_specimens(self):
        env = MaterialLabEnv(specimens=[specimen('large', 1200, 600)], max_experiments=2)
        original = env.private_manifest()
        self.assertEqual(env.experiment({'operation': 'balance', 'left_pan': ['large'], 'right_pan': []})['observation']['reading'], 'overload')
        result = env.experiment({'operation': 'displace', 'specimen_id': 'large'})
        self.assertEqual(result['observation']['reading'], 'overflow')
        self.assertIsNone(result['observation']['water_level_after_ml'])
        self.assertFalse(env.experiment({'operation': 'displace', 'specimen_id': 'large'})['success'])
        self.assertTrue(env.experiment({'operation': 'inspect'})['success'])
        env.reset()
        self.assertEqual(env.private_manifest(), original)
        self.assertEqual(env.observe()['experiments_used'], 0)

    def test_observations_and_returned_readings_cannot_mutate_environment(self):
        result = self.env.experiment({'operation': 'balance', 'left_pan': ['A'], 'right_pan': []})
        result['observation']['left_pan'].clear()
        view = self.env.observe()
        view['notebook'].clear()
        view['specimens'][0]['id'] = 'changed'
        self.assertEqual(self.env.observe()['notebook'][0]['left_pan'], ['A'])
        self.assertEqual(self.env.observe()['specimens'][0]['id'], 'A')

    def test_private_manifest_round_trip_keeps_exact_episode(self):
        env = MaterialLabEnv(seed=13, max_experiments=21)
        manifest = json.loads(json.dumps(env.private_manifest()))
        restored = MaterialLabEnv.from_private_manifest(manifest)
        self.assertEqual(restored.private_manifest(), manifest)
        self.assertEqual(restored.observe(), env.observe())
        manifest['units']['mass'] = 'g'
        with self.assertRaises(ValueError):
            MaterialLabEnv.from_private_manifest(manifest)

    def test_submission_acknowledgement_is_not_a_correctness_oracle(self):
        task = IdentifyMaterialTask(self.env)
        action = {'operation': 'submit_estimates', 'estimates': [
            {'specimen_id': 'A', 'mass_g': 60, 'volume_ml': 80, 'density_kg_m3': 750}]}
        task.apply_action(action)
        correct_reply = task.evaluate()
        self.assertEqual(task.get_private_evaluation()['score'], .5)
        action['estimates'][0].update(mass_g=1, volume_ml=1, density_kg_m3=1)
        task.apply_action(action)
        self.assertEqual(task.evaluate(), correct_reply)
        self.assertEqual(task.get_private_evaluation()['score'], 0)
        self.assertNotIn('correct', task.evaluate())
        self.assertNotIn('ground_truth', task.evaluate())

    def test_invalid_submissions_are_atomic(self):
        task = IdentifyMaterialTask(self.env)
        for bad in (float('nan'), float('inf'), True, -1):
            task.apply_action({'operation': 'submit_estimates', 'estimates': [
                {'specimen_id': 'A', 'mass_g': 60, 'volume_ml': 80, 'density_kg_m3': 750},
                {'specimen_id': 'B', 'mass_g': bad, 'volume_ml': 80, 'density_kg_m3': 500}]})
            self.assertFalse(task.evaluate()['success'])
            self.assertIsNone(task.get_private_evaluation()['specimens']['A']['estimate'])

    def test_public_reference_policy_recovers_properties_across_seeds(self):
        for seed in range(16):
            task = IdentifyMaterialTask(MaterialLabEnv(seed=seed))
            def submit(action):
                task.apply_action(action)
                return task.evaluate()
            run_demo(task.env.observe(), submit)
            score = task.get_private_evaluation()
            self.assertEqual(score['score'], 1, seed)
            self.assertLessEqual(score['experiments_used'], 48)

    def test_typed_tools_and_legacy_velocity_schema(self):
        schema = build_action_tool(IdentifyMaterialTask(self.env)).parameters
        self.assertEqual(schema['properties']['operation']['type'], 'string')
        self.assertEqual(schema['properties']['left_pan']['type'], 'array')
        self.assertNotIn('seed', json.dumps(schema))
        legacy = build_action_tool(ShootBallTask()).parameters
        self.assertEqual(legacy['required'], ['vx', 'vy', 'vz'])
        self.assertEqual(legacy['properties']['vx']['type'], 'number')

    def test_runner_preserves_experiments_handles_batches_and_separates_private_score(self):
        task = IdentifyMaterialTask(self.env)
        def call(identifier, action=None, function='submit_action'):
            return ToolCall(identifier, function, json.dumps(action or {}))
        harness = ScriptedHarness([
            [call('a', {'operation': 'balance', 'left_pan': ['A'], 'right_pan': ['B']}),
             call('b', {'operation': 'reveal'}), ToolCall('bad_json', 'submit_action', '{')],
            [call('c', {'operation': 'displace', 'specimen_id': 'A'}),
             call('d', function='finish'), call('e', {'operation': 'displace', 'specimen_id': 'B'})],
        ])
        with tempfile.TemporaryDirectory() as directory:
            record = run_interaction(task, 'identify_material', harness, max_turns=3, output_dir=directory)
            public = json.loads((Path(directory)/'interaction.json').read_text())
            private = json.loads((Path(directory)/'private_evaluation.json').read_text())
        self.assertTrue(record.finished)
        self.assertEqual(task.env.observe()['experiments_used'], 2)
        self.assertEqual(len(harness.requests), 2)
        replies = [m['tool_call_id'] for m in public['messages'] if m['role'] == 'tool']
        self.assertEqual(replies, ['a', 'b', 'bad_json', 'c', 'd', 'e'])
        self.assertNotIn('ground_truth', json.dumps(public))
        self.assertNotIn('private_manifest', json.dumps(public))
        self.assertEqual(private['specimens']['A']['ground_truth']['mass_g'], 60)


if __name__ == '__main__':
    unittest.main()
