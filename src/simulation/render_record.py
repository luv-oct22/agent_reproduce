"""Write human-readable render records; also importable by Blender's Python.

This module intentionally uses only the standard library.
"""
from datetime import datetime, timezone
import json
import math
from pathlib import Path


def capture_metadata(config, env, config_path):
    """Capture resolved runtime values, including defaults omitted from YAML."""
    params = dict(config['env'].get('params', {}))
    for key, attribute in {
        'dt': '_dt', 'total_steps': '_total_steps', 'uniform_gravity': '_uniform_gravity',
        'g_constant': '_g', 'table_height': 'table_height', 'table_bounds': 'table_bounds',
        'cup_position': 'cup_position', 'cup_radius': 'cup_radius',
        'cup_height': 'cup_height', 'ball_radius': 'ball_radius', 'restitution': 'restitution',
    }.items():
        if hasattr(env, attribute):
            params[key] = getattr(env, attribute)
    return {'config_path': str(Path(config_path).resolve()), 'config': config,
            'env_type': config['env']['type'], 'resolved_env_params': params,
            'object_masses': {name: obj.mass for name, obj in env._objects.items()}}


def scene_settings(scene):
    """Read actual Blender settings, including edits made to a saved .blend."""
    result = {
        'Engine': scene.render.engine, 'Render device': scene.cycles.device,
        'Samples': scene.cycles.samples, 'Denoising': scene.cycles.use_denoising,
        'Resolution': [round(scene.render.resolution_x*scene.render.resolution_percentage/100),
                       round(scene.render.resolution_y*scene.render.resolution_percentage/100)],
        'Scene FPS': scene.render.fps/scene.render.fps_base,
        'Colour transform': scene.view_settings.view_transform,
        'Exposure': scene.view_settings.exposure, 'Render seed': scene.cycles.seed,
    }
    if scene.camera:
        camera = scene.camera
        result['Actual camera'] = {
            'position_m': list(camera.matrix_world.translation),
            'rotation_euler_rad': list(camera.rotation_euler), 'lens_mm': camera.data.lens,
            'depth_of_field': camera.data.dof.use_dof,
            'fstop': camera.data.dof.aperture_fstop,
            'focus_distance_m': camera.data.dof.focus_distance,
        }
    return result


def _value(value):
    if isinstance(value, float):
        return f'{value:.9g}'
    if isinstance(value, (list, tuple, dict, bool)) or value is None:
        return json.dumps(value, ensure_ascii=False)
    return str(value).replace('|', '\\|').replace('\n', '<br>')


def _table(values):
    rows = ['| Parameter | Value |', '|---|---|']
    def flatten(items, prefix=''):
        for key, value in items.items():
            label = f'{prefix}.{key}' if prefix else key
            if isinstance(value, dict):
                yield from flatten(value, label)
            else:
                yield f'| {_value(label)} | {_value(value)} |'
    return '\n'.join(rows + list(flatten(values)))


def write_record(directory, data, settings, artifact):
    """Save a record per output and a convenient latest-record parameters.md."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    metadata = data.get('parameter_metadata', {})
    env = dict(metadata.get('resolved_env_params', data.get('env_params', {})))
    scene = data.get('scene', {})
    lab = metadata.get('env_type') == 'robotics_lab' or scene.get('style') == 'robotics_lab'
    inferred = not bool(metadata)
    if lab:
        env.setdefault('uniform_gravity', [0, 0, -9.8])
        env.setdefault('restitution', .28)
        env['cup_wall_thickness_m'] = .008
        env['cup_bottom_thickness_m'] = .012
    history = data.get('history', [])
    initial = history[0] if history else {}
    objects = {}
    names = data.get('object_names', [key for key, value in initial.items() if isinstance(value, dict)])
    for name in names:
        obj = initial[name]
        objects[name] = {'release_position_m': obj['position'], 'release_velocity_m_s': obj['velocity']}
        if 'object_radius' in data:
            objects[name]['rendered_radius_m'] = data['object_radius']
        objects[name]['mass_kg'] = metadata.get('object_masses', {}).get(name, 'not recorded')
    if names and env.get('cup_position') is not None:
        ball, cup = initial[names[0]]['position'], env['cup_position']
        objects['Horizontal release-to-cup distance (m)'] = math.hypot(ball[0]-cup[0], ball[1]-cup[1])
    timing = {'Time step (s)': data.get('dt', env.get('dt')),
              'Simulation states': len(history),
              'Post-release simulation duration (s)': history[-1]['time'] if history else None}
    motion = {key: value for key, value in data.get('animation', {}).items() if key != 'samples'}
    sections = [f'# Render parameters — {Path(artifact).name}',
                f'Recorded at {datetime.now(timezone.utc).isoformat(timespec="seconds")}.',
                'Coordinates are [x, y, z] in metres, with Z upward. Cup position denotes the opening centre.',
                '## Ball and placement\n\n' + _table(objects),
                '## Physics and environment\n\n' + _table(env),
                '## Simulation timing\n\n' + _table(timing),
                '## Scene, robot and configured camera\n\n' + _table(scene),
                '## Planned robot motion\n\n' + _table(motion),
                '## Render and playback\n\n' + _table(settings)]
    if metadata.get('config_path'):
        sections.append('Source configuration: ' + metadata['config_path'])
    if inferred:
        sections.append('This history predates automatic parameter capture. Omitted laboratory gravity and '
                        'restitution use the renderer workflow defaults; unrecorded masses are marked above.')
    sections.append('Video retiming changes playback speed only; it does not change the recorded launch velocity or physics.')
    contents = '\n\n'.join(sections) + '\n'
    path = directory / f'{Path(artifact).stem}_parameters.md'
    path.write_text(contents)
    (directory / 'parameters.md').write_text(contents)
    return path
