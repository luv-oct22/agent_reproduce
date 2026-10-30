"""Hard paired-world questions with two-object conjunction and image-only heights."""
import argparse
from copy import deepcopy
from datetime import datetime
import html
import json
import math
from pathlib import Path
import random
import tempfile

from src.envs.bounce_lab import BounceLabEnv
from src.worlds.bounce_motion import advance_bouncing
from src.simulation.bounce_scene import IMAGES, build_question, write_record


def identity(env):
    p = env.private_manifest()
    return {'world_id': p['world_id'], 'object_registry_id': p['object_registry_id'],
            'contact_registry_id': p['contact_registry']['registry_id']}


def second_world(env):
    p = env.private_manifest()
    coefficients = dict(env._contacts.restitution)
    return BounceLabEnv(seed=p['seed'], specimens=p['specimens'], gravity_m_s2=env._world.gravity_m_s2*1.35,
                        restitution_by_specimen={k: round(min(.95, max(.15, e+(.12 if e < .65 else -.11))), 3)
                                                 for k, e in coefficients.items()}, **p['apparatus'])


def select_pair(envs, category, rng, excluded):
    catalog = envs[0]._specimens
    for _ in range(40000):
        keys = rng.sample(list(catalog), 2)
        heights = [rng.randrange(2, 23)*.05 for k in keys]
        elapsed = round(rng.uniform(.3, 2.8), 2)
        signature = (tuple(keys), tuple(heights), elapsed)
        if signature in excluded:
            continue
        objects = []
        for slot, (key, height) in enumerate(zip(keys, heights)):
            o = catalog[key]
            x = -.95 if slot == 0 else .15
            vx = rng.choice((.15, .20, .25))
            objects.append({'station': str(slot+1), 'source_specimen_id': key, 'color': o.color,
                            'color_rgba': list(o.color_rgba), 'radius_m': o.radius_m,
                            'release_height_m': height, 'position_m': [x, 0, .86+o.radius_m+height],
                            'velocity_m_s': [vx, 0, 0]})
        frames = [[dict(source_specimen_id=o['source_specimen_id'],
                        **advance_bouncing(env._world, env._contacts, o['source_specimen_id'], o['position_m'],
                                           o['velocity_m_s'], elapsed, o['radius_m'], .86)) for o in objects]
                  for env in envs]
        impacts = [s['impacts'] for s in frames[0]]
        if None in impacts:
            continue
        if category == 'first_impact' and sorted(impacts) != [0, 1]:
            continue
        if category == 'mixed_bounces' and not (min(impacts) == 1 and max(impacts) >= 2):
            continue
        if category == 'repeated_bounces' and min(impacts) < 2:
            continue
        gaps = [math.dist(frames[0][i]['position_m'], frames[1][i]['position_m']) for i in range(2)]
        if not all(.045 <= gap <= .12 for gap in gaps):
            continue
        # Near-impact timing can magnify a small visual reading error. Reject cases
        # whose correct positions shift > 1 cm for a +/-5 mm clearance error.
        stable = True
        for wi, env in enumerate(envs):
            for i, o in enumerate(objects):
                for dh in (-.005, .005):
                    p = list(o['position_m']); p[2] += dh
                    s = advance_bouncing(env._world, env._contacts, o['source_specimen_id'], p,
                                         o['velocity_m_s'], elapsed, o['radius_m'], .86)
                    if math.dist(s['position_m'], frames[wi][i]['position_m']) > .01:
                        stable = False
        if not stable:
            continue
        # Horizontal trajectories remain separated for all times, not only in the target frame.
        if objects[1]['position_m'][0]-objects[0]['position_m'][0]+min(0, elapsed*(objects[1]['velocity_m_s'][0]-objects[0]['velocity_m_s'][0])) < .3:
            continue
        excluded.add(signature)
        return objects, elapsed, frames, gaps
    raise ValueError(f'No identifiable, visually readable {category} question for these world parameters.')


def create_manifests(envs, seed=921):
    rng = random.Random(seed)
    categories = ['first_impact']*2+['mixed_bounces']*3+['repeated_bounces']*3
    rng.shuffle(categories)
    # Each world's answer labels are balanced, with a random order and distinct paired answers.
    answer_pairs = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 3), (1, 0), (2, 1), (3, 2)]
    rng.shuffle(answer_pairs)
    result, excluded = [], set()
    for index, (category, answer_pair) in enumerate(zip(categories, answer_pairs)):
        objects, elapsed, frames, gaps = select_pair(envs, category, rng, excluded)
        masks = [None]*4
        masks[answer_pair[0]], masks[answer_pair[1]] = (0, 0), (1, 1)
        mixed = [(0, 1), (1, 0)]; rng.shuffle(mixed)
        for i in range(4):
            if masks[i] is None:
                masks[i] = mixed.pop()
        choices = {label: {'hypothesis': 'paired_world_components', 'component_worlds': list(mask),
                           'objects': [deepcopy(frames[mask[i]][i]) for i in range(2)]}
                   for label, mask in zip('ABCD', masks)}
        for wi, env in enumerate(envs):
            result.append({'format': 'bounce_prediction_scene', 'schema_version': 2, 'visual_version': 2,
                           'id': f'bounce_hard_{index+1:03d}_w{wi+1}', 'pair_id': f'pair_{index+1:03d}',
                           'experiment_world': f'world_{wi+1:03d}', 'category': category,
                           **identity(env), 'surface_id': env._contacts.surface_id,
                           'surface_z_m': .86, 'objects': deepcopy(objects), 'elapsed_s': elapsed,
                           'choices': deepcopy(choices), 'answer': 'ABCD'[answer_pair[wi]], 'images': dict(IMAGES),
                           'minimum_candidate_separation_m': min(gaps), 'object_alternative_separations_m': gaps,
                           'correct_impact_counts': [s['impacts'] for s in frames[wi]],
                           'scene': {'camera_position_m': [0, -7, 1.51], 'camera_target_m': [0, 0, 1.51],
                                     'ortho_scale_m': 2.9, 'grid_spacing_m': .1, 'minor_grid_spacing_m': .025,
                                     'table_bounds_m': [-1.4, 1.4, -.6, .6], 'grid_back_y_m': .22}})
    return result


