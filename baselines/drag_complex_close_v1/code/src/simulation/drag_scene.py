"""Prepare image questions using the exact drag world saved by an interaction."""
import argparse
from copy import deepcopy
import html
from itertools import combinations
import json
import math
from pathlib import Path
import random

from src.envs.drag_lab import DragLabEnv
from src.worlds.layered_drag import LayeredDragWorld
from src.worlds.height_drag import HeightDragWorld, load_drag_world
from src.simulation.bounce_scene import IMAGES, write_record
from src.simulation.drag_candidates import CLOSE_POLICY, close_frames, validate_candidate_geometry


def build_question(manifest):
    question = {'id': manifest['id'], 'type': 'image_multiple_choice',
            'question': 'The context image shows the calibrated specimen held immediately before horizontal launch. '
                'Use the prior experimental evidence for this same specimen, surface and invisible medium. '
                'Read the initial bottom clearance and horizontal launch velocity from the image. '
                'Initial vertical velocity is zero; the holder retracts instantly without any extra impulse. '
                f"Which image shows the specimen {manifest['elapsed_s']:.2f} seconds after launch? "
                'Gravity, specimen mass/radius and surface restitution retain their experimental calibration values. '
                'The same two invisible horizontal layers exert F_drag = -b(z) * velocity in ALL velocity components, '
                'where z is sphere-centre height above the impact surface. Infer their boundary and coefficients '
                'from the experiments. At each impact the normal velocity reverses with the calibrated restitution; '
                'horizontal velocity is continuous at impact but is damped by the medium. '
                'There is no buoyancy, spin coupling or tangential contact friction. Track all impacts before the '
                'requested time. The major grid spacing is 0.10 m; minor horizontal lines are 0.025 m apart. '
                'All choices have the same elapsed time, camera and scale. No layer boundary is drawn.',
            'context_caption': 'Context — immediately before launch', 'context_image': IMAGES['context'],
            'choices': [{'label': k, 'image': IMAGES[k]} for k in 'ABCD'], 'answer': manifest['answer']}
    if manifest.get('profile_type') == 'smooth_random':
        question['question'] = question['question'].replace(
            'The same two invisible horizontal layers exert F_drag = -b(z) * velocity in ALL velocity components, '
            'where z is sphere-centre height above the impact surface. Infer their boundary and coefficients '
            'from the experiments.',
            'The same invisible, fixed smooth function b(z) exerts F_drag = -b(z) * velocity in ALL velocity components, '
            'where z is sphere-centre height above the impact surface. Infer the height-dependent drag from the experiments.'
        ).replace('No layer boundary is drawn.', 'The drag distribution is not drawn.')
    return question


def frame_state(world, obj, elapsed, restitution, floor):
    position = list(obj['position_m'])
    position[2] -= floor
    state = world.advance(position, obj['velocity_m_s'], elapsed, obj['mass_kg'], obj['radius_m'], restitution)
    state['position_m'][2] += floor
    return dict(source_specimen_id=obj['source_specimen_id'], **state)


