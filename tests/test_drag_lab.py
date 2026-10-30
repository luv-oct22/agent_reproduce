from copy import deepcopy
import json
import math
from pathlib import Path
import tempfile
import unittest

from src.envs.drag_lab import DragLabEnv
from src.envs.drag_lab.demo import run_demo
from src.interact import run_interaction
from src.tasks.identify_drag import IdentifyDragTask
from src.worlds.layered_drag import LayeredDragWorld


def bounce(height=1):
    return dict(operation='bounce', specimen_id='sample_A', surface_id='surface_1', release_height_m=height)


def numeric_drop(world, height, dt=2e-5):
    """Independent small-step RK4 reference, with interpolated floor/apex events."""
    mass, radius, e = .1, .03, .8
    z, v, time, impact = radius+height, 0.0, 0.0, None
    def acceleration(z, v):
        b = world.lower_drag_kg_s if z < world.boundary_height_m else world.upper_drag_kg_s
        return -world.gravity_m_s2-b*v/mass
    for _ in range(1000000):
        a1 = acceleration(z, v)
        v2 = v+dt*a1/2
        a2 = acceleration(z+dt*v/2, v2)
        v3 = v+dt*a2/2
        a3 = acceleration(z+dt*v2/2, v3)
        v4 = v+dt*a3
        a4 = acceleration(z+dt*v3, v4)
        nz = z+dt*(v+2*v2+2*v3+v4)/6
        nv = v+dt*(a1+2*a2+2*a3+a4)/6
        if nz <= radius and impact is None:
            fraction = (z-radius)/(z-nz)
            time += dt*fraction
            impact = time
            z, v = radius, -e*(v+(nv-v)*fraction)
            continue
        if impact is not None and v > 0 >= nv:
            fraction = v/(v-nv)
            return impact, z+(nz-z)*fraction-radius
        z, v, time = nz, nv, time+dt
    raise AssertionError('Reference did not reach rebound apex.')


class DragWorldTests(unittest.TestCase):
    def test_vacuum_limit_and_uniform_drag_closed_form(self):
        world = LayeredDragWorld(lower_drag_kg_s=0, upper_drag_kg_s=0)
        for height in (.1, .85, 2.5):
            reading = world.drop_readings(height, .1, .03, .8)
            self.assertAlmostEqual(reading['time_to_first_impact_s'], math.sqrt(2*height/3), places=10)
            self.assertAlmostEqual(reading['first_rebound_height_m'], .8**2*height, places=10)
        world = LayeredDragWorld(lower_drag_kg_s=.1, upper_drag_kg_s=.1)
        reading = world.drop_readings(2, .1, .03, .8)
        t = reading['time_to_first_impact_s']
        self.assertAlmostEqual(3*(t-(1-math.exp(-t))), 2, places=10)
        up = .8*3*(1-math.exp(-t))
        expected_peak = up-3*math.log1p(up/3)
        self.assertAlmostEqual(reading['first_rebound_height_m'], expected_peak, places=10)

    def test_layer_events_against_independent_integration(self):
        for world in (LayeredDragWorld(), LayeredDragWorld(boundary_height_m=.4, lower_drag_kg_s=.25, upper_drag_kg_s=.01)):
            for height in (.2, 2.5):
                reading = world.drop_readings(height, .1, .03, .8)
                time, peak = numeric_drop(world, height)
                self.assertAlmostEqual(reading['time_to_first_impact_s'], time, delta=.00015)
                self.assertAlmostEqual(reading['first_rebound_height_m'], peak, delta=.00015)

    def test_arbitrary_time_states_boundaries_multiple_bounces_and_dissipation(self):
        world = LayeredDragWorld()
        p, v = [0, 0, 2.53], [.7, 0, 0]
        first = world.advance(p, v, .73, .1, .03, .8)
        split = world.advance(first['position_m'], first['velocity_m_s'], 3.27, .1, .03, .8)
        direct = world.advance(p, v, 4, .1, .03, .8)
        for name in ('position_m', 'velocity_m_s'):
            for a, b in zip(split[name], direct[name]):
                self.assertAlmostEqual(a, b, places=9)
        self.assertGreaterEqual(direct['impacts'], 2)
        previous_energy = float('inf')
        for i in range(61):
            state = world.advance(p, v, i/10, .1, .03, .8)
            pos, vel = state['position_m'], state['velocity_m_s']
            self.assertGreaterEqual(pos[2], .03-1e-10)
            energy = .5*.1*sum(x*x for x in vel)+.1*3*(pos[2]-.03)
            self.assertLessEqual(energy, previous_energy+1e-9)
            previous_energy = energy
        boundary = world.advance([0, 0, .85], [0, 0, 0], .01, .1, .03, .8)
        self.assertLess(boundary['position_m'][2], .85)
        resting = world.advance([0, 0, .03], [1, 0, 0], 2, .1, .03, .8)
        self.assertEqual(resting['position_m'][2], .03)
        self.assertAlmostEqual(resting['velocity_m_s'][0], math.exp(-.6))

    def test_low_probes_cannot_observe_upper_drag_but_high_probes_can(self):
        a = DragLabEnv(upper_drag_kg_s=.1)
        b = DragLabEnv(upper_drag_kg_s=.4)
        for height in (.1, .3, .5):
            self.assertEqual(a.experiment(bounce(height)), b.experiment(bounce(height)))
        self.assertNotEqual(a.experiment(bounce(2.5))['observation'], b.experiment(bounce(2.5))['observation'])


