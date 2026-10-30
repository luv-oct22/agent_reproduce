"""Prepare or render a density experiment with one folder per material comparison."""
import argparse
from copy import deepcopy
import html
from itertools import combinations
import json
import os
from pathlib import Path
import re
import subprocess

from src.objects.registry import ObjectRegistry
from src.simulation.balance_scene import build_manifest, prepare_bundle, IMAGES


def prepare_experiment(registry_path, output_dir, volume_ml=60, include_reversed=False, migrate_flat=False):
    registry = ObjectRegistry.load(registry_path)
    root = Path(output_dir)
    specimens = sorted(registry.specimens, key=lambda obj: obj.specimen_id)
    pairs = list(combinations(specimens, 2))
    if not pairs:
        raise ValueError('At least two recorded materials are required.')
    if include_reversed:
        pairs += [(right, left) for left, right in pairs]
    plan = []
    for i, (left, right) in enumerate(pairs, 1):
        slug = lambda value: re.sub(r'[^a-z0-9]+', '_', value.lower()).strip('_') or 'material'
        folder = f'questions/q{i:03d}_{slug(left.color)}_{slug(right.color)}'
        manifest = build_manifest(registry, left.specimen_id, right.specimen_id, volume_ml)
        plan.append((folder, manifest))

    # Validate all existing work before moving or creating question folders.
    if (root/'object_registry.json').exists():
        if ObjectRegistry.load(root/'object_registry.json').to_dict() != registry.to_dict():
            raise ValueError('Experiment registry differs from the requested registry.')
    if (root/'batch.json').exists():
        old = json.loads((root/'batch.json').read_text())
        if old['include_reversed'] != include_reversed or old['volume_ml'] != volume_ml:
            raise ValueError('Batch settings changed; use a new output directory.')
    for folder, manifest in plan:
        target = root/folder
        if target.exists() and any(target.iterdir()):
            if not (target/'scene.json').exists() or json.loads((target/'scene.json').read_text()) != manifest:
                raise ValueError(f'Existing question parameters differ: {target}')
            if not (target/'questions.json').exists():
                raise ValueError(f'Existing question is incomplete: {target}')
    if (root/'scene.json').exists():
        if not migrate_flat:
            raise ValueError('Flat render found; pass --migrate-flat to preserve it in its question folder.')
        flat = json.loads((root/'scene.json').read_text())
        matches = [folder for folder, manifest in plan if manifest == flat]
        if len(matches) != 1:
            raise ValueError('Existing flat scene does not match a requested comparison.')
        target = root/matches[0]
        if target.exists() and any(target.iterdir()):
            raise FileExistsError(f'Migration target is not empty: {target}')
        if any(p.is_dir() and p.name != 'questions' for p in root.iterdir()):
            raise ValueError('Unexpected subdirectory in flat render; reorganize it separately.')
        files = [p for p in root.iterdir() if p.is_file()]
        target.mkdir(parents=True, exist_ok=True)
        for source in files:
            source.rename(target/source.name)
        print(f'Preserved existing render in {target}')

    root.mkdir(parents=True, exist_ok=True)
    registry.save(root/'object_registry.json')
    registry.write_markdown(root/'object_registry.md')
    questions, entries = [], []
    for folder, manifest in plan:
        target = root/folder
        objects = manifest['objects']
        left, right = [objects[side]['source_specimen_id'] for side in ('left', 'right')]
        if not (target/'scene.json').exists():
            prepare_bundle(root/'object_registry.json', target, left, right, volume_ml)
        local_questions = json.loads((target/'questions.json').read_text())
        if len(local_questions) != 1:
            raise ValueError(f'Expected one question in {target}')
        q = deepcopy(local_questions[0])
        q['context_image'] = f"{folder}/{q['context_image']}"
        for choice in q['choices']:
            choice['image'] = f"{folder}/{choice['image']}"
        questions.append(q)
        entries.append({'folder': folder, 'left': left, 'right': right,
                        'left_color': objects['left']['color'], 'right_color': objects['right']['color']})
    batch = {'format': 'density_balance_batch', 'schema_version': 1,
             'object_registry_id': registry.registry_id, 'volume_ml': volume_ml,
             'include_reversed': include_reversed, 'questions': entries}
    (root/'batch.json').write_text(json.dumps(batch, indent=2)+'\n')
    (root/'questions.json').write_text(json.dumps(questions, indent=2)+'\n')
    rows = '\n'.join(f"| [{Path(e['folder']).name}]({e['folder']}/index.html) | {e['left']} ({e['left_color']}) | "
                     f"{e['right']} ({e['right_color']}) |" for e in entries)
    (root/'README.md').write_text('# Density balance experiment\n\n'
        f'{len(entries)} questions, five images per question, {volume_ml:g} mL per sample.\n\n'
        '| Question | Left pan | Right pan |\n|---|---|---|\n'+rows+'\n\n'
        'Each question owns its images, scene, question JSON and parameter Markdown records. '
        'The root questions.json evaluates all questions; image paths are relative to that file.\n\n'
        'Render pending questions: `bash scripts/render/render_density_balance_batch.sh` from the repository root. '
        'Completed questions are skipped; add `--rerender` to render them again.\n')
    links = ''.join(f'<li><a href="{e["folder"]}/index.html">'
                    f'{html.escape(e["left_color"])} vs {html.escape(e["right_color"])}'
                    f'</a></li>' for e in entries)
    (root/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Density balance experiment</title>'
        '<style>body{font:20px system-ui;max-width:900px;margin:60px auto}li{margin:18px}</style>'
        '<h1>Density balance experiment</h1><p>One context image and four choices per question.</p><ul>'+links+'</ul>')
    return batch


