"""Generate deterministic Rule 1 question specifications for central_force_dynamics_g1."""
import hashlib
import json
import math
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = (ROOT / 'world_instances' / 'attraction' / 'central_force_dynamics_g1' / 'rule_1')
BASELINE_PATH = ROOT / 'world_instances' / 'attraction' / 'central_force_dynamics_g1' / 'baseline' / 'instance.json'

VARIANTS = {
    'variant_1': {'q': 0.7, 'alpha': 1.0, 'beta': 1.0, 'p': 2.7, 's': 0.0},
    'variant_2': {'q': 1.3, 'alpha': 1.0, 'beta': 1.0, 'p': 1.3, 's': 0.0},
    'variant_3': {'q': 0.9, 'alpha': 1.0, 'beta': 1.0, 'p': 2.0, 's': 0.4},
    'variant_4': {'q': 1.1, 'alpha': 1.0, 'beta': 1.0, 'p': 2.0, 's': -0.6},
    'variant_5': {'q': 0.8, 'alpha': 1.2, 'beta': 0.8, 'p': 2.7, 's': 0.4},
    'variant_6': {'q': 1.2, 'alpha': 0.8, 'beta': 1.2, 'p': 1.3, 's': -0.6},
}


def rounded(value):
    return round(value, 1)


def sample_state(rng):
    anchor = [rounded(rng.uniform(-0.5, 0.5)) for _ in range(3)]
    while True:
        offset = [rounded(rng.uniform(-1.2, 1.2)) for _ in range(3)]
        distance = math.sqrt(sum(value * value for value in offset))
        if 0.8 <= distance <= 2.4:
            break
    probe = [rounded(a + b) for a, b in zip(anchor, offset)]
    velocity = [rounded(rng.uniform(-1.2, 1.2)) for _ in range(3)]
    return {
        'anchor_center_m': anchor,
        'probe_center_m': probe,
        'probe_initial_velocity_m_s': velocity,
        'start_time_s': rounded(rng.uniform(0.0, 5.0)),
        'probe_offset_distance_m': rounded(distance),
    }


def main():
    baseline = json.loads(BASELINE_PATH.read_text())
    baseline_payload = baseline['payload']
    baseline_world = baseline_payload['world']['payload']
    baseline_law = baseline_world['laws'][0]['payload']
    baseline_field = baseline_world['fields'][0]['payload']
    group_constants = {
        'strength_N': baseline_field['parameters']['value'],
        'reference_distance_m': baseline_law['parameters']['reference_distance_m'],
        'reference_mass_kg': baseline_law['parameters']['reference_mass_kg'],
        'minimum_distance_m': baseline_law['parameters']['minimum_distance_m'],
        'baseline_exponent_p': baseline_law['parameters']['exponent'],
    }
    for variant_id, equation in VARIANTS.items():
        target = OUT / variant_id
        target.mkdir(parents=True, exist_ok=True)
        for index in range(1, 16):
            seed_text = f'central_force_dynamics_g1:{variant_id}:{index}'
            seed = int.from_bytes(hashlib.sha256(seed_text.encode()).digest()[:8], 'big')
            rng = random.Random(seed)
            record = {
                'schema_version': 1,
                'question_id': f'{variant_id}_q{index:02d}',
                'family': 'attraction',
                'group_id': 'central_force_dynamics_g1',
                'rule': 'rule_1',
                'variant_id': variant_id,
                'hidden_equation_parameters': equation,
                'intrinsic_objects': {
                    'anchor': {'mass_kg': 1.0, 'color': 'orange', 'motion': 'fixed'},
                    'probe': {'mass_kg': 0.1, 'color': 'blue', 'motion': 'dynamic'},
                },
                'scene_state': sample_state(rng),
                'pairing': {
                    'baseline_group': 'central_force_dynamics_g1',
                    'reuse_scene_state_for_baseline': True,
                },
            }
            question_dir = target / f'q{index:02d}'
            question_dir.mkdir(parents=True, exist_ok=True)
            public_record = {
                key: record[key] for key in
                ('schema_version', 'question_id', 'family', 'group_id', 'rule', 'variant_id', 'pairing')
            }
            (question_dir / 'question.json').write_text(json.dumps(public_record, indent=2) + '\n')
            # Host-only resolved episode record. The agent receives only the
            # public environment observation; this file is used by render,
            # interaction, and evaluation hosts to apply the hidden values.
            instance = {
                'format': 'question_instance',
                'schema_version': 1,
                'visibility': 'host_only',
                'question': record,
                'baseline_world': {
                    'path': 'baseline/instance.json',
                    'record_id': baseline['record_id'],
                    'constants': group_constants,
                },
                'resolved_environment': {
                    'equation': equation,
                    'scene_state': record['scene_state'],
                    'intrinsic_objects': record['intrinsic_objects'],
                },
            }
            (question_dir / 'instance.json').write_text(json.dumps(instance, indent=2) + '\n')
    print(f'generated {len(VARIANTS) * 15} question specifications under {OUT}')


if __name__ == '__main__':
    main()
