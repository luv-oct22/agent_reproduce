from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import tempfile
import unittest

from src.envs.drag_lab import DragLabEnv
from src.worlds.definition import (
    ContactSpec, FieldSpec, LawSpec, ObjectSpec, ProtocolSpec, SolverSpec, WorldInstance, WorldSpec,
)
from src.worlds.drag_adapter import from_drag_manifest, restore_drag_env


def attraction_instance(exponent=2, mass=.1, strength=1., seed=42):
    field = FieldSpec(dict(id='strength', kind='constant', version=1, unit='N',
                          bounds=[0., 10.], parameters={'value': strength}))
    law = LawSpec(dict(id='attraction', kind='central_attraction', version=1,
        fields={'strength': 'strength'}, parameters=dict(exponent=exponent, reference_distance_m=1.,
        reference_mass_kg=1., minimum_distance_m=.1, coefficient_sample='pair_midpoint', mass_coupling='inertial_mass')))
    objects = [ObjectSpec(dict(id=name, color=color, color_rgba=rgba, shape='sphere',
                              mass_kg=mass if name == 'probe' else 1., volume_m3=.001, motion=motion))
               for name, color, rgba, motion in [('probe', 'blue', [.08, .35, .8, 1.], 'dynamic'),
                                                 ('source', 'orange', [1., .35, .05, 1.], 'fixed')]]
    world = WorldSpec(dict(coordinate_frame='cartesian_z_up_m', motion_law='newton_second_law_v1',
                          laws=[law.to_dict()], fields=[field.to_dict()],
                          objects=[obj.to_dict() for obj in objects], contacts=[]))
    tools = [dict(name=name, description=description,
                  parameters={'type': 'object', 'properties': {}, 'additionalProperties': False},
                  measurements=[], sample_definition='One instrument call.',
                  cost=dict(base_units=cost, per_sample_units=0, per_simulated_second_units=0))
             for name, description, cost in [('inspect', 'Read visible apparatus information.', 0),
                                             ('measure_force', 'Read the calibrated force sensor.', 1),
                                             ('track_motion', 'Read the calibrated position sensor.', 1)]]
    protocol = ProtocolSpec(dict(id='common_bench', track='law_discovery',
        instructions='Gather evidence within the measurement budget to predict later outcomes.',
        tools=tools, budget={'measurement_units': 24, 'max_turns': 8},
        clock=dict(mode='resettable', start_time_s=0., time_range_s=[0., 10.], reset_behavior='explicit_start_time'),
        disclosures=[]))
    solver = SolverSpec(dict(kind='central_attraction_rk4', version=1, parameters={'max_step_s': .001}))
    return WorldInstance(dict(world=world.to_dict(), protocol=protocol.to_dict(), solver=solver.to_dict(),
                              provenance={'seed': seed}))


