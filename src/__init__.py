"""Lazy public exports; rendering does not require model-provider packages."""
from importlib import import_module

_EXPORTS = {
    'ModelHarness': ('src.harness', 'ModelHarness'), 'OpenAIHarness': ('src.harness', 'OpenAIHarness'),
    'ChatResponse': ('src.harness', 'ChatResponse'), 'Message': ('src.harness', 'Message'),
    'ToolCall': ('src.harness', 'ToolCall'), 'ToolDef': ('src.harness', 'ToolDef'), 'Usage': ('src.harness', 'Usage'),
    'Object': ('src.objects', 'Object'), 'Ball': ('src.objects', 'Ball'), 'Block': ('src.objects', 'Block'),
    'Cup': ('src.objects', 'Cup'), 'Box': ('src.objects', 'Box'), 'Spring': ('src.objects', 'Spring'),
    'Rope': ('src.objects', 'Rope'), 'BaseEnv': ('src.envs', 'BaseEnv'),
    'GravityFieldEnv': ('src.envs', 'GravityFieldEnv'), 'SpringSystemEnv': ('src.envs', 'SpringSystemEnv'),
    'BaseTask': ('src.tasks', 'BaseTask'), 'ShootBallTask': ('src.tasks', 'ShootBallTask'),
    'get_task': ('src.tasks', 'get_task'), 'list_tasks': ('src.tasks', 'list_tasks'),
    'NewtonBenchEnv': ('src.newtonbench_env', 'NewtonBenchEnv'),
}


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attribute = _EXPORTS[name]
    value = getattr(import_module(module_name), attribute)
    globals()[name] = value
    return value


__all__ = list(_EXPORTS)
