"""Static buoyancy questions: infer liquid density, then judge every object's equilibrium."""
import argparse
from copy import deepcopy
import html
import json
import math
from pathlib import Path
import random

IMAGES = {'context': 'context.png', **{letter: f'choice_{letter}.png' for letter in 'ABCD'}}

LIQUID_VISUAL_SETTINGS = {
    'version': 2, 'style': 'measurement_view',
    'glass_surface_mix': .045, 'liquid_body_surface_mix': .04, 'liquid_top_surface_mix': .22,
    'liquid_tint_rgba': [.80, .94, 1.0, 1.0],
    'waterline_color_rgb': [.015, .22, .29],
    'wall_waterline_radius_m': .00065, 'object_waterline_radius_m': .0003,
    'neutral_backdrop': True, 'optical_refraction': False,
    'note': 'Surface outlines and controlled transparency make immersion readable; physics and displacement are unchanged.'}


def liquid_visual_settings(manifest):
    return dict(LIQUID_VISUAL_SETTINGS, **manifest.get('visual', {}))


def equilibrium(density, liquid_density):
    if not all(math.isfinite(x) and x > 0 for x in (density, liquid_density)):
        raise ValueError('Densities must be finite and positive.')
    if math.isclose(density, liquid_density, rel_tol=1e-9):
        raise ValueError('Neutral buoyancy has no unique resting height; choose another liquid density.')
    return {'mode': 'floating', 'submerged_fraction': density/liquid_density} if density < liquid_density else {
        'mode': 'bottom', 'submerged_fraction': 1.0}


def frame_geometry(manifest, objects, states):
    """Conserve liquid volume across independently reset context/choice arrangements."""
    tank = manifest['tank']
    if len(objects) != len(states) or not objects:
        raise ValueError('Every object needs a state.')
    displaced = sum(obj['volume_m3']*state['submerged_fraction'] for obj, state in zip(objects, states))
    height = tank['initial_liquid_depth_m']+displaced/tank['inner_side_m']**2
    if height >= tank['inner_side_m']:
        raise ValueError('Liquid would overflow the tank.')
    surface = tank['floor_z_m']+height
    result = []
    for obj, state in zip(objects, states):
        size = obj['side_length_m']
        fraction = state['submerged_fraction']
        if state['mode'] == 'floating' and 0 < fraction < 1:
            z = surface+(.5-fraction)*size
        elif state['mode'] == 'bottom' and fraction == 1:
            z = tank['floor_z_m']+size/2
        else:
            raise ValueError('Unsupported resting state.')
        if z-size/2 < tank['floor_z_m']-1e-9 or z+size/2 >= tank['floor_z_m']+tank['inner_side_m']:
            raise ValueError('Object would intersect floor or extend above the tank.')
        if state['mode'] == 'bottom' and height < size:
            raise ValueError('Bottom object must be fully submerged.')
        x, y = obj['xy_m']
        if max(abs(x), abs(y))+size/2 >= tank['inner_side_m']/2:
            raise ValueError('Object would intersect tank wall.')
        for other in result:
            half = (size+other['side_length_m'])/2
            if all(abs(a-b) < half-1e-9 for a, b in zip((x, y, z), other['center_m'])):
                raise ValueError('Objects overlap.')
        result.append(dict(obj, **state, center_m=[x, y, z]))
    return {'surface_z_m': surface, 'liquid_depth_m': height, 'displaced_volume_m3': displaced, 'objects': result}


def object_record(specimen, volume_ml, x=0):
    volume = volume_ml*1e-6
    return {'source_specimen_id': specimen.specimen_id, 'shape': specimen.shape, 'color': specimen.color,
            'color_rgba': list(specimen.color_rgba), 'density_kg_m3': specimen.density_kg_m3,
            'volume_m3': volume, 'mass_kg': volume*specimen.density_kg_m3,
            'side_length_m': volume**(1/3), 'xy_m': [x, 0]}


