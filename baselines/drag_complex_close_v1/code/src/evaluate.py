from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Any
from pathlib import Path

from src.harness.base import ModelHarness
from src.harness.types import Message
from src.interact import InteractionRecord
from src.envs.base import BaseEnv
from src.simulation.renderer import SimulationRenderer
from src.evaluation.visual import (
    sample_frame_steps,
    render_frames,
    build_multimodal_content,
    build_image_choice_content,
)


@dataclass
class EvaluationRecord:
    task_name: str
    model: str
    with_history: bool
    questions: list[dict] = field(default_factory=list)
    answers: list[dict] = field(default_factory=list)
    score: float = 0.0

    def save(self, path: str) -> str:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)
        return path


def load_questions(path: str) -> list[dict]:
    with open(path) as f:
        return json.load(f)


def _build_history_context(record: InteractionRecord) -> str:
    lines = ["Below is the record of your prior interaction with the environment:\n"]
    for msg in record.messages:
        role = msg["role"]
        content = msg.get("content", "")
        if role == "tool":
            lines.append(f"[Tool Result]: {content}")
        elif role == "assistant":
            tc = msg.get("tool_calls")
            if tc:
                for t in tc:
                    lines.append(f"[Your Action]: {t['function_name']}({t['arguments']})")
            if content:
                lines.append(f"[Your Reasoning]: {content}")
        elif role == "user":
            lines.append(f"[Environment]: {content}")
    return "\n".join(lines)


def _format_question(q: dict) -> str:
    text = q["question"] + "\n"
    for choice in q["choices"]:
        text += f"  {choice}\n"
    text += "\nAnswer with just the letter (e.g. A, B, C, or D)."
    return text


def _parse_answer(response_text: str) -> str:
    match = re.search(r"\b([A-D])\b", response_text.upper())
    if match:
        return match.group(1)
    return response_text.strip()[:1].upper()


def _format_prediction_question(q: dict) -> str:
    state = q.get("current_state", {})
    obj_name = q["object"]
    text = q["question"] + "\n\n"
    if state:
        text += f"Current state at step {q.get('step', '?')}:\n"
        text += json.dumps(state, indent=2) + "\n\n"
    text += (
        f"Predict the position of '{obj_name}' at the next timestep.\n"
        f"Reply in JSON format: {{\"position\": [x, y, z]}}"
    )
    return text


