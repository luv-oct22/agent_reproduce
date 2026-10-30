import json
from pathlib import Path
import tempfile
import unittest

from src.envs.object_attribute_bench import ObjectAttributeBenchEnv
from src.harness.types import ChatResponse, ToolCall
from src.interact import run_interaction
from src.simulation.config import build_env_from_config, build_task_from_config, load_config
from src.tasks.characterize_objects import CharacterizeObjectsTask
from src.worlds.attraction_setup import build_instance


class ObjectAttributeBenchTests(unittest.TestCase):
    def test_same_catalog_and_no_law_leak(self):
        tasks = [CharacterizeObjectsTask(ObjectAttributeBenchEnv(instance=build_instance(p))) for p in (2, 3)]
        self.assertEqual(tasks[0].get_prompt(), tasks[1].get_prompt())
        self.assertEqual(tasks[0].get_native_tools(), tasks[1].get_native_tools())
        prompt = tasks[0].get_prompt()
        for private in ('sha256:', 'central_attraction', 'exponent', 'strength', 'force', 'acceleration'):
            self.assertNotIn(private, prompt)
        self.assertEqual([t.name for t in tasks[0].get_native_tools()],
                         ['inspect_object', 'measure_mass', 'measure_volume', 'measure_geometry',
                          'measure_density', 'measure_inertia', 'finish'])

    def test_intrinsic_values_and_no_relational_result(self):
        env = ObjectAttributeBenchEnv(instance=build_instance(2))
        self.assertTrue(env.execute('inspect_object', {'object_id': 'probe'})['success'])
        mass = env.execute('measure_mass', {'object_id': 'probe'})
        volume = env.execute('measure_volume', {'object_id': 'probe'})
        geometry = env.execute('measure_geometry', {'object_id': 'probe'})
        density = env.execute('measure_density', {'object_id': 'probe'})
        inertia = env.execute('measure_inertia', {'object_id': 'probe'})
        self.assertEqual(mass['measurement']['value'], .1)
        self.assertEqual(volume['measurement']['value'], .000113)
        self.assertEqual(geometry['radius']['value'], .03)
        self.assertEqual(geometry['diameter']['value'], .06)
        self.assertAlmostEqual(density['measurement']['value'], 884.2, places=1)
        self.assertEqual(inertia['measurement']['value'], .000036)
        for result in (mass, volume, geometry, density, inertia):
            self.assertNotIn('force', result)
            self.assertNotIn('acceleration', result)
        self.assertEqual(env.units_used, 5)

    def test_values_do_not_depend_on_world_exponent(self):
        for object_id in ('anchor', 'probe'):
            results = []
            for exponent in (2, 3):
                env = ObjectAttributeBenchEnv(instance=build_instance(exponent))
                results.append([env.execute(name, {'object_id': object_id}) for name in
                                ('measure_mass', 'measure_volume', 'measure_geometry', 'measure_density', 'measure_inertia')])
            self.assertEqual(results[0], results[1])

    def test_budget_and_validation_fail_closed(self):
        env = ObjectAttributeBenchEnv(instance=build_instance(2), measurement_units=1)
        self.assertFalse(env.execute('measure_mass', {'object_id': 'missing'})['success'])
        self.assertFalse(env.execute('measure_mass', {'object_id': True})['success'])
        self.assertEqual(env.units_used, 0)
        self.assertTrue(env.execute('measure_mass', {'object_id': 'probe'})['success'])
        self.assertFalse(env.execute('measure_volume', {'object_id': 'probe'})['success'])
        self.assertFalse(env.execute('measure_force', {'object_id': 'probe'})['success'])
        self.assertEqual(env.units_used, 1)

    def test_finish_and_private_replay_record(self):
        env = ObjectAttributeBenchEnv(instance=build_instance(3))
        class Harness:
            model_name = 'offline-test'
            def generate(self, messages, tools=None):
                if not hasattr(self, 'called'):
                    self.called = True
                    return ChatResponse(tool_calls=[ToolCall('a', 'measure_mass', '{"object_id":"probe"}')])
                return ChatResponse(tool_calls=[ToolCall('b', 'finish', '{}')])
        with tempfile.TemporaryDirectory() as directory:
            record = run_interaction(CharacterizeObjectsTask(env), 'characterize_objects', Harness(),
                                     max_turns=8, output_dir=directory)
            self.assertTrue(record.finished)
            private = json.loads((Path(directory)/'private_episode.json').read_text())
            self.assertEqual(private['units_used'], 1)
            self.assertNotIn('sha256:', json.dumps(record.messages))
            self.assertNotIn('mass_kg', json.dumps(record.messages))

    def test_configs_build(self):
        for p in (2, 3):
            config = load_config(f'configs/object_attributes_p{p}.yaml')
            env = build_env_from_config(config)
            task = build_task_from_config(config, env)
            self.assertEqual(task.get_turn_limit(), 8)
            self.assertEqual(env.units_remaining, 12)


if __name__ == '__main__':
    unittest.main()
