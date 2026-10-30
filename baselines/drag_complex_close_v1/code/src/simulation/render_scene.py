from __future__ import annotations

import argparse
import os
from pathlib import Path

from src.simulation.config import load_config, build_env_from_config, build_renderer_from_config
from src.simulation.threejs_renderer import ThreeJSRenderer
from src.simulation.render_record import capture_metadata, write_record


def blender_executable():
    """Prefer an explicit executable, then the optional project-local Blender."""
    if os.environ.get("BLENDER_BIN"):
        return os.environ["BLENDER_BIN"]
    portable = Path(__file__).resolve().parents[2] / ".tools/blender-3.6.23-linux-x64/blender"
    return str(portable) if portable.is_file() else "blender"

def _build_scene(config: dict, velocity: list[float]):
    env = build_env_from_config(config)
    vx, vy, vz = velocity
    env.configure([{
        "name": "ball",
        "mass": 0.1,
        "position": config.get("task", {}).get("params", {}).get("ball_position", [0, 0, 0]),
        "velocity": [vx, vy, vz],
    }])
    env.run()

    extra_markers = []
    task_params = config.get("task", {}).get("params", {})
    if "cup_position" in task_params:
        extra_markers.append({
            "position": task_params["cup_position"],
            "radius": task_params.get("cup_radius", 0.3),
            "color": "red",
            "label": "cup",
            "style": "open",
        })
    return env, extra_markers


def _record_data(config, env, args):
    return {'history': env._history, 'scene': config.get('scene', {}),
            'dt': env._dt, 'env_params': config['env'].get('params', {}),
            'parameter_metadata': capture_metadata(config, env, args.config)}


def _render_matplotlib(config, env, extra_markers, args):
    renderer = build_renderer_from_config(config, output_dir=args.output_dir)
    history = env._history
    total = len(history)

    if args.step is not None:
        steps_to_render = [args.step]
    elif args.steps:
        steps_to_render = args.steps
    elif args.every:
        steps_to_render = list(range(0, total, args.every))
    else:
        steps_to_render = list(range(0, total, max(1, total // 10)))

    for s in steps_to_render:
        if s >= total:
            print(f"Skipping step {s} (max {total - 1})")
            continue
        path = renderer.render_trajectory(history, step=s, trail_length=args.trail, extra_markers=extra_markers)
        print(f"Step {s}/{total - 1} -> {path}")
        write_record(args.output_dir, _record_data(config, env, args),
                     {'Format': 'Matplotlib', 'Step': s, 'Trail length': args.trail,
                      'Renderer configuration': config.get('renderer', {})}, path)

    print(f"\nRendered {len(steps_to_render)} frames to {args.output_dir}")


def _render_threejs(config, env, extra_markers, args):
    renderer = ThreeJSRenderer(output_dir=args.output_dir)
    path = renderer.render(env._history, extra_markers=extra_markers)
    write_record(args.output_dir, _record_data(config, env, args),
                 {'Format': 'Three.js HTML'}, path)
    print(f"Three.js simulation saved to {path}")
    print("Open in a browser to view the interactive 3D scene.")


def _render_blender(config, env, extra_markers, args):
    import json
    import os
    import subprocess

    obj_names = [k for k in env._history[0] if k != "time" and isinstance(env._history[0][k], dict)]
    data = {
        "object_names": obj_names,
        "markers": extra_markers,
        "dt": config["env"]["params"].get("dt", 0.001),
        "total_frames": len(env._history),
        "history": env._history,
        "scene": config.get("scene", {}),
        "env_params": config["env"].get("params", {}),
        "object_radius": config.get("task", {}).get("params", {}).get("ball_radius", 0.05),
        "parameter_metadata": capture_metadata(config, env, args.config),
    }

    from src.robotics.panda import plan_motion
    animation = plan_motion(data)
    if animation:
        data['animation'] = animation
    os.makedirs(args.output_dir, exist_ok=True)
    json_path = os.path.join(args.output_dir, "sim_history.json")
    with open(json_path, "w") as f:
        json.dump(data, f)
    print(f"Exported history to {json_path}")

    script_path = os.path.join(os.path.dirname(__file__), "blender_render.py")
    video_path = os.path.join(args.output_dir, "scene.png" if args.still else "simulation.mp4")

    cmd = [
        args.blender, "--background", "--python-exit-code", "1", "--python", script_path, "--",
        "--input", json_path,
        "--output", video_path,
        "--fps", str(args.fps),
        "--resolution", str(args.res_x), str(args.res_y),
        "--samples", str(args.samples),
        "--frame-step", str(args.frame_step),
    ]
    if args.trail:
        cmd.append("--trail")
    if args.still:
        cmd.extend(["--still", "--step", str(args.step if args.step is not None else config.get("scene", {}).get("preview_step", 0))])
    if args.save_blend:
        cmd.extend(["--save-blend", os.path.join(args.output_dir, "scene.blend")])

    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render simulation snapshots.")
    parser.add_argument("--config", required=True, help="Path to YAML config file.")
    parser.add_argument("--output-dir", default="renders", help="Directory to save output.")
    parser.add_argument("--format", choices=["matplotlib", "threejs", "blender"], default="matplotlib",
                        help="Render format: matplotlib (PNG), threejs (HTML), or blender (MP4 video).")
    parser.add_argument("--step", type=int, default=None, help="Simulation step for a PNG (matplotlib or Blender --still).")
    parser.add_argument("--still", action="store_true", help="Render a single Blender PNG instead of video.")
    parser.add_argument("--save-blend", action="store_true", help="Also save the editable Blender scene.")
    parser.add_argument("--blender", default=blender_executable(), help="Blender executable (also configurable with BLENDER_BIN).")
    parser.add_argument("--steps", nargs="+", type=int, help="Render specific steps (matplotlib only).")
    parser.add_argument("--every", type=int, default=None, help="Render every N-th step (matplotlib only).")
    parser.add_argument("--trail", type=int, default=None, help="Trajectory overlay; defaults to 50 for matplotlib and disabled for Blender.")
    parser.add_argument("--fps", type=int, default=60, help="Video FPS (blender only).")
    parser.add_argument("--res-x", type=int, default=1920, help="Video width (blender only).")
    parser.add_argument("--res-y", type=int, default=1080, help="Video height (blender only).")
    parser.add_argument("--samples", type=int, default=64, help="Render samples (blender only).")
    parser.add_argument("--frame-step", type=int, default=10, help="Simulation steps between animation keyframes; playback time is preserved (Blender only).")
    parser.add_argument(
        "--velocity", nargs=3, type=float, default=None,
        metavar=("VX", "VY", "VZ"), help="Initial velocity; defaults to simulation.velocity in YAML, then 5 0 5.",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    if args.velocity is None:
        args.velocity = config.get("simulation", {}).get("velocity", [5.0, 0.0, 5.0])
    if args.trail is None:
        args.trail = 50 if args.format == "matplotlib" else 0
    if args.frame_step < 1 or args.samples < 1 or args.fps < 1 or min(args.res_x, args.res_y) < 1:
        parser.error("Frame step, samples, FPS and resolution must be positive.")
    if args.step is not None and not 0 <= args.step <= config["env"].get("params", {}).get("total_steps", 1000):
        parser.error("--step is outside the simulation history.")
    env, extra_markers = _build_scene(config, args.velocity)

    if args.format == "threejs":
        _render_threejs(config, env, extra_markers, args)
    elif args.format == "blender":
        _render_blender(config, env, extra_markers, args)
    else:
        _render_matplotlib(config, env, extra_markers, args)


if __name__ == "__main__":
    main()
