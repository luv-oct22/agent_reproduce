from __future__ import annotations

from typing import Any
import json
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


# Models whose tool calling is only served by /v1/responses. On this provider,
# /v1/chat/completions rejects function tools for them with HTTP 400
# ("Function tools with reasoning_effort are not supported ...").
RESPONSES_API_MODELS = {'gpt-6.1-sol', 'gpt-5.6-sol'}


def api_mode_for(model: str) -> str:
    """'chat' or 'responses'. OPENAI_API_MODE=chat|responses overrides the per-model default."""
    mode = os.environ.get('OPENAI_API_MODE', 'auto').strip().lower()
    if mode in ('chat', 'responses'):
        return mode
    if mode != 'auto':
        raise ValueError("OPENAI_API_MODE must be 'auto', 'chat' or 'responses'.")
    return 'responses' if model in RESPONSES_API_MODELS else 'chat'


class OpenAIHarness(ModelHarness):

    def __init__(self, model: str = "gpt-4o", api_key: str | None = None):
        self._model = model
        self._api_mode = api_mode_for(model)
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

    @property
    def api_mode(self) -> str:
        return self._api_mode

    def supports_tools(self) -> bool:
        return True

    def _call_with_retries(self, request):
        delay = self._retry_settings['initial_delay_seconds']
        for attempt in range(self._retry_settings['max_retries']+1):
            try:
                return request()
            except (APIConnectionError, APIStatusError) as exc:
                if not retryable_error(exc) or attempt == self._retry_settings['max_retries']:
                    raise
                print(f"API retry {attempt+1}/{self._retry_settings['max_retries']} "
                      f"in {delay}s ({type(exc).__name__})", flush=True)
                time.sleep(delay)
                delay = min(delay*2, self._retry_settings['max_delay_seconds'])

    def generate(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        if self._api_mode == 'responses':
            return self._generate_responses(messages, tools, **kwargs)
        return self._generate_chat(messages, tools, **kwargs)

    def _generate_chat(self, messages, tools, **kwargs) -> ChatResponse:
        oai_messages = [self._to_oai_message(m) for m in messages]

        call_kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": oai_messages,
            **kwargs,
        }
        if tools:
            call_kwargs["tools"] = [self._to_oai_tool(t) for t in tools]

        resp = self._call_with_retries(lambda: self._client.chat.completions.create(**call_kwargs))
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

    # Generation kwargs the responses API does not accept for these models.
    # Verified against the provider: 'temperature' -> HTTP 400 unsupported
    # parameter; 'seed' does not exist on /v1/responses.
    RESPONSES_DROPPED_KWARGS = ('temperature', 'seed')

    @classmethod
    def responses_call_kwargs(cls, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Translate chat-completions generation kwargs for /v1/responses."""
        out = {k: v for k, v in kwargs.items() if k not in cls.RESPONSES_DROPPED_KWARGS}
        if 'max_completion_tokens' in out:
            out['max_output_tokens'] = out.pop('max_completion_tokens')
        return out

    def _generate_responses(self, messages, tools, **kwargs) -> ChatResponse:
        call_kwargs: dict[str, Any] = {
            "model": self._model,
            "input": self._to_responses_input(messages),
            **self.responses_call_kwargs(kwargs),
        }
        if tools:
            call_kwargs["tools"] = [self._to_responses_tool(t) for t in tools]

        resp = self._call_with_retries(lambda: self._client.responses.create(**call_kwargs))

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for item in resp.output or []:
            item_type = getattr(item, 'type', None)
            if item_type == 'function_call':
                tool_calls.append(ToolCall(id=item.call_id, function_name=item.name, arguments=item.arguments))
            elif item_type == 'message':
                for part in getattr(item, 'content', None) or []:
                    if getattr(part, 'type', None) == 'output_text':
                        text_parts.append(part.text or '')

        usage = None
        if resp.usage:
            usage = Usage(prompt_tokens=resp.usage.input_tokens, completion_tokens=resp.usage.output_tokens)

        return ChatResponse(content=''.join(text_parts), tool_calls=tool_calls, usage=usage)

    @classmethod
    def _to_responses_input(cls, messages: list[Message]) -> list[dict[str, Any]]:
        """Flatten chat messages into /v1/responses input items.

        assistant tool_calls -> function_call items; tool messages ->
        function_call_output items keyed by call_id. The full history is sent
        on every turn, exactly as the chat path does.
        """
        items: list[dict[str, Any]] = []
        for msg in messages:
            if msg.role == 'tool':
                output = msg.content if isinstance(msg.content, str) else json.dumps(msg.content)
                items.append({"type": "function_call_output", "call_id": msg.tool_call_id, "output": output or ""})
                continue
            content = cls._to_responses_content(msg.content, msg.role)
            if msg.role != 'assistant' or content:
                items.append({"role": msg.role, "content": content})
            for tc in msg.tool_calls or []:
                items.append({"type": "function_call", "call_id": tc.id,
                              "name": tc.function_name, "arguments": tc.arguments})
        return items

    @staticmethod
    def _to_responses_content(content, role: str):
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        # Multimodal chat parts -> responses parts.
        parts = []
        for part in content:
            kind = part.get('type')
            if kind == 'text':
                parts.append({"type": "output_text" if role == 'assistant' else "input_text", "text": part.get('text', '')})
            elif kind == 'image_url':
                url = part['image_url']['url'] if isinstance(part.get('image_url'), dict) else part.get('image_url')
                parts.append({"type": "input_image", "image_url": url})
            else:
                parts.append(part)
        return parts

    @staticmethod
    def _to_responses_tool(tool: ToolDef) -> dict[str, Any]:
        return {"type": "function", "name": tool.name, "description": tool.description,
                "parameters": tool.parameters}

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
