"""Portable project-root paths for records and user-facing logs."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def display_path(path) -> str:
    """Render a path as agent_reproduce/<relative path>, never host-absolute."""
    value = Path(path)
    try:
        relative = value.resolve().relative_to(PROJECT_ROOT)
        return str(Path('agent_reproduce') / relative)
    except ValueError:
        return str(value)
