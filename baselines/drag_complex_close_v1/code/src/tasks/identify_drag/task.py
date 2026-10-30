"""Public profile submissions, private prediction-based scoring."""
from copy import deepcopy
import json
from pathlib import Path

from src.envs.drag_lab import DragLabEnv
from src.envs.drag_lab.scene import PROFILE_BOUNDS, validate_profile
from src.tasks.base import BaseTask
from src.tasks.registry import register_task
from src.worlds.layered_drag import LayeredDragWorld
from src.worlds.height_drag import HeightDragWorld, validate_samples


@register_task('identify_drag')
class IdentifyDragTask(BaseTask):
    reset_on_failure = False

    def __init__(self, env=None):
        super().__init__(env if env is not None else DragLabEnv())
        if not isinstance(self.env, DragLabEnv):
            raise ValueError('identify_drag requires drag_lab.')
        self.setup()

    def setup(self):
        self.env.reset()
        self._estimate = None
        self._result = dict(success=True, observation=self.env.observe())

    def get_prompt(self):
        submission = ('Submit your inferred profile with operation submit_drag_estimate and boundary_height_m, '
                      'lower_drag_kg_s, upper_drag_kg_s. Boundary height is centre height above the floor, ')
        if isinstance(self.env._world, HeightDragWorld):
            submission = ('Submit your approximate function with operation submit_drag_estimate, heights_m '
                          'and coefficients_kg_s arrays, using the public interpolation rule. '
                          'The samples are your chosen approximation, not a request for the private grid. '
                          'Function heights refer to sphere centres above the floor, ')
        return (self.env.description()+'\nUse submit_action: inspect, drop, or bounce. '
                'Drop and bounce require specimen_id and release_height_m; bounce also requires surface_id. '
                'Valid measurements share a budget; invalid actions, inspection and submissions are free. '
                +submission+
                'while release and rebound heights are bottom clearances. '
                'Your profile will be assessed by how well it predicts impact times and rebound heights '
                'at additional release heights; an exact parameter match is not required. '
                'Submissions only acknowledge receipt and provide no correctness feedback. '
                'Explain the experiments supporting your conclusion, then call finish.\nInitial observation:\n'
                +json.dumps(self.env.observe(), indent=2))

    def get_action_space(self):
        schema = {'type': 'object', 'additionalProperties': False, 'required': ['operation'],
                'properties': {
                    'operation': {'type': 'string', 'enum': ['inspect', 'drop', 'bounce', 'submit_drag_estimate']},
                    'specimen_id': {'type': 'string', 'enum': ['sample_A']},
                    'surface_id': {'type': 'string', 'enum': ['surface_1']},
                    'release_height_m': {'type': 'number', 'minimum': .05, 'maximum': 2.5,
                                         'description': 'Initial bottom-of-sphere clearance above floor.'},
                    **{key: {'type': 'number', 'minimum': bounds[0], 'maximum': bounds[1]}
                       for key, bounds in PROFILE_BOUNDS.items()}}}
        if isinstance(self.env._world, HeightDragWorld):
            for key in PROFILE_BOUNDS:
                del schema['properties'][key]
            for key, upper in (('heights_m', 3), ('coefficients_kg_s', .5)):
                schema['properties'][key] = {'type': 'array', 'minItems': 2, 'maxItems': 65,
                                            'items': {'type': 'number', 'minimum': 0, 'maximum': upper}}
        return schema

    def apply_action(self, action):
        if not isinstance(action, dict) or action.get('operation') != 'submit_drag_estimate':
            self._result = self.env.experiment(action)
            return
        estimate = {k: v for k, v in action.items() if k != 'operation'}
        try:
            if isinstance(self.env._world, HeightDragWorld):
                if set(estimate) != {'heights_m', 'coefficients_kg_s'}:
                    raise ValueError('Provide heights_m and coefficients_kg_s arrays.')
                validate_samples(estimate['heights_m'], estimate['coefficients_kg_s'])
            else:
                validate_profile(estimate)
        except ValueError as exc:
            self._result = dict(success=False, error=str(exc))
            return
        self._estimate = deepcopy(estimate)
        self._result = {'success': True, 'status': 'drag_estimate_recorded'}

    def evaluate(self):
        return deepcopy(self._result)

    def get_private_evaluation(self):
        truth = self.env._world
        calibration = self.env.observe()['calibration']
        ball = self.env.observe()['specimens'][0]
        args = (ball['mass_kg'], ball['radius_m'], calibration['restitution'])
        world_type = HeightDragWorld if isinstance(truth, HeightDragWorld) else LayeredDragWorld
        predicted = world_type(gravity_m_s2=calibration['gravity_m_s2'], **self._estimate) if self._estimate else None
        observed_heights = {row['release_height_m'] for row in self.env.observe()['notebook']}
        # Deterministic host-only probe heights; exclude measured settings.
        heights = [.12, .4, .7, 1.0, 1.3, 1.7, 2.2, 2.45]
        for i, height in enumerate(heights):
            while any(abs(height-seen) < .002 for seen in observed_heights):
                height += .007
                if height > 2.5:
                    height = .051
            heights[i] = height
        rows = []
        for height in heights:
            target = truth.drop_readings(height, *args)
            guess = predicted.drop_readings(height, *args) if predicted else None
            errors = {k: abs(guess[k]-target[k]) for k in target} if guess else None
            rows.append({'release_height_m': height, 'expected': target, 'predicted': guess,
                         'absolute_errors': errors, 'correct': errors is not None
                         and errors['time_to_first_impact_s'] <= .005
                         and errors['first_rebound_height_m'] <= .005})
        if isinstance(truth, HeightDragWorld):
            ground_truth = {'heights_m': list(truth.heights_m), 'coefficients_kg_s': list(truth.coefficients_kg_s)}
            parameter_errors = None  # Different sampling grids are permitted; compare predictions.
        else:
            ground_truth = {k: getattr(truth, k) for k in PROFILE_BOUNDS}
            parameter_errors = {k: abs(self._estimate[k]-getattr(truth, k)) for k in PROFILE_BOUNDS} if self._estimate else None
        return {'score': sum(row['correct'] for row in rows)/len(rows),
                'score_definition': 'fraction of unmeasured drops predicted within 0.005 s AND 0.005 m',
                'estimate': deepcopy(self._estimate), 'ground_truth': ground_truth,
                'parameter_absolute_errors': parameter_errors, 'prediction_checks': rows,
                'experiments_used': len(self.env.observe()['notebook']),
                'world_id': truth.world_id, 'object_registry_id': self.env._registry.registry_id,
                'private_manifest': self.env.private_manifest()}

    def save_private_artifacts(self, directory):
        self.env.export_private_artifacts(directory)
        (Path(directory)/'task_parameters.md').write_text('# Drag task scoring (host-only)\n\n'
            'Eight unmeasured release heights; both impact-time error <=0.005 s and rebound-height error <=0.005 m. '
            'Parameter errors are diagnostic; they do not determine the main score. '
            'Never append this private score or probe outcomes to the model conversation.\n')
