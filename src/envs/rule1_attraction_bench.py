"""Question-bound parametric attraction environment for Rule 1 variants."""
import json
from pathlib import Path

from src.envs.autonomous_attraction_bench import AutonomousAttractionBenchEnv
from src.envs.registry import register_env


@register_env('rule1_attraction_bench')
class Rule1AttractionBenchEnv(AutonomousAttractionBenchEnv):
    """Load fixed group constants from a world and hidden equation values from a question."""

    def __init__(self, instance_path, question_path=None, *, question=None):
        if (question_path is None) == (question is None):
            raise ValueError('Provide exactly one question_path or question.')
        question = question if question is not None else json.loads(Path(question_path).read_text())
        equation = question.get('hidden_equation_parameters')
        if not isinstance(equation, dict):
            raise ValueError('Rule 1 question must provide hidden_equation_parameters.')
        # AttractionBenchEnv initializes by calling reset(), so bind the
        # question before entering the parent constructor.
        self.question = question
        super().__init__(instance_path=instance_path, equation=equation)

    def reset(self):
        super().reset()
        scene = self.question['scene_state']
        anchor = scene['anchor_center_m']
        probe = scene['probe_center_m']
        velocity = scene['probe_initial_velocity_m_s']
        self.state = self.world.make_state(
            {'anchor': anchor, 'probe': probe},
            {'anchor': [0., 0., 0.], 'probe': velocity},
            scene['start_time_s'])
        self.initial_state = self.state
        self.trial_setup = {name: dict(value) for name, value in self.state.payload['objects'].items()}
        self.trial_start_time_s = scene['start_time_s']
        self._time = scene['start_time_s']
