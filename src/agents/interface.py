"""Interfaces that keep agent behavior independent from physical worlds."""
from dataclasses import dataclass, field
from typing import Any, Protocol

from src.harness.types import Message, ToolDef


@dataclass(frozen=True)
class AgentProfile:
    """Model-facing policy; it contains no world constants or solver state."""

    agent_id: str
    system_prompt: str
    tool_policy: str = 'choose'
    answer_format: str = 'freeform'
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentPolicy(Protocol):
    """Build prompts and tool declarations for an interaction or evaluation."""

    @property
    def profile(self) -> AgentProfile:
        ...

    def interaction_messages(self, prompt: str) -> list[Message]:
        ...

    def interaction_tools(self, tools: list[ToolDef]) -> list[ToolDef]:
        ...

    def evaluation_messages(self, prompt: str, history: str | None = None) -> list[Message]:
        ...
