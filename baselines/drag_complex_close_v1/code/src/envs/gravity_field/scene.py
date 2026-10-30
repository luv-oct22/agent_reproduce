from __future__ import annotations

import math
from typing import Any

from src.envs.base import BaseEnv
from src.envs.registry import register_env
from src.objects.base import Object


G = 6.674e-11


@register_env("gravity_field")
class GravityFieldEnv(BaseEnv):

    def __init__(
        self,
        g_constant: float = G,
        dt: float = 0.01,
        total_steps: int = 1000,
        uniform_gravity: list[float] | None = None,
    ):
        super().__init__()
        self._g = g_constant
        self._dt = dt
        self._total_steps = total_steps
        self._uniform_gravity = uniform_gravity or [0.0, 0.0, 0.0]
        self._initial_states: dict[str, tuple[list[float], list[float]]] = {}
        self._history: list[dict[str, Any]] = []
        self._has_run = False

    # ------------------------------------------------------------------
    # Interface for the agent: configure, run, observe
    # ------------------------------------------------------------------

    def configure(self, objects: list[dict[str, Any]]) -> None:
        """Agent sets initial parameters for objects.

        Each dict: {"name": str, "mass": float, "position": [x,y,z], "velocity": [x,y,z]}
        """
        self._objects.clear()
        self._initial_states.clear()
        self._history.clear()
        self._has_run = False
        self._time = 0.0

        for spec in objects:
            obj = Object(
                name=spec["name"],
                mass=spec.get("mass", 1.0),
                position=list(spec.get("position", [0.0, 0.0, 0.0])),
                velocity=list(spec.get("velocity", [0.0, 0.0, 0.0])),
            )
            self._objects[obj.name] = obj
            self._initial_states[obj.name] = (list(obj.position), list(obj.velocity))

    def run(self) -> None:
        """Run the full simulation. Agent cannot control stepping."""
        self._history.clear()
        self._history.append(self._snapshot())
        for _ in range(self._total_steps):
            self._step_internal()
            self._history.append(self._snapshot())
        self._has_run = True

    def observe(self) -> dict[str, Any]:
        """Return the full trajectory after simulation. This is the only
        data the agent gets back."""
        if not self._has_run:
            return {"error": "Simulation has not been run yet. Call run() first."}

        trajectory: dict[str, Any] = {"time": [], "objects": {}}
        names = list(self._initial_states.keys())
        for name in names:
            trajectory["objects"][name] = {
                "position": [],
                "velocity": [],
                "mass": self._initial_states[name][0] and self._objects[name].mass,
            }

        for snap in self._history:
            trajectory["time"].append(snap["time"])
            for name in names:
                trajectory["objects"][name]["position"].append(snap[name]["position"])
                trajectory["objects"][name]["velocity"].append(snap[name]["velocity"])

        trajectory["dt"] = self._dt
        trajectory["total_steps"] = self._total_steps
        return trajectory

    def reset(self) -> None:
        self._time = 0.0
        self._history.clear()
        self._has_run = False
        for name, (pos, vel) in self._initial_states.items():
            obj = self._objects[name]
            obj.position = list(pos)
            obj.velocity = list(vel)

    # ------------------------------------------------------------------
    # Internal simulation — not exposed to the agent
    # ------------------------------------------------------------------

    def _step_internal(self) -> None:
        names = list(self._objects.keys())
        objs = [self._objects[n] for n in names]
        n = len(objs)
        dt = self._dt

        forces = [[0.0, 0.0, 0.0] for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                f = self._gravity_force(objs[i], objs[j])
                for k in range(3):
                    forces[i][k] += f[k]
                    forces[j][k] -= f[k]

        for i, obj in enumerate(objs):
            if obj.mass <= 0:
                continue
            ax = forces[i][0] / obj.mass + self._uniform_gravity[0]
            ay = forces[i][1] / obj.mass + self._uniform_gravity[1]
            az = forces[i][2] / obj.mass + self._uniform_gravity[2]
            obj.velocity[0] += ax * dt
            obj.velocity[1] += ay * dt
            obj.velocity[2] += az * dt
            obj.position[0] += obj.velocity[0] * dt
            obj.position[1] += obj.velocity[1] * dt
            obj.position[2] += obj.velocity[2] * dt

        self._time += dt

    def _snapshot(self) -> dict[str, Any]:
        snap: dict[str, Any] = {"time": round(self._time, 6)}
        for name, obj in self._objects.items():
            snap[name] = {
                "position": list(obj.position),
                "velocity": list(obj.velocity),
            }
        return snap

    def _gravity_force(self, a: Object, b: Object) -> list[float]:
        dx = b.position[0] - a.position[0]
        dy = b.position[1] - a.position[1]
        dz = b.position[2] - a.position[2]
        r2 = dx * dx + dy * dy + dz * dz
        if r2 < 1e-20:
            return [0.0, 0.0, 0.0]
        r = math.sqrt(r2)
        mag = self._g * a.mass * b.mass / r2
        return [mag * dx / r, mag * dy / r, mag * dz / r]

    # ------------------------------------------------------------------
    # BaseEnv requires step() — delegate to internal
    # ------------------------------------------------------------------

    def step(self, dt: float = 0.01) -> dict[str, Any]:
        self._dt = dt
        self._step_internal()
        return self._snapshot()
