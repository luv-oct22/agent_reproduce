from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from copy import deepcopy
from typing import Any

from openai import APITimeoutError

from src.harness.base import ModelHarness
from src.harness.types import Message, ToolDef, ToolCall
from src.tasks.base import BaseTask


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
) -> InteractionRecord:
    task.setup()
    if output_dir:
        task.save_private_artifacts(output_dir)
    action_tool = build_action_tool(task)
    tools = [action_tool, FINISH_TOOL]

    messages: list[Message] = [
        Message(role="system", content=(
            "You are a physics-reasoning agent. "
            "Use submit_action to interact with the environment. "
            "When you are satisfied with your understanding, call finish to end the interaction."
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
            # The harness owns the retry budget. A timeout reaches this handler
            # only after that budget is exhausted; never add another retry loop.
            response = harness.generate(messages, tools=tools)
        except APITimeoutError:
            record.skipped_turns.append({
                'turn': turn, 'error_type': 'APITimeoutError',
                'reason': 'api_timeout_after_retries', 'action_executed': False,
            })
            print(f'SKIP turn {turn}/{max_turns}: API timeout after retries; '
                  'experiment state preserved.', flush=True)
            # There is no action to execute or tool result to fabricate. Give
            # the next model call an explicit notice while retaining evidence.
            messages.append(Message(role='user', content=(
                f'The API request for turn {turn} timed out after retries, so this turn was skipped. '
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
                content="Use submit_action to interact or finish when done.",
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
        if finished:
            break

    if not finished:
        print(f"\nMax turns ({max_turns}) reached.")
    if record.skipped_turns:
        print(f'Skipped {len(record.skipped_turns)} turn(s) after API timeout retries.')

    record.messages = [_serialize_message(m) for m in messages]
    record.finished = finished

    if output_dir:
        path = os.path.join(output_dir, "interaction.json")
        record.save(path)
        print(f"Interaction record saved to {path}")
        private_evaluation = task.get_private_evaluation()
        if private_evaluation is not None:
            # This file is host-only. Never append scores or ground truth to messages.
            private_path = os.path.join(output_dir, 'private_evaluation.json')
            with open(private_path, 'w') as stream:
                json.dump(private_evaluation, stream, indent=2)

    return record