def write_batch(root, source, envs, manifests, seed):
    root.mkdir(parents=True, exist_ok=True)
    worlds = []
    for wi, env in enumerate(envs):
        folder = f'worlds/world_{wi+1:03d}'
        env.export_private_artifacts(root/folder)
        worlds.append({'key': f'world_{wi+1:03d}', 'folder': folder, **identity(env),
                       'source_record': str(source/'interaction.json') if wi == 0 else None})
    entries, questions = [], []
    for i, manifest in enumerate(manifests, 1):
        relative = f'questions/q{i:03d}'
        folder = root/relative; folder.mkdir(parents=True)
        (folder/'scene.json').write_text(json.dumps(manifest, indent=2)+'\n')
        q = build_question(manifest)
        (folder/'questions.json').write_text(json.dumps([q], indent=2)+'\n')
        write_record(folder, manifest)
        cards = ''.join(f'<figure><img src="{IMAGES[k]}"><figcaption>Choice {k}</figcaption></figure>' for k in 'ABCD')
        (folder/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Bounce prediction</title>'
            '<style>body{font:18px system-ui;max-width:1300px;margin:40px auto}img{width:100%}'
            '.choices{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0}</style>'
            '<h1>Bounce prediction</h1><p>'+html.escape(q['question'])+'</p><img src="context.png"><div class="choices">'+cards+'</div>')
        q['context_image'] = relative+'/'+q['context_image']
        for c in q['choices']:
            c['image'] = relative+'/'+c['image']
        questions.append(q)
        entries.append({'folder': relative, 'id': manifest['id'], 'experiment_world': manifest['experiment_world'],
                        'pair_id': manifest['pair_id']})
    batch = {'format': 'bounce_prediction_batch', 'schema_version': 2, 'difficulty': 'paired_world_hard',
             'source_run': str(source), 'generation_seed': seed, **identity(envs[0]),
             'worlds': worlds, 'questions': entries}
    (root/'batch.json').write_text(json.dumps(batch, indent=2)+'\n')
    (root/'questions.json').write_text(json.dumps(questions, indent=2)+'\n')
    (root/'index.html').write_text('<!doctype html><meta charset="utf-8"><h1>Bounce prediction: 16 questions, two worlds</h1>'
        '<p>Each paired question shares identical images but uses its own experimental history.</p><ul>'+
        ''.join(f'<li><a href="{e["folder"]}/index.html">{e["id"]}</a> ({e["experiment_world"]})</li>' for e in entries)+'</ul>')
    (root/'parameters.md').write_text('# Hard bounce batch (host-only)\n\n'
        '16 questions in eight paired contexts. Each pair has identical images and different correct answers. '
        'Each object alone agrees with two choices, so both objects are required. '
        'Heights and launch speeds are read from the context image; neither color nor height is named in question text. '
        'Alternatives differ by 4.5–12 cm per object, with a 0.025 m minor grid and a +/-5 mm input-height robustness check.\n\n'
        'World 1 reuses the saved interaction. World 2 requires its own interaction; the evaluation command creates it '
        'unless a matching --world-record is provided. World records are in worlds/.\n\n```json\n'+json.dumps(batch, indent=2)+'\n```\n')
    return batch


def prepare_hard_batch(run_dir, output_dir, seed=921, replace=False):
    source, root = Path(run_dir).resolve(), Path(output_dir).resolve()
    first = BounceLabEnv.from_private_manifest(json.loads((source/'private_manifest.json').read_text()))
    envs = [first, second_world(first)]
    manifests = create_manifests(envs, seed)
    if root.exists() and any(root.iterdir()) and not replace:
        raise FileExistsError('Use --replace to archive and replace the current batch, or choose an empty directory.')
    root.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.bounce_prepare_', dir=root.parent) as temporary:
        staged = Path(temporary)/'batch'
        batch = write_batch(staged, source, envs, manifests, seed)
        archive = None
        if root.exists():
            archive = root.parent/(root.name+'_archive_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
            root.rename(archive)
        try:
            staged.rename(root)
        except Exception:
            if archive is not None:
                archive.rename(root)
            raise
        if archive is not None:
            print(f'ARCHIVED {archive}')
    return batch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True)
    parser.add_argument('--output-dir', default='renders/lab_4/bounce_prediction')
    parser.add_argument('--seed', type=int, default=921)
    parser.add_argument('--replace', action='store_true')
    args = parser.parse_args()
    batch = prepare_hard_batch(args.run_dir, args.output_dir, args.seed, args.replace)
    print(f"Prepared {len(batch['questions'])} questions in {args.output_dir}")


if __name__ == '__main__':
    main()
