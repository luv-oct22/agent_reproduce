import json
import tempfile
import unittest
from pathlib import Path

from src.envs.autonomous_attraction_bench import AutonomousAttractionBenchEnv
from src.harness.types import ChatResponse, ToolCall
from src.interact import run_interaction
from src.simulation.config import build_env_from_config, build_task_from_config, load_config
from src.tasks.discover_world import DiscoverWorldTask
from src.worlds.attraction_setup import build_instance


class AutonomousAttractionBenchTests(unittest.TestCase):
    def test_agent_gets_combined_catalog_and_public_matched_prompt(self):
        tasks = [DiscoverWorldTask(AutonomousAttractionBenchEnv(instance=build_instance(p))) for p in (2, 3)]
        self.assertEqual(tasks[0].get_prompt(), tasks[1].get_prompt())
        names = [t.name for t in tasks[0].get_native_tools()]
        self.assertEqual(names, ['inspect', 'configure_trial', 'apply_impulse', 'measure_force',
                                 'track_motion', 'finish', 'inspect_object', 'measure_mass',
                                 'measure_volume', 'measure_geometry', 'measure_density', 'measure_inertia'])
        prompt = tasks[0].get_prompt()
        for secret in ('sha256:', 'central_attraction', 'exponent', 'strength', 'mass_kg', 'radius_m'):
            self.assertNotIn(secret, prompt)

    def test_intrinsic_and_law_measurements_share_budget_but_remain_separate(self):
        env = AutonomousAttractionBenchEnv(instance=build_instance(2))
        mass = env.execute('measure_mass', {'object_id': 'probe'})
        force = env.execute('measure_force', {'object_id': 'probe'})
        self.assertTrue(mass['success'])
        self.assertTrue(force['success'])
        self.assertEqual(mass['measurement']['value'], .1)
        self.assertNotIn('force', mass)
        self.assertIn('force', force)
        self.assertEqual(env.units_used, 2)
        self.assertEqual(env.attributes.units_used, env.units_used)

    def test_attribute_tool_does_not_reset_motion_and_finish_is_shared(self):
        env = AutonomousAttractionBenchEnv(instance=build_instance(3))
        env.execute('configure_trial', dict(object_id='probe', position_m=[1., 0., 1.5],
                                            velocity_m_s=[0., 0., 0.], start_time_s=4.))
        state = env.state
        env.execute('measure_geometry', {'object_id': 'probe'})
        self.assertEqual(env.state, state)
        self.assertTrue(env.execute('finish', {})['success'])
        self.assertTrue(env.finished)
        self.assertFalse(env.execute('measure_mass', {'object_id': 'probe'})['success'])

    def test_combined_runner_allows_agent_planning(self):
        class Harness:
            model_name = 'offline-test'
            def generate(self, messages, tools=None):
                if len([m for m in messages if getattr(m, 'role', None) == 'assistant']) == 0:
                    return ChatResponse(tool_calls=[ToolCall('mass', 'measure_mass', '{"object_id":"probe"}')])
                return ChatResponse(tool_calls=[ToolCall('done', 'finish', '{}')])
        with tempfile.TemporaryDirectory() as directory:
            task = DiscoverWorldTask(AutonomousAttractionBenchEnv(instance=build_instance(2)))
            record = run_interaction(task, 'discover_world', Harness(), max_turns=8, output_dir=directory)
            self.assertTrue(record.finished)
            private = json.loads((Path(directory)/'private_episode.json').read_text())
            self.assertEqual(private['units_used'], 1)

    def test_configs_build(self):
        for p in (2, 3):
            config = load_config(f'configs/attraction_autonomous_p{p}.yaml')
            env = build_env_from_config(config)
            task = build_task_from_config(config, env)
            self.assertEqual(len(task.get_native_tools()), 12)


if __name__ == '__main__':
    unittest.main()
