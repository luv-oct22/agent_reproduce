"""Agent-facing experiments and private, post-interaction property scoring."""
from copy import deepcopy
import json
import math

from src.envs.material_lab import MaterialLabEnv
from src.tasks.base import BaseTask
from src.tasks.registry import register_task


@register_task('identify_material')
class IdentifyMaterialTask(BaseTask):
    reset_on_failure = False

    def __init__(self, env=None, relative_tolerance=.03):
        if not isinstance(relative_tolerance, (int, float)) or not math.isfinite(relative_tolerance) or not 0 < relative_tolerance < 1:
            raise ValueError('relative_tolerance must be between zero and one.')
        super().__init__(env if env is not None else MaterialLabEnv())
        if not isinstance(self.env, MaterialLabEnv):
            raise ValueError('identify_material requires a material_lab environment.')
        self.relative_tolerance = relative_tolerance
        self.setup()

    def setup(self):
        self.env.reset()
        self._estimates = {}
        self._result = {'success': True, 'observation': self.env.observe()}

    def save_private_artifacts(self, directory):
        self.env.export_private_artifacts(directory)

    def get_prompt(self):
        return (self.env.description() + '\n'
                'Use submit_action with operation balance or displace to gather evidence; inspect reviews your notebook. '
                'On an equal-arm balance, the heavier side goes down. Reference-weight masses are calibrated and public. '
                'Unknown specimens remain rigid and do not absorb water. All experiments are independent setups, '
                'but your notebook and experiment budget persist.\n'
                'Submit estimates for every specimen using operation submit_estimates, with mass_g, volume_ml '
                'and density_kg_m3. Submission only acknowledges receipt and does not reveal correctness. '
                'Then call finish.\nInitial observation:\n' + json.dumps(self.env.observe(), indent=2))

    def get_action_space(self):
        weights = self.env.observe()['apparatus']['balance']['reference_weights']
        identifiers = list(self.env.objects)+[weight['id'] for weight in weights]
        specimen_ids = list(self.env.objects)
        return {
            'type': 'object', 'additionalProperties': False, 'required': ['operation'],
            'properties': {
                'operation': {'type': 'string', 'enum': ['inspect', 'balance', 'displace', 'submit_estimates']},
                'left_pan': {'type': 'array', 'items': {'type': 'string', 'enum': identifiers},
                             'description': 'Required for balance; IDs placed on the left pan.'},
                'right_pan': {'type': 'array', 'items': {'type': 'string', 'enum': identifiers},
                              'description': 'Required for balance; IDs placed on the right pan.'},
                'specimen_id': {'type': 'string', 'enum': specimen_ids, 'description': 'Required for displace.'},
                'estimates': {'type': 'array', 'description': 'Required for submit_estimates; one or more specimen estimates.',
                              'items': {'type': 'object', 'additionalProperties': False,
                                        'required': ['specimen_id', 'mass_g', 'volume_ml', 'density_kg_m3'],
                                        'properties': {'specimen_id': {'type': 'string', 'enum': specimen_ids},
                                                       **{key: {'type': 'number', 'exclusiveMinimum': 0}
                                                          for key in ('mass_g', 'volume_ml', 'density_kg_m3')}}}},
            },
        }

    def apply_action(self, action):
        if not isinstance(action, dict) or action.get('operation') != 'submit_estimates':
            self._result = self.env.experiment(action)
            return
        try:
            if set(action) != {'operation', 'estimates'} or not isinstance(action['estimates'], list) or not action['estimates']:
                raise ValueError('submit_estimates requires a nonempty estimates list.')
            pending = {}
            for item in action['estimates']:
                if not isinstance(item, dict) or set(item) != {'specimen_id', 'mass_g', 'volume_ml', 'density_kg_m3'}:
                    raise ValueError('Each estimate needs specimen_id, mass_g, volume_ml and density_kg_m3.')
                key = item['specimen_id']
                if not isinstance(key, str) or key not in self.env.objects or key in pending:
                    raise ValueError('Estimates must name known, unique specimen IDs.')
                for field in ('mass_g', 'volume_ml', 'density_kg_m3'):
                    value = item[field]
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                        raise ValueError('Estimated properties must be finite positive numbers.')
                pending[key] = deepcopy(item)
            self._estimates.update(pending)
            self._result = {'success': True, 'status': 'estimates_recorded', 'specimen_ids': list(pending)}
        except ValueError as exc:
            self._result = {'success': False, 'error': str(exc)}

    def evaluate(self):
        # This method is sent directly to the model by the interaction runner.
        return deepcopy(self._result)

    def get_private_evaluation(self):
        results, passed = {}, 0
        manifest = self.env.private_manifest()
        for specimen in manifest['specimens']:
            key = specimen['id']
            truth = {'mass_g': specimen['mass_kg']*1000, 'volume_ml': specimen['volume_m3']*1e6,
                     'density_kg_m3': specimen['density_kg_m3']}
            estimate = self._estimates.get(key)
            errors = {field: abs(estimate[field]-value)/value for field, value in truth.items()} if estimate else None
            correct = errors is not None and all(error <= self.relative_tolerance+1e-12 for error in errors.values())
            passed += int(correct)
            results[key] = {'estimate': deepcopy(estimate), 'ground_truth': truth,
                            'relative_errors': errors, 'correct': correct}
        return {'score': passed/len(results), 'relative_tolerance': self.relative_tolerance,
                'object_registry_id': manifest['object_registry_id'],
                'experiments_used': self.env.observe()['experiments_used'], 'specimens': results,
                'private_manifest': manifest}
