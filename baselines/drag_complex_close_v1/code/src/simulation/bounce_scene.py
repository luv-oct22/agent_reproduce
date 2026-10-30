"""Prepare recorded-world bounce image questions. Blender can import record helpers."""
import argparse
from copy import deepcopy
import hashlib
import html
import json
import math
from pathlib import Path


IMAGES = {'context': 'context.png', **{k: f'choice_{k}.png' for k in 'ABCD'}}
VISUAL_VERSION = 1


def scene_digest(manifest):
    return hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def write_record(directory, manifest, artifact='scene.blend', actual=None):
    path = Path(directory)/(Path(artifact).stem+'_parameters.md')
    name = 'Drag' if manifest.get('format') == 'drag_prediction_scene' else 'Bounce'
    path.write_text(f'# {name} scene parameters (host-only)\n\n'
        'Exact recorded objects, gravity and contact rules; do not include this file in model context. '
        'Heights in the public instructions are sphere-bottom clearances. All options depict the same elapsed time.\n\n'
        '```json\n'+json.dumps({'scene': manifest, 'actual': actual}, indent=2)+'\n```\n')


def build_question(manifest):
    if manifest.get('schema_version') == 2:
        return build_hard_question(manifest)
    launches = []
    for obj in manifest['objects']:
        launches.append(f"Launch station {obj['station']}: bottom clearance {obj['release_height_m']:.2f} m, "
                        f"horizontal velocity {obj['velocity_m_s'][0]:.2f} m/s toward the right.")
    return {'id': manifest['id'], 'type': 'image_multiple_choice',
            'question': 'The context image shows specimens held immediately before simultaneous launch. '
                        'Identify the specimens by their appearance in the image and use the prior experimental evidence. '
                        f"These are the same specimens and the same {manifest['surface_id']} used in the experiments. "
                        +' '.join(launches)+' Initial vertical velocities are zero. '
                        f"Which image shows every specimen's position {manifest['elapsed_s']:.2f} seconds after launch? "
                        'The world has the same constant gravity and constant specimen–surface restitution as in the experiments. '
                        'The horizontal surface is stationary and frictionless; there is no air drag, spin coupling or '
                        'object–object collision. Horizontal velocities remain unchanged at impact. '
                        'The grid is marked every 0.10 m. Launch station markings are fixed location markers, not object identities. '
                        'Any launch holders retract instantly without imparting additional velocity. '
                        'All four options show the same elapsed time, camera and scale.',
            'context_caption': 'Context — immediately before launch', 'context_image': IMAGES['context'],
            'choices': [{'label': k, 'image': IMAGES[k]} for k in 'ABCD'], 'answer': manifest['answer'],
            'world_id': manifest['world_id'], 'object_registry_id': manifest['object_registry_id'],
            'contact_registry_id': manifest['contact_registry_id']}


def build_hard_question(manifest):
    return {'id': manifest['id'], 'type': 'image_multiple_choice',
            'question': 'The image shows two specimens held before simultaneous horizontal launch. '
                        'Identify each specimen by appearance and use the experimental evidence for this world. '
                        f"The impact surface is the same {manifest['surface_id']} used in the experiments. "
                        'Read initial bottom-of-sphere clearances and launch velocities from the image; '
                        'major horizontal grid lines are 0.10 m apart and minor lines are 0.025 m apart. '
                        'Heights are measured above the surface, not from the sphere centers. '
                        'Both initial vertical velocities are zero and both holders retract instantly. '
                        f"Which image shows BOTH specimens {manifest['elapsed_s']:.2f} seconds after launch? "
                        'Gravity and specimen–surface restitution remain constant at their experimentally determined values. '
                        'The stationary horizontal surface is frictionless. There is no air drag, spin coupling or '
                        'object–object collision; horizontal velocity stays unchanged during impacts. '
                        'Track all impacts that occur before the requested time. '
                        'All choices have the same time, camera and scale. Station labels mark launch locations only.',
            'context_caption': 'Context — immediately before launch', 'context_image': IMAGES['context'],
            'choices': [{'label': k, 'image': IMAGES[k]} for k in 'ABCD'], 'answer': manifest['answer'],
            'world_id': manifest['world_id'], 'object_registry_id': manifest['object_registry_id'],
            'contact_registry_id': manifest['contact_registry_id']}


