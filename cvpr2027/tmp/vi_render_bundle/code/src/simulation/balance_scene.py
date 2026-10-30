"""Prepare a registry-backed density question; rendering is a separate CUDA job."""
import argparse
import json
import math
from pathlib import Path

IMAGES = {'context': 'context.png', 'A': 'choice_A.png', 'B': 'choice_B.png',
          'C': 'choice_C.png', 'D': 'choice_D.png'}


def pan_objects(manifest, side):
    """Read both the original single-object format and multi-object scenes."""
    objects = manifest['objects'][side]
    return objects if isinstance(objects, list) else [objects]


def build_manifest(registry, left='sample_A', right='sample_B', volume_ml=60):
    if not math.isfinite(volume_ml) or not 0 < volume_ml <= 216:
        raise ValueError('Equal sample volume must be in (0, 216] mL to fit the pans and suspension.')
    catalog = {obj.specimen_id: obj for obj in registry.specimens}
    objects = {}
    for side, key in [('left', left), ('right', right)]:
        if key not in catalog:
            raise ValueError(f'Unknown registry specimen: {key}')
        source = catalog[key]
        volume = volume_ml*1e-6
        objects[side] = {'source_specimen_id': key, 'color': source.color,
                         'shape': source.shape, 'color_rgba': list(source.color_rgba),
                         'source_mass_kg': source.mass_kg, 'source_volume_m3': source.volume_m3,
                         'density_kg_m3': source.density_kg_m3,
                         'volume_m3': volume, 'mass_kg': source.density_kg_m3*volume,
                         'side_length_m': volume**(1/3)}
    lm, rm = objects['left']['mass_kg'], objects['right']['mass_kg']
    answer = 'C' if math.isclose(lm, rm, rel_tol=1e-9, abs_tol=1e-12) else ('A' if lm > rm else 'B')
    return {'format': 'density_balance_scene', 'schema_version': 1, 'visibility': 'host_only',
            'object_registry_id': registry.registry_id, 'objects': objects,
            'transfer': 'Equal-volume samples of recorded materials; preserve density, shape and RGBA. Recompute mass.',
            'balance': {'arm_length_m': .22, 'pivot_z_m': 1.32, 'pan_drop_m': .25,
                        'pan_radius_m': .075, 'pan_thickness_m': .006, 'tilt_degrees': 14,
                        'model': 'Ideal equal arms, identical tared pans, negligible friction, symmetric 14-degree travel stops; endpoint illustrations.'},
            'scene': {'table_height_m': .86, 'camera_position_m': [0, -1.65, 1.76],
                      'camera_target_m': [0, 0, 1.12], 'lens_mm': 52, 'fstop': 8,
                      'seed': 7, 'resolution': [1536, 1024], 'samples': 96},
            'unknown': {'text': 'Unknown', 'background': 'context.png', 'gaussian_blur_pixels': 28},
            'images': dict(IMAGES), 'answer': answer}


def build_question(manifest):
    left, right = [pan_objects(manifest, side)[0] for side in ('left', 'right')]
    text = (
        'The context image shows an equal-arm beam balance held level before release. '
        'Identify and count the objects on each pan from the image. All objects have exactly equal volumes. '
        'Objects with the same appearance are samples of the same homogeneous material. '
        'Materials matching specimens from the prior experiments retain their measured densities, '
        'but the new sample masses may differ from the original specimen masses. '
        'Other materials may not have appeared in those experiments; their densities are unspecified positive values. '
        'Use only the experimental evidence, not assumptions about material density from appearance. '
        'The pans are identical and tared, the arms have equal lengths, pivot friction is negligible, '
        'and symmetric mechanical stops limit the tilt. '
        'After release and settling, which image shows the outcome? '
        'Choose Unknown if more than one outcome is compatible with the available evidence. '
        'Identical material amounts on opposite pans may cancel even when their density is unknown.'
    ) if manifest.get('schema_version', 1) >= 2 else None
    return {'id': manifest.get('question_id', f"density_balance_{left['source_specimen_id']}_{right['source_specimen_id']}"),
            'type': 'image_multiple_choice',
            'object_registry_id': manifest['object_registry_id'],
            'question': text or (
                'The context image shows an equal-arm beam balance held level before release. '
                'Identify the material on each pan from its appearance in the image, '
                'using what you learned about the specimens in the prior experiments. '
                'These are new samples with exactly equal volumes. Their material densities are unchanged '
                'from the prior experiments, but their masses may differ from the original specimens. '
                'The pans are identical and tared, the arms have equal lengths, pivot friction is negligible, '
                'and symmetric mechanical stops limit the tilt. '
                'After the balance is released and settles, which image shows the outcome? '
                'Choose Unknown only if the available evidence is insufficient.'),
            'context_image': IMAGES['context'],
            'choices': [{'label': label, 'text': caption, 'image': IMAGES[label]}
                        for label, caption in [('A', 'Left pan down'), ('B', 'Right pan down'),
                                               ('C', 'Both pans level'), ('D', 'Unknown')]],
            'answer': manifest['answer']}


