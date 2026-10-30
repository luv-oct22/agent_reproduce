"""Baseline object characterization; no world-law measurements are available."""
import json
from pathlib import Path

from src.envs.object_attribute_bench import ATTRIBUTE_RULES, ObjectAttributeBenchEnv
from src.harness.types import ToolDef
from src.tasks.base import BaseTask
from src.tasks.registry import register_task


def _save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


@register_task('characterize_objects')
class CharacterizeObjectsTask(BaseTask):
    reset_on_failure = False

    def __init__(self, env):
        if not isinstance(env, ObjectAttributeBenchEnv):
            raise ValueError('characterize_objects requires object_attribute_bench.')
        super().__init__(env)
        self._directory = None

    def setup(self):
        self.env.reset()
        self._directory = None

    def get_prompt(self):
        return json.dumps(self.env.observe(), indent=2, allow_nan=False)

    def get_native_tools(self):
        return [ToolDef(name=t['name'], description=t['description'], parameters=t['parameters'])
                for t in self.env._tools]

    def get_turn_limit(self):
        return self.env.max_turns

    def execute_tool(self, name, arguments):
        result = self.env.execute(name, arguments)
        self._checkpoint()
        return result

    def save_private_artifacts(self, directory):
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)
        self.env.instance.save(self._directory/'world_instance.json')
        _save(self._directory/'attribute_rules.json', ATTRIBUTE_RULES)
        _save(self._directory/'public_initial_observation.json', self.env.observe())
        self._checkpoint()

    def _checkpoint(self):
        if self._directory:
            _save(self._directory/'private_episode.json', dict(visibility='host_only',
                instance_id=self.env.instance.record_id, units_used=self.env.units_used,
                events=self.env.events, finished=self.env.finished))

    def get_action_space(self):
        raise NotImplementedError('This task exposes named intrinsic-property tools.')

    def apply_action(self, action):
        raise NotImplementedError('Use execute_tool with a named tool.')

    def evaluate(self):
        return {'success': True, 'status': 'Object characterization complete; world-law evaluation is separate.'}
