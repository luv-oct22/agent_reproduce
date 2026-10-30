"""Freeze and verify a drag benchmark without rendering or making model calls."""
import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import shutil
import sys
import tempfile

from src.drag_evaluate import validate_inputs


REPO = Path(__file__).resolve().parents[2]


def read_json(path):
    return json.loads(path.read_text())


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def inventory(root):
    return {p.relative_to(root).as_posix(): {'sha256': digest(p), 'bytes': p.stat().st_size}
            for p in sorted(root.rglob('*')) if p.is_file() and p != root/'baseline.json'}


def verify_integrity(root):
    root = Path(root).resolve()
    manifest = read_json(root/'baseline.json')
    actual = inventory(root)
    expected = manifest['files']
    changed = sorted(k for k in actual.keys() | expected.keys() if actual.get(k) != expected.get(k))
    if changed:
        raise ValueError('Baseline files missing, added or changed: '+', '.join(changed[:10]))
    return manifest


def verify(root):
    """Check archived bytes, then recompute physics with the CURRENT implementation."""
    root = Path(root).resolve()
    manifest = verify_integrity(root)
    records = [root/manifest['source_interaction']]
    records += [root/run['snapshot']/'interaction.json' for run in manifest['evaluations']
                if run['status'] == 'complete']
    for record in records:
        validate_inputs(record, root/'batch')
    return manifest