def build_liquid_manifest(registry, liquid_density, index=0, volume_ml=60, seed=23):
    if not math.isfinite(volume_ml) or not 10 <= volume_ml <= 100:
        raise ValueError('Sample volume must be between 10 and 100 mL for this apparatus.')
    if len(registry.specimens) != 4:
        raise ValueError('This tank layout requires four recorded specimens.')
    candidates = [obj for obj in registry.specimens if .30 <= obj.density_kg_m3/liquid_density <= .85]
    if not candidates:
        raise ValueError('Need a clearly partially floating known specimen in the context.')
    context = candidates[index % len(candidates)]
    rng = random.Random(seed+index)
    specimens = list(registry.specimens)
    rng.shuffle(specimens)
    objects = [object_record(obj, volume_ml, (i-1.5)*.058) for i, obj in enumerate(specimens)]
    correct = [equilibrium(obj['density_kg_m3'], liquid_density) for obj in objects]
    context_objects = [object_record(context, volume_ml, objects[index % 4]['xy_m'][0])]
    context_states = [equilibrium(context.density_kg_m3, liquid_density)]
    # Same composition and apparatus in every choice; change one, two, or three states.
    alternatives = []
    for count in (1, 2, 3):
        candidate = deepcopy(correct)
        for j in rng.sample(range(4), count):
            state = candidate[j]
            if state['mode'] == 'bottom':
                state.update(mode='floating', submerged_fraction=.55)
            elif count == 2:
                state.update(mode='bottom', submerged_fraction=1.0)
            else:
                fraction = state['submerged_fraction']
                state['submerged_fraction'] = fraction-.25 if fraction >= .5 else fraction+.25
        alternatives.append(candidate)
    answer = 'ABCD'[index % 4]
    choices = {}
    for label in 'ABCD':
        choices[label] = deepcopy(correct) if label == answer else alternatives.pop(0)
    manifest = {'format': 'liquid_equilibrium_scene', 'schema_version': 1, 'visibility': 'host_only',
                'object_registry_id': registry.registry_id, 'question_id': f'liquid_{index+1:03d}',
                'answer': answer, 'liquid_density_kg_m3': liquid_density,
                'tank': {'inner_side_m': .28, 'wall_thickness_m': .004, 'floor_z_m': .872,
                         'initial_liquid_depth_m': .17},
                'scene': {'table_height_m': .86, 'camera_position_m': [0, -1.4, 1.38],
                          'camera_target_m': [0, 0, 1.012], 'ortho_scale_m': .60,
                          'resolution': [1536, 1024], 'samples': 96, 'seed': seed},
                'visual': deepcopy(LIQUID_VISUAL_SETTINGS),
                'physics': {'model': 'Archimedes equilibrium with conserved liquid volume',
                            'gravity_m_s2': 9.81, 'upright_frictionless_guides': True,
                            'guide_vertical_force': 0, 'uniform_nonabsorbing_materials': True,
                            'surface_tension_ignored': True,
                            'reset_same_liquid_volume_for_every_image': True},
                'objects': objects, 'context_objects': context_objects,
                'context_states': context_states, 'choice_states': choices, 'images': dict(IMAGES)}
    manifest['frames'] = {'context': frame_geometry(manifest, context_objects, context_states)}
    manifest['frames'].update({key: frame_geometry(manifest, objects, states) for key, states in choices.items()})
    matches = [key for key, states in choices.items() if states == correct]
    if matches != [answer]:
        raise ValueError('Exactly one choice must have every object correct.')
    return manifest


def build_liquid_question(manifest):
    return {'id': manifest['question_id'], 'type': 'image_multiple_choice',
            'object_registry_id': manifest['object_registry_id'],
            'question': (
                'The context image shows one object at rest in an unknown liquid. '
                'Use its appearance to match it to a material studied in the prior experiments. '
                'Infer the liquid density from the fraction of that object submerged. '
                'The four candidate images show the same collection of objects in the same liquid, all at rest. '
                'Identify the materials visually and select the single image in which EVERY object has the correct '
                'floating depth or position on the tank bottom. All samples have equal volumes and retain the '
                'densities of their corresponding experimental materials. Thin guides keep cubes upright without '
                'friction or vertical support. The markings divide each cube into ten equal-volume horizontal layers. '
                'Objects are homogeneous and do not absorb liquid; surface tension is negligible. '
                'Each arrangement starts with the same liquid volume, so the surface may move as objects are added. '
                'Exactly one candidate is fully correct. Answer with its letter.'),
            'context_image': IMAGES['context'],
            'context_caption': 'Context — reference object at equilibrium',
            'choices': [{'label': key, 'text': f'Candidate {key}', 'image': IMAGES[key]} for key in 'ABCD'],
            'answer': manifest['answer']}


