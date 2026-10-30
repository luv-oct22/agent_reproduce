"""Discover gravity and constant contact restitution using public measurements."""
import json
import math
from pathlib import Path

from src.envs.bounce_lab import BounceLabEnv
from src.tasks.identify_world import IdentifyWorldTask
from src.tasks.registry import register_task


@register_task('identify_bounce')
class IdentifyBounceTask(IdentifyWorldTask):
    def __init__(self, env=None, relative_tolerance=.03, restitution_absolute_tolerance=.03):
        env = env if env is not None else BounceLabEnv()
        if not isinstance(env, BounceLabEnv):
            raise ValueError('identify_bounce requires bounce_lab.')
        if (isinstance(restitution_absolute_tolerance, bool) or not isinstance(restitution_absolute_tolerance, (int, float))
                or not math.isfinite(restitution_absolute_tolerance) or not 0 < restitution_absolute_tolerance < 1):
            raise ValueError('Restitution tolerance must be finite and between zero and one.')
        self.restitution_absolute_tolerance = restitution_absolute_tolerance
        super().__init__(env, relative_tolerance)

    def setup(self):
        super().setup()
        self._contact_estimates = {}

    def get_prompt(self):
        return (self.env.description()+'\nUse submit_action to perform experiments. '
                'Operation drop takes specimen_id and distance_m. Operation bounce takes specimen_id, '
                'surface_id and release_height_m. Operation inspect reviews the notebook. '
                'Only valid measurements consume the shared experiment budget. '
                'Submit gravity using submit_world_estimate with gravity_m_s2. '
                'Submit all specimen–surface restitution estimates using submit_contact_estimates with '
                'an estimates list; each item has specimen_id, surface_id and restitution. '
                'Submissions only acknowledge receipt and never disclose correctness. '
                'Mass, volume and density estimates are optional and are not part of this task score. '
                'Explain your findings and the measurements supporting them, then call finish.\n'
                'Initial observation:\n'+json.dumps(self.env.observe(), indent=2))

    def get_action_space(self):
        schema = super().get_action_space()
        p = schema['properties']
        p['operation']['enum'] += ['bounce', 'submit_contact_estimates']
        p['specimen_id']['description'] = 'Required for displace, drop and bounce.'
        p['surface_id'] = {'type': 'string', 'enum': [self.env.observe()['apparatus']['bounce_tower']['surface_id']],
                           'description': 'Required for bounce.'}
        p['release_height_m'] = {'type': 'number', 'minimum': .05, 'maximum': self.env.drop_max_distance_m,
                                'description': 'Required for bounce: initial bottom-of-sphere clearance above the surface.'}
        material_items = p['estimates']['items']
        p['estimates'] = {'type': 'array', 'minItems': 1,
                         'description': 'For submit_contact_estimates use contact items; for optional submit_estimates use material items.',
                         'items': {'anyOf': [material_items, {
                             'type': 'object', 'additionalProperties': False,
                             'required': ['specimen_id', 'surface_id', 'restitution'],
                             'properties': {'specimen_id': {'type': 'string', 'enum': list(self.env.objects)},
                                            'surface_id': {'type': 'string', 'enum': p['surface_id']['enum']},
                                            'restitution': {'type': 'number', 'minimum': 0, 'maximum': 1}}}]}}
        return schema

    def apply_action(self, action):
        if not isinstance(action, dict) or action.get('operation') != 'submit_contact_estimates':
            return super().apply_action(action)
        try:
            if set(action) != {'operation', 'estimates'} or not isinstance(action['estimates'], list) or not action['estimates']:
                raise ValueError('Provide a nonempty contact estimates list.')
            pending = {}
            surface = self.env.observe()['apparatus']['bounce_tower']['surface_id']
            for item in action['estimates']:
                if not isinstance(item, dict) or set(item) != {'specimen_id', 'surface_id', 'restitution'}:
                    raise ValueError('Each estimate needs specimen_id, surface_id and restitution.')
                key, value = item['specimen_id'], item['restitution']
                if not isinstance(key, str) or key not in self.env.objects or key in pending or item['surface_id'] != surface:
                    raise ValueError('Estimates must name known, unique specimen–surface pairs.')
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                    raise ValueError('Restitution must be a finite number in [0, 1].')
                pending[key] = float(value)
            self._contact_estimates.update(pending)
            self._result = {'success': True, 'status': 'contact_estimates_recorded', 'specimen_ids': list(pending)}
        except ValueError as exc:
            self._result = {'success': False, 'error': str(exc)}

    def get_private_evaluation(self):
        result = super().get_private_evaluation()
        registry = self.env.private_manifest()['contact_registry']
        pairs = []
        for item in registry['pairs']:
            estimate = self._contact_estimates.get(item['specimen_id'])
            error = abs(estimate-item['restitution']) if estimate is not None else None
            pairs.append({'specimen_id': item['specimen_id'], 'surface_id': item['surface_id'],
                          'estimate': estimate, 'ground_truth': item['restitution'], 'absolute_error': error,
                          'correct': error is not None and error <= self.restitution_absolute_tolerance+1e-12})
        contact_score = sum(pair['correct'] for pair in pairs)/len(pairs)
        result.update(gravity_score=result['world_score'], contact_score=contact_score, contacts=pairs,
                      contact_registry_id=registry['registry_id'],
                      restitution_absolute_tolerance=self.restitution_absolute_tolerance,
                      score=(result['world_score']+contact_score)/2,
                      score_definition='mean(gravity_accuracy, fraction_of_correct_contact_pairs); material_score is diagnostic only')
        return result

    def save_private_artifacts(self, directory):
        super().save_private_artifacts(directory)
        (Path(directory)/'task_parameters.md').write_text('# Bounce task scoring (host-only)\n\n'
            f'Gravity relative tolerance: {self.relative_tolerance:g}. '
            f'Restitution absolute tolerance: {self.restitution_absolute_tolerance:g}.\n\n'
            'Score is the mean of gravity accuracy and the fraction of correct specimen–surface coefficients. '
            'Material estimates are optional and do not affect this score.\n')
