import json
from pathlib import Path
import tempfile
import unittest

from src.envs.world_lab import WorldLabEnv
from src.tasks.identify_world import IdentifyWorldTask
from src.worlds import UniformGravityWorld


class WorldLabTests(unittest.TestCase):
    def test_gravity_hidden_until_experiment_and_fall_is_mass_independent(self):
        low = WorldLabEnv(gravity_m_s2=3)
        other = WorldLabEnv(gravity_m_s2=12)
        self.assertEqual(low.observe(), other.observe())
        self.assertEqual(IdentifyWorldTask(low).get_prompt(), IdentifyWorldTask(other).get_prompt())
        readings = []
        for specimen in low.objects:
            result = low.experiment({'operation': 'drop', 'specimen_id': specimen, 'distance_m': 1.5})
            readings.append(result['observation']['elapsed_time_s'])
            self.assertNotIn('gravity_m_s2', result['observation'])
        self.assertEqual(readings, [1, 1, 1, 1])
        self.assertEqual(other.experiment({'operation': 'drop', 'specimen_id': 'sample_A', 'distance_m': 1.5})['observation']['elapsed_time_s'], .5)
        self.assertEqual(low.observe()['experiments_used'], 4)

    def test_drop_validation_budget_and_reset(self):
        env = WorldLabEnv(max_experiments=1)
        for distance in (-1, 0, 3, True, float('nan')):
            self.assertFalse(env.experiment({'operation': 'drop', 'specimen_id': 'sample_A', 'distance_m': distance})['success'])
        self.assertEqual(env.observe()['experiments_used'], 0)
        action = {'operation': 'drop', 'specimen_id': 'sample_A', 'distance_m': .5}
        self.assertTrue(env.experiment(action)['success'])
        self.assertFalse(env.experiment(action)['success'])
        env.reset()
        self.assertTrue(env.experiment(action)['success'])
        self.assertEqual(env.private_manifest()['world']['gravity_m_s2'], 3)

    def test_world_records_round_trip_and_cannot_silently_change(self):
        env = WorldLabEnv(gravity_m_s2=3, seed=19)
        with tempfile.TemporaryDirectory() as directory:
            env.export_private_artifacts(directory)
            world = UniformGravityWorld.load(Path(directory)/'world.json')
            self.assertEqual(world.gravity_m_s2, 3)
            restored = WorldLabEnv.from_private_manifest(json.loads((Path(directory)/'private_manifest.json').read_text()))
            self.assertEqual(env.private_manifest(), restored.private_manifest())
            manifest_before = (Path(directory)/'private_manifest.json').read_bytes()
            with self.assertRaises(FileExistsError):
                WorldLabEnv(gravity_m_s2=9.81, seed=19).export_private_artifacts(directory)
            self.assertEqual((Path(directory)/'private_manifest.json').read_bytes(), manifest_before)
        changed = world.to_dict()
        changed['gravity_vector_m_s2'][-1] = -9.81
        with self.assertRaises(ValueError):
            UniformGravityWorld.from_dict(changed)

    def test_submission_not_an_oracle_and_world_grade_is_separate(self):
        task = IdentifyWorldTask()
        for estimate in (3, 9.81):
            task.apply_action({'operation': 'submit_world_estimate', 'gravity_m_s2': estimate})
            self.assertEqual(task.evaluate(), {'success': True, 'status': 'world_estimate_recorded'})
            self.assertEqual(task.get_private_evaluation()['world_score'], 1 if estimate == 3 else 0)
        schema = task.get_action_space()
        self.assertIn('drop', schema['properties']['operation']['enum'])
        self.assertIn('submit_world_estimate', schema['properties']['operation']['enum'])
        self.assertNotIn('default', schema['properties']['gravity_m_s2'])

    def test_exact_motion_and_unchanged_static_comparisons(self):
        world = UniformGravityWorld(3)
        state = world.advance([0, 0, 2], [1, 0, 0], 1)
        self.assertEqual(state, {'position_m': [1, 0, .5], 'velocity_m_s': [1, 0, -3]})
        low, high = WorldLabEnv(gravity_m_s2=3), WorldLabEnv(gravity_m_s2=12)
        for action in ({'operation': 'balance', 'left_pan': ['sample_A'], 'right_pan': ['sample_B']},
                       {'operation': 'displace', 'specimen_id': 'sample_C'}):
            self.assertEqual(low.experiment(action), high.experiment(action))


if __name__ == '__main__':
    unittest.main()