def make_manifest(env, index, answer, rng, candidate_mode='close', truth_rank=None):
    if candidate_mode not in ('close', 'legacy'):
        raise ValueError('Expected close or legacy candidate mode.')
    private = env.private_manifest()
    world = load_drag_world(private['world'])
    ball = env._ball
    restitution = env._contacts.restitution[0][1]
    height = (.975, 1.225, 1.475, 1.725, 1.975, 2.225, 2.425, 1.825,
              .625, .825, 1.075, 1.375, 1.625, 1.875, 2.075, 2.325)[index]
    vx = (.65, .8, 1., .7, .9, 1.1, .75, .95,
          .9, 1.05, .75, .95, 1.15, .8, 1., .7)[index]
    floor = .86
    obj = {'station': '1', 'source_specimen_id': ball.specimen_id, 'color': ball.color,
           'color_rgba': list(ball.color_rgba), 'radius_m': ball.radius_m, 'mass_kg': ball.mass_kg,
           'release_height_m': height, 'position_m': [-1.5, 0, floor+ball.radius_m+height],
           'velocity_m_s': [vx, 0, 0]}
    g = world.gravity_m_s2
    if isinstance(world, HeightDragWorld):
        values = world.coefficients_kg_s
        mean = sum(values)/len(values)
        variants = [('recorded_physics', world), ('no_drag', LayeredDragWorld(g, .85, 0, 0)),
                    ('uniform_mean_drag', LayeredDragWorld(g, .85, mean, mean)),
                    ('reversed_profile', HeightDragWorld(g, world.heights_m, tuple(reversed(values)))),
                    ('weaker_profile', HeightDragWorld(g, world.heights_m, tuple(v*.35 for v in values))),
                    ('stronger_profile', HeightDragWorld(g, world.heights_m, tuple(min(.5, v*2.5) for v in values)))]
    else:
        h, low, high = world.boundary_height_m, world.lower_drag_kg_s, world.upper_drag_kg_s
        variants = [('recorded_physics', world), ('no_drag', LayeredDragWorld(g, h, 0, 0)),
                ('uniform_lower_drag', LayeredDragWorld(g, h, low, low)),
                ('uniform_upper_drag', LayeredDragWorld(g, h, high, high)),
                ('swapped_layers', LayeredDragWorld(g, h, high, low)),
                ('shifted_boundary', LayeredDragWorld(g, .2 if h > 1 else 1.8, low, high))]
    first = world.drop_readings(height, ball.mass_kg, ball.radius_m, restitution)['time_to_first_impact_s']
    # Include falling and different stages of rebound motion. The legacy policy
    # maximizes separation; the default instead constrains a small local cluster.
    windows = ((.65*first, .95*first), (first+.1, first+.7), (first+.75, first+1.6))
    start, stop = windows[index % 3]
    best = None
    ticks = range(math.ceil(start*100), math.floor(stop*100)+1, 2) if candidate_mode == 'legacy' else ()
    for tick in ticks:
        elapsed = tick/100
        frames = [dict(hypothesis=name, world=w.to_dict(), restitution=restitution,
                       objects=[frame_state(w, obj, elapsed, restitution, floor)]) for name, w in variants]
        for wrong in combinations(range(1, len(frames)), 3):
            selected = [frames[i] for i in (0, *wrong)]
            points = [f['objects'][0]['position_m'] for f in selected]
            if any(not -2 < p[0] < 2 or p[2] > floor+2.55 for p in points):
                continue
            separation = min(math.dist(a, b) for a, b in combinations(points, 2))
            if best is None or separation > best[0]:
                best = separation, elapsed, selected
    if candidate_mode == 'close':
        truth_rank = rng.randrange(4) if truth_rank is None else truth_rank
        best = close_frames(world, obj, restitution, floor, (start, stop),
                            truth_rank, rng, frame_state)
    elif best is None or best[0] < .07:
        raise ValueError(f'Question {index+1} cannot separate four options by 0.07 m in this world.')
    separation, elapsed, frames = best
    distractors = frames[1:]
    rng.shuffle(distractors)
    choices = {key: frames[0] if key == answer else distractors.pop() for key in 'ABCD'}
    manifest = {'format': 'drag_prediction_scene', 'schema_version': 1, 'visual_version': 1,
            'id': f'drag_{index+1:03d}', 'world_id': private['world_id'],
            'object_registry_id': private['object_registry_id'],
            'contact_registry_id': private['contact_registry']['registry_id'],
            'surface_id': env._contacts.surface_id, 'surface_z_m': floor, 'objects': [obj],
            'elapsed_s': elapsed, 'choices': choices, 'answer': answer, 'images': dict(IMAGES),
            'minimum_candidate_separation_m': separation,
            'truth_impacts': frames[0]['objects'][0]['impacts'],
            'scene': {'camera_position_m': [0, -7, floor+1.3], 'camera_target_m': [0, 0, floor+1.3],
                      'ortho_scale_m': 4.6, 'grid_spacing_m': .1, 'minor_grid_spacing_m': .025,
                      'grid_height_m': 2.6, 'grid_half_width_m': 2.1, 'show_launch_height': True,
                      'table_bounds_m': [-2.2, 2.2, -.6, .6], 'grid_back_y_m': .22}}
    if isinstance(world, HeightDragWorld):
        manifest['profile_type'] = 'smooth_random'
    if candidate_mode == 'close':
        manifest.update(schema_version=2, visual_version=2, candidate_policy=dict(CLOSE_POLICY),
                        truth_profile_rank=truth_rank)
        manifest['maximum_candidate_separation_m'] = max(
            math.dist(a['objects'][0]['position_m'], b['objects'][0]['position_m'])
            for a, b in combinations(choices.values(), 2))
    validate_candidate_geometry(manifest)
    return manifest


