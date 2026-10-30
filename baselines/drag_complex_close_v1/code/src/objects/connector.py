from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from .base import Object


@dataclass
class Spring(Object):
    stiffness: float = 100.0
    rest_length: float = 0.5
    damping: float = 0.0
    attached_a: Optional[str] = None
    attached_b: Optional[str] = None


@dataclass
class Rope(Object):
    length: float = 1.0
    material: str = "nylon"
    attached_a: Optional[str] = None
    attached_b: Optional[str] = None
