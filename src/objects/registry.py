"""Host-only source of truth for objects shared by experiments and video scenes."""
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path

from .specimen import Specimen


UNITS = {'length': 'm', 'mass': 'kg', 'volume': 'm^3', 'density': 'kg/m^3', 'inertia': 'kg*m^2'}


@dataclass(frozen=True)
class ObjectRegistry:
    specimens: tuple[Specimen, ...]
    seed: int | float | str | None = None

    def __post_init__(self):
        if (self.seed is not None and not isinstance(self.seed, (int, float, str))) or (
                isinstance(self.seed, float) and not math.isfinite(self.seed)):
            raise ValueError('Registry seed must be a finite number, string, or null.')
        object.__setattr__(self, 'specimens', tuple(self.specimens))
        if not self.specimens or not all(isinstance(obj, Specimen) for obj in self.specimens):
            raise ValueError('A registry requires at least one Specimen.')
        ids = [obj.specimen_id for obj in self.specimens]
        if len(set(ids)) != len(ids):
            raise ValueError('Registry object IDs must be unique.')

    @property
    def registry_id(self):
        objects = [obj.private_dict() for obj in sorted(self.specimens, key=lambda obj: obj.specimen_id)]
        payload = json.dumps({'units': UNITS, 'objects': objects}, sort_keys=True, separators=(',', ':'), allow_nan=False)
        return 'sha256:'+hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self):
        return {'format': 'physics_object_registry', 'schema_version': 1, 'visibility': 'host_only',
                'registry_id': self.registry_id, 'units': dict(UNITS),
                'provenance': {'source_environment': 'material_lab', 'seed': self.seed},
                'objects': [obj.private_dict() for obj in self.specimens]}

    @classmethod
    def from_dict(cls, data):
        if (data.get('format') != 'physics_object_registry' or data.get('schema_version') != 1
                or data.get('units') != UNITS or data.get('visibility') != 'host_only'):
            raise ValueError('Unsupported object registry format or units.')
        registry = cls(tuple(Specimen.from_dict(obj) for obj in data['objects']), data['provenance'].get('seed'))
        if registry.registry_id != data.get('registry_id'):
            raise ValueError('Object registry identity check failed; object properties have changed.')
        return registry

    @classmethod
    def load(cls, path):
        return cls.from_dict(json.loads(Path(path).read_text()))

    def save(self, path):
        """Never silently replace a run's registry with a different set of objects."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.to_dict()
        try:
            with path.open('x') as stream:
                json.dump(data, stream, indent=2, allow_nan=False)
                stream.write('\n')
        except FileExistsError:
            existing = ObjectRegistry.load(path)
            if existing.to_dict() != data:
                raise FileExistsError('This output directory already records a different object registry.')
        return path

    def write_markdown(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = ['# Shared object registry (host-only)', '', f'Registry ID: `{self.registry_id}`', '',
                 'These are ground-truth properties for the environment and subsequent video simulation. '
                 'Do not include this file in model prompts or observations.', '',
                 '| Object | Color | Shape | Mass (kg) | Volume (m³) | Density (kg/m³) | Side length / diameter (m) |',
                 '|---|---|---|---|---|---|---|']
        for obj in self.specimens:
            key = obj.specimen_id.replace('|', '\\|').replace('\n', ' ')
            color = obj.color.replace('|', '\\|').replace('\n', ' ')
            lines.append(f'| {key} | {color} | {obj.shape} | {obj.mass_kg:.9g} | {obj.volume_m3:.9g} '
                         f'| {obj.density_kg_m3:.9g} | {obj.private_dict()["geometry"]["dimensions_m"][0]:.9g} |')
        lines += ['', 'The JSON companion additionally records exact RGBA colors, dimensions, collision shape, '
                  'local center of mass, inertia, and rigid/nonporous/nonabsorbing assumptions.', '',
                  'Positions, orientations, launch velocities, fluid properties, contact coefficients and '
                  'camera settings belong to each later scene and are not invented here.', '']
        path.write_text('\n'.join(lines))
        return path

    def simulation_objects(self):
        """Fresh renderer/physics definitions, with geometry and properties intact.

        Scene builders add placement and initial motion separately. No random
        generation or model-inferred estimates participate in this handoff.
        """
        return [obj.private_dict() for obj in self.specimens]
