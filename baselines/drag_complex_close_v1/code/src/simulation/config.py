from __future__ import annotations

from typing import Any

import yaml

from src.envs.base import BaseEnv
from src.envs.registry import get_env
from src.tasks.base import BaseTask
from src.tasks.registry import get_task
from src.simulation.renderer import SimulationRenderer


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def build_env_from_config(config: dict) -> BaseEnv:
    env_cfg = config["env"]
    env_cls = get_env(env_cfg["type"])
    params = env_cfg.get("params", {})
    return env_cls(**params)


def build_task_from_config(config: dict, env: BaseEnv | None = None) -> BaseTask:
    task_cfg = config["task"]
    task_cls = get_task(task_cfg["type"])
    params = task_cfg.get("params", {})
    if env is not None:
        return task_cls(env=env, **params)
    return task_cls(**params)


def build_renderer_from_config(config: dict, output_dir: str | None = None) -> SimulationRenderer:
    renderer_cfg = config.get("renderer", {})
    kwargs: dict[str, Any] = {}
    if "projection" in renderer_cfg:
        kwargs["projection"] = renderer_cfg["projection"]
    if "xlim" in renderer_cfg:
        kwargs["xlim"] = renderer_cfg["xlim"]
    if "ylim" in renderer_cfg:
        kwargs["ylim"] = renderer_cfg["ylim"]
    if "figsize" in renderer_cfg:
        kwargs["figsize"] = tuple(renderer_cfg["figsize"])
    if "axes" in renderer_cfg:
        kwargs["axes"] = tuple(renderer_cfg["axes"])
    if output_dir:
        kwargs["output_dir"] = output_dir
    return SimulationRenderer(**kwargs)
