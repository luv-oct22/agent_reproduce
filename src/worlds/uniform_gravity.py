"""Host-only physical world definition, shared by experiments and future motion scenes."""
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path


@dataclass(frozen=True)
class UniformGravityWorld:
    gravity_m_s2: float = 3.0

    def __post_init__(self):
        if isinstance(self.gravity_m_s2, bool) or not isinstance(self.gravity_m_s2, (int, float)) or not math.isfinite(self.gravity_m_s2) or self.gravity_m_s2 <= 0:
            raise ValueError('Gravity must be a finite positive acceleration in m/s².')
        object.__setattr__(self, 'gravity_m_s2', float(self.gravity_m_s2))

    def parameters(self):
        return {'dynamics': 'newtonian_uniform_gravity', 'gravity_m_s2': self.gravity_m_s2,
                'gravity_vector_m_s2': [0.0, 0.0, -self.gravity_m_s2],
                'units': {'length': 'm', 'time': 's', 'mass': 'kg', 'acceleration': 'm/s^2'},
                'air_drag': False, 'mass_independent_free_fall': True}

    @property
    def world_id(self):
        data = json.dumps(self.parameters(), sort_keys=True, separators=(',', ':'))
        return 'sha256:'+hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self):
        return {'format': 'physics_world', 'schema_version': 1, 'visibility': 'host_only',
                'world_id': self.world_id, **self.parameters()}

    @classmethod
    def from_dict(cls, data):
        world = cls(data['gravity_m_s2'])
        if data != world.to_dict():
            raise ValueError('Unsupported or inconsistent world record.')
        return world

    @classmethod
    def load(cls, path):
        return cls.from_dict(json.loads(Path(path).read_text()))

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if self.load(path) != self:
                raise FileExistsError('Output already contains a different physical world.')
        else:
            with path.open('x') as stream:
                json.dump(self.to_dict(), stream, indent=2)
                stream.write('\n')
        return path

    def free_fall_time(self, distance_m):
        if isinstance(distance_m, bool) or not isinstance(distance_m, (float, int)) or not math.isfinite(distance_m) or distance_m <= 0:
            raise ValueError('Fall distance must be finite and positive.')
        return math.sqrt(2*distance_m/self.gravity_m_s2)

    def advance(self, position_m, velocity_m_s, elapsed_s):
        """Exact free flight in z-up coordinates. No contact or drag solver is implied."""
        if (not isinstance(position_m, (list, tuple)) or not isinstance(velocity_m_s, (list, tuple))
                or len(position_m) != 3 or len(velocity_m_s) != 3):
            raise ValueError('Position and velocity must each have three components.')
        if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v)
               for v in [*position_m, *velocity_m_s, elapsed_s]) or elapsed_s < 0:
            raise ValueError('Motion inputs must be finite; elapsed time must be nonnegative.')
        acceleration = [0, 0, -self.gravity_m_s2]
        return {'position_m': [p+v*elapsed_s+.5*a*elapsed_s**2 for p, v, a in zip(position_m, velocity_m_s, acceleration)],
                'velocity_m_s': [v+a*elapsed_s for v, a in zip(velocity_m_s, acceleration)]}
