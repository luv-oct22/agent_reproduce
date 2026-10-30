import json
import math
from pathlib import Path
import tempfile
import unittest

from src.worlds.attraction import AttractionWorld, DomainError, MotionState
from src.worlds.attraction_setup import build_instance, prepare_pair
from src.worlds.definition import FieldSpec, LawSpec, ObjectSpec, SolverSpec, WorldSpec, WorldInstance


def modify(instance, component, change):
    d = instance.payload
    if component == 'solver':
        payload = d['solver']['payload']
        change(payload)
        d['solver'] = SolverSpec(payload).to_dict()
    else:
        world = d['world']['payload']
        cls = {'laws': LawSpec, 'fields': FieldSpec, 'objects': ObjectSpec}[component]
        payload = world[component][0]['payload']
        change(payload)
        world[component][0] = cls(payload).to_dict()
        d['world'] = WorldSpec(world).to_dict()
    return WorldInstance(d)


def probe_state(world, position=(1., 0., 0.), velocity=(0., 0., 0.), time=0.):
    return world.make_state({'anchor': [0., 0., 0.], 'probe': list(position)},
                            {'anchor': [0., 0., 0.], 'probe': list(velocity)}, time)


def values(state):
    obj = state.payload['objects']['probe']
    return obj['position_m']+obj['velocity_m_s']


