"""Baseline instruments for intrinsic, single-object properties only."""
from copy import deepcopy

from src.envs.base import BaseEnv
from src.envs.registry import register_env
from src.envs.attraction_bench import sensor_reading, validate_arguments
from src.worlds.definition import ObjectSpec, WorldInstance

ATTRIBUTE_RULES = {
    'version': 'intrinsic_attribute_bench_v1',
    'scope': 'Each measurement describes one selected object in isolation. Pair-interaction experiments are unavailable in this baseline.',
    'units': 'Mass kg; volume m^3; length m; density kg/m^3; moment of inertia kg m^2.',
    'precision': 'Scalar measurements are clipped to range and rounded to resolution; saturation is reported.',
    'semantics': {
        'mass': 'The object inertial mass used by the simulator.',
        'volume': 'The object geometric volume.',
        'geometry': 'The object sphere radius and diameter.',
        'density': 'Mass divided by geometric volume; a derived intrinsic property.',
        'inertia': 'The solid-sphere moment of inertia about a centre axis, 2/5 m r^2.',
    },
}


def _scalar(value, spec):
    reading = sensor_reading([value, 0., 0.], dict(resolution=spec['resolution'],
        range=spec['range'], unit=spec['unit']))
    return dict(value=reading['value'][0], unit=spec['unit'], resolution=spec['resolution'],
                saturated=reading['saturated'][0])


def _tools(ids):
    enum = dict(type='string', enum=sorted(ids))
    def tool(name, description, measurement, cost=1, object_required=True):
        properties = {'object_id': enum} if object_required else {}
        return dict(name=name, description=description,
                    parameters=dict(type='object', properties=properties,
                                    required=['object_id'] if object_required else [], additionalProperties=False),
                    measurement=measurement, cost_units=cost)
    return [
        tool('inspect_object', 'Read the selected object appearance and available intrinsic instruments.', None, 0),
        tool('measure_mass', 'Measure the selected object inertial mass in kilograms.',
             dict(name='mass', unit='kg', resolution=.001, range=[0., 10.])),
        tool('measure_volume', 'Measure the selected object geometric volume in cubic metres.',
             dict(name='volume', unit='m^3', resolution=1e-6, range=[0., 1.])),
        tool('measure_geometry', 'Measure the selected object sphere radius and diameter in metres.',
             dict(name='radius', unit='m', resolution=.001, range=[0., 10.])),
        tool('measure_density', 'Measure the selected object density derived from mass and geometric volume.',
             dict(name='density', unit='kg/m^3', resolution=.1, range=[0., 100000.])),
        tool('measure_inertia', 'Measure the selected object centre-axis moment of inertia.',
             dict(name='moment_of_inertia', unit='kg m^2', resolution=1e-6, range=[0., 10.])),
        tool('finish', 'End intrinsic-property measurements.', None, 0, False),
    ]


@register_env('object_attribute_bench')
class ObjectAttributeBenchEnv(BaseEnv):
    """Single-object measurements; interaction physics is deliberately absent."""
    def __init__(self, instance_path=None, *, instance=None, measurement_units=12, max_turns=8):
        super().__init__()
        if (instance is None) == (instance_path is None):
            raise ValueError('Provide exactly one saved instance path or WorldInstance.')
        self.instance = instance if instance is not None else WorldInstance.load(instance_path)
        world = self.instance.payload['world']['payload']
        self._objects = {o['payload']['id']: o['payload'] for o in world['objects']}
        if not self._objects or any(o['shape'] != 'sphere' for o in self._objects.values()):
            raise ValueError('Intrinsic attribute v1 requires spherical objects.')
        if type(measurement_units) is not int or measurement_units < 0 or type(max_turns) is not int or max_turns < 1:
            raise ValueError('Invalid attribute-bench budget.')
        self.measurement_budget, self.max_turns = measurement_units, max_turns
        self._tools = _tools(self._objects)
        self._tool_map = {t['name']: t for t in self._tools}
        self.reset()

    def reset(self):
        self.units_used, self.finished, self.events, self._time = 0, False, [], 0.

    @property
    def units_remaining(self):
        return self.measurement_budget - self.units_used

    def observe(self):
        return dict(instruments=deepcopy(self._tools), rules=deepcopy(ATTRIBUTE_RULES),
                    objects=[ObjectSpec(o).public_dict() for o in self._objects.values()],
                    units_used=self.units_used, units_remaining=self.units_remaining,
                    finished=self.finished)

    def get_state(self):
        return self.observe()

    def step(self, dt=.01):
        raise ValueError('Intrinsic measurements do not advance a physical simulation.')

    def execute(self, name, arguments):
        before = dict(units_used=self.units_used, finished=self.finished)
        if name not in self._tool_map:
            return dict(success=False, error='Unknown tool.')
        tool = self._tool_map[name]
        try:
            validate_arguments(arguments, tool['parameters'])
        except ValueError as exc:
            return dict(success=False, error=str(exc))
        if self.finished:
            return dict(success=False, error='Interaction already complete.')
        cost = tool['cost_units']
        if cost > self.units_remaining:
            return dict(success=False, error='Insufficient measurement budget.', cost_units=0,
                        units_remaining=self.units_remaining)
        self.units_used += cost
        object_id = arguments.get('object_id')
        obj = ObjectSpec(self._objects[object_id]) if object_id is not None else None
        result = self._perform(name, object_id, obj, tool)
        result.update(success=True, cost_units=cost, units_remaining=self.units_remaining)
        self.events.append(dict(tool=name, arguments=deepcopy(arguments), result=deepcopy(result),
                                state_before=before, state_after=dict(units_used=self.units_used, finished=self.finished)))
        return result

    def _perform(self, name, object_id, obj, tool):
        if name == 'finish':
            self.finished = True
            return {'status': 'interaction complete'}
        if name == 'inspect_object':
            return dict(object_id=object_id, object=deepcopy(obj.public_dict()),
                        available_intrinsic_measurements=[t['name'] for t in self._tools if t['measurement']])
        properties, spec = obj.properties(), tool['measurement']
        if name == 'measure_mass':
            return dict(object_id=object_id, measurement=_scalar(properties['mass_kg'], spec))
        if name == 'measure_volume':
            return dict(object_id=object_id, measurement=_scalar(properties['volume_m3'], spec))
        if name == 'measure_geometry':
            return dict(object_id=object_id, radius=_scalar(properties['radius_m'], spec),
                        diameter=_scalar(2*properties['radius_m'], spec), shape=obj.payload['shape'])
        if name == 'measure_density':
            return dict(object_id=object_id, measurement=_scalar(properties['density_kg_m3'], spec))
        if name == 'measure_inertia':
            return dict(object_id=object_id, measurement=_scalar(.4*properties['mass_kg']*properties['radius_m']**2, spec),
                        model='solid_sphere_centre_axis')
        raise RuntimeError('Unsupported intrinsic instrument.')
