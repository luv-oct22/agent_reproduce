"""Material experiments plus a photogate drop tower in a hidden-gravity world."""
from copy import deepcopy
import math
from pathlib import Path

from src.envs.material_lab import MaterialLabEnv
from src.envs.registry import register_env
from src.worlds import UniformGravityWorld


@register_env('world_lab')
class WorldLabEnv(MaterialLabEnv):
    def __init__(self, gravity_m_s2=None, world_path=None, drop_max_distance_m=2.0,
                 drop_clock_resolution_s=.001, **kwargs):
        if world_path is not None and gravity_m_s2 is not None:
            raise ValueError('Use world_path or gravity_m_s2, not both.')
        self._world = UniformGravityWorld.load(world_path) if world_path is not None else UniformGravityWorld(
            3.0 if gravity_m_s2 is None else gravity_m_s2)
        for value in (drop_max_distance_m, drop_clock_resolution_s):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError('Drop apparatus settings must be finite positive numbers.')
        if drop_max_distance_m < .05:
            raise ValueError('Drop tower must allow at least 0.05 m travel.')
        self.drop_max_distance_m = drop_max_distance_m
        self.drop_clock_resolution_s = drop_clock_resolution_s
        super().__init__(**kwargs)

    def description(self):
        return (super().description()+' This world also has a vacuum drop tower. '
                'Gravity is uniform, constant in time and directed downward; its strength is unknown. '
                'Do not assume terrestrial gravity. Determine it experimentally.')

    def observe(self):
        observation = super().observe()
        observation['apparatus']['drop_tower'] = {
            'min_distance_m': .05, 'max_distance_m': self.drop_max_distance_m,
            'clock_resolution_s': self.drop_clock_resolution_s,
            'procedure': 'Release a specimen from rest in vacuum. Set a calibrated vertical travel distance; '
                         'a photogate timer reports the time taken to travel that distance. '
                         'The specimen is recovered after each trial.'}
        return observation

    def experiment(self, action):
        if not isinstance(action, dict) or action.get('operation') != 'drop':
            return super().experiment(action)
        if len(self._notebook) >= self.max_experiments:
            return {'success': False, 'error': 'Experiment budget exhausted.', 'experiments_remaining': 0}
        if set(action) != {'operation', 'specimen_id', 'distance_m'}:
            return {'success': False, 'error': 'drop requires only operation, specimen_id and distance_m.'}
        key, distance = action['specimen_id'], action['distance_m']
        if not isinstance(key, str) or key not in self._specimens:
            return {'success': False, 'error': 'Unknown specimen ID.'}
        if (isinstance(distance, bool) or not isinstance(distance, (int, float)) or not math.isfinite(distance)
                or not .05 <= distance <= self.drop_max_distance_m):
            return {'success': False, 'error': 'Drop distance is outside the calibrated range.'}
        time = self._world.free_fall_time(distance)
        measured = round(math.floor(time/self.drop_clock_resolution_s+.5)*self.drop_clock_resolution_s, 9)
        reading = {'instrument': 'drop_tower', 'specimen_id': key, 'distance_m': distance,
                   'release_from_rest': True, 'elapsed_time_s': measured}
        self._notebook.append(deepcopy(reading))
        return {'success': True, 'experiment_index': len(self._notebook), 'observation': reading,
                'experiments_remaining': self.max_experiments-len(self._notebook)}

    def private_manifest(self):
        manifest = super().private_manifest()
        manifest.update(environment='world_lab', world=self._world.to_dict(), world_id=self._world.world_id)
        manifest['apparatus'].update(drop_max_distance_m=self.drop_max_distance_m,
                                     drop_clock_resolution_s=self.drop_clock_resolution_s)
        return manifest

    def export_private_artifacts(self, directory):
        directory = Path(directory)
        if (directory/'world.json').exists() and UniformGravityWorld.load(directory/'world.json') != self._world:
            raise FileExistsError('Output already contains a different physical world.')
        super().export_private_artifacts(directory)
        self._world.save(directory/'world.json')
        (directory/'world.md').write_text('# Physical world (host-only)\n\n'
            f'World ID: `{self._world.world_id}`\n\n'
            f'Gravity: **{self._world.gravity_m_s2:g} m/s²**, downward along the negative z-axis.\n\n'
            'Newtonian mechanics, uniform constant gravity, no air drag, mass-independent free fall. '
            'The model receives instrument readings, not this record. Future motion scenes should load world.json.\n')

    @classmethod
    def from_private_manifest(cls, manifest):
        world = UniformGravityWorld.from_dict(manifest['world'])
        if manifest.get('environment') != 'world_lab' or manifest.get('world_id') != world.world_id:
            raise ValueError('Invalid world-lab manifest.')
        env = cls(seed=manifest.get('seed'), specimens=manifest['specimens'], gravity_m_s2=world.gravity_m_s2,
                  **manifest['apparatus'])
        if env.private_manifest() != manifest:
            raise ValueError('Inconsistent world-lab manifest.')
        return env
