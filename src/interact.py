from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from copy import deepcopy
from typing import Any

from openai import APIConnectionError  # Parent of APITimeoutError.

from src.harness.base import ModelHarness
from src.harness.types import Message, ToolDef, ToolCall
from src.tasks.base import BaseTask
from src.path_display import display_path


FINISH_TOOL = ToolDef(
    name="finish",
    description="Call this when you have finished interacting with the environment and are ready for evaluation.",
    parameters={"type": "object", "properties": {}, "required": []},
)


@dataclass
class InteractionRecord:
    task_name: str
    model: str
    messages: list[dict] = field(default_factory=list)
    finished: bool = False
    skipped_turns: list[dict] = field(default_factory=list)

    def save(self, path: str) -> str:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)
        return path

    @classmethod
    def load(cls, path: str) -> InteractionRecord:
        with open(path) as f:
            data = json.load(f)
        return cls(**data)


def _serialize_message(msg: Message) -> dict:
    d: dict[str, Any] = {"role": msg.role, "content": msg.content}
    if msg.tool_calls:
        d["tool_calls"] = [
            {"id": tc.id, "function_name": tc.function_name, "arguments": tc.arguments}
            for tc in msg.tool_calls
        ]
    if msg.tool_call_id is not None:
        d["tool_call_id"] = msg.tool_call_id
    return d


def build_action_tool(task: BaseTask) -> ToolDef:
    action_space = task.get_action_space()
    if action_space.get('type') == 'object' and 'properties' in action_space:
        return ToolDef(name='submit_action', description='Perform an experiment or submit estimates for this task.',
                       parameters=deepcopy(action_space))
    properties = {}
    for name, spec in action_space.items():
        properties[name] = {
            "type": "number",
            "description": spec["description"],
        }
    return ToolDef(
        name="submit_action",
        description="Submit your action parameters for this task.",
        parameters={
            "type": "object",
            "properties": properties,
            "required": list(action_space.keys()),
        },
    )