def write_liquid_record(root, manifest, artifact='scene.json', actual=None):
    root = Path(root)
    lines = ['# Liquid scene parameters (host-only)', '',
             f"Liquid density: {manifest['liquid_density_kg_m3']:g} kg/m³; answer: {manifest['answer']}.", '',
             'Context submersion fraction = object density / liquid density. '
             'A denser object rests on the bottom; liquid volume is conserved in each frame.', '',
             '```json', json.dumps({'scene': manifest, 'actual_render': actual}, indent=2), '```', '']
    text = '\n'.join(lines)
    (root/f'{Path(artifact).stem}_parameters.md').write_text(text)
    (root/'parameters.md').write_text(text)


def prepare_liquid_batch(registry_path, output_dir, volume_ml=60, seed=23,
                         liquid_densities=(900, 1000, 1100, 1300, 1400, 1500, 1800, 2000)):
    from src.objects.registry import ObjectRegistry
    registry = ObjectRegistry.load(registry_path)
    if not liquid_densities or any(not math.isfinite(x) or x <= 0 for x in liquid_densities):
        raise ValueError('Supply positive finite liquid densities.')
    manifests = [build_liquid_manifest(registry, density, i, volume_ml, seed)
                 for i, density in enumerate(liquid_densities)]
    root = Path(output_dir)
    if root.exists() and any(root.iterdir()):
        raise FileExistsError('Use a new output folder for the liquid batch.')
    root.mkdir(parents=True, exist_ok=True)
    registry.save(root/'object_registry.json')
    registry.write_markdown(root/'object_registry.md')
    entries, questions = [], []
    for i, manifest in enumerate(manifests, 1):
        folder = f'questions/q{i:03d}'
        target = root/folder
        target.mkdir(parents=True)
        (target/'scene.json').write_text(json.dumps(manifest, indent=2)+'\n')
        question = build_liquid_question(manifest)
        (target/'questions.json').write_text(json.dumps([question], indent=2)+'\n')
        write_liquid_record(target, manifest)
        cards = ''.join(f'<figure><img src="{IMAGES[key]}"><figcaption>{key}</figcaption></figure>' for key in 'ABCD')
        (target/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Liquid equilibrium</title>'
            '<style>body{font:18px system-ui;max-width:1200px;margin:30px auto}img{width:100%}'
            'figure{margin:12px}.choices{display:grid;grid-template-columns:1fr 1fr}</style>'
            '<h1>Liquid equilibrium</h1><p>'+html.escape(question['question'])+'</p>'
            '<figure><img src="context.png"><figcaption>Context</figcaption></figure><div class="choices">'+cards+'</div>')
        question = deepcopy(question)
        question['context_image'] = folder+'/'+question['context_image']
        for choice in question['choices']:
            choice['image'] = folder+'/'+choice['image']
        questions.append(question)
        entries.append({'folder': folder})
    batch = {'format': 'liquid_equilibrium_batch', 'schema_version': 1,
             'object_registry_id': registry.registry_id, 'volume_ml': volume_ml, 'include_reversed': False,
             'seed': seed, 'questions': entries, 'grading': 'all_objects_correct_at_equilibrium'}
    (root/'batch.json').write_text(json.dumps(batch, indent=2)+'\n')
    (root/'questions.json').write_text(json.dumps(questions, indent=2)+'\n')
    (root/'README.md').write_text('# Liquid equilibrium evaluation\n\n'
        f'{len(entries)} questions; each has one context image and four candidate arrangements. '
        'Exactly one arrangement has all objects at the correct equilibrium.\n\n'
        'The original experimental object registry is reused. Liquid densities remain host-only. '
        'Images await rendering. See docs/liquid_equilibrium.md for commands and assumptions.\n')
    (root/'index.html').write_text('<!doctype html><meta charset="utf-8"><h1>Liquid equilibrium</h1><ol>'+
        ''.join(f'<li><a href="{entry["folder"]}/index.html">Question {i}</a></li>' for i, entry in enumerate(entries, 1))+'</ol>')
    return batch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--volume-ml', type=float, default=60)
    parser.add_argument('--seed', type=int, default=23)
    parser.add_argument('--liquid-densities', type=float, nargs='+', default=[900, 1000, 1100, 1300, 1400, 1500, 1800, 2000])
    args = parser.parse_args()
    batch = prepare_liquid_batch(args.registry, args.output_dir, args.volume_ml, args.seed, args.liquid_densities)
    print(f"Prepared {len(batch['questions'])} liquid equilibrium questions.")


if __name__ == '__main__':
    main()
