"""Question-bound attraction environment for hidden rule_2 coefficient fields."""
import json
from pathlib import Path

from src.envs.autonomous_attraction_bench import AutonomousAttractionBenchEnv
from src.envs.registry import register_env


@register_env('rule2_attraction_bench')
class Rule2AttractionBenchEnv(AutonomousAttractionBenchEnv):
    def __init__(self, instance_path, question_path=None, *, question=None):
        if (question_path is None) == (question is None):
            raise ValueError('Provide exactly one question_path or question.')
        question = question if question is not None else json.loads(Path(question_path).read_text())
        function = question.get('hidden_force_function')
        if not isinstance(function, dict):
            raise ValueError('Rule 2 question must provide hidden_force_function.')
        self.question = question
        super().__init__(instance_path=instance_path, equation=function)

    def reset(self):
        super().reset()
        scene = self.question['scene_state']
        self.state = self.world.make_state(
            {'anchor': scene['anchor_center_m'], 'probe': scene['probe_center_m']},
            {'anchor': [0., 0., 0.], 'probe': scene['probe_initial_velocity_m_s']},
            scene['start_time_s'])
        self.initial_state = self.state
        self.trial_setup = {name: dict(value) for name, value in self.state.payload['objects'].items()}
        self.trial_start_time_s = scene['start_time_s']
        self._time = scene['start_time_s']