def aggregate_question(manifest, folder):
    q = deepcopy(build_question(manifest))
    q['context_image'] = folder+'/'+q['context_image']
    for choice in q['choices']:
        choice['image'] = folder+'/'+choice['image']
    return q


def shortcut_audit(manifests, source):
    """Report exact-coordinate baselines; never use their scores to select scenes."""
    world = load_drag_world(manifests[0]['choices'][manifests[0]['answer']]['world'])
    models = {'true_world': world}
    for b in (0., .05, .1, .15, .2, .25):
        models[f'constant_{b:g}'] = LayeredDragWorld(world.gravity_m_s2, .85, b, b)
    estimate_path = source/'private_evaluation.json'
    if estimate_path.exists():
        evaluation = json.loads(estimate_path.read_text())
        if evaluation.get('world_id') != world.world_id:
            raise ValueError('Saved estimate belongs to a different world.')
        if evaluation.get('estimate'):
            models['submitted_estimate'] = type(world)(gravity_m_s2=world.gravity_m_s2, **evaluation['estimate'])
    results = {}
    for name, model in models.items():
        rows = []
        for m in manifests:
            frames = m['choices']
            predicted = frame_state(model, m['objects'][0], m['elapsed_s'],
                                    frames[m['answer']]['restitution'], m['surface_z_m'])['position_m']
            distances = {k: math.dist(predicted, f['objects'][0]['position_m']) for k, f in frames.items()}
            nearest = min(distances, key=distances.get)
            rows.append(dict(id=m['id'], nearest=nearest, answer=m['answer'],
                             correct=nearest == m['answer'], distances_m=distances))
        results[name] = dict(correct=sum(r['correct'] for r in rows), total=len(rows), questions=rows)
    return dict(visibility='host_only',
                method='Exact-coordinate nearest-candidate diagnostic; bypasses image perception. '
                       'Scenes are selected independently of these baselines. This is not an LLM evaluation.',
                baselines=results)


