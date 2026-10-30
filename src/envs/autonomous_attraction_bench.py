"""Combined autonomous bench: intrinsic attributes plus law experiments."""
from copy import deepcopy

from src.envs.attraction_bench import AttractionBenchEnv, sensor_reading, validate_arguments
from src.envs.object_attribute_bench import ObjectAttributeBenchEnv
from src.envs.registry import register_env


@register_env('autonomous_attraction_bench')
class AutonomousAttractionBenchEnv(AttractionBenchEnv):
    """One shared budget; the agent chooses whether and when to measure attributes."""
    def __init__(self, instance_path=None, *, instance=None, equation=None):
        super().__init__(instance_path, instance=instance, reveal_disclosures=False, equation=equation)
        self.baseline_world = AttractionBenchEnv(instance=self.instance, reveal_disclosures=False).world
        self._baseline_tool = dict(
            name='measure_baseline_force',
            description='Run a reference force measurement under the standard baseline law for this world group.',
            parameters=dict(type='object', properties={
                'position_m': {'type': 'array', 'items': {'type': 'number'}, 'minItems': 3, 'maxItems': 3},
                'object_id': {'type': 'string', 'enum': ['probe']},
            }, required=['object_id', 'position_m'], additionalProperties=False),
            measurements=[dict(name='force', unit='N', resolution=.001, range=[-10., 10.])],
            sample_definition='One baseline force vector is one sample.',
            cost=dict(base_units=1, per_sample_units=0, per_simulated_second_units=0),
        )
        self.attributes = ObjectAttributeBenchEnv(instance=self.instance,
                                                   measurement_units=self.protocol['budget']['measurement_units'],
                                                   max_turns=self.protocol['budget']['max_turns'] or 8)

    def reset(self):
        super().reset()
        if hasattr(self, 'attributes'):
            self.attributes.reset()

    def native_tool_specs(self):
        return list(self._tools.values()) + [self._baseline_tool] + [t for t in self.attributes._tools if t['name'] != 'finish']

    def observe(self):
        public = super().observe()
        public['tools'] = deepcopy(self.native_tool_specs())
        public['intrinsic_stage'] = 'These tools measure one object in isolation. They do not measure pair forces or motion.'
        return public

    def execute(self, name, arguments):
        if name == 'measure_baseline_force':
            try:
                validate_arguments(arguments, self._baseline_tool['parameters'])
            except ValueError as exc:
                return dict(success=False, error=str(exc), error_type='invalid_arguments')
            if self.finished:
                return dict(success=False, error='Interaction already complete.')
            if self.units_remaining < 1:
                return dict(success=False, error='Insufficient measurement budget.', cost_units=0,
                            units_remaining=self.units_remaining)
            self.units_used += 1
            current = self.state.payload
            anchor = current['objects']['anchor']['position_m']
            try:
                state = self.baseline_world.make_state(
                    {'anchor': anchor, 'probe': arguments['position_m']},
                    {'anchor': [0., 0., 0.], 'probe': [0., 0., 0.]}, current['time_s'])
                reading = sensor_reading(self.baseline_world.forces(state)['probe'], self._baseline_tool['measurements'][0])
            except (ValueError, OverflowError):
                return dict(success=False, error='Baseline trial could not be completed within apparatus limits.',
                            cost_units=1, units_remaining=self.units_remaining)
            result = dict(success=True, object_id='probe', baseline=True, force=reading,
                          cost_units=1, units_remaining=self.units_remaining)
            self.events.append(dict(tool=name, arguments=deepcopy(arguments), result=deepcopy(result),
                                    state_before=self.state.record_id, state_after=self.state.record_id,
                                    units_used=self.units_used))
            return result
        if name not in self.attributes._tool_map or name in self._tools:
            result = super().execute(name, arguments)
            self.attributes.units_used = self.units_used
            self.attributes.finished = self.finished
            return result
        # Mirror the shared budget into the attribute apparatus, then copy the
        # resulting accounting back. It never receives a partner or world law.
        self.attributes.units_used = self.units_used
        self.attributes.finished = self.finished
        before = self.state.record_id
        result = self.attributes.execute(name, arguments)
        self.units_used = self.attributes.units_used
        self.finished = self.attributes.finished
        if result.get('success'):
            self.events.append(dict(tool=name, arguments=deepcopy(arguments), result=deepcopy(result),
                                    state_before=before, state_after=self.state.record_id,
                                    units_used=self.units_used))
        return result
