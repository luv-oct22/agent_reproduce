from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional, Union

MessageContent = Union[str, list[dict[str, Any]], None]


@dataclass
class ToolCall:
    id: str
    function_name: str
    arguments: str  # JSON string


@dataclass
class ToolDef:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema


@dataclass
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: MessageContent = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: Optional[str] = None


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class ChatResponse:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: Optional[Usage] = None
