"""Serializable contracts shared by interaction and evaluation runners."""
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass(frozen=True)
class HarnessProfile:
    harness_id: str
    provider: str
    model: str
    timeout_seconds: float = 600.0
    connect_timeout_seconds: float = 60.0
    max_retries: int = 3
    multimodal: bool = False


@dataclass(frozen=True)
class RunContext:
    world_instance: str
    question_file: str
    agent_id: str
    harness_id: str
    renderer_id: str | None = None
    output_dir: str | None = None


@dataclass
class InteractionArtifact:
    world_id: str
    question_id: str
    agent_id: str
    harness_id: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finished: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvaluationArtifact:
    world_id: str
    question_id: str
    interaction_record: str
    agent_id: str
    harness_id: str
    answer: Any = None
    expected: Any = None
    correct: bool | None = None
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
