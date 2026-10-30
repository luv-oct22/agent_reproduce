"""Two invisible drag layers, observed only through timed drops and rebounds."""
from copy import deepcopy
import json
import math
from pathlib import Path

from src.envs.base import BaseEnv
from src.envs.registry import register_env
from src.objects.registry import ObjectRegistry
from src.objects.specimen import Specimen
from src.worlds.contact_registry import ContactRegistry
from src.worlds.layered_drag import LayeredDragWorld, finite
from src.worlds.height_drag import HeightDragWorld, load_drag_world


PROFILE_BOUNDS = {'boundary_height_m': [.2, 1.8], 'lower_drag_kg_s': [0, .5], 'upper_drag_kg_s': [0, .5]}


def validate_profile(profile):
    if not isinstance(profile, dict) or set(profile) != set(PROFILE_BOUNDS):
        raise ValueError('Provide boundary_height_m, lower_drag_kg_s and upper_drag_kg_s.')
    for key, (low, high) in PROFILE_BOUNDS.items():
        if not finite(profile[key]) or not low <= profile[key] <= high:
            raise ValueError(f'{key} is outside the declared profile range.')


@register_env('drag_lab')
class DragLabEnv(BaseEnv):
    def __init__(self, gravity_m_s2=3.0, restitution=.8, boundary_height_m=.85,
                 lower_drag_kg_s=.03, upper_drag_kg_s=.18, max_experiments=12,
                 clock_resolution_s=.001, height_resolution_m=.001,
                 profile_type='two_layer', profile_seed=42, profile_knot_count=13,
                 profile_min_drag_kg_s=.01, profile_max_drag_kg_s=.30, profile_record=None):
        super().__init__()
        profile = dict(boundary_height_m=boundary_height_m, lower_drag_kg_s=lower_drag_kg_s,
                       upper_drag_kg_s=upper_drag_kg_s)
        validate_profile(profile)
        if abs(lower_drag_kg_s-upper_drag_kg_s) < .02:
            raise ValueError('Authored worlds require a drag contrast of at least 0.02 kg/s.')
        if not finite(gravity_m_s2) or not .5 <= gravity_m_s2 <= 20:
            raise ValueError('Calibrated gravity must be in [0.5, 20] m/s^2.')
        if not finite(restitution) or not .2 <= restitution <= .95:
            raise ValueError('Calibrated restitution must be in [0.2, 0.95].')
        if isinstance(max_experiments, bool) or not isinstance(max_experiments, int) or max_experiments < 1:
            raise ValueError('Measurement budget must be a positive integer.')
        if any(not finite(v) or not 0 < v <= .01 for v in (clock_resolution_s, height_resolution_m)):
            raise ValueError('Instrument resolutions must be in (0, 0.01].')
        if profile_type == 'two_layer':
            self._world = LayeredDragWorld(gravity_m_s2=gravity_m_s2, **profile)
        elif profile_type == 'smooth_random':
            self._world = (HeightDragWorld.from_dict(profile_record) if profile_record is not None else
                           HeightDragWorld.generate(gravity_m_s2, profile_seed, profile_knot_count,
                                                    profile_min_drag_kg_s, profile_max_drag_kg_s))
            if self._world.gravity_m_s2 != gravity_m_s2:
                raise ValueError('Recorded drag profile uses different gravity.')
        else:
            raise ValueError('profile_type must be two_layer or smooth_random.')
        if profile_record is not None and profile_type != 'smooth_random':
            raise ValueError('profile_record requires smooth_random.')
        self._ball = Specimen('sample_A', .1, 4*math.pi*.03**3/3, 'blue', 'sphere')
        self._registry = ObjectRegistry((self._ball,), None)
        self._contacts = ContactRegistry(self._world.world_id, self._registry.registry_id,
                                         'surface_1', (('sample_A', restitution),), air_drag=True)
        self.max_experiments = max_experiments
        self.clock_resolution_s = clock_resolution_s
        self.height_resolution_m = height_resolution_m
        self.reset()

    def reset(self):
        self._time = 0.0
        self._notebook = []

    @property
    def objects(self):
        return {self._ball.specimen_id: dict(self._ball.public_dict(), mass_kg=self._ball.mass_kg,
                                            radius_m=self._ball.radius_m)}

    def get_object(self, name):
        return self.objects.get(name)

    def add_object(self, obj):
        raise ValueError('The calibrated specimen is fixed.')

    def remove_object(self, name):
        raise ValueError('The calibrated specimen is fixed.')

    def description(self):
        if isinstance(self._world, HeightDragWorld):
            return ('A calibrated drop-and-bounce lab in a stationary synthetic medium. '
                    'Gravity, ball mass/radius and surface restitution are known. '
                    'F_drag = -b(z) * velocity in all components, with z the sphere-centre height above the floor. '
                    'The invisible coefficient b(z) is a fixed, nonnegative, continuously varying function of height, '
                    'not restricted to two constant layers. It does not change between experiments. '
                    'Infer an approximate profile from timed drops and rebounds. '
                    'No buoyancy, spin, tangential contact friction or object-object collisions are modeled. '
                    'Only instrument readings are available, not trajectories or direct coefficient measurements.')
        return ('A calibrated drop-and-bounce lab in a stationary synthetic medium. '
                'Gravity, ball mass/radius and surface restitution are known. Air resistance follows '
                'F_drag = -b(z) * velocity, where z is sphere-centre height above the floor. '
                'There are exactly two horizontal layers with constant nonnegative drag coefficients '
                'and one unknown boundary. Either layer may have stronger drag. '
                'The layers are invisible; infer their effects by choosing release heights. '
                'No buoyancy, spin, tangential contact friction or object-object collisions are modeled. '
                'Each trial releases the ball from rest and returns it to the bench. '
                'Only instrument readings are available, not intermediate states or drag values.')

    def observe(self):
        observation = {'specimens': list(self.objects.values()),
                'calibration': {'gravity_m_s2': self._world.gravity_m_s2,
                                'surface_id': 'surface_1', 'restitution': self._contacts.restitution[0][1]},
                'profile_family': {'number_of_layers': 2, 'parameter_bounds': deepcopy(PROFILE_BOUNDS),
                                   'coefficient_units': 'kg/s', 'height_reference': 'sphere centre above floor'},
                'apparatus': {'min_release_height_m': .05, 'max_release_height_m': 2.5,
                              'release_height_reference': 'bottom-of-sphere clearance above floor',
                              'clock_resolution_s': self.clock_resolution_s,
                              'height_resolution_m': self.height_resolution_m,
                              'drop_readout': 'time to first impact',
                              'bounce_readout': 'time to first impact and first rebound bottom clearance'},
                'experiments_used': len(self._notebook),
                'experiments_remaining': self.max_experiments-len(self._notebook),
                'notebook': deepcopy(self._notebook)}
        if isinstance(self._world, HeightDragWorld):
            observation['profile_family'] = {
                'type': 'unknown_smooth_height_function', 'coefficient_bounds_kg_s': [0, .5],
                'height_domain_m': [0, 3], 'height_reference': 'sphere centre above floor',
                'stationary': True, 'outside_domain': 'constant endpoint values',
                'estimate_representation': 'Choose 2–65 heights spanning 0 to 3 m and matching coefficients. '
                    'Between adjacent samples use u=(z-z_i)/(z_next-z_i), w=3*u^2-2*u^3, '
                    'b(z)=(1-w)*b_i+w*b_next. Minimum sample spacing is 0.01 m. '
                    'Your sampling grid need not match the hidden function grid.'}
        return observation

    def get_state(self):
        return self.observe()

    def step(self, dt=.01):
        if not finite(dt) or dt <= 0:
            raise ValueError('Time step must be finite and positive.')
        self._time += dt
        return self.observe()

    def experiment(self, action):
        if not isinstance(action, dict):
            return {'success': False, 'error': 'Action must be an object.'}
        operation = action.get('operation')
        if action == {'operation': 'inspect'}:
            return dict(success=True, observation=self.observe())
        if operation not in ('drop', 'bounce'):
            return {'success': False, 'error': 'Supported experiments: inspect, drop, bounce.'}
        expected = {'operation', 'specimen_id', 'release_height_m'}
        if operation == 'bounce':
            expected.add('surface_id')
        height = action.get('release_height_m')
        if (set(action) != expected or action.get('specimen_id') != 'sample_A'
                or (operation == 'bounce' and action.get('surface_id') != 'surface_1')
                or not finite(height) or not .05 <= height <= 2.5):
            return {'success': False, 'error': 'Invalid fields, specimen, surface or release height (0.05–2.5 m).'}
        if len(self._notebook) >= self.max_experiments:
            return {'success': False, 'error': 'Experiment budget exhausted.', 'experiments_remaining': 0}
        raw = self._world.drop_readings(height, self._ball.mass_kg, self._ball.radius_m,
                                        self._contacts.restitution[0][1])
        def read(value, resolution):
            return round(math.floor(value/resolution+.5)*resolution, 9)
        reading = {'instrument': 'drag_'+operation+'_tower', 'specimen_id': 'sample_A',
                   'release_height_m': height, 'release_from_rest': True,
                   'time_to_first_impact_s': read(raw['time_to_first_impact_s'], self.clock_resolution_s)}
        if operation == 'bounce':
            reading.update(surface_id='surface_1', first_rebound_height_m=read(
                raw['first_rebound_height_m'], self.height_resolution_m))
        self._notebook.append(deepcopy(reading))
        return dict(success=True, observation=reading, experiment_index=len(self._notebook),
                    experiments_remaining=self.max_experiments-len(self._notebook))

    def private_manifest(self):
        return {'format': 'drag_lab_manifest', 'schema_version': 1, 'environment': 'drag_lab',
                'world': self._world.to_dict(), 'world_id': self._world.world_id,
                'object_registry': self._registry.to_dict(), 'object_registry_id': self._registry.registry_id,
                'contact_registry': self._contacts.to_dict(),
                'apparatus': {'max_experiments': self.max_experiments,
                              'clock_resolution_s': self.clock_resolution_s,
                              'height_resolution_m': self.height_resolution_m},
                'motion_contact_approximation': 'normal rebound speed <1e-7 m/s becomes sustained floor contact'}

    @classmethod
    def from_private_manifest(cls, manifest):
        world = load_drag_world(manifest['world'])
        contacts = ContactRegistry.from_dict(manifest['contact_registry'])
        if isinstance(world, HeightDragWorld):
            profile = dict(profile_type='smooth_random', profile_record=world.to_dict())
        else:
            profile = dict(boundary_height_m=world.boundary_height_m,
                           lower_drag_kg_s=world.lower_drag_kg_s, upper_drag_kg_s=world.upper_drag_kg_s)
        env = cls(gravity_m_s2=world.gravity_m_s2, restitution=contacts.restitution[0][1],
                  **profile, **manifest['apparatus'])
        if env.private_manifest() != manifest:
            raise ValueError('Inconsistent drag world, objects, contacts or apparatus.')
        return env

    def export_private_artifacts(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        records = {'private_manifest.json': self.private_manifest(), 'world.json': self._world.to_dict(),
                   'object_registry.json': self._registry.to_dict(), 'contact_registry.json': self._contacts.to_dict()}
        for name, data in records.items():
            if (directory/name).exists() and json.loads((directory/name).read_text()) != data:
                raise FileExistsError(f'Output already contains different {name}.')
        for name, data in records.items():
            (directory/name).write_text(json.dumps(data, indent=2)+'\n')
        self._registry.write_markdown(directory/'object_registry.md')
        self._contacts.write_markdown(directory/'contact_registry.md')
        (directory/'world.md').write_text('# Height-dependent drag world (host-only)\n\n```json\n'
                                         +json.dumps(self._world.to_dict(), indent=2)+'\n```\n')
        (directory/'parameters.md').write_text('# Drag interaction parameters (host-only)\n\n'
            'One calibrated sphere; invisible height-dependent drag; impact time and rebound height only. '
            'World height is sphere-centre height; release/rebound heights are bottom clearance.\n\n```json\n'
            +json.dumps(self.private_manifest(), indent=2)+'\n```\n')
