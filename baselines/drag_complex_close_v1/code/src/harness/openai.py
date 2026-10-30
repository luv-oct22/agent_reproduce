from __future__ import annotations

from typing import Any
import math
import os
import time

import httpx
from openai import OpenAI, APIConnectionError, APIStatusError

from .types import ChatResponse, Message, ToolCall, ToolDef, Usage
from .base import ModelHarness


def request_timeout_settings() -> dict[str, float]:
    """Seconds per network operation; these are not an overall request deadline."""
    settings = {}
    for key, variable, default in (
        ('timeout_seconds', 'OPENAI_TIMEOUT', '600'),
        ('connect_timeout_seconds', 'OPENAI_CONNECT_TIMEOUT', '60'),
    ):
        try:
            value = float(os.environ.get(variable, default))
        except ValueError:
            raise ValueError(f'{variable} must be a finite positive number of seconds.') from None
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f'{variable} must be a finite positive number of seconds.')
        settings[key] = value
    return settings


def request_retry_settings() -> dict[str, int | float]:
    try:
        retries = int(os.environ.get('OPENAI_MAX_RETRIES', '3'))
    except ValueError:
        raise ValueError('OPENAI_MAX_RETRIES must be a nonnegative integer.') from None
    if retries < 0:
        raise ValueError('OPENAI_MAX_RETRIES must be a nonnegative integer.')
    return {'max_retries': retries, 'initial_delay_seconds': 5, 'max_delay_seconds': 30}


def retryable_error(error) -> bool:
    if isinstance(error, APIConnectionError):
        return True  # Includes SDK connection and read timeout exceptions.
    if isinstance(error, APIStatusError):
        if error.status_code in (408, 409, 429) or error.status_code >= 500:
            return True
        # This provider reports a temporary image-backend failure as HTTP 400.
        # Do not retry unrelated validation errors, unsupported models, etc.
        return error.status_code == 400 and 'download multimodal file timed out' in str(error.body).lower()
    return False


class OpenAIHarness(ModelHarness):

    def __init__(self, model: str = "gpt-4o", api_key: str | None = None):
        self._model = model
        settings = request_timeout_settings()
        self._retry_settings = request_retry_settings()
        self._client = OpenAI(
            api_key=api_key,
            timeout=httpx.Timeout(settings['timeout_seconds'], connect=settings['connect_timeout_seconds']),
            max_retries=0,  # One shared retry budget, including provider-specific HTTP 400 timeouts.
        )

    @property
    def model_name(self) -> str:
        return self._model

    def supports_tools(self) -> bool:
        return True

    def generate(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        oai_messages = [self._to_oai_message(m) for m in messages]

        call_kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": oai_messages,
            **kwargs,
        }
        if tools:
            call_kwargs["tools"] = [self._to_oai_tool(t) for t in tools]

        delay = self._retry_settings['initial_delay_seconds']
        for attempt in range(self._retry_settings['max_retries']+1):
            try:
                resp = self._client.chat.completions.create(**call_kwargs)
                break
            except (APIConnectionError, APIStatusError) as exc:
                if not retryable_error(exc) or attempt == self._retry_settings['max_retries']:
                    raise
                print(f"API retry {attempt+1}/{self._retry_settings['max_retries']} "
                      f"in {delay}s ({type(exc).__name__})", flush=True)
                time.sleep(delay)
                delay = min(delay*2, self._retry_settings['max_delay_seconds'])
        choice = resp.choices[0]

        tool_calls: list[ToolCall] = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        function_name=tc.function.name,
                        arguments=tc.function.arguments,
                    )
                )

        usage = None
        if resp.usage:
            usage = Usage(
                prompt_tokens=resp.usage.prompt_tokens,
                completion_tokens=resp.usage.completion_tokens,
            )

        return ChatResponse(
            content=choice.message.content or "",
            tool_calls=tool_calls,
            usage=usage,
        )

    @staticmethod
    def _to_oai_message(msg: Message) -> dict[str, Any]:
        if isinstance(msg.content, list):
            content = msg.content
        elif msg.content is not None:
            content = msg.content
        else:
            content = ""

        oai: dict[str, Any] = {"role": msg.role, "content": content}
        if msg.tool_calls:
            oai["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function_name,
                        "arguments": tc.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        if msg.tool_call_id is not None:
            oai["tool_call_id"] = msg.tool_call_id
        return oai

    @staticmethod
    def _to_oai_tool(tool: ToolDef) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
