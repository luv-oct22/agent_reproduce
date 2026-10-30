"""Create the scene-bound central_force_dynamics_g1 horizontal-projection baseline."""
from copy import deepcopy
import json
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / 'world_instances' / 'attraction' /
          'central_force_dynamics_g1' / 'baseline' / 'instance.json')
OUT = (ROOT / 'world_instances' / 'attraction' /
       'central_force_dynamics_g1' / 'baseline')


def main():
    source_record = json.loads(SOURCE.read_text())
    payload = deepcopy(source_record['payload'])
    payload['provenance'] = {
        'authoring_version': 'central_force_dynamics_g1_horizontal_v1',
        'family': 'attraction',
        'group_id': 'central_force_dynamics_g1',
        'world_role': 'baseline',
        'scene_ids': ['horizontal_projection_001'],
        'equation_slots': ['pair_force', 'acceleration', 'radial_motion_optional'],
        'constants': {'strength_field': 'strength', 'distance_exponent': 2},
    }
    record_body = {'format': 'world_instance', 'schema_version': 1, 'payload': payload}
    encoded = json.dumps(record_body, sort_keys=True, separators=(',', ':'), allow_nan=False)
    record_id = 'sha256:' + hashlib.sha256(encoded.encode()).hexdigest()
    instance = {
        'format': 'world_instance', 'schema_version': 1, 'visibility': 'host_only',
        'record_id': record_id, 'payload': payload,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / 'instance.json'
    if target.exists() and json.loads(target.read_text()) != instance:
        raise FileExistsError(f'Different record already exists: {target}')
    if not target.exists():
        target.write_text(json.dumps(instance, indent=2) + '\n')
    scene = {
        'schema_version': 1,
        'scene_id': 'horizontal_projection_001',
        'family': 'attraction',
        'group_id': 'central_force_dynamics_g1',
        'world_id': record_id,
        'world_role': 'baseline',
        'equation_slots': ['pair_force', 'acceleration'],
        'optional_equation_slots': ['radial_motion'],
        'initial_state': {
            'anchor': {'position_m': [0.0, 0.0, 0.0], 'velocity_m_s': [0.0, 0.0, 0.0]},
            'probe': {'position_m': [1.5, 0.0, 1.0], 'velocity_m_s': [0.0, 0.8, 0.0]},
            'time_s': 0.0,
        },
        'surface_friction': None,
        'baseline_binding': {
            'required': True,
            'reason': 'Horizontal projection has no rough-surface friction constant.',
        },
    }
    (OUT / 'scenes').mkdir(exist_ok=True)
    (OUT / 'scenes' / 'horizontal_projection_001.json').write_text(
        json.dumps(scene, indent=2) + '\n'
    )
    print(record_id)


if __name__ == '__main__':
    main()
