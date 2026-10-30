from __future__ import annotations

from abc import ABC, abstractmethod

from .types import ChatResponse, Message, ToolDef


class ModelHarness(ABC):

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

    @abstractmethod
    def generate(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        **kwargs,
    ) -> ChatResponse:
        ...

    def supports_tools(self) -> bool:
        return False
