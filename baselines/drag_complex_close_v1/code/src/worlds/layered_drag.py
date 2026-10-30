"""Exact linear-drag flight within layers, with explicit boundary/impact events.

Host-side physics shared by experimental instruments and future visual scenes.
Coordinates are sphere-centre positions in metres, z up, floor at z=0.
"""
from dataclasses import dataclass, asdict
import hashlib
import json
import math
from pathlib import Path


def finite(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


@dataclass(frozen=True)
class LayeredDragWorld:
    gravity_m_s2: float = 3.0
    boundary_height_m: float = .85
    lower_drag_kg_s: float = .03
    upper_drag_kg_s: float = .18

    def __post_init__(self):
        for name, value in asdict(self).items():
            if not finite(value) or value < 0 or (name in ('gravity_m_s2', 'boundary_height_m') and value == 0):
                raise ValueError('World parameters must be finite; gravity/boundary positive and drag nonnegative.')
            object.__setattr__(self, name, float(value))

    def parameters(self):
        return dict(asdict(self), law='F_drag = -b(z) * velocity',
                    coordinate='sphere centre z above a stationary horizontal floor at z=0',
                    layer_rule='lower below boundary; upper above boundary; continuous position and velocity',
                    drag_units='kg/s', gravity_units='m/s^2', length_units='m',
                    medium_stationary=True, buoyancy=False, spin_coupling=False,
                    object_object_collisions=False, rest_normal_speed_threshold_m_s=1e-7,
                    solver='exact_layer_flight_with_bisected_events_v1')

    @property
    def world_id(self):
        payload = json.dumps(self.parameters(), sort_keys=True, separators=(',', ':'))
        return 'sha256:'+hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self):
        return dict(format='layered_drag_world', schema_version=1, visibility='host_only',
                    world_id=self.world_id, **self.parameters())

    @classmethod
    def from_dict(cls, data):
        world = cls(**{name: data[name] for name in cls.__dataclass_fields__})
        if world.to_dict() != data:
            raise ValueError('Unsupported or inconsistent drag world record.')
        return world

    @classmethod
    def load(cls, path):
        return cls.from_dict(json.loads(Path(path).read_text()))

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if self.load(path) != self:
                raise FileExistsError('Output already contains a different drag world.')
        else:
            path.write_text(json.dumps(self.to_dict(), indent=2)+'\n')

    def _flight(self, position, velocity, duration, rate):
        """Solve dv/dt = -rate*v + (0,0,-g) without time stepping."""
        x = rate*duration
        if abs(x) < 1e-4:
            a = duration*(1-x/2+x*x/6-x**3/24+x**4/120)
            b = duration**2*(.5-x/6+x*x/24-x**3/120+x**4/720)
        else:
            a = -math.expm1(-x)/rate
            b = (duration-a)/rate
        decay = math.exp(-x)
        gravity = (0, 0, -self.gravity_m_s2)
        return ([p+v*a+g*b for p, v, g in zip(position, velocity, gravity)],
                [v*decay+g*a for v, g in zip(velocity, gravity)])

    def _next_event(self, position, velocity, mass, radius):
        z, vz = position[2], velocity[2]
        upper = z > self.boundary_height_m or (z == self.boundary_height_m and vz > 0)
        rate = (self.upper_drag_kg_s if upper else self.lower_drag_kg_s)/mass
        if vz > 0:
            apex_time = math.log1p(rate*vz/self.gravity_m_s2)/rate if rate else vz/self.gravity_m_s2
            apex, _ = self._flight(position, velocity, apex_time, rate)
            if upper or apex[2] <= self.boundary_height_m:
                apex_velocity = self._flight(position, velocity, apex_time, rate)[1]
                apex_velocity[2] = 0.0
                return apex_time, apex, apex_velocity, 'apex', rate
            target, high, kind = self.boundary_height_m, apex_time, 'boundary'
        else:
            target = self.boundary_height_m if upper else radius
            kind = 'boundary' if upper else 'impact'
            high = .25
            for _ in range(80):
                if self._flight(position, velocity, high, rate)[0][2] <= target:
                    break
                high *= 2
            else:
                raise RuntimeError('Could not bracket a flight event.')
        low = 0.0
        for _ in range(48):
            mid = (low+high)/2
            zm = self._flight(position, velocity, mid, rate)[0][2]
            if (zm < target) == (vz > 0):
                low = mid
            else:
                high = mid
        elapsed = (low+high)/2
        p, v = self._flight(position, velocity, elapsed, rate)
        p[2] = target
        return elapsed, p, v, kind, rate

    def _validate_motion(self, position, velocity, mass, radius, restitution):
        if (not isinstance(position, (list, tuple)) or not isinstance(velocity, (list, tuple))
                or len(position) != 3 or len(velocity) != 3
                or not all(finite(x) for x in [*position, *velocity, mass, radius, restitution])
                or mass <= 0 or not 0 < radius < self.boundary_height_m
                or position[2] < radius or not 0 <= restitution <= 1):
            raise ValueError('Invalid sphere state, mass, radius or restitution.')

    def drop_readings(self, release_height_m, mass_kg, radius_m, restitution):
        if not finite(release_height_m) or release_height_m <= 0:
            raise ValueError('Release clearance must be finite and positive.')
        p, v = [0, 0, radius_m+release_height_m], [0, 0, 0]
        self._validate_motion(p, v, mass_kg, radius_m, restitution)
        elapsed, impact_time = 0.0, None
        for _ in range(12):
            dt, p, v, kind, _ = self._next_event(p, v, mass_kg, radius_m)
            elapsed += dt
            if kind == 'impact':
                impact_time = elapsed
                v[2] = -restitution*v[2]
                if restitution == 0:
                    return {'time_to_first_impact_s': impact_time, 'first_rebound_height_m': 0.0}
            elif kind == 'apex' and impact_time is not None:
                return {'time_to_first_impact_s': impact_time, 'first_rebound_height_m': max(0, p[2]-radius_m)}
        raise RuntimeError('Unexpected event sequence in drop experiment.')

    def advance(self, position_m, velocity_m_s, elapsed_s, mass_kg, radius_m, restitution):
        """Host-only arbitrary-time state, including horizontal drag and repeated impacts.

        Impacts preserve horizontal velocity. At tiny normal rebound speeds (<1e-7
        m/s), sustained floor contact replaces unresolved micro-bounces. Horizontal
        motion continues to damp in contact. This approximation is recorded below.
        """
        self._validate_motion(position_m, velocity_m_s, mass_kg, radius_m, restitution)
        if not finite(elapsed_s) or elapsed_s < 0:
            raise ValueError('Elapsed time must be finite and nonnegative.')
        p, v, remaining, impacts = list(position_m), list(velocity_m_s), elapsed_s, 0
        for _ in range(10000):
            if remaining == 0:
                return {'position_m': p, 'velocity_m_s': v, 'impacts': impacts}
            if p[2] == radius_m and abs(v[2]) < 1e-7:
                p, v = self._flight(p, v, remaining, self.lower_drag_kg_s/mass_kg)
                p[2], v[2] = radius_m, 0.0
                return {'position_m': p, 'velocity_m_s': v, 'impacts': impacts}
            dt, end_p, end_v, kind, rate = self._next_event(p, v, mass_kg, radius_m)
            if remaining < dt:
                p, v = self._flight(p, v, remaining, rate)
                return {'position_m': p, 'velocity_m_s': v, 'impacts': impacts}
            p, v, remaining = end_p, end_v, max(0, remaining-dt)
            if kind == 'impact':
                impacts += 1
                v[2] *= -restitution
        raise RuntimeError('Too many collision events for this trajectory.')
