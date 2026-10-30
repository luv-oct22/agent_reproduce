from __future__ import annotations

import math
from typing import Any

from src.tasks.base import BaseTask
from src.tasks.registry import register_task
from src.envs.gravity_field.scene import GravityFieldEnv


@register_task("shoot_ball")
class ShootBallTask(BaseTask):

    def __init__(
        self,
        env: GravityFieldEnv | None = None,
        cup_position: list[float] | None = None,
        cup_radius: float = 0.3,
        ball_position: list[float] | None = None,
        ball_radius: float = 0.05,
        g: float = 9.8,
        dt: float = 0.001,
        total_steps: int = 5000,
    ):
        if env is None:
            env = GravityFieldEnv(
                g_constant=0,
                dt=dt,
                total_steps=total_steps,
                uniform_gravity=[0.0, 0.0, -g],
            )
        super().__init__(env)
        self._cup_pos = cup_position or [5.0, 0.0, 0.0]
        self._cup_radius = cup_radius
        self._ball_pos = ball_position or [0.0, 0.0, 0.0]
        self._ball_radius = ball_radius
        self._g = g

    def setup(self) -> None:
        pass

    def get_prompt(self) -> str:
        return (
            f"You are throwing a ball into a cup.\n"
            f"Ball starts at position {self._ball_pos} with radius {self._ball_radius}.\n"
            f"Cup is at position {self._cup_pos} with opening radius {self._cup_radius}.\n"
            f"Gravity pulls downward along the z-axis at g={self._g} m/s^2.\n"
            f"Set the ball's initial velocity [vx, vy, vz] so that it lands in the cup."
        )

    def get_action_space(self) -> dict[str, Any]:
        return {
            "vx": {"type": "float", "description": "Initial velocity in x"},
            "vy": {"type": "float", "description": "Initial velocity in y"},
            "vz": {"type": "float", "description": "Initial velocity in z"},
        }

    def apply_action(self, action: dict[str, Any]) -> None:
        vx = float(action.get("vx", 0.0))
        vy = float(action.get("vy", 0.0))
        vz = float(action.get("vz", 0.0))

        env: GravityFieldEnv = self._env  # type: ignore[assignment]
        env.configure([
            {
                "name": "ball",
                "mass": 0.1,
                "position": list(self._ball_pos),
                "velocity": [vx, vy, vz],
            },
        ])

    def evaluate(self) -> dict[str, Any]:
        env: GravityFieldEnv = self._env  # type: ignore[assignment]
        env.run()
        obs = env.observe()

        positions = obs["objects"]["ball"]["position"]
        min_dist = float("inf")
        landed = False

        for pos in positions:
            dx = pos[0] - self._cup_pos[0]
            dy = pos[1] - self._cup_pos[1]
            dz = pos[2] - self._cup_pos[2]
            horiz = math.sqrt(dx * dx + dy * dy)
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)

            if dist < min_dist:
                min_dist = dist

            if horiz <= self._cup_radius and abs(dz) <= self._cup_radius:
                landed = True
                break

        return {
            "success": landed,
            "min_distance_to_cup": round(min_dist, 4),
            "cup_position": self._cup_pos,
            "total_time": obs["time"][-1],
        }
