"""Export simulation history to JSON for use with Blender or other 3D tools."""
from __future__ import annotations

import json
import os

from src.simulation.config import load_config, build_env_from_config
from src.simulation.render_record import capture_metadata


def export_history(config_path: str, velocity: list[float], output_path: str, markers: list[dict] | None = None) -> str:
    config = load_config(config_path)
    env = build_env_from_config(config)

    vx, vy, vz = velocity
    task_params = config.get("task", {}).get("params", {})
    env.configure([{
        "name": "ball",
        "mass": 0.1,
        "position": task_params.get("ball_position", [0, 0, 0]),
        "velocity": [vx, vy, vz],
    }])
    env.run()

    extra_markers = markers or []
    if not extra_markers and "cup_position" in task_params:
        extra_markers.append({
            "position": task_params["cup_position"],
            "radius": task_params.get("cup_radius", 0.3),
            "label": "cup",
        })

    obj_names = [k for k in env._history[0] if k != "time" and isinstance(env._history[0][k], dict)]

    data = {
        "object_names": obj_names,
        "markers": extra_markers,
        "dt": config["env"]["params"].get("dt", 0.001),
        "total_frames": len(env._history),
        "history": env._history,
        "scene": config.get("scene", {}),
        "env_params": config["env"].get("params", {}),
        "object_radius": task_params.get("ball_radius", 0.05),
        "parameter_metadata": capture_metadata(config, env, config_path),
    }

    from src.robotics.panda import plan_motion
    animation = plan_motion(data)
    if animation:
        data['animation'] = animation
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f)
    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Export simulation history to JSON.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", default="sim_history.json")
    parser.add_argument("--velocity", nargs=3, type=float)
    args = parser.parse_args()

    velocity = args.velocity or load_config(args.config).get("simulation", {}).get("velocity", [5.0, 0.0, 5.0])
    path = export_history(args.config, velocity, args.output)
    print(f"Exported {path}")