def _parse_prediction(response_text: str) -> dict | None:
    match = re.search(r"\{[^}]*\"position\"\s*:\s*\[[^\]]*\][^}]*\}", response_text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def _score_prediction(predicted: dict | None, answer: dict, tolerance: float) -> bool:
    if predicted is None:
        return False
    pred_pos = predicted.get("position", [])
    true_pos = answer.get("position", [])
    if len(pred_pos) != len(true_pos):
        return False
    dist = math.sqrt(sum((p - t) ** 2 for p, t in zip(pred_pos, true_pos)))
    return dist <= tolerance


def run_evaluation(
    task_name: str,
    harness: ModelHarness,
    questions_path: str,
    interaction_record: InteractionRecord | None = None,
    with_history: bool = True,
    output_dir: str | None = None,
    env: BaseEnv | None = None,
    renderer: SimulationRenderer | None = None,
    extra_markers: list[dict] | None = None,
) -> EvaluationRecord:
    questions = load_questions(questions_path)

    record = EvaluationRecord(
        task_name=task_name,
        model=harness.model_name,
        with_history=with_history and interaction_record is not None,
        questions=questions,
    )

    history_context = ""
    if with_history and interaction_record is not None:
        history_context = _build_history_context(interaction_record)

    correct = 0
    for i, q in enumerate(questions):
        q_type = q.get("type", "multiple_choice")
        print(f"\n--- Question {i + 1}/{len(questions)} ({q_type}) ---")
        print(f"Q: {q.get('question', q_type)}")

        messages: list[Message] = [
            Message(role="system", content=(
                "You are answering physics questions based on simulation data."
            )),
        ]

        if history_context:
            messages.append(Message(role="user", content=history_context))
            messages.append(Message(
                role="assistant",
                content="I have reviewed the interaction record. Please ask your question.",
            ))

        if q_type == "predict_next_frame":
            question_text = _format_prediction_question(q)
            messages.append(Message(role="user", content=question_text))

            response = harness.generate(messages)
            predicted = _parse_prediction(response.content)
            tolerance = q.get("tolerance", 0.1)
            is_correct = _score_prediction(predicted, q["answer"], tolerance)

            if is_correct:
                correct += 1

            print(f"Predicted: {predicted}")
            print(f"Expected: {q['answer']}")
            print(f"Tolerance: {tolerance} | {'Correct' if is_correct else 'Wrong'}")

            record.answers.append({
                "question_id": q.get("id", str(i)),
                "type": "predict_next_frame",
                "predicted": predicted,
                "expected": q["answer"],
                "correct": is_correct,
            })

        elif q_type == "visual_predict":
            if env is None or renderer is None:
                raise ValueError(
                    "visual_predict questions require env and renderer. "
                    "Pass --config to provide them."
                )
            history = env._history
            if not history:
                raise ValueError("Environment history is empty. Was the simulation run?")

            num_context = q.get("num_context_frames", 4)
            object_name = q["object"]
            tolerance = q.get("tolerance", 0.1)

            context_steps, target_step = sample_frame_steps(
                total_history_length=len(history),
                num_context_frames=num_context,
            )

            image_paths = render_frames(
                renderer, history, context_steps,
                trail_length=q.get("trail_length", 50),
                extra_markers=extra_markers,
            )

            context_times = [history[s]["time"] for s in context_steps]
            target_time = history[target_step]["time"]
            question_text = (
                f"\nThe frames above show the simulation at times "
                f"{[round(t, 4) for t in context_times]}.\n"
                f"Predict the position of '{object_name}' at the next time step "
                f"(t = {target_time:.4f}).\n"
                f"Reply in JSON format: {{\"position\": [x, y, z]}}"
            )
            if q.get("question"):
                question_text = q["question"] + question_text

            multimodal_content = build_multimodal_content(question_text, image_paths)

            vis_messages: list[Message] = [
                Message(role="system", content=(
                    "You are answering physics questions based on simulation frames. "
                    "Analyze the trajectory shown in the images to predict future positions."
                )),
            ]
            if history_context:
                vis_messages.append(Message(role="user", content=history_context))
                vis_messages.append(Message(
                    role="assistant",
                    content="I have reviewed the interaction record. Please ask your question.",
                ))
            vis_messages.append(Message(role="user", content=multimodal_content))

            response = harness.generate(vis_messages)
            predicted = _parse_prediction(response.content)
            true_answer = {"position": history[target_step][object_name]["position"]}
            is_correct = _score_prediction(predicted, true_answer, tolerance)

            if is_correct:
                correct += 1

            print(f"Predicted: {predicted}")
            print(f"Expected:  {true_answer}")
            print(f"Tolerance: {tolerance} | {'Correct' if is_correct else 'Wrong'}")

            record.answers.append({
                "question_id": q.get("id", str(i)),
                "type": "visual_predict",
                "context_steps": context_steps,
                "target_step": target_step,
                "predicted": predicted,
                "expected": true_answer,
                "correct": is_correct,
            })

        elif q_type == 'image_multiple_choice':
            content = build_image_choice_content(q, Path(questions_path).resolve().parent)
            messages.append(Message(role='user', content=content))
            response = harness.generate(messages)
            agent_answer = _parse_answer(response.content)
            expected = q['answer'].strip().upper()
            is_correct = agent_answer == expected
            correct += int(is_correct)
            print(f"Agent: {agent_answer} | Expected: {expected} | {'Correct' if is_correct else 'Wrong'}")
            record.answers.append({'question_id': q.get('id', str(i)), 'type': q_type,
                                   'agent_answer': agent_answer, 'expected': expected,
                                   'correct': is_correct, 'response': response.content})

        else:
            question_text = _format_question(q)
            messages.append(Message(role="user", content=question_text))

            response = harness.generate(messages)
            agent_answer = _parse_answer(response.content)
            expected = q["answer"].strip().upper()
            is_correct = agent_answer == expected

            if is_correct:
                correct += 1

            print(f"Agent: {agent_answer} | Expected: {expected} | {'Correct' if is_correct else 'Wrong'}")

            record.answers.append({
                "question_id": q.get("id", str(i)),
                "type": "multiple_choice",
                "agent_answer": agent_answer,
                "expected": expected,
                "correct": is_correct,
            })

        # Checkpoint completed answers before making another API request.
        if output_dir:
            record.score = correct / len(questions) if questions else 0.0
            mode = 'with_history' if record.with_history else 'no_history'
            record.save(os.path.join(output_dir, f'evaluation_{mode}.json'))

    record.score = correct / len(questions) if questions else 0.0
    print(f"\nScore: {correct}/{len(questions)} ({record.score:.1%})")

    if output_dir:
        mode = "with_history" if record.with_history else "no_history"
        path = os.path.join(output_dir, f"evaluation_{mode}.json")
        record.save(path)
        print(f"Evaluation record saved to {path}")

    return record