def question_complete(directory):
    root = Path(directory)
    if (root/'scene.json').is_file():
        manifest = json.loads((root/'scene.json').read_text())
        if manifest.get('format') in ('bounce_prediction_scene', 'drag_prediction_scene'):
            from src.simulation.bounce_scene import scene_digest
            report_path = root/'build_report.json'
            if not report_path.is_file():
                return False
            report = json.loads(report_path.read_text())
            if not report.get('images_rendered') or report.get('scene_digest') != scene_digest(manifest):
                return False
            for filename in manifest['images'].values():
                image_path = root/filename
                if not image_path.is_file() or image_path.read_bytes()[:8] != b'\x89PNG\r\n\x1a\n' or not (root/(image_path.stem+'_parameters.md')).is_file():
                    return False
            return (root/'scene.blend').is_file() and (root/'scene_parameters.md').is_file()
        if manifest.get('format') == 'liquid_equilibrium_scene':
            from src.simulation.liquid_scene import liquid_visual_settings
            report_path = root/'build_report.json'
            if not report_path.is_file():
                return False
            report = json.loads(report_path.read_text())
            if not report.get('images_rendered') or report.get('visual_settings') != liquid_visual_settings(manifest):
                return False
    for name in IMAGES.values():
        path = root/name
        if not path.is_file() or not (root/f'{path.stem}_parameters.md').is_file():
            return False
        with path.open('rb') as stream:
            if stream.read(8) != b'\x89PNG\r\n\x1a\n':
                return False
    return (root/'scene.blend').is_file() and (root/'scene_parameters.md').is_file()


def render_experiment(output_dir, device='CUDA', samples=96, resolution=(1536, 1024), rerender=False, dry_run=False):
    root = Path(output_dir).resolve()
    batch = json.loads((root/'batch.json').read_text())
    renderers = {'density_balance_batch': 'blender_balance.py', 'liquid_equilibrium_batch': 'blender_liquid.py',
                 'bounce_prediction_batch': 'blender_bounce.py', 'drag_prediction_batch': 'blender_bounce.py'}
    if batch.get('format') not in renderers:
        raise ValueError('Unsupported image experiment batch.')
    repo = Path(__file__).resolve().parents[2]
    blender = os.environ.get('BLENDER_BIN', str(repo/'.tools/blender-3.6.23-linux-x64/blender'))
    for entry in batch['questions']:
        folder = root/entry['folder']
        if not rerender and question_complete(folder):
            print(f'SKIP complete: {folder.name}', flush=True)
            continue
        cmd = [blender, '--background', '--python-exit-code', '1', '--python',
               str(repo/'src/simulation'/renderers[batch['format']]), '--', '--manifest', str(folder/'scene.json'),
               '--device', device, '--samples', str(samples), '--resolution', *map(str, resolution)]
        print(f"{'PLAN' if dry_run else 'RENDER'}: {folder.name}", flush=True)
        if not dry_run:
            subprocess.run(cmd, check=True, cwd=repo)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--registry', required=True)
    prep.add_argument('--output-dir', required=True)
    prep.add_argument('--volume-ml', type=float, default=60)
    prep.add_argument('--include-reversed', action='store_true')
    prep.add_argument('--migrate-flat', action='store_true')
    render = sub.add_parser('render')
    render.add_argument('--output-dir', default='renders/lab_2/density_balance')
    render.add_argument('--device', choices=['CUDA', 'OPTIX', 'CPU'], default=os.environ.get('RENDER_DEVICE', 'CUDA'))
    render.add_argument('--samples', type=int, default=96)
    render.add_argument('--resolution', nargs=2, type=int, default=[1536, 1024])
    render.add_argument('--rerender', action='store_true')
    render.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if args.action == 'prepare':
        result = prepare_experiment(args.registry, args.output_dir, args.volume_ml, args.include_reversed, args.migrate_flat)
        print(f"Prepared {len(result['questions'])} question folders in {args.output_dir}")
    else:
        if args.samples < 1 or min(args.resolution) < 64:
            parser.error('Samples must be positive and resolution dimensions at least 64.')
        render_experiment(args.output_dir, args.device, args.samples, args.resolution, args.rerender, args.dry_run)


if __name__ == '__main__':
    main()
