from __future__ import annotations

from src.tasks.base import BaseTask


TASK_REGISTRY: dict[str, type[BaseTask]] = {}


def register_task(name: str):
    def decorator(cls: type[BaseTask]) -> type[BaseTask]:
        TASK_REGISTRY[name] = cls
        return cls
    return decorator


def get_task(name: str) -> type[BaseTask]:
    if name not in TASK_REGISTRY:
        available = ", ".join(TASK_REGISTRY.keys())
        raise KeyError(f"Unknown task {name!r}. Available: {available}")
    return TASK_REGISTRY[name]


def list_tasks() -> list[str]:
    return list(TASK_REGISTRY.keys())
