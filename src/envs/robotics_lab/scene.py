"""Tabletop projectile environment in metres, with a cup and solid work surface.

The robot is a visual fixture (static or kinematically animated); actions set ball velocity.
Contact is a simple sphere/plane and cylindrical-container approximation, not a
robot dynamics or general rigid-body solver.
"""
from __future__ import annotations

import math

from src.envs.gravity_field.scene import GravityFieldEnv
from src.envs.registry import register_env
from src.objects.cup_geometry import WALL_THICKNESS, cup_body_distance, cup_profile


@register_env("robotics_lab")
class RoboticsLabEnv(GravityFieldEnv):
    def __init__(
        self, dt=0.001, total_steps=1600, uniform_gravity=None,
        table_height=0.86, table_bounds=(-1.4, 1.6, -0.7, 0.7),
        cup_position=(0.85, -0.12, 1.08), cup_radius=0.105,
        cup_height=0.22, ball_radius=0.04, restitution=0.28,
    ):
        super().__init__(g_constant=0, dt=dt, total_steps=total_steps,
                         uniform_gravity=uniform_gravity or [0, 0, -9.8])
        if cup_radius <= ball_radius or ball_radius <= 0:
            raise ValueError("Cup radius must exceed the positive ball radius.")
        self.table_height = table_height
        self.table_bounds = tuple(table_bounds)
        self.cup_position = list(cup_position)
        self.cup_radius = cup_radius
        self.cup_height = cup_height
        self.ball_radius = ball_radius
        self.restitution = restitution
        self._cup_profile = cup_profile(cup_radius, cup_height)
        self._inside_cup: set[str] = set()

    def configure(self, objects):
        super().configure(objects)
        self._inside_cup.clear()

    def reset(self):
        super().reset()
        self._inside_cup.clear()

    def _step_internal(self):
        # Keep motion per contact step below both the ball and wall thickness.
        # This prevents fast balls from crossing an entire wall between checks.
        dt, start_time = self._dt, self._time
        speed = max((math.sqrt(sum(v*v for v in obj.velocity))
                     for obj in self._objects.values() if obj.mass > 0), default=0)
        acceleration = math.sqrt(sum(g*g for g in self._uniform_gravity))
        travel = (speed + acceleration*dt)*dt
        steps = max(1, math.ceil(travel/min(self.ball_radius/4, WALL_THICKNESS/2)))
        try:
            self._dt = dt/steps
            for _ in range(steps):
                super()._step_internal()
                self._resolve_contacts()
        finally:
            self._dt = dt
        self._time = start_time + dt

    def _resolve_contacts(self):
        cx, cy, rim = self.cup_position
        radius = self.ball_radius
        xmin, xmax, ymin, ymax = self.table_bounds
        for name, obj in self._objects.items():
            if obj.mass <= 0:
                continue
            p, v = obj.position, obj.velocity
            supported = False
            # Alternate constraints where the ceramic wall meets the tabletop.
            for _ in range(4):
                surface = self.table_height if xmin <= p[0] <= xmax and ymin <= p[1] <= ymax else 0.0
                if p[2] < surface + radius:
                    p[2] = surface + radius
                    self._bounce(v, (0, 0, 1))
                    supported = True
                distance, normal = cup_body_distance(p, self.cup_position, self._cup_profile)
                if distance >= radius:
                    break
                for axis in range(3):
                    p[axis] += (radius-distance+1e-9)*normal[axis]
                self._bounce(v, normal)
                supported |= normal[2] > 0.5
            if supported:
                damping = math.exp(-8.0 * self._dt)
                v[0] *= damping
                v[1] *= damping
            if (math.hypot(p[0]-cx, p[1]-cy) <= self.cup_radius-radius+1e-6
                    and rim-self.cup_height < p[2] < rim):
                self._inside_cup.add(name)
            else:
                self._inside_cup.discard(name)

    def _bounce(self, velocity, normal):
        incoming = sum(v*n for v, n in zip(velocity, normal))
        if incoming < 0:
            restitution = self.restitution if abs(incoming) > 0.12 else 0
            for axis in range(3):
                velocity[axis] -= (1+restitution)*incoming*normal[axis]