def write_parameters(directory, manifest, artifact=None, actual=None):
    directory = Path(directory)
    lines = ['# Density balance parameters (host-only)', '',
             f"Source registry: `{manifest['object_registry_id']}`", '', manifest['transfer'], '',
             '| Pan | Source specimen | Shape | Color | Volume (mL) | Mass (g) | Density (kg/m³) |',
             '|---|---|---|---|---:|---:|---:|']
    for side in ('left', 'right'):
        for index, obj in enumerate(pan_objects(manifest, side), 1):
            lines.append(f"| {side} #{index} | {obj['source_specimen_id']} | {obj['shape']} | {obj['color']} | "
                         f"{obj['volume_m3']*1e6:.9g} | {obj['mass_kg']*1e3:.9g} | {obj['density_kg_m3']:.9g} |")
    lines += ['', f"Expected choice: **{manifest['answer']}** (private; never included in model messages).", '',
              'Context is held level before release. C is the level outcome; D blurs that same scene and adds Unknown.',
              'The tilted images illustrate the direction of the final outcome, not a time-integrated simulation.', '',
              '## Complete scene definition', '', '```json', json.dumps(manifest, indent=2), '```', '']
    if actual:
        lines += ['## Actual render settings', '', '```json', json.dumps(actual, indent=2), '```', '']
    text = '\n'.join(lines)
    (directory/(f'{Path(artifact).stem}_parameters.md' if artifact else 'scene_parameters.md')).write_text(text)
    (directory/'parameters.md').write_text(text)


def prepare_bundle(registry_path, output_dir, left='sample_A', right='sample_B', volume_ml=60):
    from src.objects.registry import ObjectRegistry
    registry = ObjectRegistry.load(registry_path)
    manifest = build_manifest(registry, left, right, volume_ml)
    return write_bundle(registry, output_dir, manifest)


def write_bundle(registry, output_dir, manifest):
    root = Path(output_dir)
    if root.exists() and any(root.iterdir()):
        raise FileExistsError('Use an empty output directory to keep render records consistent.')
    root.mkdir(parents=True, exist_ok=True)
    registry.save(root/'object_registry.json')
    registry.write_markdown(root/'object_registry.md')
    (root/'scene.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (root/'questions.json').write_text(json.dumps([build_question(manifest)], indent=2)+'\n')
    write_parameters(root, manifest)
    # Local review page uses only public question fields and image paths, never the answer.
    import html
    question = build_question(manifest)
    cards = ''.join(f'<figure><img src="{c["image"]}"><figcaption>{c["label"]}. {c["text"]}</figcaption></figure>'
                    for c in question['choices'])
    (root/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Density balance</title>'
        '<style>body{font:18px system-ui;background:#edf0f2;color:#18232b;max-width:1200px;margin:40px auto;'
        'padding:0 20px}img{width:100%;border-radius:12px}figure{margin:0}figcaption{padding:12px 0}'
        '.choices{display:grid;grid-template-columns:1fr 1fr;gap:24px}.context{max-width:850px;margin:24px auto}'
        '@media(max-width:650px){.choices{grid-template-columns:1fr}}</style>'
        '<h1>Predict the balance outcome</h1><p>'+html.escape(question['question'])+'</p>'
        '<figure class="context"><img src="context.png"><figcaption>Context — held level before release</figcaption>'
        '</figure><div class="choices">'+cards+'</div>')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--left', default='sample_A')
    parser.add_argument('--right', default='sample_B')
    parser.add_argument('--volume-ml', type=float, default=60)
    args = parser.parse_args()
    prepare_bundle(args.registry, args.output_dir, args.left, args.right, args.volume_ml)
    print(f'Prepared {args.output_dir}/scene.json; images await Blender rendering.')


if __name__ == '__main__':
    main()
