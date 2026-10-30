from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from src.simulation.renderer import SimulationRenderer


def build_image_choice_content(question: dict, question_dir: str | Path) -> list[dict[str, Any]]:
    """Send only the public question and pixels; keep answers/scene metadata host-only."""
    root = Path(question_dir)
    choices = question['choices']
    if [choice['label'] for choice in choices] != list('ABCD'):
        raise ValueError('Image choices must be labeled A, B, C, D in order.')
    content = [{'type': 'text', 'text': question['question']}]
    for caption, filename in [(question.get('context_caption', 'Context — before release'), question['context_image'])] + [
            (f"Choice {choice['label']}", choice['image']) for choice in choices]:
        path = root/filename
        if not path.is_file():
            raise FileNotFoundError(f'Missing evaluation image: {path}. Render the balance bundle first.')
        if path.read_bytes()[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError(f'Evaluation image must be a PNG: {path}')
        content.append({'type': 'text', 'text': caption})
        content.append({'type': 'image_url', 'image_url': {'url': encode_image_base64(str(path)), 'detail': 'high'}})
    content.append({'type': 'text', 'text': 'Answer with just one letter: A, B, C, or D.'})
    return content


def sample_frame_steps(
    total_history_length: int,
    num_context_frames: int = 4,
) -> tuple[list[int], int]:
    target_step = total_history_length - 1
    interval = target_step / num_context_frames
    context_steps = [round(i * interval) for i in range(num_context_frames)]
    return context_steps, target_step


def render_frames(
    renderer: SimulationRenderer,
    history: list[dict],
    steps: list[int],
    trail_length: int = 50,
    extra_markers: list[dict] | None = None,
) -> list[str]:
    paths = []
    for step in steps:
        path = renderer.render_trajectory(
            history, step=step, trail_length=trail_length,
            extra_markers=extra_markers,
        )
        paths.append(path)
    return paths


def encode_image_base64(path: str) -> str:
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{data}"


def build_multimodal_content(
    question_text: str,
    image_paths: list[str],
) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    parts.append({
        "type": "text",
        "text": (
            f"Here are {len(image_paths)} frames from a physics simulation, "
            f"shown at evenly spaced time intervals:"
        ),
    })
    for i, path in enumerate(image_paths):
        data_uri = encode_image_base64(path)
        parts.append({"type": "text", "text": f"Frame {i + 1}:"})
        parts.append({
            "type": "image_url",
            "image_url": {"url": data_uri, "detail": "high"},
        })
    parts.append({"type": "text", "text": question_text})
    return parts