def freeze(batch_dir, output_dir, evaluations_dir=REPO/'results/drag_evaluation'):
    batch_dir, output_dir = Path(batch_dir).resolve(), Path(output_dir).resolve()
    if output_dir.exists():
        raise FileExistsError(f'Baseline already exists; verify it or choose a new version: {output_dir}')
    batch = read_json(batch_dir/'batch.json')
    source = Path(batch['source_run'])
    validate_inputs(source/'interaction.json', batch_dir)
    batch_questions = read_json(batch_dir/'questions.json')
    # Compare actual questions, scenes and images, not just count or world ID.
    required = ['questions.json', 'private_manifest.json']
    for entry in batch['questions']:
        folder = entry['folder']
        scene = read_json(batch_dir/folder/'scene.json')
        required += [folder+'/scene.json']+[folder+'/'+name for name in scene['images'].values()]
    hashes = {name: digest(batch_dir/name) for name in required}
    matched, excluded = [], []
    for directory in sorted(Path(evaluations_dir).iterdir()):
        params_path = directory/'run_parameters.json'
        if not params_path.is_file():
            continue
        params = read_json(params_path)
        if params.get('question_count') != len(batch_questions) or params.get('world_id') != batch['world_id']:
            continue
        saved = directory/'drag_prediction'
        if any(not (saved/name).is_file() or digest(saved/name) != expected for name, expected in hashes.items()):
            excluded.append({'source': str(directory), 'reason': 'Saved scene/question/image content differs or is incomplete.'})
            continue
        summary = read_json(directory/'summary.json') if (directory/'summary.json').exists() else {}
        status = read_json(directory/'status.json') if (directory/'status.json').exists() else {}
        if digest(directory/'interaction.json') != params['record_sha256']:
            raise ValueError(f'Interaction checksum mismatch: {directory}')
        if summary.get('status') == 'complete':
            validate_inputs(directory/'interaction.json', batch_dir)
        private = read_json(directory/'experiment_private_evaluation.json') if (directory/'experiment_private_evaluation.json').exists() else {}
        interaction = read_json(directory/'interaction.json')
        matched.append({'source': str(directory), 'snapshot': 'evaluations/'+directory.name,
                        'model': params['evaluation_model'],
                        'status': summary.get('status', status.get('status', 'incomplete')),
                        'image_score': summary.get('image_score'),
                        'questions_answered': summary.get('questions_answered'),
                        'numerical_score': private.get('score'),
                        'experiments_used': private.get('experiments_used'),
                        'interaction_finished': interaction['finished'],
                        'record_source': params['record_source']})
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.freeze-', dir=output_dir.parent) as temporary:
        staged = Path(temporary)/'snapshot'
        staged.mkdir()
        shutil.copytree(batch_dir, staged/'batch')
        interaction_dirs = {source}
        for run in matched:
            target = staged/run['snapshot']
            target.mkdir(parents=True)
            for path in Path(run['source']).iterdir():
                if path.is_file():
                    shutil.copy2(path, target/path.name)
            original = Path(run['record_source']).parent
            if original.is_dir():
                interaction_dirs.add(original)
        source_record = None
        for directory in sorted(interaction_dirs):
            relative = Path('interactions')/directory.relative_to(REPO/'results/drag_lab')
            target = staged/relative
            target.mkdir(parents=True)
            for path in directory.iterdir():
                if path.is_file():
                    shutil.copy2(path, target/path.name)
            if directory == source:
                source_record = (relative/'interaction.json').as_posix()
        # Small executable source snapshot; no environment files or credentials.
        code_files = list((REPO/'src').rglob('*.py'))
        code_files += list((REPO/'tests').glob('test_drag*.py'))+[REPO/'tests/test_height_drag.py']
        code_files += [REPO/p for p in ('eval.py', 'requirements.txt', 'configs/drag_lab.yaml',
                       'configs/drag_lab_complex.yaml', 'scripts/render/render_drag_prediction.sh',
                       'scripts/interact/interact_drag_lab.sh', 'scripts/eval/eval_drag_prediction.sh',
                       'docs/drag_lab.md')]
        for path in code_files:
            target = staged/'code'/path.relative_to(REPO)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        packages = {}
        for name in ('numpy', 'scipy', 'matplotlib', 'PyYAML', 'openai', 'Pillow'):
            try:
                packages[name] = version(name)
            except PackageNotFoundError:
                packages[name] = None
        rows = ['| Model | Image score | Numerical score | Measurements used | Finished interaction |',
                '|---|---:|---:|---:|---|']
        for run in matched:
            if run['status'] == 'complete':
                rows.append(f"| {run['model']} | {run['image_score']:.2%} | {run['numerical_score']:.2%} | "
                            f"{run['experiments_used']} | {run['interaction_finished']} |")
        (staged/'README.md').write_text('# Frozen drag baseline\n\n'
            f'{len(batch_questions)} questions; {len(batch_questions)*5} PNG images. '
            'This is the disclosed-law, hidden-height-function benchmark.\n\n'
            +'\n'.join(rows)+'\n\n'
            'These are historical observations, not new model runs. Completion and measurement use differ; '
            'turn limits are not consistently recorded, so do not infer identical run budgets. '
            'Incomplete attempts are preserved separately in baseline.json and are not aggregate scores.\n\n'
            'batch/ contains the shared images, Blender scenes, physics, questions and render records. '
            'evaluations/ contains original per-run records and logs; their duplicate drag_prediction/ '
            'assets are represented by batch/, verified against each original snapshot before freezing. '
            'interactions/ contains source experiment records; code/ records the current implementation. '
            'Original absolute paths inside copied files are provenance, not rewritten runnable paths.\n\n'
            'Files are independent copies with SHA-256 checksums; this is a versioned snapshot, '
            'not filesystem-enforced immutability or protection against edits to the checksum manifest. '
            'Use a new version for any intended benchmark change. No API secrets are captured from the environment.\n')
        manifest = {'format': 'drag_benchmark_baseline', 'schema_version': 1,
                    'name': output_dir.name, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
                    'source_batch': str(batch_dir), 'source_interaction': source_record,
                    'question_count': len(batch_questions), 'candidate_policy': batch.get('candidate_policy'),
                    'world_id': batch['world_id'], 'evaluations': matched, 'excluded_evaluations': excluded,
                    'environment_at_freeze': {'python': sys.version, 'packages': packages},
                    'files': inventory(staged)}
        (staged/'baseline.json').write_text(json.dumps(manifest, indent=2)+'\n')
        verify(staged)
        # The working batch and existing results are never modified.
        if output_dir.exists():
            raise FileExistsError(output_dir)
        staged.rename(output_dir)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['freeze', 'verify'])
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--batch-dir', default=str(REPO/'renders/lab_5/drag_prediction_complex_close'))
    args = parser.parse_args()
    result = freeze(args.batch_dir, args.baseline) if args.action == 'freeze' else verify(args.baseline)
    complete = sum(r['status'] == 'complete' for r in result['evaluations'])
    print(f"Baseline {args.action} passed: {result['question_count']} questions, "
          f"{len(result['files'])} files, {complete} completed evaluations. No model calls.")


if __name__ == '__main__':
    main()