def prepare_batch(run_dir, output_dir, seed=42, candidate_mode='close', count=8):
    if count not in (8, 16):
        raise ValueError('Question count must be 8 or 16.')
    source, root = Path(run_dir).resolve(), Path(output_dir).resolve()
    env = DragLabEnv.from_private_manifest(json.loads((source/'private_manifest.json').read_text()))
    rng = random.Random(seed)
    manifests = []
    # Shuffle in fixed blocks so extending a batch cannot change its prefix.
    for start in range(0, count, 8):
        answers = list('ABCD'*2)
        rng.shuffle(answers)
        ranks = list(range(4))*2
        if candidate_mode == 'close':
            rng.shuffle(ranks)
        manifests.extend(make_manifest(env, start+i, answer, rng, candidate_mode, ranks[i])
                         for i, answer in enumerate(answers))
    entries = [{'folder': f'questions/q{i+1:03d}', 'id': m['id']} for i, m in enumerate(manifests)]
    batch = {'format': 'drag_prediction_batch', 'schema_version': 1, 'source_run': str(source), 'seed': seed,
             **{k: manifests[0][k] for k in ('world_id', 'object_registry_id', 'contact_registry_id')},
             'questions': entries}
    if candidate_mode == 'close':
        batch.update(schema_version=2, candidate_policy=dict(CLOSE_POLICY))
    audit = shortcut_audit(manifests, source) if candidate_mode == 'close' else None
    if (root/'batch.json').exists():
        previous = json.loads((root/'batch.json').read_text())
        prefix = previous.get('questions', [])
        if (dict(previous, questions=entries) != batch or not prefix
                or prefix != entries[:len(prefix)]):
            raise FileExistsError('Different batch or smaller count requested; choose a new output directory.')
    preserved = set()
    for entry, manifest in zip(entries, manifests):
        folder = root/entry['folder']
        if folder.exists() and any(folder.iterdir()):
            if not (folder/'scene.json').exists() or json.loads((folder/'scene.json').read_text()) != manifest:
                raise FileExistsError(f'Different scene already exists: {folder}')
            if (folder/'questions.json').exists():
                if json.loads((folder/'questions.json').read_text()) != [build_question(manifest)]:
                    raise FileExistsError(f'Different question already exists: {folder}')
                if (folder/'index.html').exists() and (folder/'scene_parameters.md').exists():
                    preserved.add(entry['folder'])
    env.export_private_artifacts(root)
    questions = []
    for entry, manifest in zip(entries, manifests):
        folder = root/entry['folder']
        questions.append(aggregate_question(manifest, entry['folder']))
        if entry['folder'] in preserved:
            continue  # Preserve rendered images and their actual Blender parameter records.
        folder.mkdir(parents=True, exist_ok=True)
        q = build_question(manifest)
        (folder/'scene.json').write_text(json.dumps(manifest, indent=2)+'\n')
        (folder/'questions.json').write_text(json.dumps([q], indent=2)+'\n')
        write_record(folder, manifest)
        cards = ''.join(f'<figure><img src="{IMAGES[k]}"><figcaption>Choice {k}</figcaption></figure>' for k in 'ABCD')
        (folder/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Drag prediction</title>'
            '<style>body{font:18px system-ui;max-width:1400px;margin:40px auto;background:#eef1f3}'
            'img{width:100%}.choices{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0}</style>'
            '<h1>Drag prediction</h1><p>'+html.escape(q['question'])+'</p><img src="context.png">'
            '<div class="choices">'+cards+'</div>')
    (root/'batch.json').write_text(json.dumps(batch, indent=2)+'\n')
    (root/'questions.json').write_text(json.dumps(questions, indent=2)+'\n')
    if audit is not None:
        (root/'candidate_audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    (root/'batch_parameters.md').write_text('# Drag image batch (host-only)\n\n'
        f'{len(manifests)} questions, five images each. Correct frames use the saved world; distractors change only the drag profile. '
        'Answer labels are balanced and shuffled. Layer parameters are never drawn.\n\n```json\n'
        +json.dumps(batch, indent=2)+'\n```\n')
    (root/'index.html').write_text('<!doctype html><meta charset="utf-8"><h1>Drag prediction questions</h1><ul>'
        +''.join(f'<li><a href="{e["folder"]}/index.html">{e["id"]}</a></li>' for e in entries)+'</ul>')
    return batch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True, help='Saved drag interaction or demo directory.')
    parser.add_argument('--output-dir', default='renders/lab_5/drag_prediction')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--count', type=int, choices=[8, 16], default=8,
                        help='Number of questions; 16 safely extends a matching eight-question batch.')
    parser.add_argument('--candidate-mode', choices=['close', 'legacy'], default='close',
                        help='Close: same-phase positions 2–8 cm apart (default). Legacy: widely separated choices.')
    args = parser.parse_args()
    batch = prepare_batch(args.run_dir, args.output_dir, args.seed, args.candidate_mode, args.count)
    print(f"Prepared {len(batch['questions'])} drag image questions in {args.output_dir}; render next.")
    if args.candidate_mode == 'close':
        audit = json.loads((Path(args.output_dir)/'candidate_audit.json').read_text())
        print('Offline nearest-choice checks: '+', '.join(
            f"{name}={r['correct']}/{r['total']}" for name, r in audit['baselines'].items()))


if __name__ == '__main__':
    main()
