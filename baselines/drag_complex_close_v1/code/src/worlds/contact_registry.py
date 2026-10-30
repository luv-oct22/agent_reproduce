"""Immutable, host-only contact rules shared by experiments and future scenes."""
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path


@dataclass(frozen=True)
class ContactRegistry:
    world_id: str
    object_registry_id: str
    surface_id: str
    restitution: tuple[tuple[str, float], ...]
    air_drag: bool = False

    def __post_init__(self):
        if not isinstance(self.air_drag, bool):
            raise ValueError('air_drag must be boolean.')
        if any(not isinstance(v, str) or not v for v in
               (self.world_id, self.object_registry_id, self.surface_id)):
            raise ValueError('Contact records require world, object registry and surface IDs.')
        pairs = tuple(tuple(pair) for pair in self.restitution)
        if not pairs or any(len(pair) != 2 for pair in pairs):
            raise ValueError('Contact records require specimen/coefficient pairs.')
        for key, value in pairs:
            if not isinstance(key, str) or not key or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError('Restitution must be a finite coefficient in [0, 1] for each specimen.')
        if len({key for key, _ in pairs}) != len(pairs):
            raise ValueError('Duplicate specimen contact rules.')
        object.__setattr__(self, 'restitution', tuple(sorted((key, float(e)) for key, e in pairs)))

    def parameters(self):
        return {'world_id': self.world_id, 'object_registry_id': self.object_registry_id,
                'surface': {'id': self.surface_id, 'stationary': True, 'horizontal': True},
                'law': 'constant_normal_restitution', 'coefficient_units': 'dimensionless',
                'tangential_friction': 0.0, 'air_drag': self.air_drag,
                'spin_coupling': False, 'object_object_collisions': False,
                'pairs': [{'specimen_id': key, 'surface_id': self.surface_id, 'restitution': e}
                          for key, e in self.restitution]}

    @property
    def registry_id(self):
        encoded = json.dumps(self.parameters(), sort_keys=True, separators=(',', ':'), allow_nan=False)
        return 'sha256:'+hashlib.sha256(encoded.encode()).hexdigest()

    def to_dict(self):
        return {'format': 'physics_contact_registry', 'schema_version': 1, 'visibility': 'host_only',
                'registry_id': self.registry_id, **self.parameters()}

    @classmethod
    def from_dict(cls, data):
        registry = cls(data['world_id'], data['object_registry_id'], data['surface']['id'],
                       tuple((p['specimen_id'], p['restitution']) for p in data['pairs']),
                       air_drag=data['air_drag'])
        if registry.to_dict() != data:
            raise ValueError('Unsupported or inconsistent contact registry.')
        return registry

    @classmethod
    def load(cls, path):
        return cls.from_dict(json.loads(Path(path).read_text()))

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if self.load(path) != self:
                raise FileExistsError('Output already contains different contact rules.')
        else:
            with path.open('x') as stream:
                json.dump(self.to_dict(), stream, indent=2, allow_nan=False)
                stream.write('\n')

    def impact_velocity(self, specimen_id, velocity_m_s):
        """Instantaneous impact with a horizontal plane, in z-up coordinates."""
        if (not isinstance(velocity_m_s, (tuple, list)) or len(velocity_m_s) != 3 or
                any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
                    for v in velocity_m_s) or velocity_m_s[2] > 0):
            raise ValueError('Impact needs a finite incoming three-component velocity with vz <= 0.')
        e = dict(self.restitution)[specimen_id]
        return [velocity_m_s[0], velocity_m_s[1], -e*velocity_m_s[2]]

    def write_markdown(self, path):
        rows = ['# Contact parameters (host-only)', '', f'Contact registry: `{self.registry_id}`', '',
                f'World: `{self.world_id}`', '', f'Object registry: `{self.object_registry_id}`', '',
                'Constant normal restitution on a stationary horizontal surface; no tangential friction, '
                'spin coupling or object–object collisions. '
                + ('Air drag is defined in the linked world record. ' if self.air_drag else 'No air drag. ')
                + 'Restitution belongs to each '
                'specimen material–surface pair, not to an isolated object.', '',
                '| Specimen | Surface | Restitution |', '|---|---|---|']
        rows += [f'| {key} | {self.surface_id} | {e:g} |' for key, e in self.restitution]
        Path(path).write_text('\n'.join(rows)+'\n')
