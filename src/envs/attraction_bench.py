"""Budgeted, quantized apparatus for the saved common_bench_v1 protocol."""
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
import math

from src.envs.base import BaseEnv
from src.envs.registry import register_env
from src.worlds.attraction import AttractionWorld, DomainError
from src.worlds.attraction_setup import bench_protocol
from src.worlds.definition import ObjectSpec, WorldInstance


# Versioned execution semantics supplement the saved tool schemas. These are
# identical in every supported world and are saved with each interaction.
APPARATUS_RULES = dict(
    version='common_bench_execution_v1',
    axes='Cartesian laboratory axes in metres, z up. Positions denote sphere centres.',
    clock='Virtual time is paused between calls. Only track_motion advances time. '
          'configure_trial starts a new trial at the supplied absolute time and does not replenish the budget.',
    force='The sensor reads the external load on the specimen, excluding the holding reaction. '
          'This instantaneous snapshot does not change position, velocity or time.',
    sampling='track_motion records exactly sample_count positions, at start + duration * k / sample_count '
             'for k=1,...,sample_count. The starting position is not an extra sample.',
    precision='Each component is clipped to the sensor range, then rounded to the nearest resolution '
              'with ties away from zero. Each component has a saturation flag.',
    failures='Malformed or out-of-budget actions are rejected without charge. A valid paid experiment '
             'that cannot complete within apparatus limits is charged in full; state and time stay unchanged '
             'and no partial measurements are returned.',
    inspection='inspect reports calibration, clock, budget and the last commanded trial setup, '
               'not the current unmeasured position or velocity. Impulse acknowledgments do not measure velocity.',
)


def validate_arguments(value, schema, path='arguments'):
    """Validate the closed JSON-schema subset used by this version of the bench."""
    kind = schema['type']
    valid = {'object': isinstance(value, dict), 'array': isinstance(value, list),
             'string': isinstance(value, str), 'integer': type(value) is int,
             'number': type(value) in (int, float)}[kind]
    if not valid:
        raise ValueError(f'{path} must have type {kind}.')
    if kind in ('number', 'integer'):
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError(f'{path} must be finite.')
        for key, fails in [('minimum', lambda a, b: a < b), ('maximum', lambda a, b: a > b),
                           ('exclusiveMinimum', lambda a, b: a <= b)]:
            if key in schema and fails(value, schema[key]):
                raise ValueError(f'{path} violates {key}={schema[key]}.')
    if 'enum' in schema and value not in schema['enum']:
        raise ValueError(f'{path} must be one of {schema["enum"]}.')
    if kind == 'object':
        properties = schema['properties']
        if set(value) - set(properties) or set(schema.get('required', [])) - set(value):
            raise ValueError(f'{path} has missing or unknown fields.')
        for key, item in value.items():
            validate_arguments(item, properties[key], f'{path}.{key}')
    if kind == 'array':
        if not schema.get('minItems', 0) <= len(value) <= schema.get('maxItems', math.inf):
            raise ValueError(f'{path} has an invalid length.')
        for index, item in enumerate(value):
            validate_arguments(item, schema['items'], f'{path}[{index}]')


def sensor_reading(values, spec):
    resolution = Decimal(str(spec['resolution']))
    low, high = spec['range']
    clipped = [max(low, min(high, value)) for value in values]
    return dict(value=[float((Decimal(str(v))/resolution).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                            * resolution) for v in clipped],
                unit=spec['unit'], resolution=spec['resolution'],
                saturated=[v < low or v > high for v in values])


