"""Hard density questions: mass sums, unseen materials and cancellation of unknowns."""
import argparse
from collections import Counter
from copy import deepcopy
from itertools import combinations_with_replacement
import json
import math
from pathlib import Path
import random

from src.objects.registry import ObjectRegistry
from src.objects.specimen import Specimen, COLORS
from src.simulation.balance_scene import build_manifest, build_question, write_bundle


def sign_answer(value):
    return 'C' if math.isclose(value, 0, abs_tol=1e-7) else ('A' if value > 0 else 'B')


def evidence_answer(left, right, known):
    """Resolve the sign of sum(count * density) for any positive unseen densities.

    Each same-appearance material has one shared unknown density. Equal volume
    is common to every object and cancels. Hidden evaluation densities are never used.
    """
    coefficients = Counter(left)
    coefficients.subtract(right)
    constant = sum(count*known[key].density_kg_m3 for key, count in coefficients.items() if key in known)
    unknown = {key: count for key, count in coefficients.items() if key not in known and count}
    if not unknown:
        return sign_answer(constant), {'known_density_difference': constant, 'unknown_coefficients': unknown}
    if all(count > 0 for count in unknown.values()) and constant >= -1e-7:
        answer = 'A'
    elif all(count < 0 for count in unknown.values()) and constant <= 1e-7:
        answer = 'B'
    else:
        answer = 'D'
    return answer, {'known_density_difference': constant, 'unknown_coefficients': unknown}


def make_evaluation_registry(registry, seed):
    rng = random.Random(seed)
    used_colors = {obj.color.lower() for obj in registry.specimens}
    used_rgba = {obj.color_rgba for obj in registry.specimens}
    candidates = [name for name in ('red', 'yellow', 'white', 'black', 'gray')
                  if name not in used_colors and COLORS[name] not in used_rgba]
    if len(candidates) < 2:
        raise ValueError('Need two unused colors for unseen evaluation materials.')
    unseen = tuple(Specimen(f'unseen_{i+1}', rng.uniform(350, 1900)*60e-6, 60e-6, color)
                   for i, color in enumerate(candidates[:2]))
    if set(obj.specimen_id for obj in unseen) & set(obj.specimen_id for obj in registry.specimens):
        raise ValueError('Unseen material IDs conflict with the experiment registry.')
    return ObjectRegistry(registry.specimens+unseen, seed=seed), unseen


def build_multi_manifest(registry, evaluation_registry, left, right, question_id, category, volume_ml=60):
    if not all(1 <= len(pan) <= 3 for pan in (left, right)):
        raise ValueError('Each pan must hold one to three objects.')
    catalog = {obj.specimen_id: obj for obj in evaluation_registry.specimens}
    known = {obj.specimen_id: obj for obj in registry.specimens}
    for key, obj in known.items():
        if key not in catalog or catalog[key] != obj:
            raise ValueError('Evaluation registry must preserve every experimental specimen.')
    # Reuse the established scene defaults, validating IDs and sample size.
    manifest = build_manifest(evaluation_registry, left[0], right[0], volume_ml)
    manifest.update(schema_version=2, object_registry_id=registry.registry_id,
                    evaluation_registry_id=evaluation_registry.registry_id,
                    question_id=question_id, category=category, show_specimen_labels=False,
                    transfer='Every instance has equal volume; known densities and appearances transfer. '
                             'Unseen materials exist only in the evaluation registry.')
    manifest['objects'] = {}
    for side, keys in [('left', left), ('right', right)]:
        items = []
        for index, key in enumerate(keys):
            record = build_manifest(evaluation_registry, key, key, volume_ml)['objects']['left']
            record.update(instance_id=f'{side}_{index+1}', seen_in_experiments=key in known)
            # Symmetric side-by-side placement keeps objects separated and countable.
            record['pan_offset_m'] = [(index-(len(keys)-1)/2)*(record['side_length_m']+.012), 0]
            items.append(record)
        manifest['objects'][side] = items
    manifest['balance'].update(arm_length_m=.27, pan_radius_m=.12)
    manifest['answer'], evidence = evidence_answer(left, right, known)
    manifest['grading'] = dict(evidence, basis='identifiability_from_experimental_materials',
                               physical_answer=sign_answer(sum(catalog[k].density_kg_m3 for k in left)
                                                           -sum(catalog[k].density_kg_m3 for k in right)))
    return manifest


