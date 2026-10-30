from __future__ import annotations

from src.envs.base import BaseEnv


ENV_REGISTRY: dict[str, type[BaseEnv]] = {}


def register_env(name: str):
    def decorator(cls: type[BaseEnv]) -> type[BaseEnv]:
        ENV_REGISTRY[name] = cls
        return cls
    return decorator


def get_env(name: str) -> type[BaseEnv]:
    if name not in ENV_REGISTRY:
        available = ", ".join(ENV_REGISTRY.keys())
        raise KeyError(f"Unknown env {name!r}. Available: {available}")
    return ENV_REGISTRY[name]


def list_envs() -> list[str]:
    return list(ENV_REGISTRY.keys())
