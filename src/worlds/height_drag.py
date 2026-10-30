"""Fixed, smooth random drag fields and shared event-aware trajectory integration."""
from bisect import bisect_right
from dataclasses import dataclass
import hashlib
import json
import math
import random

from src.worlds.layered_drag import LayeredDragWorld, finite


def validate_samples(heights, coefficients):
    if (not isinstance(heights, (list, tuple)) or not isinstance(coefficients, (list, tuple))
            or not 2 <= len(heights) <= 65 or len(heights) != len(coefficients)
            or not all(finite(x) for x in (*heights, *coefficients))
            or heights[0] != 0 or heights[-1] != 3
            or any(b-a < .01-1e-12 for a, b in zip(heights, heights[1:]))
            or any(not 0 <= b <= .5 for b in coefficients)):
        raise ValueError('Use 2–65 ordered heights from 0 to 3 m, spacing >=0.01 m, with matching drag values in [0, 0.5] kg/s.')


@dataclass(frozen=True)
class HeightDragWorld:
    gravity_m_s2: float = 3.0
    heights_m: tuple = (0., 3.)
    coefficients_kg_s: tuple = (.1, .1)
    generation_seed: int | None = None
    max_step_s: float = .002

    def __post_init__(self):
        validate_samples(self.heights_m, self.coefficients_kg_s)
        if (not finite(self.gravity_m_s2) or self.gravity_m_s2 <= 0
                or not finite(self.max_step_s) or not 0 < self.max_step_s <= .005
                or (self.generation_seed is not None and
                    (isinstance(self.generation_seed, bool) or not isinstance(self.generation_seed, int)))):
            raise ValueError('Invalid gravity, integration step or generation seed.')
        object.__setattr__(self, 'heights_m', tuple(map(float, self.heights_m)))
        object.__setattr__(self, 'coefficients_kg_s', tuple(map(float, self.coefficients_kg_s)))
        object.__setattr__(self, 'gravity_m_s2', float(self.gravity_m_s2))
        object.__setattr__(self, 'max_step_s', float(self.max_step_s))

    @classmethod
    def generate(cls, gravity_m_s2=3., seed=42, knot_count=13, min_drag_kg_s=.01, max_drag_kg_s=.30):
        if (isinstance(seed, bool) or not isinstance(seed, int)
                or isinstance(knot_count, bool) or not isinstance(knot_count, int) or not 3 <= knot_count <= 65
                or not all(finite(v) for v in (min_drag_kg_s, max_drag_kg_s))
                or not 0 <= min_drag_kg_s < max_drag_kg_s <= .5):
            raise ValueError('Invalid random profile seed, knot count or coefficient range.')
        rng = random.Random(seed)
        return cls(gravity_m_s2, tuple(3*i/(knot_count-1) for i in range(knot_count)),
                   tuple(rng.uniform(min_drag_kg_s, max_drag_kg_s) for _ in range(knot_count)), seed)

    def coefficient(self, height_m):
        """C1 smoothstep interpolation; nonnegative and constant outside [0,3]."""
        if not finite(height_m):
            raise ValueError('Height must be finite.')
        i = bisect_right(self.heights_m, height_m)-1
        if i < 0:
            return self.coefficients_kg_s[0]
        if i >= len(self.heights_m)-1:
            return self.coefficients_kg_s[-1]
        u = (height_m-self.heights_m[i])/(self.heights_m[i+1]-self.heights_m[i])
        weight = u*u*(3-2*u)
        return self.coefficients_kg_s[i]*(1-weight)+self.coefficients_kg_s[i+1]*weight

    def parameters(self):
        return {'gravity_m_s2': self.gravity_m_s2, 'heights_m': list(self.heights_m),
                'coefficients_kg_s': list(self.coefficients_kg_s), 'generation_seed': self.generation_seed,
                'law': 'F_drag = -b(z) * velocity', 'interpolation': 'smoothstep: w(u)=3*u^2-2*u^3',
                'extrapolation': 'constant endpoint values', 'coordinate': 'sphere centre z above impact surface at z=0',
                'drag_units': 'kg/s', 'gravity_units': 'm/s^2', 'length_units': 'm',
                'medium_stationary': True, 'buoyancy': False, 'spin_coupling': False,
                'object_object_collisions': False, 'rest_normal_speed_threshold_m_s': 1e-7,
                'solver': 'rk4_with_bisected_impact_and_apex_events_v1', 'max_step_s': self.max_step_s}

    @property
    def world_id(self):
        return 'sha256:'+hashlib.sha256(json.dumps(self.parameters(), sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    def to_dict(self):
        return dict(format='height_drag_world', schema_version=1, visibility='host_only',
                    world_id=self.world_id, **self.parameters())

    @classmethod
    def from_dict(cls, data):
        world = cls(**{k: data[k] for k in cls.__dataclass_fields__})
        if world.to_dict() != data:
            raise ValueError('Unsupported or inconsistent height-drag world record.')
        return world

    def _step(self, state, dt, mass):
        def derivative(s):
            rate = self.coefficient(s[2])/mass
            return (s[3], s[4], s[5], -rate*s[3], -rate*s[4], -self.gravity_m_s2-rate*s[5])
        a = derivative(state)
        b = derivative([s+dt*x/2 for s, x in zip(state, a)])
        c = derivative([s+dt*x/2 for s, x in zip(state, b)])
        d = derivative([s+dt*x for s, x in zip(state, c)])
        return [s+dt*(w+2*x+2*y+z)/6 for s, w, x, y, z in zip(state, a, b, c, d)]

    def _integrate(self, position, velocity, duration, mass, radius, restitution, stop_at_rebound=False):
        if (not isinstance(position, (tuple, list)) or not isinstance(velocity, (tuple, list))
                or len(position) != 3 or len(velocity) != 3
                or not all(finite(x) for x in (*position, *velocity, duration, mass, radius, restitution))
                or duration < 0 or mass <= 0 or radius <= 0 or position[2] < radius or not 0 <= restitution <= 1):
            raise ValueError('Invalid sphere motion parameters.')
        state = [*position, *velocity]
        time, impacts, first_impact = 0., 0, None
        spatial_step = min(b-a for a, b in zip(self.heights_m, self.heights_m[1:]))/16
        rate_max = max(self.coefficients_kg_s)/mass
        max_step = min(self.max_step_s, .05/rate_max if rate_max else self.max_step_s)
        for _ in range(2000000):
            if time >= duration:
                if stop_at_rebound:
                    raise RuntimeError('Rebound not reached within integration horizon.')
                return dict(position_m=state[:3], velocity_m_s=state[3:], impacts=impacts)
            if state[2] == radius and abs(state[5]) < 1e-7:
                if stop_at_rebound:
                    return dict(time_to_first_impact_s=first_impact, first_rebound_height_m=0.)
                remaining = duration-time
                rate = self.coefficient(radius)/mass
                integral = -math.expm1(-rate*remaining)/rate if rate else remaining
                for i in (0, 1):
                    state[i] += state[i+3]*integral
                    state[i+3] *= math.exp(-rate*remaining)
                state[5] = 0.
                return dict(position_m=state[:3], velocity_m_s=state[3:], impacts=impacts)
            dt = min(max_step, duration-time, spatial_step/max(abs(state[5]), .01))
            if state[5] > 0:
                # Resolve even tiny rebound arcs before their next impact.
                dt = min(dt, max(state[5]/self.gravity_m_s2, 1e-12))
            trial = self._step(state, dt, mass)
            kind = 'apex' if state[5] > 0 and trial[5] <= 0 else 'impact' if trial[2] <= radius else None
            if kind:
                lo, hi = 0., dt
                for _ in range(36):
                    mid = (lo+hi)/2
                    probe = self._step(state, mid, mass)
                    crossed = probe[5] <= 0 if kind == 'apex' else probe[2] <= radius
                    if crossed:
                        hi = mid
                    else:
                        lo = mid
                dt = (lo+hi)/2
                trial = self._step(state, dt, mass)
                if kind == 'impact':
                    trial[2], trial[5] = radius, -restitution*trial[5]
                    impacts += 1
                    if first_impact is None:
                        first_impact = time+dt
                else:
                    trial[5] = 0.
                    if stop_at_rebound and first_impact is not None:
                        return dict(time_to_first_impact_s=first_impact, first_rebound_height_m=max(0, trial[2]-radius))
            state, time = trial, time+dt
        raise RuntimeError('Trajectory integration exceeded the step budget.')

    def advance(self, position_m, velocity_m_s, elapsed_s, mass_kg, radius_m, restitution):
        return self._integrate(position_m, velocity_m_s, elapsed_s, mass_kg, radius_m, restitution)

    def drop_readings(self, release_height_m, mass_kg, radius_m, restitution):
        if not finite(release_height_m) or release_height_m <= 0:
            raise ValueError('Release clearance must be finite and positive.')
        return self._integrate([0, 0, radius_m+release_height_m], [0, 0, 0], 300.,
                               mass_kg, radius_m, restitution, stop_at_rebound=True)


def load_drag_world(data):
    if data.get('format') == 'height_drag_world':
        return HeightDragWorld.from_dict(data)
    return LayeredDragWorld.from_dict(data)