def make_manifest(env, index, keys):
    from src.worlds import UniformGravityWorld
    from src.worlds.contact_registry import ContactRegistry
    from src.worlds.bounce_motion import advance_bouncing
    private = env.private_manifest()
    world = UniformGravityWorld.from_dict(private['world'])
    contacts = ContactRegistry.from_dict(private['contact_registry'])
    catalog = {obj['id']: obj for obj in private['specimens']}
    surface_z = .86
    objects = []
    for slot, key in enumerate(keys):
        record = catalog[key]
        radius = record['geometry']['dimensions_m'][0]/2
        height = (.65, .85, 1.05, .75)[(index+slot)%4]
        x = (-.85 if slot == 0 else .15) if len(keys) > 1 else -.6
        vx = (.30 if slot == 0 else .35) if len(keys) > 1 else .45
        objects.append({'station': str(slot+1), 'source_specimen_id': key, 'color': record['color'],
                        'color_rgba': record['appearance']['color_rgba'], 'radius_m': radius,
                        'release_height_m': height, 'position_m': [x, 0, surface_z+radius+height],
                        'velocity_m_s': [vx, 0, 0]})
    truth = dict(contacts.restitution)
    # Wrong-world candidates use complete alternative dynamics, never arbitrary pixel offsets.
    alternate_g = 9.81 if abs(world.gravity_m_s2-9.81) > 1 else 3.0
    elastic = dict(truth)
    confused = dict(truth)
    for obj in objects:
        key = obj['source_specimen_id']
        elastic[key] = 1.0 if truth[key] < .95 else .15
        other = max(truth, key=lambda k: abs(truth[k]-truth[key]))
        confused[key] = truth[other]
    if len(keys) == 2 and abs(truth[keys[0]]-truth[keys[1]]) > .1:
        confused[keys[0]], confused[keys[1]] = truth[keys[1]], truth[keys[0]]
    if all(abs(confused[k]-truth[k]) < .05 for k in keys):
        for k in keys:
            confused[k] = .25 if truth[k] > .5 else .75
    variants = [('recorded_physics', world, truth),
                ('wrong_gravity', UniformGravityWorld(alternate_g), truth),
                ('wrong_restitution', world, elastic), ('wrong_contact_assignment', world, confused)]
    def states(t):
        result = []
        for name, w, coefficients in variants:
            c = ContactRegistry(w.world_id, contacts.object_registry_id, contacts.surface_id, tuple(coefficients.items()))
            frame = [dict(source_specimen_id=o['source_specimen_id'],
                          **advance_bouncing(w, c, o['source_specimen_id'], o['position_m'], o['velocity_m_s'],
                                             t, o['radius_m'], surface_z)) for o in objects]
            result.append({'hypothesis': name, 'gravity_m_s2': w.gravity_m_s2,
                           'restitution_by_specimen': coefficients, 'objects': frame})
        return result
    first = max(world.free_fall_time(o['release_height_m']) for o in objects)
    best = None
    for step in range(8, 66):
        t = round(first+step*.01, 2)
        frames = states(t)
        # Require a clearly separated object in every pair of candidate images.
        separation = min(max(math.dist(a['position_m'], b['position_m'])
                             for a, b in zip(frames[i]['objects'], frames[j]['objects']))
                         for i in range(4) for j in range(i))
        if best is None or separation > best[0]:
            best = separation, t, frames
    separation, elapsed, frames = best
    if separation < .08:
        raise ValueError('Cannot produce four visually distinguishable outcomes for these world parameters.')
    correct_index = index % 4
    mapping = {label: frames[(i-correct_index)%4] for i, label in enumerate('ABCD')}
    return {'format': 'bounce_prediction_scene', 'schema_version': 1, 'visual_version': VISUAL_VERSION,
            'id': f'bounce_{index+1:03d}', 'world_id': world.world_id, 'object_registry_id': contacts.object_registry_id,
            'contact_registry_id': contacts.registry_id, 'surface_id': contacts.surface_id,
            'surface_z_m': surface_z, 'objects': objects, 'elapsed_s': elapsed,
            'choices': mapping, 'answer': 'ABCD'[correct_index], 'images': dict(IMAGES),
            'minimum_candidate_separation_m': separation,
            'scene': {'camera_position_m': [0, -7, 1.51], 'camera_target_m': [0, 0, 1.51],
                      'ortho_scale_m': 2.9, 'grid_spacing_m': .1,
                      'table_bounds_m': [-1.4, 1.4, -.6, .6], 'grid_back_y_m': .22}}


