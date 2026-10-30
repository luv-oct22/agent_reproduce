from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.envs.base import BaseEnv


class BaseTask(ABC):

    reset_on_failure = True

    def get_native_tools(self):
        """Optional named apparatus tools; None preserves the submit_action API."""
        return None

    def get_turn_limit(self) -> int | None:
        return None

    def execute_tool(self, name: str, arguments: dict) -> dict:
        raise NotImplementedError('This task uses submit_action.')

    def save_private_artifacts(self, directory) -> None:
        """Persist host-only episode inputs before the first model request."""
        pass

    def get_private_evaluation(self) -> dict[str, Any] | None:
        """Optional host-only final score, never returned as an agent tool result."""
        return None

    def __init__(self, env: BaseEnv):
        self._env = env

    @property
    def env(self) -> BaseEnv:
        return self._env

    @abstractmethod
    def setup(self) -> None:
        ...

    @abstractmethod
    def get_prompt(self) -> str:
        ...

    @abstractmethod
    def get_action_space(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def apply_action(self, action: dict[str, Any]) -> None:
        ...

    @abstractmethod
    def evaluate(self) -> dict[str, Any]:
        ...
