"""Prepare and validate paired attraction image questions without rendering pixels."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import random
import struct
import subprocess

from src.worlds.attraction import AttractionWorld, DomainError, MotionState
from src.simulation.attraction_visual import (
    IMAGES, POLICY, CAMERA, ANCHOR, digest, projected, geometry, validate_projections,
)
from src.worlds.definition import FieldSpec, LawSpec, ObjectSpec, SolverSpec, WorldInstance, WorldSpec


def variant(instance, exponent, strength, half_step=False):
    data = instance.payload
    world = data['world']['payload']
    law = world['laws'][0]['payload']
    law['parameters']['exponent'] = exponent
    world['laws'][0] = LawSpec(law).to_dict()
    field = world['fields'][0]['payload']
    field['parameters']['value'] = strength
    world['fields'][0] = FieldSpec(field).to_dict()
    data['world'] = WorldSpec(world).to_dict()
    if half_step:
        solver = data['solver']['payload']
        solver['parameters']['max_step_s'] /= 2
        data['solver'] = SolverSpec(solver).to_dict()
    return WorldInstance(data)


def initial_state(instance, launch):
    return AttractionWorld(instance).make_state(
        {'anchor': ANCHOR, 'probe': launch['position_m']},
        {'anchor': [0., 0., 0.], 'probe': launch['velocity_m_s']}, launch['start_time_s'])


def simulate(instance, launch):
    return AttractionWorld(instance).advance(initial_state(instance, launch), launch['duration_s'])


def probe(state):
    return state.payload['objects']['probe']['position_m']


def _cluster(instances, index, ranks):
    radius = [1.25, 1.4, 1.35, 1.7, .65, .72, .8, .88][index]
    angle = math.radians([0, 15, -15, 30, 180, 165, 195, 150][index])
    radial = [math.cos(angle), 0., math.sin(angle)]
    tangent = [-math.sin(angle), 0., math.cos(angle)]
    speed = [.2, .25, .2, .25, .3, .3, .35, .35][index]
    launch = dict(position_m=[round(a+radius*r, 6) for a, r in zip(ANCHOR, radial)],
                  velocity_m_s=[round(speed*t, 6) for t in tangent], start_time_s=float(2*index), duration_s=.1)
    # Match truth distance to the predeclared rank gap; no model or shortcut
    # scores are consulted while selecting durations or candidate strengths.
    target = .024*abs(ranks[0]-ranks[1])
    low, high = .02, .1

    def states_at(duration):
        return [simulate(w, dict(launch, duration_s=duration)) for w in instances]

    while True:
        states = states_at(high)
        if math.dist(*map(probe, states)) >= target:
            break
        low, high = high, high+.05
        if high > 1.6:
            raise ValueError('Cannot separate paired true predictions.')
    for _ in range(16):
        mid = (low+high)/2
        if math.dist(*map(probe, states_at(mid))) < target:
            low = mid
        else:
            high = mid
    # Displayed time exactly matches the simulated time.
    launch['duration_s'] = round((low+high)/2, 4)
    truth = [simulate(w, launch) for w in instances]
    direction = [b-a for a, b in zip(probe(truth[0]), probe(truth[1]))]
    length = math.hypot(*direction)
    direction = [v/length for v in direction]
    origin = probe(truth[0])

    def coordinate(state):
        return sum((v-a)*d for v, a, d in zip(probe(state), origin, direction))

    choices = {rank: dict(instance=w.to_dict(), state=s.to_dict())
               for rank, w, s in zip(ranks, instances, truth)}
    for rank in set(range(4))-set(ranks):
        target_coordinate = (rank-ranks[0])/(ranks[1]-ranks[0])*length
        # A positive strength scan brackets the requested nearby pose. Invalid
        # trajectories are rejected, never replaced with manually moved spheres.
        samples = []
        for k in range(41):
            strength = k/10
            candidate = variant(instances[0], 2, strength)
            try:
                state = simulate(candidate, launch)
            except DomainError:
                continue
            samples.append((strength, coordinate(state)-target_coordinate))
        bracket = next(((a[0], b[0], a[1]) for a, b in zip(samples, samples[1:]) if a[1]*b[1] <= 0), None)
        if bracket is None:
            raise ValueError(f'Cannot bracket distractor for pair {index+1}, rank {rank}: {samples[:1]}, {samples[-1:]}.')
        low, high, sign = bracket
        for _ in range(22):
            mid = (low+high)/2
            candidate = variant(instances[0], 2, mid)
            value = coordinate(simulate(candidate, launch))-target_coordinate
            if value*sign > 0:
                low = mid
            else:
                high = mid
        candidate = variant(instances[0], 2, (low+high)/2)
        choices[rank] = dict(instance=candidate.to_dict(), state=simulate(candidate, launch).to_dict())
    return launch, choices


def public_question(manifest):
    return dict(type='image_multiple_choice',
        question='Use your experimental evidence for this same world. The context shows the initial positions '
                 'and velocity of the blue probe; the orange anchor stays fixed. All coordinates are sphere '
                 'centres in metres, with x right and z up; y and initial y velocity are zero. '
                 f'World start time is {manifest["launch"]["start_time_s"]:.1f} s. '
                 f'Which image shows the probe after {manifest["launch"]["duration_s"]:.4f} s? '
                 'Object calibrations are unchanged. Grid spacing is 0.10 m. All choices use the same '
                 'camera, scale, initial conditions and elapsed time. Infer motion from your experiments.',
        context_image=IMAGES['context'], choices=[dict(label=k, image=IMAGES[k]) for k in 'ABCD'])


def make_manifests(instances, seed=42):
    if len(instances) != 2 or variant(instances[0], 3, 1.2) != instances[1]:
        raise ValueError('This suite requires the recorded p=2/p=3 pair with A=1.2 N.')
    if variant(instances[0], 2, 1.2) != instances[0]:
        raise ValueError('Expected p=2 first.')
    instances[0].require_same_public_interface(instances[1])
    objects = []
    for record in instances[0].payload['world']['payload']['objects']:
        obj = ObjectSpec.from_dict(record)
        objects.append(dict(obj.public_dict(), radius_m=obj.properties()['radius_m'], mass_kg=obj.properties()['mass_kg']))
    rng = random.Random(seed)
    labels_a, labels_b = list('ABCD'*2), list('ABCD'*2)
    rng.shuffle(labels_a)
    for _ in range(10000):
        rng.shuffle(labels_b)
        if all(a != b for a, b in zip(labels_a, labels_b)):
            break
    else:
        raise ValueError('Cannot balance paired answer labels.')
    rank_pairs = [(1, 0), (2, 1), (3, 2), (3, 0), (0, 1), (1, 2), (2, 3), (0, 3)]
    manifests = []
    for index, ranks in enumerate(rank_pairs):
        launch, choices_by_rank = _cluster(instances, index, ranks)
        labels = {ranks[0]: labels_a[index], ranks[1]: labels_b[index]}
        remaining = sorted(set('ABCD')-set(labels.values()))
        rng.shuffle(remaining)
        for rank in sorted(set(range(4))-set(ranks)):
            labels[rank] = remaining.pop()
        choices = {labels[rank]: value for rank, value in sorted(choices_by_rank.items())}
        choices = {k: choices[k] for k in 'ABCD'}
        for world_index, instance in enumerate(instances):
            manifest = dict(format='attraction_prediction_scene', schema_version=1, visibility='host_only',
                id=f'attraction_{2*index+world_index+1:03d}', pair_id=f'pair_{index+1:03d}',
                instance_id=instance.record_id, world_index=world_index+1, launch=deepcopy(launch),
                initial_state=initial_state(instance, launch).to_dict(), objects=deepcopy(objects),
                choices=deepcopy(choices), answer=labels[ranks[world_index]], truth_rank=ranks[world_index],
                camera=deepcopy(CAMERA), candidate_policy=deepcopy(POLICY), images=deepcopy(IMAGES))
            manifest['geometry_audit'] = geometry(manifest)
            manifests.append(manifest)
    return manifests


def validate_manifest(manifest, instance):
    if manifest['format'] != 'attraction_prediction_scene' or manifest['schema_version'] != 1:
        raise ValueError('Unsupported attraction scene.')
    if manifest['instance_id'] != instance.record_id or manifest['images'] != IMAGES:
        raise ValueError('Scene world binding or image map mismatch.')
    if manifest['initial_state'] != initial_state(instance, manifest['launch']).to_dict():
        raise ValueError('Initial state mismatch.')
    if set(manifest['choices']) != set('ABCD'):
        raise ValueError('Expected four labelled choices.')
    objects = [ObjectSpec.from_dict(o) for o in instance.payload['world']['payload']['objects']]
    expected = [dict(o.public_dict(), radius_m=o.properties()['radius_m'], mass_kg=o.properties()['mass_kg']) for o in objects]
    if manifest['objects'] != expected:
        raise ValueError('Rendered objects differ from saved calibration.')
    matches, errors = [], []
    for label, candidate in manifest['choices'].items():
        alternative = WorldInstance.from_dict(candidate['instance'])
        instance.require_same_public_interface(alternative)
        data = alternative.payload['world']['payload']
        p = data['laws'][0]['payload']['parameters']['exponent']
        strength = data['fields'][0]['payload']['parameters']['value']
        if variant(instance, p, strength) != alternative:
            raise ValueError('Distractor changed physics outside exponent/strength.')
        state = simulate(alternative, manifest['launch'])
        if state.to_dict() != candidate['state']:
            raise ValueError('Candidate pose differs from simulated physics.')
        refined = simulate(variant(alternative, p, strength, half_step=True), manifest['launch'])
        errors.append(math.dist(probe(state), probe(refined)))
        if alternative == instance:
            matches.append(label)
    if matches != [manifest['answer']]:
        raise ValueError('Answer does not uniquely match the bound world.')
    launch = manifest['launch']['position_m']
    inward = {k: sum((x-p)*(x-a) for x, a, p in zip(launch, ANCHOR, probe(MotionState.from_dict(c['state']))))
              for k, c in manifest['choices'].items()}
    if sorted(inward, key=inward.get).index(manifest['answer']) != manifest['truth_rank']:
        raise ValueError('Recorded truth rank differs from actual inward displacement rank.')
    if max(errors) > POLICY['max_step_halving_error_m']:
        raise ValueError('Candidate integration has not converged.')
    measured = geometry(manifest)
    if measured != manifest['geometry_audit']:
        raise ValueError('Recorded candidate geometry differs from measured geometry.')
    return dict(**measured, max_step_halving_error_m=max(errors))


def shortcut_audit(manifests):
    rows = []
    for manifest in manifests:
        positions = {k: probe(MotionState.from_dict(c['state'])) for k, c in manifest['choices'].items()}
        launch = manifest['launch']
        inertial = [x + v*launch['duration_s'] for x, v in zip(launch['position_m'], launch['velocity_m_s'])]
        centers = [sum(p[k] for p in positions.values())/4 for k in range(3)]
        scores = {'nearest_initial': {k: math.dist(p, launch['position_m']) for k, p in positions.items()},
                  'nearest_inertial': {k: math.dist(p, inertial) for k, p in positions.items()},
                  'nearest_anchor': {k: math.dist(p, ANCHOR) for k, p in positions.items()},
                  'nearest_centroid': {k: math.dist(p, centers) for k, p in positions.items()}}
        reference = WorldInstance.from_dict(manifest['choices']['A']['instance'])
        for p in (2, 3):
            prediction = probe(simulate(variant(reference, p, 1.2), launch))
            scores[f'assume_p{p}_A1.2'] = {k: math.dist(v, prediction) for k, v in positions.items()}
        row = dict(id=manifest['id'], answer=manifest['answer'], predictions={})
        for name, distances in scores.items():
            lowest = min(distances.values())
            ties = [k for k, v in distances.items() if abs(v-lowest) <= 1e-10]
            row['predictions'][name] = dict(labels=ties, credit=(1/len(ties) if manifest['answer'] in ties else 0),
                                           distances_m=distances)
        rows.append(row)
    scores = {name: sum(r['predictions'][name]['credit'] for r in rows) for name in rows[0]['predictions']}
    return dict(visibility='host_only', method='Exact-coordinate baselines; ties split credit. No image/model evaluation.',
                scene_selection='Predeclared rank pairs and physical separation constraints, independent of baseline scores.',
                correct_equivalents=scores, total=len(rows), questions=rows,
                fixed_label_correct=dict(Counter(m['answer'] for m in manifests)),
                image_only_pair_ceiling=.5,
                warning='Identical paired options with different answers imply a 50% ceiling for any deterministic '
                        'world-independent visual rule on this paired suite. Fixed-law priors may reach 50%; '
                        'this is not a claim that all shortcuts perform at 25%.')


def evidence_margin(manifest, instance, audit):
    world = next(w for w in audit['worlds'] if w['instance_id'] == instance.record_id)
    case = next(c for c in world['cases'] if c['policy_id'] == 'two_distances')
    if case['status'] != 'pass_within_audit_scope' or len(case['compatible_intervals']) != 1:
        raise ValueError('Need a resolved two-distance reference control for this scene.')
    interval = case['compatible_intervals'][0]
    low, high = interval['strength_bounds_n']
    positions = {k: probe(MotionState.from_dict(c['state'])) for k, c in manifest['choices'].items()}
    margins, errors = [], []
    for k in range(9):
        predicted = probe(simulate(variant(instance, interval['exponent'], low+(high-low)*k/8), manifest['launch']))
        distances = {label: math.dist(predicted, p) for label, p in positions.items()}
        error = distances[manifest['answer']]
        errors.append(error)
        margins.append(min(v for label, v in distances.items() if label != manifest['answer'])-error)
    if min(margins) <= 0:
        raise ValueError('Reference evidence leaves a competing answer on a sampled scene hypothesis.')
    return dict(method='Nine sampled strengths including conservative interval endpoints; not a continuous proof.',
                strength_interval=interval, maximum_truth_error_m=max(errors), minimum_answer_margin_m=min(margins))


def prepare(output_dir, audit_dir='results/attraction_audit/attraction_pair_v1', seed=42):
    root, source = Path(output_dir), Path(audit_dir)
    if root.exists():
        raise FileExistsError('Choose a new suite directory; existing artifacts are never overwritten.')
    report = json.loads((source/'audit.json').read_text())
    hashes = json.loads((source/'checksums.json').read_text())
    if report.get('format') != 'attraction_learnability_v1' or not {'audit.json', 'world_1.json', 'world_2.json'} <= hashes.keys():
        raise ValueError('Expected a complete versioned learnability audit.')
    for name, expected in hashes.items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest() != expected:
            raise ValueError('Learnability audit artifact checksum mismatch.')
    instances = [WorldInstance.load(source/f'world_{i}.json') for i in (1, 2)]
    if not report['passes_reference_audit'] or [w['instance_id'] for w in report['worlds']] != [w.record_id for w in instances]:
        raise ValueError('Require a successful audit bound to this world pair.')
    manifests = make_manifests(instances, seed)
    validation = [validate_manifest(m, instances[m['world_index']-1]) for m in manifests]
    audit = shortcut_audit(manifests)
    transfer = [evidence_margin(m, instances[m['world_index']-1], report) for m in manifests]
    entries = [dict(id=m['id'], pair_id=m['pair_id'], world_index=m['world_index'], instance_id=m['instance_id'],
                    folder=f'questions/q{i+1:03d}', scene_digest=digest(m)) for i, m in enumerate(manifests)]
    batch = dict(format='attraction_prediction_batch', schema_version=1, visibility='host_only', seed=seed,
                 instance_ids=[w.record_id for w in instances], learnability_audit_sha256=hashes['audit.json'],
                 questions=entries, candidate_policy=POLICY, images_expected=80,
                 source_sha256={name: hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
                                for name in ('attraction_scene.py', 'attraction_visual.py', 'blender_attraction.py')})
    outputs = {'batch.json': batch, 'candidate_audit.json': audit,
               'physics_validation.json': dict(visibility='host_only', questions=validation),
               'evidence_transfer.json': dict(visibility='host_only', questions=transfer),
               'learnability_audit.json': report,
               'questions.json': [dict(entry, question=public_question(m)) for entry, m in zip(entries, manifests)]}
    outputs.update({f'world_{i}.json': w.to_dict() for i, w in enumerate(instances, 1)})
    for entry, manifest in zip(entries, manifests):
        outputs[entry['folder']+'/scene.json'] = manifest
        outputs[entry['folder']+'/question.json'] = public_question(manifest)
    root.mkdir(parents=True)
    checksums = {}
    for name, value in outputs.items():
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
        checksums[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (root/'checksums.json').write_text(json.dumps(checksums, indent=2)+'\n')
    return batch


def validate_batch(output_dir, require_images=False):
    root = Path(output_dir)
    batch = json.loads((root/'batch.json').read_text())
    if batch['format'] != 'attraction_prediction_batch' or len(batch['questions']) != 16:
        raise ValueError('Expected the sixteen-question attraction suite.')
    hashes = json.loads((root/'checksums.json').read_text())
    for name, expected in hashes.items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Artifact checksum mismatch: {name}')
    instances = [WorldInstance.load(root/f'world_{i}.json') for i in (1, 2)]
    audit = json.loads((root/'learnability_audit.json').read_text())
    if hashlib.sha256((root/'learnability_audit.json').read_bytes()).hexdigest() != batch['learnability_audit_sha256']:
        raise ValueError('Copied learnability audit does not match the recorded source.')
    if batch['instance_ids'] != [w.record_id for w in instances]:
        raise ValueError('Batch world IDs differ from saved records.')
    manifests, validation, transfer = [], [], []
    for entry in batch['questions']:
        folder = root/entry['folder']
        manifest = json.loads((folder/'scene.json').read_text())
        if entry['scene_digest'] != digest(manifest) or entry['instance_id'] != manifest['instance_id']:
            raise ValueError('Scene digest/world routing mismatch.')
        if any(entry[k] != manifest[k] for k in ('id', 'pair_id', 'world_index')):
            raise ValueError('Question routing disagrees with its manifest.')
        validation.append(validate_manifest(manifest, instances[entry['world_index']-1]))
        transfer.append(evidence_margin(manifest, instances[entry['world_index']-1], audit))
        if json.loads((folder/'question.json').read_text()) != public_question(manifest):
            raise ValueError('Public question disagrees with the scene.')
        if require_images:
            validate_render(folder, manifest)
        manifests.append(manifest)
    if json.loads((root/'physics_validation.json').read_text())['questions'] != validation:
        raise ValueError('Saved physics audit differs from the current solver.')
    if json.loads((root/'evidence_transfer.json').read_text())['questions'] != transfer:
        raise ValueError('Saved evidence-transfer audit differs from current predictions.')
    expected_questions = [dict(entry, question=public_question(m)) for entry, m in zip(batch['questions'], manifests)]
    if json.loads((root/'questions.json').read_text()) != expected_questions:
        raise ValueError('Aggregate question routing or text disagrees with the scenes.')
    for a, b in zip(manifests[::2], manifests[1::2]):
        if (a['pair_id'] != b['pair_id'] or a['answer'] == b['answer']
                or a['choices'] != b['choices'] or public_question(a) != public_question(b)):
            raise ValueError('Paired visual questions are not matched with distinct answers.')
    for world_index in (1, 2):
        group = [m for m in manifests if m['world_index'] == world_index]
        if Counter(m['answer'] for m in group) != Counter(dict.fromkeys('ABCD', 2)):
            raise ValueError('Answer labels are not balanced within each world.')
        if Counter(m['truth_rank'] for m in group) != Counter(dict.fromkeys(range(4), 2)):
            raise ValueError('Truth ranks are not balanced within each world.')
    if json.loads((root/'candidate_audit.json').read_text()) != shortcut_audit(manifests):
        raise ValueError('Shortcut audit does not match current candidate physics.')
    return batch


def validate_render(folder, manifest):
    report = json.loads((folder/'build_report.json').read_text())
    if not report['images_rendered'] or report['scene_digest'] != digest(manifest):
        raise ValueError('Images missing or render report is stale.')
    geometry(manifest, report['resolution'])
    for key, filename in IMAGES.items():
        path = folder/filename
        if not path.is_file() or path.read_bytes()[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError('Missing PNG image.')
        if hashlib.sha256(path.read_bytes()).hexdigest() != report['image_sha256'][key]:
            raise ValueError('Image bytes do not match their render record.')
        if len(path.read_bytes()) < 24 or list(struct.unpack('>II', path.read_bytes()[16:24])) != report['resolution']:
            raise ValueError('PNG dimensions disagree with the recorded resolution.')
        if not (folder/(Path(filename).stem+'_parameters.md')).is_file():
            raise ValueError('Missing frame parameter record.')
    if not (folder/'scene.blend').is_file():
        raise ValueError('Missing saved Blender scene.')
    validate_projections(manifest, report['frames'], report['resolution'])


def render_batch(output_dir, device='CUDA', samples=96, resolution=(1920, 1280), build_only=False, dry_run=False):
    root = Path(output_dir).resolve()
    batch = validate_batch(root)
    repo = Path(__file__).resolve().parents[2]
    blender = os.environ.get('BLENDER_BIN', str(repo/'.tools/blender-3.6.23-linux-x64/blender'))
    for entry in batch['questions']:
        folder = root/entry['folder']
        manifest = json.loads((folder/'scene.json').read_text())
        geometry(manifest, resolution)
        if (folder/'build_report.json').exists():
            old = json.loads((folder/'build_report.json').read_text())
            if old.get('images_rendered'):
                try:
                    validate_render(folder, manifest)
                except (ValueError, KeyError, OSError):
                    if build_only:
                        raise ValueError('Build-only cannot replace a previous render record.')
                else:
                    if build_only or (old['resolution'] == list(resolution) and old['samples'] == samples and old['device'] == device):
                        print('SKIP complete '+entry['id'], flush=True)
                        continue
        command = [blender, '--background', '--python-exit-code', '1', '--python',
                   str(repo/'src/simulation/blender_attraction.py'), '--', '--manifest', str(folder/'scene.json'),
                   '--device', device, '--samples', str(samples), '--resolution', *map(str, resolution)]
        if build_only:
            command.append('--build-only')
        print(('PLAN ' if dry_run else 'BUILD ' if build_only else 'RENDER ') + entry['id'], flush=True)
        if not dry_run:
            subprocess.run(command, check=True, cwd=repo)
    if not dry_run and not build_only:
        validate_batch(root, require_images=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--audit-dir', default='results/attraction_audit/attraction_pair_v1')
    prep.add_argument('--seed', type=int, default=42)
    check = sub.add_parser('validate')
    check.add_argument('--require-images', action='store_true')
    render = sub.add_parser('render')
    render.add_argument('--device', choices=['CPU', 'CUDA', 'OPTIX'], default='CUDA')
    render.add_argument('--samples', type=int, default=96)
    render.add_argument('--resolution', nargs=2, type=int, default=[1920, 1280])
    render.add_argument('--build-only', action='store_true')
    render.add_argument('--dry-run', action='store_true')
    for command in (prep, check, render):
        command.add_argument('--output-dir', default='renders/attraction/paired_close_v1')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(args.output_dir, args.audit_dir, args.seed)
        print(f'Prepared 16 questions / 8 matched pairs. No pixels rendered. {args.output_dir}')
    elif args.action == 'validate':
        validate_batch(args.output_dir, args.require_images)
        print('Attraction suite validation passed.' + (' Images verified.' if args.require_images else ' Physics only.'))
    else:
        render_batch(args.output_dir, args.device, args.samples, args.resolution, args.build_only, args.dry_run)


if __name__ == '__main__':
    main()
