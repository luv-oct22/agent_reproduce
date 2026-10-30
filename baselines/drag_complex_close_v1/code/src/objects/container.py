from __future__ import annotations

from dataclasses import dataclass
from .base import Object


@dataclass
class Cup(Object):
    capacity: float = 0.25
    material: str = "ceramic"
    filled_fraction: float = 0.0


@dataclass
class Box(Object):
    width: float = 0.3
    height: float = 0.3
    depth: float = 0.3
    material: str = "cardboard"
    is_open: bool = True
