"""Stage two: discover gravity and constant specimen–surface restitution."""
from copy import deepcopy
import math
from pathlib import Path
import random

from src.envs.registry import register_env
from src.envs.world_lab import WorldLabEnv
from src.objects.specimen import generate_specimens
from src.worlds import UniformGravityWorld
from src.worlds.contact_registry import ContactRegistry


@register_env('bounce_lab')
class BounceLabEnv(WorldLabEnv):
    def __init__(self, restitution_by_specimen=None, contact_registry_path=None,
                 surface_id='surface_1', bounce_height_resolution_m=.001, **kwargs):
        if restitution_by_specimen is not None and contact_registry_path is not None:
            raise ValueError('Use authored restitution or a contact registry, not both.')
        if (isinstance(bounce_height_resolution_m, bool) or not isinstance(bounce_height_resolution_m, (int, float))
                or not math.isfinite(bounce_height_resolution_m) or not 0 < bounce_height_resolution_m <= .05):
            raise ValueError('Rebound height resolution must be finite and in (0, 0.05] metres.')
        if kwargs.get('specimens') is None and kwargs.get('registry_path') is None:
            kwargs['specimens'] = [dict(obj.public_dict(), shape='sphere', mass_kg=obj.mass_kg,
                                       volume_m3=obj.volume_m3)
                                  for obj in generate_specimens(kwargs.get('seed', 7))]
        super().__init__(**kwargs)
        if any(obj.shape != 'sphere' for obj in self._specimens.values()):
            raise ValueError('bounce_lab requires spherical specimens.')
        self.bounce_height_resolution_m = bounce_height_resolution_m
        if contact_registry_path is not None:
            contacts = ContactRegistry.load(contact_registry_path)
            if contacts.surface_id != surface_id:
                raise ValueError('Contact registry surface does not match the configured surface.')
        else:
            if restitution_by_specimen is None:
                rng = random.Random(self._seed)
                restitution_by_specimen = {key: rng.choice((.35, .5, .6, .75, .85)) for key in self._specimens}
            if not isinstance(restitution_by_specimen, dict):
                raise ValueError('restitution_by_specimen must map every specimen ID to a coefficient.')
            contacts = ContactRegistry(self._world.world_id, self._registry.registry_id, surface_id,
                                       tuple(restitution_by_specimen.items()))
        if (contacts.air_drag or contacts.world_id != self._world.world_id or contacts.object_registry_id != self._registry.registry_id
                or {key for key, _ in contacts.restitution} != set(self._specimens)):
            raise ValueError('Contact rules must match this exact world and specimen catalog.')
        self._contacts = contacts

    def description(self):
        return ('A vacuum experimental lab with spherical specimens, a drop tower and a fixed horizontal impact surface. '
                'Discover the unknown constant downward gravity and the unknown constant normal coefficient of '
                'restitution for every specimen material–surface pair. Do not assume terrestrial gravity or '
                'infer bounce behavior from color. Restitution is between zero and one and independent of impact '
                'speed in this task. The surface is stationary; impacts have no tangential friction or spin coupling. '
                'Objects do not collide with each other. Each trial releases one object from rest and returns it '
                'to the bench afterwards. Balance and displacement instruments are also available.')

    def observe(self):
        observation = super().observe()
        observation['apparatus']['bounce_tower'] = {
            'surface_id': self._contacts.surface_id,
            'min_release_height_m': .05, 'max_release_height_m': self.drop_max_distance_m,
            'clock_resolution_s': self.drop_clock_resolution_s,
            'height_resolution_m': self.bounce_height_resolution_m,
            'procedure': 'Release from rest; measure time to first impact and peak height of the first rebound. '
                         'Both heights are center displacement above the center position at contact, '
                         'equivalently the gap between the bottom of the sphere and the surface. '
                         'A zero height reading may mean no rebound or a rebound below instrument resolution.'}
        return observation

    def experiment(self, action):
        if not isinstance(action, dict) or action.get('operation') != 'bounce':
            return super().experiment(action)
        if len(self._notebook) >= self.max_experiments:
            return {'success': False, 'error': 'Experiment budget exhausted.', 'experiments_remaining': 0}
        if set(action) != {'operation', 'specimen_id', 'surface_id', 'release_height_m'}:
            return {'success': False, 'error': 'bounce requires only operation, specimen_id, surface_id and release_height_m.'}
        key, height = action['specimen_id'], action['release_height_m']
        if not isinstance(key, str) or key not in self._specimens or action['surface_id'] != self._contacts.surface_id:
            return {'success': False, 'error': 'Unknown specimen or surface ID.'}
        if (isinstance(height, bool) or not isinstance(height, (int, float)) or not math.isfinite(height)
                or not .05 <= height <= self.drop_max_distance_m):
            return {'success': False, 'error': 'Release height is outside the calibrated range.'}
        elapsed = self._world.free_fall_time(height)
        incoming = self._world.advance([0, 0, height], [0, 0, 0], elapsed)['velocity_m_s']
        outgoing = self._contacts.impact_velocity(key, incoming)
        rebound = self._world.advance([0, 0, 0], outgoing, outgoing[2]/self._world.gravity_m_s2)['position_m'][2]
        def measure(value, resolution):
            return round(math.floor(value/resolution+.5)*resolution, 9)
        reading = {'instrument': 'bounce_tower', 'specimen_id': key, 'surface_id': self._contacts.surface_id,
                   'release_height_m': height, 'release_from_rest': True,
                   'time_to_first_impact_s': measure(elapsed, self.drop_clock_resolution_s),
                   'first_rebound_height_m': measure(rebound, self.bounce_height_resolution_m)}
        self._notebook.append(deepcopy(reading))
        return {'success': True, 'experiment_index': len(self._notebook), 'observation': reading,
                'experiments_remaining': self.max_experiments-len(self._notebook)}

    def private_manifest(self):
        manifest = super().private_manifest()
        manifest.update(environment='bounce_lab', contact_registry=self._contacts.to_dict())
        manifest['apparatus'].update(surface_id=self._contacts.surface_id,
                                     bounce_height_resolution_m=self.bounce_height_resolution_m)
        return manifest

    def export_private_artifacts(self, directory):
        directory = Path(directory)
        if (directory/'contact_registry.json').exists() and ContactRegistry.load(directory/'contact_registry.json') != self._contacts:
            raise FileExistsError('Output already contains different contact rules.')
        super().export_private_artifacts(directory)
        self._contacts.save(directory/'contact_registry.json')
        self._contacts.write_markdown(directory/'contact_registry.md')
        (directory/'parameters.md').write_text('# Bounce experiment parameters (host-only)\n\n'
            f'Gravity: {self._world.gravity_m_s2:g} m/s².\n\n'
            f'Measurement budget: {self.max_experiments}. Release/drop range: 0.05–{self.drop_max_distance_m:g} m.\n\n'
            f'Clock resolution: {self.drop_clock_resolution_s:g} s. Rebound height resolution: {self.bounce_height_resolution_m:g} m.\n\n'
            'Object geometry and appearance: object_registry.json/.md. World: world.json/.md. '
            'Contact pairs and coefficients: contact_registry.json/.md. Complete apparatus: private_manifest.json.\n')

    @classmethod
    def from_private_manifest(cls, manifest):
        world = UniformGravityWorld.from_dict(manifest['world'])
        contacts = ContactRegistry.from_dict(manifest['contact_registry'])
        env = cls(seed=manifest.get('seed'), specimens=manifest['specimens'], gravity_m_s2=world.gravity_m_s2,
                  restitution_by_specimen=dict(contacts.restitution), **manifest['apparatus'])
        if env.private_manifest() != manifest:
            raise ValueError('Inconsistent bounce-lab manifest.')
        return env