class DragLabTests(unittest.TestCase):
    def test_public_interfaces_do_not_reveal_hidden_profile(self):
        a = IdentifyDragTask(DragLabEnv())
        b = IdentifyDragTask(DragLabEnv(boundary_height_m=1.6, lower_drag_kg_s=.3, upper_drag_kg_s=.02))
        self.assertEqual(a.get_prompt(), b.get_prompt())
        self.assertEqual(a.get_action_space(), b.get_action_space())
        self.assertEqual(a.env.get_state(), b.env.get_state())
        self.assertEqual(a.env.objects, b.env.objects)
        a.apply_action(bounce())
        reading = a.evaluate()['observation']
        self.assertEqual(set(reading), {'instrument', 'specimen_id', 'surface_id', 'release_height_m',
                                       'release_from_rest', 'time_to_first_impact_s', 'first_rebound_height_m'})
        for task in (a, b):
            task.apply_action(dict(operation='submit_drag_estimate', boundary_height_m=.85,
                                   lower_drag_kg_s=.03, upper_drag_kg_s=.18))
        self.assertEqual(a.evaluate(), b.evaluate())
        self.assertEqual(a.get_private_evaluation()['score'], 1)
        self.assertLess(b.get_private_evaluation()['score'], 1)

    def test_validation_budget_and_no_oracle_via_invalid_actions(self):
        env = DragLabEnv(max_experiments=2)
        invalid = [dict(bounce(), release_height_m=x) for x in (0, True, float('nan'), float('inf'), '1', 2.6)]
        invalid += [dict(bounce(), extra=True), dict(bounce(), specimen_id=[]), None,
                    {'operation': 'drop', 'specimen_id': 'sample_A', 'release_height_m': .1, 'trajectory': True}]
        for action in invalid:
            self.assertFalse(env.experiment(action)['success'])
        self.assertEqual(env.observe()['experiments_used'], 0)
        result = env.experiment(bounce())
        result['observation']['first_rebound_height_m'] = 900
        self.assertNotEqual(env.observe()['notebook'][0]['first_rebound_height_m'], 900)
        self.assertTrue(env.experiment({'operation': 'drop', 'specimen_id': 'sample_A', 'release_height_m': .1})['success'])
        self.assertFalse(env.experiment(bounce())['success'])
        self.assertTrue(env.experiment({'operation': 'inspect'})['success'])
        original = env.private_manifest()
        env.reset()
        self.assertEqual(original, env.private_manifest())
        self.assertEqual(env.observe()['experiments_used'], 0)

    def test_artifacts_roundtrip_conflicts_and_failed_api_checkpoint(self):
        env = DragLabEnv()
        task = IdentifyDragTask(env)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            task.save_private_artifacts(root)
            manifest = json.loads((root/'private_manifest.json').read_text())
            restored = DragLabEnv.from_private_manifest(manifest)
            self.assertEqual(env.experiment(bounce()), restored.experiment(bounce()))
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            with self.assertRaises(FileExistsError):
                DragLabEnv(upper_drag_kg_s=.4).export_private_artifacts(root)
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})
            changed = deepcopy(manifest)
            changed['world']['upper_drag_kg_s'] = .4
            with self.assertRaises(ValueError):
                DragLabEnv.from_private_manifest(changed)
            class FailingHarness:
                model_name = 'offline-failure'
                def generate(self, *args, **kwargs):
                    raise RuntimeError('test failure')
            with self.assertRaises(RuntimeError):
                run_interaction(task, 'identify_drag', FailingHarness(), output_dir=d)
            self.assertTrue((root/'interaction.json').exists())
            public = (root/'interaction.json').read_text()
            self.assertNotIn(env._world.world_id, public)
            self.assertNotIn('private_manifest', public)

    def test_demo_recovers_predictions_from_public_measurements(self):
        for params in ({}, {'boundary_height_m': 1.15, 'lower_drag_kg_s': .2, 'upper_drag_kg_s': .04}):
            task = IdentifyDragTask(DragLabEnv(**params))
            def submit(action):
                task.apply_action(action)
                return task.evaluate()
            run_demo(task.env.observe(), submit)
            evaluation = task.get_private_evaluation()
            self.assertEqual(evaluation['experiments_used'], 7)
            self.assertGreaterEqual(evaluation['score'], .875, evaluation)
            observed = {x['release_height_m'] for x in task.env.observe()['notebook']}
            self.assertTrue(all(row['release_height_m'] not in observed for row in evaluation['prediction_checks']))


if __name__ == '__main__':
    unittest.main()
