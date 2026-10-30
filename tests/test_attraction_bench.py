from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from src.envs.attraction_bench import AttractionBenchEnv, sensor_reading
from src.harness.types import ChatResponse, ToolCall
from src.interact import InteractionRecord, run_interaction
from src.simulation.config import load_config, build_env_from_config, build_task_from_config
from src.tasks.discover_world import DiscoverWorldTask
from src.worlds.attraction_setup import build_instance
from src.worlds.definition import ProtocolSpec, WorldInstance


def bench(p=2, budget=24, **kwargs):
    instance = build_instance(p, **kwargs)
    if budget != 24:
        data = instance.payload
        protocol = data['protocol']['payload']
        protocol['budget']['measurement_units'] = budget
        data['protocol'] = ProtocolSpec(protocol).to_dict()
        instance = WorldInstance(data)
    return AttractionBenchEnv(instance=instance)


def configure(env, x=2., time=0., velocity=None):
    return env.execute('configure_trial', dict(object_id='probe', position_m=[x, 0., 1.5],
                                              velocity_m_s=velocity or [0., 0., 0.], start_time_s=time))


class AttractionBenchTests(unittest.TestCase):
    def test_matched_public_prompts_and_tools_without_truth(self):
        tasks = [DiscoverWorldTask(bench(p)) for p in (2, 3)]
        self.assertEqual(tasks[0].get_prompt(), tasks[1].get_prompt())
        self.assertEqual(tasks[0].get_native_tools(), tasks[1].get_native_tools())
        for word in ('exponent', 'strength', 'sha256:', 'inverse', 'solver', 'provenance'):
            self.assertNotIn(word, tasks[0].get_prompt())
        self.assertEqual([t.name for t in tasks[0].get_native_tools()],
                         ['inspect', 'configure_trial', 'apply_impulse', 'measure_force', 'track_motion', 'finish'])

    def test_force_reading_direction_precision_cost_and_distinguishability(self):
        values = []
        for p in (2, 3):
            env = bench(p)
            self.assertTrue(configure(env)['success'])
            before = env.state
            result = env.execute('measure_force', {'object_id': 'probe'})
            values.append(result['force']['value'])
            self.assertEqual(result['units_remaining'], 23)
            self.assertEqual(env.state, before)
            reverse = env.execute('measure_force', {'object_id': 'anchor'})
            self.assertEqual(reverse['force']['value'], [-v for v in values[-1]])
        self.assertEqual(values, [[-.03, 0., 0.], [-.015, 0., 0.]])

    def test_rounding_ties_and_sensor_saturation(self):
        spec = dict(resolution=.001, range=[-10., 10.], unit='N')
        self.assertEqual(sensor_reading([.0015, -.0015, 12.], spec)['value'], [.002, -.002, 10.])
        env = bench(3)
        configure(env, .21)
        result = env.execute('measure_force', {'object_id': 'probe'})
        self.assertEqual(result['force']['value'], [-10., 0., 0.])
        self.assertEqual(result['force']['saturated'], [True, False, False])

    def test_tracking_clock_and_no_free_state_readout(self):
        env = bench(strength_n=0.)
        configure(env, 4.5, 10., [1., 0., 0.])
        setup = env.observe()['last_commanded_setup']
        result = env.execute('track_motion', dict(object_id='probe', duration_s=1., sample_count=2))
        self.assertTrue(result['success'])
        self.assertEqual([s['time_s'] for s in result['samples']], [10.5, 11.])
        self.assertEqual([s['position']['value'][0] for s in result['samples']], [5., 5.])
        self.assertEqual(result['samples'][-1]['position']['saturated'], [True, False, False])
        self.assertEqual(env.time, 11.)
        self.assertAlmostEqual(env.state.payload['objects']['probe']['position_m'][0], 5.5)
        observation = env.execute('inspect', {})['observation']
        self.assertEqual(observation['last_commanded_setup'], setup)
        self.assertEqual(observation, env.get_state())
        self.assertNotIn('5.5', json.dumps(observation))
        self.assertEqual(env.units_used, 2)
        configure(env, time=2.)
        self.assertEqual(env.time, 2.)
        self.assertEqual(env.units_remaining, 22)

    def test_impulse_updates_velocity_without_measuring_it(self):
        env = bench(strength_n=0.)
        configure(env, velocity=[1., 0., 0.])
        result = env.execute('apply_impulse', dict(object_id='probe', impulse_N_s=[.1, 0., 0.]))
        self.assertEqual(result['cost_units'], 1)
        self.assertNotIn('velocity', json.dumps(result))
        self.assertEqual(env.state.payload['objects']['probe']['velocity_m_s'], [2., 0., 0.])
        result = env.execute('track_motion', dict(object_id='probe', duration_s=.5, sample_count=1))
        self.assertEqual(result['samples'][0]['position']['value'], [3., 0., 1.5])

    def test_validation_no_cost_no_state_change(self):
        env = bench()
        original = env.state
        cases = [('measure_force', {'object_id': 'unknown'}), ('inspect', {'secret': True}),
                 ('finish', {'ignored': 1}), ('configure_trial', {}),
                 ('track_motion', dict(object_id='probe', duration_s=1., sample_count=True)),
                 ('track_motion', dict(object_id='probe', duration_s=float('nan'), sample_count=1)),
                 ('apply_impulse', dict(object_id='probe', impulse_N_s=[0., float('inf'), 0.])),
                 ('apply_impulse', dict(object_id='probe', impulse_N_s=[0., 0.])),
                 ('apply_impulse', dict(object_id='anchor', impulse_N_s=[0., 0., 0.])),
                 ('track_motion', dict(object_id='probe', duration_s=1., sample_count=25)),
                 ('unknown', {})]
        for name, args in cases:
            with self.subTest(name=name, args=args):
                self.assertFalse(env.execute(name, args)['success'])
                self.assertEqual(env.state, original)
                self.assertEqual(env.units_used, 0)
        self.assertFalse(env.finished)

    def test_budget_enforced_before_execution_and_never_reset_by_agent(self):
        env = bench(budget=2)
        original = env.state
        self.assertFalse(env.execute('track_motion', dict(object_id='probe', duration_s=.1, sample_count=3))['success'])
        self.assertEqual(env.state, original)
        self.assertEqual(env.units_used, 0)
        for _ in range(2):
            self.assertTrue(env.execute('measure_force', {'object_id': 'probe'})['success'])
        configure(env)
        self.assertEqual(env.units_remaining, 0)
        self.assertFalse(env.execute('measure_force', {'object_id': 'probe'})['success'])
        self.assertTrue(env.execute('inspect', {})['success'])
        self.assertTrue(env.execute('finish', {})['success'])

    def test_failed_paid_experiment_charged_and_atomically_rolled_back(self):
        env = bench()
        configure(env, .3, velocity=[-10., 0., 0.])
        original = env.state
        result = env.execute('track_motion', dict(object_id='probe', duration_s=.1, sample_count=4))
        self.assertFalse(result['success'])
        self.assertEqual(env.state, original)
        self.assertEqual(env.time, 0.)
        self.assertEqual(result['cost_units'], 4)
        self.assertEqual(env.units_remaining, 20)
        self.assertNotIn('samples', result)
        self.assertNotIn('minimum step', result['error'])
        configure(env, time=29.9)
        original = env.state
        result = env.execute('track_motion', dict(object_id='probe', duration_s=.2, sample_count=1))
        self.assertFalse(result['success'])
        self.assertEqual(env.state, original)
        self.assertEqual(env.units_remaining, 19)

    def test_configuration_failure_and_finished_state(self):
        env = bench()
        original = env.state
        self.assertFalse(configure(env, .1)['success'])
        self.assertEqual(env.state, original)
        self.assertEqual(env.units_remaining, 24)
        env.execute('finish', {})
        self.assertFalse(configure(env)['success'])
        self.assertEqual(env.state, original)

    def test_journal_replays_motion_impulse_failures_and_clock_resets(self):
        env = bench()
        configure(env, time=2., velocity=[0., .5, 0.])
        env.execute('apply_impulse', dict(object_id='probe', impulse_N_s=[0., .01, 0.]))
        env.execute('track_motion', dict(object_id='probe', duration_s=.2, sample_count=3))
        configure(env, .3, time=0., velocity=[-10., 0., 0.])
        env.execute('track_motion', dict(object_id='probe', duration_s=.1, sample_count=2))
        env.execute('finish', {})
        # Validation also remains safe after finish, even for non-JSON numbers.
        env.execute('track_motion', dict(object_id='probe', duration_s=float('nan'), sample_count=1))
        journal = json.loads(json.dumps(env.events, allow_nan=False))
        replay = bench()
        for event in journal:
            self.assertEqual(replay.state.record_id, event['state_before'])
            self.assertEqual(replay.execute(event['tool'], event['arguments']), event['result'])
            self.assertEqual(replay.state.record_id, event['state_after'])
            self.assertEqual(replay.units_used, event['units_used'])
        self.assertEqual(env.units_used, 6)
        self.assertEqual(replay.observe(), env.observe())

    def test_config_builds_saved_world_without_changing_it(self):
        for p in (2, 3):
            config = load_config(f'configs/attraction_p{p}.yaml')
            env = build_env_from_config(config)
            self.assertEqual(env.instance, build_instance(p))
            task = build_task_from_config(config, env)
            self.assertEqual(task.get_turn_limit(), 8)

    def test_runner_native_batch_validation_finish_and_checkpoint_replay(self):
        env = bench()
        task = DiscoverWorldTask(env)
        class Harness:
            model_name = 'offline-test'
            def generate(self, messages, tools=None):
                return ChatResponse(tool_calls=[
                    ToolCall('bad-json', 'finish', '{'),
                    ToolCall('invalid-finish', 'finish', '{"extra": 1}'),
                    ToolCall('unknown', 'not_a_tool', '{}'),
                    ToolCall('force', 'measure_force', '{"object_id":"probe"}'),
                    ToolCall('finish', 'finish', '{}'),
                    ToolCall('after-finish', 'measure_force', '{"object_id":"probe"}'),
                ])
        with tempfile.TemporaryDirectory() as directory:
            record = run_interaction(task, 'discover_world', Harness(), output_dir=directory)
            self.assertTrue(record.finished)
            self.assertEqual(env.units_used, 1)
            root = Path(directory)
            self.assertEqual(InteractionRecord.load(str(root/'interaction.json')), record)
            self.assertFalse((root/'private_evaluation.json').exists())
            private = json.loads((root/'private_episode.json').read_text())
            replay = AttractionBenchEnv(instance_path=root/'world_instance.json')
            for event in private['events']:
                self.assertEqual(replay.state.record_id, event['state_before'])
                self.assertEqual(replay.execute(event['tool'], event['arguments']), event['result'])
                self.assertEqual(replay.state.record_id, event['state_after'])
            self.assertEqual(replay.state.to_dict(), private['state'])
            self.assertEqual(replay.units_used, private['units_used'])
            public = json.dumps(record.messages)
            self.assertNotIn('sha256:', public)
            self.assertNotIn('state_before', public)
            params = json.loads((root/'run_parameters.json').read_text())
            self.assertEqual(params['requested_max_turns'], 10)
            self.assertEqual(params['effective_max_turns'], 8)

    def test_turn_cap_and_neutral_retry_prompt(self):
        class Harness:
            model_name = 'offline-test'
            calls = 0
            def generate(self, messages, tools=None):
                self.calls += 1
                self.messages = deepcopy(messages)
                return ChatResponse(content='thinking')
        harness = Harness()
        record = run_interaction(DiscoverWorldTask(bench()), 'discover_world', harness, max_turns=100)
        self.assertEqual(harness.calls, 8)
        self.assertFalse(record.finished)
        self.assertNotIn('submit_action', json.dumps(record.messages))


if __name__ == '__main__':
    unittest.main()
