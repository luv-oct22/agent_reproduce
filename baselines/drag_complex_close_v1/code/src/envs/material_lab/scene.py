"""Instrument-mediated property identification, with an explicit public boundary.

This is an idealized, headless experimental lab, not a video or fluid solver.
Experiments return instrument readings, never hidden specimen properties.
"""
from copy import deepcopy
import json
import math
from pathlib import Path

from src.envs.base import BaseEnv
from src.envs.registry import register_env
from src.objects.specimen import Specimen, generate_specimens
from src.objects.registry import ObjectRegistry


REFERENCE_WEIGHTS_G = {
    'weight_1g': 1, 'weight_2g_a': 2, 'weight_2g_b': 2, 'weight_5g': 5,
    'weight_10g': 10, 'weight_20g_a': 20, 'weight_20g_b': 20,
    'weight_50g': 50, 'weight_100g': 100, 'weight_200g': 200, 'weight_200g_b': 200, 'weight_500g': 500,
}


@register_env('material_lab')
class MaterialLabEnv(BaseEnv):
    def __init__(self, seed=7, specimens=None, max_experiments=48,
                 balance_tolerance_g=.5, balance_capacity_g=1000,
                 cylinder_initial_ml=100, cylinder_capacity_ml=500,
                 cylinder_graduation_ml=1, registry_path=None):
        super().__init__()
        if not isinstance(max_experiments, int) or isinstance(max_experiments, bool) or max_experiments < 1:
            raise ValueError('max_experiments must be a positive integer.')
        for value in (balance_tolerance_g, balance_capacity_g, cylinder_initial_ml,
                      cylinder_capacity_ml, cylinder_graduation_ml):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError('Instrument settings must be finite positive numbers.')
        if cylinder_initial_ml >= cylinder_capacity_ml:
            raise ValueError('The cylinder initial level must be below its capacity.')
        if balance_tolerance_g >= balance_capacity_g or cylinder_graduation_ml > cylinder_capacity_ml:
            raise ValueError('Instrument resolution must fit its range.')
        if registry_path is not None:
            if specimens is not None:
                raise ValueError('Use registry_path or authored specimens, not both.')
            registry = ObjectRegistry.load(registry_path)
            catalog = list(registry.specimens)
            seed = registry.seed
        elif specimens is None:
            catalog = generate_specimens(seed)
        else:
            if not isinstance(specimens, list) or not specimens:
                raise ValueError('specimens must be a nonempty list.')
            catalog = [Specimen.from_dict(item) for item in specimens]
        self._seed = seed
        self._registry = ObjectRegistry(tuple(catalog), seed)
        identifiers = [item.specimen_id for item in catalog]
        if len(set(identifiers)) != len(identifiers) or set(identifiers) & set(REFERENCE_WEIGHTS_G):
            raise ValueError('Specimen IDs must be unique and distinct from reference weights.')
        self._specimens = {item.specimen_id: item for item in self._registry.specimens}
        self.max_experiments = max_experiments
        self.balance_tolerance_g = balance_tolerance_g
        self.balance_capacity_g = balance_capacity_g
        self.cylinder_initial_ml = cylinder_initial_ml
        self.cylinder_capacity_ml = cylinder_capacity_ml
        self.cylinder_graduation_ml = cylinder_graduation_ml
        self.reset()

    def reset(self):
        self._time = 0.0
        self._notebook = []

    @property
    def objects(self):
        # Do not inherit BaseEnv's accessors for mass-bearing Object instances.
        return {key: value.public_dict() for key, value in self._specimens.items()}

    def get_object(self, name):
        item = self._specimens.get(name)
        return item.public_dict() if item else None

    def add_object(self, obj):
        raise ValueError('The specimen catalog is fixed for an episode.')

    def remove_object(self, name):
        raise ValueError('The specimen catalog is fixed for an episode.')

    def description(self):
        return ('An experimental lab with rigid, nonporous specimens, an equal-arm beam balance, '
                'calibrated reference weights, and a graduated water cylinder. '
                'Infer specimen mass, volume and density from experiments. '
                'Each experiment starts with calibrated, empty apparatus and returns the specimen to the bench.')

    def observe(self):
        return {
            'specimens': list(self.objects.values()),
            'apparatus': {
                'balance': {'type': 'equal_arm_beam_balance', 'tolerance_g': self.balance_tolerance_g,
                            'capacity_per_pan_g': self.balance_capacity_g,
                            'readings': ['left_down', 'right_down', 'level', 'overload'],
                            'reference_weights': [{'id': key, 'mass_g': mass, 'quantity': 1}
                                                  for key, mass in REFERENCE_WEIGHTS_G.items()]},
                'cylinder': {'initial_level_ml': self.cylinder_initial_ml,
                             'capacity_ml': self.cylinder_capacity_ml,
                             'graduation_ml': self.cylinder_graduation_ml,
                             'procedure': 'A tared holder fully submerges the specimen, including buoyant specimens. '
                                          'Read water level before and after. No float/sink outcome is provided.'},
            },
            'experiments_used': len(self._notebook),
            'experiments_remaining': self.max_experiments-len(self._notebook),
            'notebook': deepcopy(self._notebook),
        }

    def get_state(self):
        return self.observe()

    def step(self, dt=.01):
        if isinstance(dt, bool) or not isinstance(dt, (int, float)) or not math.isfinite(dt) or dt <= 0:
            raise ValueError('Time step must be finite and positive.')
        # Instruments return settled readings; waiting cannot reveal extra data.
        self._time += dt
        return self.observe()

    def _pan_mass_g(self, identifiers):
        return sum(REFERENCE_WEIGHTS_G[key] if key in REFERENCE_WEIGHTS_G
                   else self._specimens[key].mass_kg*1000 for key in identifiers)

    def _balance(self, action):
        if set(action) != {'operation', 'left_pan', 'right_pan'}:
            raise ValueError('balance requires only operation, left_pan and right_pan.')
        left, right = action['left_pan'], action['right_pan']
        if not all(isinstance(pan, list) and all(isinstance(key, str) for key in pan) for pan in (left, right)):
            raise ValueError('Pans must be lists of specimen or reference-weight IDs.')
        identifiers = left+right
        if len(set(identifiers)) != len(identifiers):
            raise ValueError('Each specimen or reference weight can occupy only one pan, once.')
        if any(key not in self._specimens and key not in REFERENCE_WEIGHTS_G for key in identifiers):
            raise ValueError('Unknown specimen or reference-weight ID.')
        a, b = self._pan_mass_g(left), self._pan_mass_g(right)
        if max(a, b) > self.balance_capacity_g+1e-9:
            reading = 'overload'
        elif abs(a-b) <= self.balance_tolerance_g+1e-9:
            reading = 'level'
        else:
            reading = 'left_down' if a > b else 'right_down'
        return {'instrument': 'beam_balance', 'left_pan': left[:], 'right_pan': right[:], 'reading': reading}

    def _displace(self, action):
        if set(action) != {'operation', 'specimen_id'}:
            raise ValueError('displace requires only operation and specimen_id.')
        key = action['specimen_id']
        if not isinstance(key, str) or key not in self._specimens:
            raise ValueError('Unknown specimen ID.')
        actual = self.cylinder_initial_ml + self._specimens[key].volume_m3*1e6
        def read(level):
            return round(math.floor(level/self.cylinder_graduation_ml+.5)*self.cylinder_graduation_ml, 9)
        return {'instrument': 'graduated_cylinder', 'specimen_id': key,
                'reading': 'overflow' if actual > self.cylinder_capacity_ml+1e-9 else 'settled',
                'water_level_before_ml': read(self.cylinder_initial_ml),
                'water_level_after_ml': None if actual > self.cylinder_capacity_ml+1e-9 else read(actual),
                'fully_submerged_by_holder': actual <= self.cylinder_capacity_ml+1e-9}

    def experiment(self, action):
        if not isinstance(action, dict):
            return {'success': False, 'error': 'Action must be a JSON object.'}
        operation = action.get('operation')
        if operation == 'inspect' and set(action) == {'operation'}:
            return dict(success=True, observation=self.observe())
        if operation not in ('balance', 'displace'):
            return {'success': False, 'error': 'Supported operations are inspect, balance and displace.'}
        if len(self._notebook) >= self.max_experiments:
            return {'success': False, 'error': 'Experiment budget exhausted.', 'experiments_remaining': 0}
        try:
            reading = self._balance(action) if operation == 'balance' else self._displace(action)
        except ValueError as exc:
            return {'success': False, 'error': str(exc)}
        self._notebook.append(deepcopy(reading))
        return {'success': True, 'experiment_index': len(self._notebook), 'observation': reading,
                'experiments_remaining': self.max_experiments-len(self._notebook)}

    def private_manifest(self):
        """Host-only handoff for scoring and future video generation, never a tool."""
        return {'schema_version': 1, 'units': {'mass': 'kg', 'volume': 'm^3', 'density': 'kg/m^3'},
                'object_registry_id': self._registry.registry_id,
                'seed': self._seed, 'specimens': [s.private_dict() for s in self._specimens.values()],
                'apparatus': {'max_experiments': self.max_experiments,
                              'balance_tolerance_g': self.balance_tolerance_g,
                              'balance_capacity_g': self.balance_capacity_g,
                              'cylinder_initial_ml': self.cylinder_initial_ml,
                              'cylinder_capacity_ml': self.cylinder_capacity_ml,
                              'cylinder_graduation_ml': self.cylinder_graduation_ml}}

    def export_private_manifest(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.private_manifest(), indent=2)+'\n')
        return path

    def export_private_artifacts(self, directory):
        """Persist the exact episode before any external model request."""
        directory = Path(directory)
        self._registry.save(directory/'object_registry.json')
        self._registry.write_markdown(directory/'object_registry.md')
        self.export_private_manifest(directory/'private_manifest.json')

    @classmethod
    def from_private_manifest(cls, manifest):
        if manifest.get('schema_version') != 1 or manifest.get('units') != {'mass': 'kg', 'volume': 'm^3', 'density': 'kg/m^3'}:
            raise ValueError('Unsupported specimen manifest version.')
        env = cls(seed=manifest.get('seed'), specimens=manifest['specimens'], **manifest['apparatus'])
        if manifest.get('object_registry_id', env._registry.registry_id) != env._registry.registry_id:
            raise ValueError('Manifest object registry identity check failed.')
        return env
