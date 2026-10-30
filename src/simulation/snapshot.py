from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Snapshot:
    time: float
    step: int
    objects: dict[str, dict] = field(default_factory=dict)
    image_path: str | None = None

    @staticmethod
    def from_history_entry(entry: dict, step: int) -> Snapshot:
        objects = {}
        for key, val in entry.items():
            if key == "time":
                continue
            if isinstance(val, dict) and "position" in val:
                objects[key] = val
        return Snapshot(time=entry["time"], step=step, objects=objects)
