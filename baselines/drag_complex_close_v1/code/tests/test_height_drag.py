from dataclasses import replace
import json
import math
from pathlib import Path
import tempfile
import unittest

from src.envs.drag_lab import DragLabEnv
from src.tasks.identify_drag import IdentifyDragTask
from src.worlds.layered_drag import LayeredDragWorld
from src.worlds.height_drag import HeightDragWorld, load_drag_world, validate_samples
from src.simulation.drag_scene import build_question, frame_state


class HeightDragTests(unittest.TestCase):
    def test_deterministic_smooth_nonnegative_profile_and_record_integrity(self):
        a = HeightDragWorld.generate(seed=42)
        self.assertEqual(a, HeightDragWorld.generate(seed=42))
        self.assertNotEqual(a, HeightDragWorld.generate(seed=43))
        self.assertEqual(load_drag_world(json.loads(json.dumps(a.to_dict()))), a)
        for i, z in enumerate(a.heights_m):
            self.assertAlmostEqual(a.coefficient(z), a.coefficients_kg_s[i])
            self.assertLess(abs(a.coefficient(z-1e-7)-a.coefficient(z+1e-7)), 1e-10)
        for i in range(601):
            self.assertTrue(.01 <= a.coefficient(i*.005) <= .30)
        self.assertEqual(a.coefficient(-1), a.coefficients_kg_s[0])
        self.assertEqual(a.coefficient(5), a.coefficients_kg_s[-1])
        data = a.to_dict()
        data['coefficients_kg_s'][2] += .01
        with self.assertRaises(ValueError):
            load_drag_world(data)

    def test_vacuum_and_uniform_analytic_reference(self):
        for coefficient in (0., .1, .5):
            numeric = HeightDragWorld(coefficients_kg_s=(coefficient, coefficient))
            exact = LayeredDragWorld(lower_drag_kg_s=coefficient, upper_drag_kg_s=coefficient)
            for height in (.1, 1., 2.5):
                a, b = numeric.drop_readings(height, .1, .03, .8), exact.drop_readings(height, .1, .03, .8)
                for key in a:
                    self.assertAlmostEqual(a[key], b[key], delta=1e-7)
            for t in (.2, 1.5, 3., 10.):
                a = numeric.advance([0, 0, 2.53], [1, 0, 0], t, .1, .03, .8)
                b = exact.advance([0, 0, 2.53], [1, 0, 0], t, .1, .03, .8)
                for key in ('position_m', 'velocity_m_s'):
                    self.assertLess(math.dist(a[key], b[key]), 1e-6)
        inelastic = HeightDragWorld().drop_readings(1, .1, .03, 0)
        self.assertEqual(inelastic['first_rebound_height_m'], 0)

    def test_step_convergence_repeated_impacts_and_horizontal_dissipation(self):
        world = HeightDragWorld.generate(seed=42)
        finer = replace(world, max_step_s=.0005)
        for h in (.2, 1.3, 2.5):
            a, b = world.drop_readings(h, .1, .03, .8), finer.drop_readings(h, .1, .03, .8)
            for key in a:
                self.assertAlmostEqual(a[key], b[key], delta=1e-6)
        p, v = [0, 0, 2.53], [.7, .2, 0]
        direct = world.advance(p, v, 4, .1, .03, .8)
        first = world.advance(p, v, .731, .1, .03, .8)
        split = world.advance(first['position_m'], first['velocity_m_s'], 3.269, .1, .03, .8)
        fine = finer.advance(p, v, 4, .1, .03, .8)
        for key in ('position_m', 'velocity_m_s'):
            self.assertLess(math.dist(direct[key], split[key]), 1e-6)
            self.assertLess(math.dist(direct[key], fine[key]), 1e-6)
        self.assertGreaterEqual(direct['impacts'], 2)
        previous = float('inf')
        for i in range(21):
            state = world.advance(p, v, i*.2, .1, .03, .8)
            energy = .05*sum(v*v for v in state['velocity_m_s'])+.3*(state['position_m'][2]-.03)
            self.assertGreaterEqual(state['position_m'][2], .03)
            self.assertLessEqual(energy, previous+1e-8)
            previous = energy
        self.assertLess(direct['velocity_m_s'][0], .7)

    def test_hidden_profiles_public_equivalence_reset_and_restoration(self):
        a = IdentifyDragTask(DragLabEnv(profile_type='smooth_random', profile_seed=42))
        b = IdentifyDragTask(DragLabEnv(profile_type='smooth_random', profile_seed=172, profile_knot_count=25))
        self.assertEqual(a.get_prompt(), b.get_prompt())
        self.assertEqual(a.get_action_space(), b.get_action_space())
        self.assertNotIn('two horizontal layers', a.get_prompt())
        for forbidden in ('generation_seed', 'world_id', 'profile_knot_count', str(a.env._world.coefficients_kg_s[0])):
            self.assertNotIn(forbidden, a.get_prompt())
        world = a.env._world.to_dict()
        action = dict(operation='bounce', specimen_id='sample_A', surface_id='surface_1', release_height_m=1.8)
        reading = a.env.experiment(action)
        a.env.reset()
        self.assertEqual(a.env._world.to_dict(), world)
        self.assertEqual(a.env.experiment(action), reading)
        with tempfile.TemporaryDirectory() as d:
            a.save_private_artifacts(d)
            saved = json.loads((Path(d)/'private_manifest.json').read_text())
            restored = DragLabEnv.from_private_manifest(saved)
            self.assertEqual(restored.experiment(action), reading)
            with self.assertRaises(FileExistsError):
                b.save_private_artifacts(d)

    def test_function_submissions_scores_and_bad_samples(self):
        task = IdentifyDragTask(DragLabEnv(profile_type='smooth_random'))
        for heights, coeff in (([0, 3], [-1, 0]), ([.1, 3], [.1, .2]),
                               ([0, 1, .5, 3], [.1]*4), ([0, .001, 3], [.1]*3),
                               ([0, 3], [float('nan'), .1]), ([0, 3], [.1]), (None, None)):
            with self.assertRaises(ValueError):
                validate_samples(heights, coeff)
            task.apply_action(dict(operation='submit_drag_estimate', heights_m=heights, coefficients_kg_s=coeff))
            self.assertFalse(task.evaluate()['success'])
        world = task.env._world
        task.apply_action(dict(operation='submit_drag_estimate', heights_m=list(world.heights_m),
                               coefficients_kg_s=list(world.coefficients_kg_s)))
        self.assertEqual(task.evaluate(), {'success': True, 'status': 'drag_estimate_recorded'})
        self.assertEqual(task.get_private_evaluation()['score'], 1)
        task.apply_action(dict(operation='submit_drag_estimate', heights_m=[0, 3], coefficients_kg_s=[0, 0]))
        self.assertLess(task.get_private_evaluation()['score'], 1)

    def test_image_prompt_and_state_use_new_profile(self):
        world = HeightDragWorld.generate()
        m = {'id': 'test', 'profile_type': 'smooth_random', 'elapsed_s': 1.2, 'answer': 'B'}
        q = build_question(m)
        self.assertIn('fixed smooth function', q['question'])
        self.assertNotIn('two invisible horizontal layers', q['question'])
        self.assertNotIn('coefficients_kg_s', q['question'])
        obj = dict(position_m=[-1, 0, 2.39], velocity_m_s=[.8, 0, 0], mass_kg=.1,
                   radius_m=.03, source_specimen_id='sample_A')
        state = frame_state(world, obj, 1.2, .8, .86)
        direct = world.advance([-1, 0, 1.53], [.8, 0, 0], 1.2, .1, .03, .8)
        self.assertAlmostEqual(state['position_m'][2]-.86, direct['position_m'][2], delta=1e-9)


if __name__ == '__main__':
    unittest.main()
