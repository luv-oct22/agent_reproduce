"""Constant-coefficient inverse-square/cube forces and guarded RK4 trajectories.

Host-side physics only. Force readings here are exact simulator outputs; an
experimental apparatus must apply its own measurement limits and costs.
"""
from itertools import combinations
import math

from src.worlds.definition import Record, WorldInstance, ObjectSpec, identifier, keys, number, vector


class DomainError(ValueError):
    """State or requested trajectory cannot be supported in the declared domain."""


class MotionState(Record):
    format = 'attraction_motion_state'

    @staticmethod
    def validate(d):
        keys(d, ('world_id', 'time_s', 'objects'))
        if not isinstance(d['world_id'], str) or not d['world_id'].startswith('sha256:'):
            raise ValueError('State must identify its physical world.')
        number(d['time_s'])
        if not isinstance(d['objects'], dict) or not d['objects']:
            raise ValueError('State requires an object map.')
        for name, state in d['objects'].items():
            identifier(name)
            keys(state, ('position_m', 'velocity_m_s'))
            vector(state['position_m'])
            vector(state['velocity_m_s'])


class AttractionWorld:
    """Explicit runtime for one supported law; unsupported compositions fail closed."""

    def __init__(self, instance, equation=None):
        if not isinstance(instance, WorldInstance):
            raise ValueError('Load a validated WorldInstance first.')
        d = instance.payload
        world, solver = d['world']['payload'], d['solver']['payload']
        if len(world['laws']) != 1 or world['contacts']:
            raise ValueError('Attraction v1 requires one force law and no contact rules.')
        law = world['laws'][0]['payload']
        if law['kind'] != 'central_attraction' or law['version'] != 1:
            raise ValueError('Attraction v1 does not execute this law.')
        p = law['parameters']
        self._field = None
        self._parametric = equation is not None and 'q' in equation
        if equation is not None and 'field_kind' in equation:
            required = ('field_kind', 'amplitude', 'time_scale', 'reference_time_s')
            optional = ('time_amplitude', 'q', 'alpha', 'beta', 'p', 's')
            keys(equation, required, optional)
            self._field = equation
            if self._parametric:
                for name in ('q', 'alpha', 'beta', 'p', 's'): number(equation[name])
        elif equation is not None:
            keys(equation, ('q', 'alpha', 'beta', 'p', 's'))
            for name in ('q', 'alpha', 'beta', 'p', 's'):
                number(equation[name])
            if equation['q'] <= 0 or equation['p'] <= 0:
                raise ValueError('Parametric attraction requires positive q and p.')
        if len(world['fields']) != 1:
            raise ValueError('Attraction v1 requires exactly one constant strength field.')
        field = world['fields'][0]['payload']
        if field['id'] != law['fields']['strength'] or field['kind'] != 'constant':
            raise ValueError('Attraction v1 cannot execute spatial or temporal strength fields.')
        if solver['kind'] != 'central_attraction_rk4' or solver['version'] != 1:
            raise ValueError('Unsupported attraction solver; no dynamic imports or fallbacks.')
        keys(solver['parameters'], ('max_step_s', 'min_step_s', 'max_steps'))
        settings = solver['parameters']
        if not 0 < settings['min_step_s'] < settings['max_step_s'] <= .02:
            raise ValueError('Require 0 < min_step_s < max_step_s <= 0.02.')
        if type(settings['max_steps']) is not int or not 1 <= settings['max_steps'] <= 1000000:
            raise ValueError('max_steps must be an integer in [1, 1000000].')
        objects = [o['payload'] for o in world['objects']]
        if len(objects) < 2 or any(o['shape'] != 'sphere' for o in objects):
            raise ValueError('Attraction v1 requires at least two spherical objects.')
        if not any(o['motion'] == 'dynamic' for o in objects):
            raise ValueError('At least one object must be movable.')
        self.instance = instance
        self.world_id = d['world']['record_id']
        self._ids = tuple(sorted(o['id'] for o in objects))
        by_id = {o['payload']['id']: ObjectSpec.from_dict(o) for o in world['objects']}
        self._mass = tuple(by_id[name].payload['mass_kg'] for name in self._ids)
        self._radius = tuple(by_id[name].properties()['radius_m'] for name in self._ids)
        self._fixed = tuple(by_id[name].payload['motion'] == 'fixed' for name in self._ids)
        self._exponent = float(p['exponent']) if equation is None or not self._parametric else float(equation['p'])
        self._q = 1.0 if not self._parametric else float(equation['q'])
        self._alpha = 1.0 if not self._parametric else float(equation['alpha'])
        self._beta = 1.0 if not self._parametric else float(equation['beta'])
        self._log_power = 0.0 if not self._parametric else float(equation['s'])
        self._strength = field['parameters']['value']
        self._r_ref, self._m_ref = p['reference_distance_m'], p['reference_mass_kg']
        self._minimum_distance = p['minimum_distance_m']
        self._max_step, self._min_step, self._max_steps = (
            settings['max_step_s'], settings['min_step_s'], settings['max_steps'])
        self._clock = d['protocol']['payload']['clock']
        self._pairs = tuple(combinations(range(len(objects)), 2))
        self._limits = {(i, j): max(self._minimum_distance, self._radius[i]+self._radius[j])
                        for i, j in self._pairs}
        # A global acceleration bound in the admissible domain, used by the
        # step guard. Fixed supports have zero actual acceleration.
        self._acceleration_bound = [0.] * len(objects)
        for i, j in self._pairs:
            force = self._magnitude(i, j, self._limits[i, j])
            if not self._fixed[i]:
                self._acceleration_bound[i] += force/self._mass[i]
            if not self._fixed[j]:
                self._acceleration_bound[j] += force/self._mass[j]
        if not all(math.isfinite(a) for a in self._acceleration_bound):
            raise ValueError('Force/acceleration scale exceeds numerical limits.')

    def _field_factor(self, distance, time_s):
        if not self._field:
            return 1.0
        f = self._field
        u = (distance - self._r_ref) / self._r_ref
        v = (time_s - f['reference_time_s']) / f['time_scale']
        kind = f['field_kind']
        if kind == 'linear_space': value = 1 + f['amplitude'] * u
        elif kind == 'linear_time': value = 1 + f['amplitude'] * v
        elif kind == 'quadratic_space': value = 1 + f['amplitude'] * u*u
        elif kind == 'log_time': value = 1 + f['amplitude'] * math.log(1 + abs(v))
        elif kind == 'space_time': value = 1 + f['amplitude'] * u + f['time_amplitude'] * math.sin(2*math.pi*v/1.5)
        elif kind == 'nested': value = 1 + .30*math.sin(math.pi*u + .5*v) + .20*math.log(1+u*u) + .15*v*v
        else: raise DomainError('Unknown hidden force field.')
        if not math.isfinite(value) or value <= 0: raise DomainError('Hidden force coefficient is outside its domain.')
        return value

    def _magnitude(self, i, j, distance, time_s=0.0):
        try:
            log_factor = math.log(math.e + distance / self._r_ref)
            force = (self._strength * self._q
                     *(self._mass[i]/self._m_ref)**self._alpha
                     *(self._mass[j]/self._m_ref)**self._beta
                     *(self._r_ref/distance)**self._exponent
                     *log_factor**self._log_power * self._field_factor(distance, time_s))
        except OverflowError as exc:
            raise DomainError('Force scale exceeds numerical limits.') from exc
        if not math.isfinite(force):
            raise DomainError('Force scale exceeds numerical limits.')
        return force

    def _check_time(self, time_s):
        number(time_s)
        domain = self._clock['time_range_s']
        if domain is not None and not domain[0] <= time_s <= domain[1]:
            raise DomainError('Time is outside the declared clock domain.')

    def make_state(self, positions_m, velocities_m_s=None, time_s=None):
        if not isinstance(positions_m, dict) or set(positions_m) != set(self._ids):
            raise ValueError('Positions must specify exactly the world objects.')
        velocities_m_s = {name: [0., 0., 0.] for name in self._ids} if velocities_m_s is None else velocities_m_s
        if not isinstance(velocities_m_s, dict) or set(velocities_m_s) != set(self._ids):
            raise ValueError('Velocities must specify exactly the world objects.')
        state = MotionState(dict(world_id=self.world_id,
            time_s=self._clock['start_time_s'] if time_s is None else time_s,
            objects={name: dict(position_m=positions_m[name], velocity_m_s=velocities_m_s[name]) for name in self._ids}))
        self._unpack(state)
        return state

    def _unpack(self, state):
        if not isinstance(state, MotionState):
            raise ValueError('Expected a validated MotionState.')
        d = state.payload
        if d['world_id'] != self.world_id or set(d['objects']) != set(self._ids):
            raise ValueError('State belongs to a different physical world or object registry.')
        self._check_time(d['time_s'])
        y = []
        for i, name in enumerate(self._ids):
            obj = d['objects'][name]
            if self._fixed[i] and any(v != 0 for v in obj['velocity_m_s']):
                raise ValueError('Fixed objects must have zero velocity.')
            y.extend(obj['position_m']+obj['velocity_m_s'])
        self._forces(y, d['time_s'])
        return d['time_s'], y

    def _pack(self, time_s, y):
        return MotionState(dict(world_id=self.world_id, time_s=time_s,
            objects={name: dict(position_m=y[6*i:6*i+3], velocity_m_s=y[6*i+3:6*i+6])
                     for i, name in enumerate(self._ids)}))

    def _separation(self, y, i, j):
        delta = [y[6*j+k]-y[6*i+k] for k in range(3)]
        distance = math.hypot(*delta)
        if not math.isfinite(distance) or distance <= self._limits[i, j]:
            raise DomainError('Object separation is outside the supported noncontact domain.')
        return delta, distance

    def _forces(self, y, time_s=0.0):
        if not all(math.isfinite(value) for value in y):
            raise DomainError('Non-finite trajectory state.')
        forces = [[0., 0., 0.] for _ in self._ids]
        for i, j in self._pairs:
            delta, distance = self._separation(y, i, j)
            magnitude = self._magnitude(i, j, distance, time_s)
            for k in range(3):
                component = magnitude*(delta[k]/distance)
                forces[i][k] += component
                forces[j][k] -= component
        if not all(math.isfinite(value) for force in forces for value in force):
            raise DomainError('Net force exceeds numerical limits.')
        return forces

    def forces(self, state):
        """Mutual attraction in N, including loads on fixed bodies, not support reactions."""
        _, y = self._unpack(state)
        return dict(zip(self._ids, self._forces(y, state.payload['time_s'])))

    def accelerations(self, state):
        _, y = self._unpack(state)
        return {name: [0., 0., 0.] if self._fixed[i] else [f/self._mass[i] for f in force]
                for i, (name, force) in enumerate(zip(self._ids, self._forces(y, state.payload['time_s'])))}

    def _derivative(self, y, time_s=0.0):
        result = []
        for i, force in enumerate(self._forces(y, time_s)):
            result.extend([0.]*6 if self._fixed[i] else y[6*i+3:6*i+6]+[f/self._mass[i] for f in force])
        return result

    def _rk4(self, y, h, time_s=0.0):
        a = self._derivative(y, time_s)
        b = self._derivative([v+h*k/2 for v, k in zip(y, a)], time_s+h/2)
        c = self._derivative([v+h*k/2 for v, k in zip(y, b)], time_s+h/2)
        d = self._derivative([v+h*k for v, k in zip(y, c)], time_s+h)
        result = [v+h*(w+2*x+2*z+q)/6 for v, w, x, z, q in zip(y, a, b, c, d)]
        self._forces(result)
        return result

    def _safe_step(self, y):
        h = self._max_step
        for i, j in self._pairs:
            _, distance = self._separation(y, i, j)
            speed = math.hypot(*(y[6*j+3+k]-y[6*i+3+k] for k in range(3)))
            acceleration = self._acceleration_bound[i]+self._acceleration_bound[j]
            margin = .25*(distance-self._limits[i, j])
            # Bound relative travel by a quarter of the clearance. This avoids
            # tunnelling through the forbidden region between RK4 stage samples.
            denominator = speed+math.hypot(speed, math.sqrt(2*acceleration*margin))
            if denominator:
                h = min(h, 2*margin/denominator)
        return h

    def advance(self, state, duration_s):
        number(duration_s, minimum=0)
        time_s, y = self._unpack(state)
        target = time_s+duration_s
        self._check_time(target)
        if duration_s == 0:
            return state
        if target <= time_s:
            raise DomainError('Duration cannot be represented at this absolute time.')
        for _ in range(self._max_steps):
            remaining = target-time_s
            safe = self._safe_step(y)
            if safe < min(self._min_step, remaining):
                raise DomainError('Cannot safely advance above the separation boundary at the configured minimum step.')
            h = min(safe, remaining)
            if h <= 0 or time_s+h == time_s:
                raise DomainError('Integration cannot make numerical progress.')
            y = self._rk4(y, h, time_s)
            if h == remaining:
                return self._pack(target, y)
            time_s += h
        raise DomainError('Integration step budget exhausted; no partial result was accepted.')

    def trajectory(self, state, sample_times_s):
        """Absolute, strictly increasing sample times; apparatus budgets are external."""
        if not isinstance(sample_times_s, (tuple, list)) or not sample_times_s:
            raise ValueError('Provide a nonempty sequence of absolute sample times.')
        start, _ = self._unpack(state)
        previous = None
        for t in sample_times_s:
            self._check_time(t)
            if t < start or (previous is not None and t <= previous):
                raise ValueError('Sample times must increase strictly and not precede the initial state.')
            previous = t
        result = []
        current = state
        for t in sample_times_s:
            current = self.advance(current, t-current.payload['time_s'])
            result.append(current)
        return result

    def diagnostics(self, state):
        """Host-only energy/momentum diagnostics for this constant, conservative law."""
        _, y = self._unpack(state)
        kinetic, potential = 0., 0.
        momentum, angular = [0., 0., 0.], [0., 0., 0.]
        for i, mass in enumerate(self._mass):
            position, velocity = y[6*i:6*i+3], y[6*i+3:6*i+6]
            kinetic += .5*mass*sum(v*v for v in velocity)
            for k in range(3):
                momentum[k] += mass*velocity[k]
                a, b = (k+1) % 3, (k+2) % 3
                angular[k] += mass*(position[a]*velocity[b]-position[b]*velocity[a])
        for i, j in self._pairs:
            _, distance = self._separation(y, i, j)
            potential -= self._magnitude(i, j, distance)*distance/(self._exponent-1)
        return dict(kinetic_energy_j=kinetic, potential_energy_j=potential, total_energy_j=kinetic+potential,
                    momentum_kg_m_s=momentum, angular_momentum_kg_m2_s=angular,
                    momentum_conservation_expected=not any(self._fixed))
