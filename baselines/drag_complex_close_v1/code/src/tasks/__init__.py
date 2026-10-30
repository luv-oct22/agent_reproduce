from .base import BaseTask
from .registry import TASK_REGISTRY, register_task, get_task, list_tasks
from .shoot_ball import ShootBallTask
from .identify_material import IdentifyMaterialTask
from .identify_world import IdentifyWorldTask
from .identify_bounce import IdentifyBounceTask
from .identify_drag import IdentifyDragTask

__all__ = [
    "BaseTask",
    "TASK_REGISTRY",
    "register_task",
    "get_task",
    "list_tasks",
    "ShootBallTask",
    "IdentifyMaterialTask",
    "IdentifyWorldTask",
    "IdentifyBounceTask",
    "IdentifyDragTask",
]