def prepare_batch(run_dir, output_dir):
    from src.envs.bounce_lab import BounceLabEnv
    source, root = Path(run_dir).resolve(), Path(output_dir).resolve()
    env = BounceLabEnv.from_private_manifest(json.loads((source/'private_manifest.json').read_text()))
    keys = list(env.objects)
    if len(keys) < 4:
        raise ValueError('This eight-question design needs at least four recorded specimens.')
    groups = [(k,) for k in keys[:4]] + [(keys[i], keys[(i+1)%4]) for i in range(4)]
    manifests = [make_manifest(env, i, group) for i, group in enumerate(groups)]
    for i, manifest in enumerate(manifests, 1):
        folder = root/'questions'/f'q{i:03d}'
        if folder.exists() and any(folder.iterdir()):
            if not (folder/'scene.json').exists() or json.loads((folder/'scene.json').read_text()) != manifest:
                raise FileExistsError(f'Scene settings changed; choose a fresh output directory: {folder}')
    root.mkdir(parents=True, exist_ok=True)
    env.export_private_artifacts(root)
    questions, entries = [], []
    for i, manifest in enumerate(manifests, 1):
        relative = f'questions/q{i:03d}'
        folder = root/relative
        folder.mkdir(parents=True, exist_ok=True)
        (folder/'scene.json').write_text(json.dumps(manifest, indent=2)+'\n')
        q = build_question(manifest)
        (folder/'questions.json').write_text(json.dumps([q], indent=2)+'\n')
        write_record(folder, manifest)
        cards = ''.join(f'<figure><img src="{IMAGES[k]}"><figcaption>Choice {k}</figcaption></figure>' for k in 'ABCD')
        (folder/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Bounce prediction</title>'
            '<style>body{font:18px system-ui;max-width:1300px;margin:40px auto;background:#eef1f3}'
            'img{width:100%}.choices{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0}</style>'
            '<h1>Bounce prediction</h1><p>'+html.escape(q['question'])+'</p><img src="context.png">'
            '<div class="choices">'+cards+'</div>')
        aggregate = deepcopy(q)
        aggregate['context_image'] = relative+'/'+q['context_image']
        for choice in aggregate['choices']:
            choice['image'] = relative+'/'+choice['image']
        questions.append(aggregate)
        entries.append({'folder': relative, 'id': manifest['id']})
    batch = {'format': 'bounce_prediction_batch', 'schema_version': 1, 'source_run': str(source),
             'world_id': manifests[0]['world_id'], 'object_registry_id': manifests[0]['object_registry_id'],
             'contact_registry_id': manifests[0]['contact_registry_id'], 'questions': entries}
    (root/'batch.json').write_text(json.dumps(batch, indent=2)+'\n')
    (root/'questions.json').write_text(json.dumps(questions, indent=2)+'\n')
    (root/'index.html').write_text('<!doctype html><meta charset="utf-8"><h1>Bounce prediction questions</h1><ul>'+
        ''.join(f'<li><a href="{e["folder"]}/index.html">{e["id"]}</a></li>' for e in entries)+'</ul>')
    return batch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True, help='Completed bounce interaction or offline demo directory.')
    parser.add_argument('--output-dir', default='renders/lab_4/bounce_prediction')
    args = parser.parse_args()
    batch = prepare_batch(args.run_dir, args.output_dir)
    print(f"Prepared {len(batch['questions'])} questions in {args.output_dir}")


if __name__ == '__main__':
    main()
