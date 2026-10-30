from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Object:
    name: str
    mass: float = 1.0
    position: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    velocity: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    color: str = "gray"
    temperature: float = 300.0
    charge: float = 0.0

    def describe(self) -> str:
        return f"{self.name}(mass={self.mass}, pos={self.position})"
