"""Simulation package with lazy exports for standalone render tools."""
from importlib import import_module

_EXPORTS = {
    'SimulationRenderer': ('src.simulation.renderer', 'SimulationRenderer'),
    'Snapshot': ('src.simulation.snapshot', 'Snapshot'),
    'load_config': ('src.simulation.config', 'load_config'),
    'build_env_from_config': ('src.simulation.config', 'build_env_from_config'),
    'build_task_from_config': ('src.simulation.config', 'build_task_from_config'),
    'build_renderer_from_config': ('src.simulation.config', 'build_renderer_from_config'),
}


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(name)
    module, attr = _EXPORTS[name]
    value = getattr(import_module(module), attr)
    globals()[name] = value
    return value


__all__ = list(_EXPORTS)
