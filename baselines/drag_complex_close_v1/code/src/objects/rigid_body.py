from __future__ import annotations

from dataclasses import dataclass
from .base import Object


@dataclass
class Ball(Object):
    radius: float = 0.1
    material: str = "rubber"
    elasticity: float = 0.8


@dataclass
class Block(Object):
    width: float = 0.1
    height: float = 0.1
    depth: float = 0.1
    material: str = "wood"