class WorldDefinitionTests(unittest.TestCase):
    def test_roundtrip_save_load_and_overwrite_protection(self):
        instance = attraction_instance()
        self.assertEqual(WorldInstance.from_dict(json.loads(json.dumps(instance.to_dict()))), instance)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'instance.json'
            instance.save(path)
            instance.save(path)
            self.assertEqual(WorldInstance.load(path), instance)
            with self.assertRaises(FileExistsError):
                attraction_instance(exponent=3).save(path)
            self.assertEqual(WorldInstance.load(path), instance)

    def test_nested_input_and_output_mutations_do_not_change_record(self):
        instance = attraction_instance()
        data = instance.payload
        copied = WorldInstance(data)
        before = copied.record_id
        data['world']['payload']['objects'][0]['payload']['mass_kg'] = 10
        public = copied.public_dict()
        public['objects'][0]['color_rgba'][0] = 1.
        exported = copied.to_dict()
        exported['payload']['provenance']['seed'] = 999
        self.assertEqual(copied, instance)
        self.assertEqual(copied.record_id, before)
        with self.assertRaises(FrozenInstanceError):
            copied._json = '{}'

    def test_private_world_changes_leave_public_interface_identical(self):
        reference = attraction_instance()
        for other in (attraction_instance(exponent=3), attraction_instance(mass=.9),
                      attraction_instance(strength=5.), attraction_instance(seed=99)):
            reference.require_same_public_interface(other)
            self.assertNotEqual(reference.record_id, other.record_id)
        self.assertEqual(reference.payload['world']['record_id'], attraction_instance(seed=99).payload['world']['record_id'])
        public = json.dumps(reference.public_dict())
        for forbidden in ('record_id', 'host_only', 'exponent', 'central_attraction', 'provenance', 'seed', 'mass_kg'):
            self.assertNotIn(forbidden, public)
        self.assertIn('blue', public)
        self.assertEqual([t['name'] for t in reference.public_dict()['tools']],
                         ['inspect', 'measure_force', 'track_motion'])

    def test_explicit_disclosure_and_interface_mismatch(self):
        data = attraction_instance().payload
        p = data['protocol']['payload']
        p['disclosures'] = ['objects.probe.mass_kg']
        data['protocol'] = ProtocolSpec(p).to_dict()
        instance = WorldInstance(data)
        self.assertEqual(instance.public_dict()['known_properties'], {'objects.probe.mass_kg': .1})
        with self.assertRaisesRegex(ValueError, 'different public'):
            instance.require_same_public_interface(attraction_instance())
        for selector in ('laws.attraction', 'fields.strength'):
            p['disclosures'] = [selector]
            with self.assertRaisesRegex(ValueError, 'cannot disclose'):
                ProtocolSpec(p)
        for selector in ('objects.unknown.mass_kg', 'objects.probe.password'):
            p['disclosures'] = [selector]
            data['protocol'] = ProtocolSpec(p).to_dict()
            with self.assertRaises(ValueError):
                WorldInstance(data)

    def test_reject_corruption_unknown_schema_and_nonfinite_values(self):
        instance = attraction_instance()
        data = instance.to_dict()
        data['payload']['provenance']['seed'] = 99
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            WorldInstance.from_dict(data)
        for version in (2, True):
            data = instance.to_dict()
            data['schema_version'] = version
            with self.assertRaisesRegex(ValueError, 'schema'):
                WorldInstance.from_dict(data)
        data = instance.payload
        data['provenance']['value'] = float('nan')
        with self.assertRaises(ValueError):
            WorldInstance(data)

    def test_cross_reference_unit_and_contact_validation(self):
        for mutation in ('unit', 'field_reference', 'object_reference', 'duplicate'):
            d = attraction_instance().payload['world']['payload']
            if mutation == 'unit':
                f = d['fields'][0]['payload']
                f['unit'] = 'kg/s'
                d['fields'][0] = FieldSpec(f).to_dict()
            elif mutation == 'field_reference':
                law = d['laws'][0]['payload']
                law['fields']['strength'] = 'missing'
                d['laws'][0] = LawSpec(law).to_dict()
            elif mutation == 'object_reference':
                d['contacts'] = [ContactSpec(dict(id='floor', kind='normal_restitution', version=1,
                    object_id='missing', surface_id='surface', surface_z_m=0., restitution=.8,
                    tangential_friction=0.)).to_dict()]
            else:
                d['objects'].append(deepcopy(d['objects'][0]))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                WorldSpec(d)

    def test_field_sampling_bounds_and_temporal_clock_contract(self):
        height = dict(id='b', kind='smoothstep_height', version=1, unit='kg/s', bounds=[0., .5],
                      parameters=dict(surface_id='floor', extrapolation='constant_endpoints',
                                      heights_m=[0., 1., 3.], values=[.1, .2, .3]))
        FieldSpec(height)
        for key, value in [('heights_m', [0., 1., 1.]), ('values', [.1, -.2, .3])]:
            broken = deepcopy(height)
            broken['parameters'][key] = value
            with self.assertRaises(ValueError):
                FieldSpec(broken)
        temporal = FieldSpec(dict(id='strength', kind='sinusoid_time', version=1, unit='N', bounds=[0., 2.],
            parameters=dict(offset=1., amplitude=.5, period_s=2., phase_rad=0., time_origin_s=0.)))
        d = attraction_instance().payload
        world = d['world']['payload']
        world['fields'] = [temporal.to_dict()]
        d['world'] = WorldSpec(world).to_dict()
        WorldInstance(d)
        p = d['protocol']['payload']
        p['clock']['time_range_s'] = None
        d['protocol'] = ProtocolSpec(p).to_dict()
        with self.assertRaisesRegex(ValueError, 'clock domain'):
            WorldInstance(d)
        p['clock']['mode'] = 'continuous'
        with self.assertRaisesRegex(ValueError, 'reset behavior'):
            ProtocolSpec(p)

    def test_unknown_laws_and_bad_budget_or_tools_are_rejected(self):
        d = attraction_instance().payload
        law = d['world']['payload']['laws'][0]['payload']
        law['kind'] = 'eval_python_expression'
        with self.assertRaises(ValueError):
            LawSpec(law)
        p = d['protocol']['payload']
        for value in (True, 0, -1):
            broken = deepcopy(p)
            broken['budget']['measurement_units'] = value
            with self.assertRaises(ValueError):
                ProtocolSpec(broken)
        broken = deepcopy(p)
        broken['tools'].append(deepcopy(broken['tools'][0]))
        with self.assertRaises(ValueError):
            ProtocolSpec(broken)
        broken = deepcopy(p)
        broken['tools'][0]['cost']['per_sample_units'] = -1
        with self.assertRaises(ValueError):
            ProtocolSpec(broken)
        for reading in (dict(name='force', unit='N', resolution=0., range=None),
                        dict(name='force', unit='N', resolution=.001, range=[10., -10.])):
            broken = deepcopy(p)
            broken['tools'][1]['measurements'] = [reading]
            with self.assertRaises(ValueError):
                ProtocolSpec(broken)
        broken = deepcopy(p)
        broken['tools'][0]['parameters']['required'] = ['unknown_argument']
        with self.assertRaises(ValueError):
            ProtocolSpec(broken)

    def test_drag_adapter_preserves_exact_solver_and_instrument_results(self):
        for profile in ('two_layer', 'smooth_random'):
            env = DragLabEnv(profile_type=profile)
            manifest = env.private_manifest()
            instance = from_drag_manifest(manifest)
            restored = restore_drag_env(WorldInstance.from_dict(instance.to_dict()))
            self.assertEqual(restored.private_manifest(), manifest)
            for h in (.2, 1., 2.3):
                action = dict(operation='bounce', specimen_id='sample_A', surface_id='surface_1', release_height_m=h)
                self.assertEqual(env.experiment(action), restored.experiment(action))
            for t in (.5, 1.8, 3.):
                args = ([-1.5, 0, 1.53], [.9, 0, 0], t, .1, .03, .8)
                self.assertEqual(env._world.advance(*args), restored._world.advance(*args))
            public = json.dumps(instance.public_dict())
            for forbidden in ('generation_seed', 'legacy_manifest', 'host_only', 'world_id'):
                self.assertNotIn(forbidden, public)

    def test_adapter_rejects_divergent_shared_solver(self):
        instance = from_drag_manifest(DragLabEnv(profile_type='smooth_random').private_manifest())
        d = instance.payload
        solver = d['solver']['payload']
        solver['parameters']['max_step_s'] = .001
        d['solver'] = SolverSpec(solver).to_dict()
        with self.assertRaisesRegex(ValueError, 'disagree'):
            restore_drag_env(WorldInstance(d))


if __name__ == '__main__':
    unittest.main()
