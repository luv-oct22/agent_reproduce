from __future__ import annotations

import math
from typing import Any, Optional

from src.envs.base import BaseEnv
from src.envs.registry import register_env
from src.objects.base import Object
from src.objects.connector import Spring


@register_env("spring_system")
class SpringSystemEnv(BaseEnv):

    def __init__(self):
        super().__init__()
        self._anchor: list[float] = [0.0, 0.0, 0.0]
        self._spring: Optional[Spring] = None
        self._initial_states: dict[str, tuple[list[float], list[float]]] = {}

    def set_spring(self, spring: Spring) -> None:
        self._spring = spring

    def set_anchor(self, pos: list[float]) -> None:
        self._anchor = list(pos)

    def add_object(self, obj: Object) -> None:
        super().add_object(obj)
        self._initial_states[obj.name] = (list(obj.position), list(obj.velocity))

    def reset(self) -> None:
        self._time = 0.0
        for name, (pos, vel) in self._initial_states.items():
            obj = self._objects[name]
            obj.position = list(pos)
            obj.velocity = list(vel)

    def step(self, dt: float = 0.01) -> dict[str, Any]:
        if self._spring is None:
            self._time += dt
            return self.observe()

        k = self._spring.stiffness
        c = self._spring.damping
        rest = self._spring.rest_length

        for obj in self._objects.values():
            if obj.mass <= 0:
                continue
            dx = obj.position[0] - self._anchor[0]
            dy = obj.position[1] - self._anchor[1]
            dz = obj.position[2] - self._anchor[2]
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            if dist < 1e-20:
                continue

            stretch = dist - rest
            force_mag = -k * stretch

            # damping along spring axis
            vr = (obj.velocity[0] * dx + obj.velocity[1] * dy + obj.velocity[2] * dz) / dist
            force_mag -= c * vr

            fx = force_mag * dx / dist
            fy = force_mag * dy / dist
            fz = force_mag * dz / dist

            obj.velocity[0] += (fx / obj.mass) * dt
            obj.velocity[1] += (fy / obj.mass) * dt
            obj.velocity[2] += (fz / obj.mass) * dt
            obj.position[0] += obj.velocity[0] * dt
            obj.position[1] += obj.velocity[1] * dt
            obj.position[2] += obj.velocity[2] * dt

        self._time += dt
        return self.observe()

    def observe(self) -> dict[str, Any]:
        state = {}
        for name, obj in self._objects.items():
            state[name] = {
                "position": list(obj.position),
                "velocity": list(obj.velocity),
                "mass": obj.mass,
            }
        if self._spring:
            state["spring"] = {
                "stiffness": self._spring.stiffness,
                "rest_length": self._spring.rest_length,
                "damping": self._spring.damping,
                "anchor": list(self._anchor),
            }
        state["time"] = self._time
        return state