def run_interaction(
    task: BaseTask,
    task_name: str,
    harness: ModelHarness,
    max_turns: int = 10,
    output_dir: str | None = None,
    generation_kwargs: dict[str, Any] | None = None,
) -> InteractionRecord:
    if type(max_turns) is not int or max_turns < 1:
        raise ValueError('max_turns must be a positive integer.')
    task.setup()
    requested_turns = max_turns
    limit = task.get_turn_limit()
    if limit is not None:
        max_turns = min(max_turns, limit)
    if output_dir:
        task.save_private_artifacts(output_dir)
    native_tools = task.get_native_tools()
    tools = native_tools if native_tools is not None else [build_action_tool(task), FINISH_TOOL]
    if output_dir and native_tools is not None:
        with open(os.path.join(output_dir, 'run_parameters.json'), 'w') as stream:
            json.dump(dict(model=harness.model_name, requested_max_turns=requested_turns,
                           effective_max_turns=max_turns, tools=[asdict(t) for t in tools]), stream, indent=2)

    messages: list[Message] = [
        Message(role="system", content=(
            "You are a physics-reasoning agent. "
            + ("Choose among the available tools to interact with the environment. "
               if native_tools is not None else "Use submit_action to interact with the environment. ") +
            "When you are satisfied with your understanding, call finish to end the interaction."
            + (f" This run permits at most {max_turns} model turns." if native_tools is not None else "")
        )),
        Message(role="user", content=task.get_prompt()),
    ]

    record = InteractionRecord(
        task_name=task_name,
        model=harness.model_name,
    )
    finished = False

    for turn in range(1, max_turns + 1):
        print(f"\n--- Turn {turn}/{max_turns} ---")

        # Preserve completed exchanges even if the next model request fails.
        if output_dir:
            record.messages = [_serialize_message(m) for m in messages]
            record.save(os.path.join(output_dir, 'interaction.json'))

        try:
            # The harness owns the retry budget. A timeout or connection error
            # reaches this handler only after that budget is exhausted; never
            # add another retry loop. APIConnectionError also covers
            # APITimeoutError and "server disconnected" errors.
            response = harness.generate(messages, tools=tools, **(generation_kwargs or {}))
        except APIConnectionError as exc:
            error_type = type(exc).__name__
            record.skipped_turns.append({
                'turn': turn, 'error_type': error_type,
                'reason': 'api_connection_error_after_retries', 'action_executed': False,
                'message': str(exc),
            })
            print(f'SKIP turn {turn}/{max_turns}: {error_type} after retries; '
                  'experiment state preserved.', flush=True)
            # There is no action to execute or tool result to fabricate. Give
            # the next model call an explicit notice while retaining evidence.
            messages.append(Message(role='user', content=(
                f'The API request for turn {turn} failed after retries, so this turn was skipped. '
                'No new experiment or action was executed. Continue from the completed observations '
                'and choose your next useful action. Keep your response concise.'
            )))
            record.messages = [_serialize_message(m) for m in messages]
            if output_dir:
                record.save(os.path.join(output_dir, 'interaction.json'))
            continue

        if not response.tool_calls:
            print(f"Agent: {response.content}")
            messages.append(Message(role="assistant", content=response.content))
            messages.append(Message(
                role="user",
                content=("Choose an available tool or finish when done." if native_tools is not None
                         else "Use submit_action to interact or finish when done."),
            ))
            continue

        messages.append(Message(
            role="assistant",
            content=response.content,
            tool_calls=response.tool_calls,
        ))

        # Tool calls can arrive in a batch. Reply to each, preserving experiment
        # order and state, so the next model request has a valid conversation.
        for tc in response.tool_calls:
            if finished:
                result = {'status': 'interaction already complete'}
            elif native_tools is not None:
                try:
                    arguments = json.loads(tc.arguments)
                    if not isinstance(arguments, dict):
                        raise ValueError('Expected an object.')
                except (ValueError, TypeError):
                    result = {'success': False, 'error': 'Action must be a valid JSON object.'}
                else:
                    result = task.execute_tool(tc.function_name, arguments)
                    if tc.function_name == 'finish' and result.get('success'):
                        finished = True
                        print('Agent called finish.')
            elif tc.function_name == 'finish':
                print('Agent called finish.')
                finished = True
                result = {'status': 'interaction complete'}
            elif tc.function_name != 'submit_action':
                result = {'success': False, 'error': 'Unknown tool.'}
            else:
                try:
                    action = json.loads(tc.arguments)
                    if not isinstance(action, dict):
                        raise ValueError('Action must be a JSON object.')
                except (ValueError, TypeError):
                    result = {'success': False, 'error': 'Action must be a valid JSON object.'}
                else:
                    print(f'Action: {action}')
                    task.apply_action(action)
                    result = task.evaluate()
                    print(f'Result: {result}')
                    if not result.get('success') and task.reset_on_failure:
                        task.env.reset()
            messages.append(Message(role='tool', content=json.dumps(result), tool_call_id=tc.id))
        if output_dir:
            record.messages = [_serialize_message(m) for m in messages]
            record.finished = finished
            record.save(os.path.join(output_dir, 'interaction.json'))
        if finished:
            break

    if not finished:
        print(f"\nMax turns ({max_turns}) reached.")
    if record.skipped_turns:
        print(f'Skipped {len(record.skipped_turns)} turn(s) after API timeout/connection retries.')

    record.messages = [_serialize_message(m) for m in messages]
    record.finished = finished

    if output_dir:
        path = os.path.join(output_dir, "interaction.json")
        record.save(path)
        print(f"Interaction record saved to {display_path(path)}")
        private_evaluation = task.get_private_evaluation()
        if private_evaluation is not None:
            # This file is host-only. Never append scores or ground truth to messages.
            private_path = os.path.join(output_dir, 'private_evaluation.json')
            with open(private_path, 'w') as stream:
                json.dump(private_evaluation, stream, indent=2)

    return record