@register_env('attraction_bench')
class AttractionBenchEnv(BaseEnv):
    def __init__(self, instance_path=None, *, instance=None, reveal_disclosures=True, equation=None):
        super().__init__()
        if (instance is None) == (instance_path is None):
            raise ValueError('Provide exactly one saved instance path or WorldInstance.')
        self.instance = instance if instance is not None else WorldInstance.load(instance_path)
        self.reveal_disclosures = reveal_disclosures
        self.equation = equation
        self.world = AttractionWorld(self.instance, equation=equation)
        self.protocol = self.instance.payload['protocol']['payload']
        expected = bench_protocol().payload
        if {k: v for k, v in self.protocol.items() if k != 'budget'} != {
                k: v for k, v in expected.items() if k != 'budget'}:
            raise ValueError('Unsupported apparatus protocol; author an explicit new execution version.')
        objects = {o['payload']['id']: o['payload'] for o in self.instance.payload['world']['payload']['objects']}
        if (set(objects) != {'anchor', 'probe'} or objects['anchor']['motion'] != 'fixed'
                or objects['probe']['motion'] != 'dynamic'):
            raise ValueError('This apparatus requires one fixed anchor and one movable probe.')
        law = self.instance.payload['world']['payload']['laws'][0]['payload']['parameters']
        radii = [ObjectSpec(o).properties()['radius_m'] for o in objects.values()]
        minimum_distance = law['minimum_distance_m']
        if minimum_distance <= 0 or sum(radii) > minimum_distance:
            raise ValueError('World separation limits disagree with the public apparatus domain.')
        self._probe_mass = objects['probe']['mass_kg']
        self._tools = {t['name']: t for t in self.protocol['tools']}
        self.reset()

    def reset(self):
        """Host-only new episode. No agent tool calls this method."""
        self.state = self.world.make_state({'anchor': [0., 0., 1.5], 'probe': [1.25, 0., 1.5]},
                                          {'anchor': [0., 0., 0.], 'probe': [0., 0., .8]})
        self.initial_state = self.state
        self.trial_setup = deepcopy(self.state.payload['objects'])
        self.trial_start_time_s = self.state.payload['time_s']
        self.units_used = 0
        self.finished = False
        self.events = []
        self._time = self.state.payload['time_s']

    @property
    def units_remaining(self):
        return self.protocol['budget']['measurement_units'] - self.units_used

    def observe(self):
        public = self.instance.public_dict()
        if not self.reveal_disclosures:
            public.pop('known_properties', None)
            public['instructions'] = public['instructions'].replace(
                'Calibrated masses and radii are provided. ',
                'Object properties can be measured with the intrinsic instruments. ')
        return dict(**public, apparatus=deepcopy(APPARATUS_RULES),
                    time_s=self.time, trial_start_time_s=self.trial_start_time_s,
                    last_commanded_setup=deepcopy(self.trial_setup),
                    units_used=self.units_used, units_remaining=self.units_remaining, finished=self.finished)

    def get_state(self):
        # The generic environment observation route must not bypass the sensors.
        return self.observe()

    def step(self, dt=.01):
        raise ValueError('Use the budgeted track_motion apparatus to advance this environment.')

    def execute(self, name, arguments):
        before = self.state.record_id
        result = self._execute(name, arguments)
        self._time = self.state.payload['time_s']
        # Malformed values (including NaN) are in the conversation, not persisted
        # as nonstandard JSON in the replayable, accepted-action journal.
        if result.get('error_type') != 'invalid_arguments':
            self.events.append(dict(tool=name, arguments=deepcopy(arguments), result=deepcopy(result),
                                    state_before=before, state_after=self.state.record_id,
                                    units_used=self.units_used))
        return result

    def _execute(self, name, arguments):
        if name not in self._tools:
            return dict(success=False, error='Unknown tool.', error_type='invalid_arguments')
        tool = self._tools[name]
        try:
            validate_arguments(arguments, tool['parameters'])
        except ValueError as exc:
            return dict(success=False, error=str(exc), error_type='invalid_arguments')
        if self.finished:
            return dict(success=False, error='Interaction already complete.')
        samples = arguments.get('sample_count', 1 if tool['measurements'] else 0)
        cost = tool['cost']['base_units'] + samples * tool['cost']['per_sample_units']
        cost += arguments.get('duration_s', 0) * tool['cost']['per_simulated_second_units']
        if cost > self.units_remaining:
            return dict(success=False, error='Insufficient measurement budget.', cost_units=0,
                        units_remaining=self.units_remaining)
        self.units_used += cost
        try:
            observation = self._perform(name, arguments)
        except (DomainError, ValueError, OverflowError):
            return dict(success=False, error='Trial could not be completed within apparatus limits.',
                        cost_units=cost, units_remaining=self.units_remaining)
        return dict(success=True, **observation, cost_units=cost, units_remaining=self.units_remaining)

    def _perform(self, name, args):
        if name == 'inspect':
            return {'observation': self.observe()}
        if name == 'finish':
            self.finished = True
            return {'status': 'interaction complete'}
        if name == 'configure_trial':
            candidate = self.world.make_state(
                {'anchor': [0., 0., 1.5], 'probe': args['position_m']},
                {'anchor': [0., 0., 0.], 'probe': args['velocity_m_s']}, args['start_time_s'])
            self.state = candidate
            self.trial_setup = deepcopy(candidate.payload['objects'])
            self.trial_start_time_s = candidate.payload['time_s']
            return dict(status='trial configured', time_s=self.trial_start_time_s)
        if name == 'apply_impulse':
            d = self.state.payload
            velocities = {k: v['velocity_m_s'] for k, v in d['objects'].items()}
            velocities['probe'] = [v + j/self._probe_mass for v, j in
                                   zip(velocities['probe'], args['impulse_N_s'])]
            candidate = self.world.make_state({k: v['position_m'] for k, v in d['objects'].items()},
                                              velocities, d['time_s'])
            self.state = candidate
            return dict(status='impulse applied', impulse_N_s=deepcopy(args['impulse_N_s']))
        if name == 'measure_force':
            reading = sensor_reading(self.world.forces(self.state)[args['object_id']],
                                     self._tools[name]['measurements'][0])
            return dict(object_id=args['object_id'], time_s=self.state.payload['time_s'], force=reading)
        if name == 'track_motion':
            start = self.state.payload['time_s']
            times = [start + args['duration_s'] * k / args['sample_count']
                     for k in range(1, args['sample_count'] + 1)]
            frames = self.world.trajectory(self.state, times)
            readings = [dict(time_s=f.payload['time_s'], position=sensor_reading(
                f.payload['objects'][args['object_id']]['position_m'], self._tools[name]['measurements'][0]))
                for f in frames]
            self.state = frames[-1]
            return dict(object_id=args['object_id'], samples=readings)
        raise RuntimeError('Unsupported apparatus dispatch.')