def prepare_challenge(registry_path, output_dir, volume_ml=60, seed=17):
    registry = ObjectRegistry.load(registry_path)
    known = {obj.specimen_id: obj for obj in registry.specimens}
    if len(known) < 3 or len({obj.color_rgba for obj in known.values()}) != len(known):
        raise ValueError('Hard suite needs at least three visually distinct known materials.')
    evaluation_registry, unseen = make_evaluation_registry(registry, seed)
    rng = random.Random(seed)
    ids = sorted(known)
    pool = [list(items) for size in (1, 2, 3) for items in combinations_with_replacement(ids, size)]
    buckets = {key: [] for key in 'ABC'}
    for left in pool:
        for right in pool:
            if len(left)+len(right) < 3:
                continue
            answer, _ = evidence_answer(left, right, known)
            buckets[answer].append((left, right, 'known_mass_sum'))
    cases = []
    for answer, candidates in buckets.items():
        rng.shuffle(candidates)
        # Prefer genuine sum comparisons over exactly identical pan contents.
        candidates.sort(key=lambda case: (case[0] == case[1], len(case[0]) == len(case[1])))
        if len(candidates) < 6:
            raise ValueError(f'Not enough {answer} cases for this registry.')
        cases.extend(candidates[:6])
    a, b, c = ids[:3]
    u, v = [obj.specimen_id for obj in unseen]
    for new, other in ((u, v), (v, u)):
        cases += [([new], [a], 'unseen_ambiguous'),
                  ([a, b], [new], 'unseen_ambiguous'),
                  ([new, new], [c], 'unseen_ambiguous'),
                  ([b], [new, other], 'unseen_ambiguous')]
    ordered = sorted(ids, key=lambda key: known[key].density_kg_m3)
    lo, hi = ordered[0], ordered[-1]
    if sign_answer(known[hi].density_kg_m3-known[lo].density_kg_m3) != 'A':
        raise ValueError('Need different known densities for the cancellation controls.')
    for new in (u, v):
        cases += [([new, hi], [new, lo], 'unseen_cancels'),
                  ([new, lo], [new, hi], 'unseen_cancels'),
                  ([new, a], [new, a], 'unseen_cancels')]
    # Avoid blocks of identical answers or categories in the evaluation order.
    rng.shuffle(cases)
    manifests = [build_multi_manifest(registry, evaluation_registry, left, right,
                                     f'density_hard_{i:03d}', category, volume_ml)
                 for i, (left, right, category) in enumerate(cases, 1)]
    root = Path(output_dir)
    if root.exists() and any(root.iterdir()):
        raise FileExistsError('Use a new output directory for a hard question suite.')
    root.mkdir(parents=True, exist_ok=True)
    registry.save(root/'object_registry.json')
    registry.write_markdown(root/'object_registry.md')
    evaluation_registry.save(root/'evaluation_registry.json')
    evaluation_registry.write_markdown(root/'evaluation_registry.md')
    questions, entries = [], []
    for i, manifest in enumerate(manifests, 1):
        folder = f'questions/q{i:03d}'
        write_bundle(registry, root/folder, manifest)
        question = build_question(manifest)
        question['context_image'] = folder+'/'+question['context_image']
        for choice in question['choices']:
            choice['image'] = folder+'/'+choice['image']
        questions.append(question)
        entries.append({'folder': folder, 'category': manifest['category'],
                        'left': [o['source_specimen_id'] for o in manifest['objects']['left']],
                        'right': [o['source_specimen_id'] for o in manifest['objects']['right']]})
    batch = {'format': 'density_balance_batch', 'schema_version': 2, 'suite': 'hard',
             'object_registry_id': registry.registry_id, 'evaluation_registry_id': evaluation_registry.registry_id,
             'volume_ml': volume_ml, 'include_reversed': False, 'seed': seed, 'questions': entries,
             'answer_counts': dict(Counter(q['answer'] for q in questions)),
             'grading': 'Evidence-based: unknown densities are arbitrary positive values; shared unknowns can cancel.'}
    (root/'batch.json').write_text(json.dumps(batch, indent=2)+'\n')
    (root/'questions.json').write_text(json.dumps(questions, indent=2)+'\n')
    (root/'parameters.md').write_text('# Hard density evaluation (host-only)\n\n```json\n'+json.dumps(batch, indent=2)+'\n```\n')
    (root/'README.md').write_text('# Hard density balance\n\n32 questions, 160 images after rendering. '
        'Each pan holds one to three equal-volume objects.\n\n'
        '18 known-material mass sums; 8 ambiguous unseen-material questions; '
        '6 questions in which unseen materials cancel. Eight correct answers per choice.\n\n'
        'object_registry.json is the experiment registry. evaluation_registry.json additionally contains '
        'unseen materials and must not be used to initialize the experiment.\n\n'
        'The model sees neither color names nor specimen IDs in question text, and the scenes have no ID labels.\n')
    links = ''.join(f'<li><a href="{e["folder"]}/index.html">Question {i}</a></li>' for i, e in enumerate(entries, 1))
    (root/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Hard density questions</title>'
                                 '<h1>Hard density questions</h1><ol>'+links+'</ol>')
    return batch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--volume-ml', type=float, default=60)
    parser.add_argument('--seed', type=int, default=17)
    args = parser.parse_args()
    batch = prepare_challenge(args.registry, args.output_dir, args.volume_ml, args.seed)
    print(f"Prepared {len(batch['questions'])} hard questions; answers: {batch['answer_counts']}")


if __name__ == '__main__':
    main()