class AttractionTests(unittest.TestCase):
    def test_exact_force_distance_exponent_direction_and_reciprocity(self):
        for p in (2, 3):
            world = AttractionWorld(build_instance(p))
            for distance in (.4, 1., 2.):
                state = probe_state(world, (0., 0., distance))
                force = world.forces(state)
                self.assertAlmostEqual(force['probe'][2], -.12/distance**p, places=13)
                self.assertEqual(force['probe'][:2], [0., 0.])
                self.assertEqual(force['anchor'], [-v for v in force['probe']])
                self.assertEqual(world.accelerations(state)['anchor'], [0., 0., 0.])
                self.assertAlmostEqual(world.accelerations(state)['probe'][2], -1.2/distance**p, places=12)
            near = abs(world.forces(probe_state(world))['probe'][0])
            far = abs(world.forces(probe_state(world, (2., 0., 0.)))['probe'][0])
            self.assertAlmostEqual(near/far, 2**p)

    def test_normalized_reference_scales_and_source_mass(self):
        instance = modify(build_instance(3), 'laws', lambda p: p['parameters'].update(
            reference_distance_m=2., reference_mass_kg=.5))
        instance = modify(instance, 'objects', lambda p: p.update(mass_kg=2.))
        world = AttractionWorld(instance)
        force = world.forces(probe_state(world, (3., 0., 0.)))['probe'][0]
        self.assertAlmostEqual(force, -1.2*(2/.5)*(.1/.5)*(2/3)**3, places=14)

    def test_circular_orbits_against_analytic_solution(self):
        radius, mu = 1.3, 1.2
        for p in (2, 3):
            world = AttractionWorld(build_instance(p, max_step_s=.01))
            speed = math.sqrt(mu/radius**(p-1))
            omega = speed/radius
            state = probe_state(world, (radius, 0., 0.), (0., speed, 0.))
            t = 2*math.pi/omega
            final = world.advance(state, t)
            self.assertLess(math.dist(values(final), values(state)), 2e-7)
            energy_a, energy_b = world.diagnostics(state), world.diagnostics(final)
            self.assertAlmostEqual(energy_a['total_energy_j'], energy_b['total_energy_j'], delta=1e-9)

    def test_convergence_and_split_trajectory(self):
        for p in (2, 3):
            worlds = [AttractionWorld(build_instance(p, max_step_s=h)) for h in (.02, .01, .000625)]
            initial = [probe_state(w, (1.4, 0., 0.), (0., .6, .1)) for w in worlds]
            outputs = [w.advance(s, 1.1) for w, s in zip(worlds, initial)]
            coarse = math.dist(values(outputs[0]), values(outputs[2]))
            fine = math.dist(values(outputs[1]), values(outputs[2]))
            self.assertGreater(coarse, 1e-13)
            self.assertLess(fine, coarse/8)
            split = worlds[2].advance(worlds[2].advance(initial[2], .333), .767)
            self.assertLess(math.dist(values(split), values(outputs[2])), 1e-10)

    def test_two_moving_bodies_conserve_energy_and_momenta(self):
        for p in (2, 3):
            instance = modify(build_instance(p), 'objects', lambda o: o.update(motion='dynamic'))
            world = AttractionWorld(instance)
            radius, total_mass = 1.4, 1.1
            speed = math.sqrt(1.2*total_mass/radius**(p-1))
            state = world.make_state({'anchor': [-radius*.1/total_mass, 0., 0.], 'probe': [radius/total_mass, 0., 0.]},
                {'anchor': [0., -speed*.1/total_mass, 0.], 'probe': [0., speed/total_mass, 0.]})
            a, b = world.diagnostics(state), world.diagnostics(world.advance(state, 2.3))
            self.assertTrue(a['momentum_conservation_expected'])
            self.assertAlmostEqual(a['total_energy_j'], b['total_energy_j'], delta=1e-10)
            for key in ('momentum_kg_m_s', 'angular_momentum_kg_m2_s'):
                self.assertLess(math.dist(a[key], b[key]), 1e-10)

    def test_zero_strength_is_inertial_motion_and_fixed_anchor_stays_fixed(self):
        world = AttractionWorld(build_instance(2, strength_n=0.))
        state = probe_state(world, (1., 0., 0.), (.25, .5, .7), time=4.)
        final = world.advance(state, 2.)
        self.assertLess(math.dist(final.payload['objects']['probe']['position_m'], [1.5, 1., 1.4]), 1e-12)
        self.assertEqual(final.payload['objects']['anchor'], state.payload['objects']['anchor'])
        self.assertEqual(final.payload['time_s'], 6.)
        self.assertEqual(world.advance(state, 0), state)

    def test_domain_rejection_prevents_overlap_singularity_and_tunnelling(self):
        world = AttractionWorld(build_instance(3))
        for distance in (0., .1, .2):
            with self.assertRaises(DomainError):
                probe_state(world, (distance, 0., 0.))
        # Bodies cannot pass through the excluded region within one large step.
        free = AttractionWorld(build_instance(2, strength_n=0.))
        fast = probe_state(free, (1., 0., 0.), (-1e6, 0., 0.))
        before = fast.to_dict()
        with self.assertRaises(DomainError):
            free.advance(fast, .001)
        self.assertEqual(fast.to_dict(), before)
        with self.assertRaises(DomainError):
            world.advance(probe_state(world), 3.)
        # Geometry can impose a stricter boundary than the law cutoff.
        instance = modify(build_instance(2), 'objects', lambda o: o.update(volume_m3=4*math.pi*.3**3/3))
        with self.assertRaises(DomainError):
            probe_state(AttractionWorld(instance), (.25, 0., 0.))

    def test_state_identity_fixed_velocity_and_clock_validation(self):
        a, b = [AttractionWorld(build_instance(p)) for p in (2, 3)]
        state = probe_state(a)
        self.assertEqual(MotionState.from_dict(json.loads(json.dumps(state.to_dict()))), state)
        with self.assertRaisesRegex(ValueError, 'different physical world'):
            b.advance(state, .1)
        bad = state.payload
        bad['objects']['anchor']['velocity_m_s'][0] = .1
        with self.assertRaisesRegex(ValueError, 'Fixed objects'):
            a.forces(MotionState(bad))
        for duration in (-1, float('nan'), True, 31.):
            with self.assertRaises(ValueError):
                a.advance(state, duration)
        for samples in ([.1, .1], [.2, .1], [-1.], [31.]):
            with self.assertRaises(ValueError):
                a.trajectory(state, samples)
        samples = a.trajectory(state, [0., .1, .2])
        self.assertEqual([s.payload['time_s'] for s in samples], [0., .1, .2])

    def test_runtime_rejects_unsupported_metadata_instead_of_falling_back(self):
        changes = [('laws', lambda p: p['parameters'].update(exponent=4)),
                   ('solver', lambda p: p.update(kind='unknown_solver')),
                   ('solver', lambda p: p['parameters'].update(unrecognized_tolerance=.1)),
                   ('solver', lambda p: p['parameters'].update(max_step_s=.1)),
                   ('solver', lambda p: p['parameters'].update(max_steps=1.5)),
                   ('fields', lambda f: f.update(kind='sinusoid_time', parameters=dict(
                       offset=1.2, amplitude=.1, period_s=2., phase_rad=0., time_origin_s=0.)))]
        for component, change in changes:
            with self.subTest(component=component), self.assertRaises(ValueError):
                AttractionWorld(modify(build_instance(2), component, change))
        limited = AttractionWorld(modify(build_instance(2), 'solver', lambda p: p['parameters'].update(max_steps=1)))
        with self.assertRaisesRegex(DomainError, 'step budget'):
            limited.advance(probe_state(limited), .1)

    def test_matched_world_generation_public_equivalence_and_existing_file_protection(self):
        a, b = build_instance(2), build_instance(3)
        a.require_same_public_interface(b)
        self.assertNotEqual(a.payload['world']['record_id'], b.payload['world']['record_id'])
        public = json.dumps(a.public_dict())
        for forbidden in ('exponent', 'central_attraction', 'inverse_square', 'inverse_cube', 'strength_n', 'record_id'):
            self.assertNotIn(forbidden, public)
        with tempfile.TemporaryDirectory() as directory:
            entries = prepare_pair(directory)
            self.assertEqual(len(entries), 2)
            for entry in entries:
                folder = Path(directory)/entry['folder']
                instance = WorldInstance.load(folder/'instance.json')
                AttractionWorld(instance)
                preview = json.loads((folder/'preview.json').read_text())
                self.assertEqual(len(preview['frames']), 4)
                self.assertEqual(preview['world_id'], entry['world_id'])
            before = {p: p.read_bytes() for p in Path(directory).rglob('*.json')}
            prepare_pair(directory)
            with self.assertRaises(FileExistsError):
                prepare_pair(directory, strength_n=1.)
            self.assertTrue(all(p.read_bytes() == contents for p, contents in before.items()))


if __name__ == '__main__':
    unittest.main()
