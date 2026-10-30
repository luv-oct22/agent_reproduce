from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.objects.base import Object


class BaseEnv(ABC):

    def __init__(self):
        self._objects: dict[str, Object] = {}
        self._time: float = 0.0

    # ------------------------------------------------------------------
    # Object management (shared by all envs)
    # ------------------------------------------------------------------

    def add_object(self, obj: Object) -> None:
        self._objects[obj.name] = obj

    def remove_object(self, name: str) -> Object | None:
        return self._objects.pop(name, None)

    def get_object(self, name: str) -> Object | None:
        return self._objects.get(name)

    @property
    def objects(self) -> dict[str, Object]:
        return dict(self._objects)

    @property
    def time(self) -> float:
        return self._time

    # ------------------------------------------------------------------
    # Abstract interface — each scene implements these
    # ------------------------------------------------------------------

    @abstractmethod
    def step(self, dt: float = 0.01) -> dict[str, Any]:
        ...

    @abstractmethod
    def reset(self) -> None:
        ...

    @abstractmethod
    def observe(self) -> dict[str, Any]:
        ...

    def description(self) -> str:
        obj_list = ", ".join(o.describe() for o in self._objects.values())
        return f"{type(self).__name__} t={self._time:.3f} objects=[{obj_list}]"

    def get_state(self) -> dict[str, Any]:
        return {
            "time": self._time,
            "objects": {
                name: {
                    "position": list(obj.position),
                    "velocity": list(obj.velocity),
                    "mass": obj.mass,
                }
                for name, obj in self._objects.items()
            },
        }
