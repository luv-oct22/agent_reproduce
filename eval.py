from __future__ import annotations

import argparse
import json
import os
from datetime import datetime

from src.harness import OpenAIHarness
from src.tasks import get_task, list_tasks
from src.interact import run_interaction, InteractionRecord
from src.evaluate import run_evaluation, load_questions


def make_run_dir(output_dir: str, task_name: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(output_dir, f"{task_name}_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Run interaction and evaluation pipeline.")
    parser.add_argument(
        "--tasks", nargs="+", required=True,
        help=f"Task names. Available: {list_tasks()}",
    )
    parser.add_argument("--model", default="gpt-4o")
    parser.add_argument("--max-turns", type=int, default=10)
    parser.add_argument(
        "--mode", choices=["interact", "evaluate", "both"], default="both",
        help="interact: run interaction only. evaluate: run evaluation only. both: run both.",
    )
    parser.add_argument("--config", help="Path to YAML config file for env/task/renderer parameters.")
    parser.add_argument("--questions", help="Path to questions.json for evaluation.")
    parser.add_argument("--record", help="Path to interaction.json (for evaluate-only mode).")
    parser.add_argument("--no-history", action="store_true", help="Evaluate without interaction history.")
    parser.add_argument("--output-dir", default="results", help="Directory to save results.")
    parser.add_argument(
        "--velocity", nargs=3, type=float, default=None,
        metavar=("VX", "VY", "VZ"),
        help="Initial velocity for standalone evaluate mode (config simulation.velocity, otherwise 5 0 5).",
    )
    args = parser.parse_args()

    if args.mode == "evaluate" and not args.questions:
        parser.error("--questions is required for evaluate mode.")

    config = None
    if args.config:
        from src.simulation.config import load_config
        config = load_config(args.config)

    if args.velocity is None:
        args.velocity = (config or {}).get("simulation", {}).get("velocity", [5.0, 0.0, 5.0])

    harness = OpenAIHarness(model=args.model)

    for task_name in args.tasks:
        print(f"\n{'='*60}")
        print(f"Task: {task_name}")
        print(f"{'='*60}")

        if args.mode == "evaluate" and args.record:
            run_dir = os.path.dirname(os.path.abspath(args.record))
        else:
            run_dir = make_run_dir(args.output_dir, task_name)

        print(f"Run directory: {run_dir}")

        interaction_record = None

        if args.mode in ("interact", "both"):
            if config:
                from src.simulation.config import build_env_from_config, build_task_from_config
                env = build_env_from_config(config)
                task = build_task_from_config(config, env=env)
            else:
                task_cls = get_task(task_name)
                task = task_cls()

            interaction_record = run_interaction(
                task=task,
                task_name=task_name,
                harness=harness,
                max_turns=args.max_turns,
                output_dir=run_dir,
            )

        if args.mode == "evaluate" and args.record:
            interaction_record = InteractionRecord.load(args.record)

        if args.mode in ("evaluate", "both") and args.questions:
            env_for_eval = None
            renderer_for_eval = None
            eval_markers = None

            questions_data = load_questions(args.questions)
            needs_visual = any(q.get("type") == "visual_predict" for q in questions_data)

            if needs_visual:
                if config is None:
                    parser.error("visual_predict questions require --config for env/renderer.")

                from src.simulation.config import build_renderer_from_config

                if args.mode == "both":
                    env_for_eval = task.env
                else:
                    from src.simulation.render_scene import _build_scene
                    env_for_eval, eval_markers = _build_scene(config, args.velocity)

                renderer_for_eval = build_renderer_from_config(
                    config, output_dir=os.path.join(run_dir, "eval_frames"),
                )

                if eval_markers is None:
                    task_params = config.get("task", {}).get("params", {})
                    if "cup_position" in task_params:
                        eval_markers = [{
                            "position": task_params["cup_position"],
                            "radius": task_params.get("cup_radius", 0.3),
                            "color": "red",
                            "label": "cup",
                            "style": "open",
                        }]

            run_evaluation(
                task_name=task_name,
                harness=harness,
                questions_path=args.questions,
                interaction_record=interaction_record if not args.no_history else None,
                with_history=not args.no_history,
                output_dir=run_dir,
                env=env_for_eval,
                renderer=renderer_for_eval,
                extra_markers=eval_markers,
            )


if __name__ == "__main__":
    main()
