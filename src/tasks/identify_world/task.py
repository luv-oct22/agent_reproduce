"""Infer specimen properties and a shared world parameter from measurements."""
import math

from src.envs.world_lab import WorldLabEnv
from src.tasks.identify_material import IdentifyMaterialTask
from src.tasks.registry import register_task


@register_task('identify_world')
class IdentifyWorldTask(IdentifyMaterialTask):
    def __init__(self, env=None, relative_tolerance=.03):
        env = env if env is not None else WorldLabEnv()
        if not isinstance(env, WorldLabEnv):
            raise ValueError('identify_world requires world_lab.')
        super().__init__(env, relative_tolerance)

    def setup(self):
        super().setup()
        self._gravity_estimate = None

    def get_prompt(self):
        return super().get_prompt().replace(
            'Then call finish.',
            'Also use operation drop with specimen_id and distance_m to investigate gravity. '
            'Submit your inferred gravitational acceleration with operation submit_world_estimate '
            'and gravity_m_s2 (in m/s²). This submission only acknowledges receipt. Then call finish.')

    def get_action_space(self):
        schema = super().get_action_space()
        properties = schema['properties']
        properties['operation']['enum'] += ['drop', 'submit_world_estimate']
        properties['specimen_id']['description'] = 'Required for displace and drop.'
        properties['distance_m'] = {'type': 'number', 'minimum': .05, 'maximum': self.env.drop_max_distance_m,
                                     'description': 'Required for drop: calibrated travel distance in metres.'}
        properties['gravity_m_s2'] = {'type': 'number', 'exclusiveMinimum': 0,
                                     'description': 'Required for submit_world_estimate: inferred downward acceleration.'}
        return schema

    def apply_action(self, action):
        if not isinstance(action, dict) or action.get('operation') != 'submit_world_estimate':
            return super().apply_action(action)
        value = action.get('gravity_m_s2')
        if (set(action) != {'operation', 'gravity_m_s2'} or isinstance(value, bool)
                or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0):
            self._result = {'success': False, 'error': 'submit_world_estimate needs a finite positive gravity_m_s2.'}
            return
        self._gravity_estimate = float(value)
        self._result = {'success': True, 'status': 'world_estimate_recorded'}

    def get_private_evaluation(self):
        result = super().get_private_evaluation()
        truth = self.env.private_manifest()['world']['gravity_m_s2']
        error = abs(self._gravity_estimate-truth)/truth if self._gravity_estimate is not None else None
        correct = error is not None and error <= self.relative_tolerance
        result.update(material_score=result['score'], world_id=self.env.private_manifest()['world_id'],
                      world_score=float(correct),
                      gravity={'estimate_m_s2': self._gravity_estimate, 'ground_truth_m_s2': truth,
                               'relative_error': error, 'correct': correct})
        result['score'] = (result['material_score']+result['world_score'])/2
        return result
