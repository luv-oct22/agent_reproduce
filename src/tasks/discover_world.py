"""Autonomous experiment collection; prediction scoring is a separate stage."""
import json
from pathlib import Path

from src.envs.attraction_bench import APPARATUS_RULES, AttractionBenchEnv
from src.harness.types import ToolDef
from src.tasks.base import BaseTask
from src.tasks.registry import register_task


def save_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


@register_task('discover_world')
class DiscoverWorldTask(BaseTask):
    reset_on_failure = False

    def __init__(self, env):
        if not isinstance(env, AttractionBenchEnv):
            raise ValueError('discover_world currently requires the attraction bench.')
        super().__init__(env)
        self._directory = None

    def setup(self):
        self.env.reset()
        self._directory = None

    def get_prompt(self):
        return json.dumps(self.env.observe(), indent=2, allow_nan=False)

    def get_native_tools(self):
        specs = self.env.native_tool_specs() if hasattr(self.env, 'native_tool_specs') else self.env.protocol['tools']
        return [ToolDef(name=t['name'], description=t['description'], parameters=t['parameters'])
                for t in specs]

    def get_turn_limit(self):
        return self.env.protocol['budget']['max_turns']

    def execute_tool(self, name, arguments):
        result = self.env.execute(name, arguments)
        self._checkpoint()
        return result

    def save_private_artifacts(self, directory):
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)
        self.env.instance.save(self._directory/'world_instance.json')
        self.env.initial_state.save(self._directory/'initial_state.json')
        save_json(self._directory/'apparatus.json', APPARATUS_RULES)
        save_json(self._directory/'public_initial_observation.json', self.env.observe())
        self._checkpoint()

    def _checkpoint(self):
        if self._directory is not None:
            save_json(self._directory/'private_episode.json', dict(visibility='host_only',
                instance_id=self.env.instance.record_id, apparatus_version=APPARATUS_RULES['version'],
                state=self.env.state.to_dict(), units_used=self.env.units_used, finished=self.env.finished,
                events=self.env.events))

    def get_action_space(self):
        raise NotImplementedError('This task exposes named apparatus tools.')

    def apply_action(self, action):
        raise NotImplementedError('Use execute_tool with a named apparatus tool.')

    def evaluate(self):
        # No answer key or score enters the experimental interaction.
        return {'success': True, 'status': 'Prediction evaluation is a separate stage.'}
