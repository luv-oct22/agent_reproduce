"""Run bounce experiments and visual evaluation, or reuse matching saved histories."""
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

from src.density_pipeline import RecordedHarness, write_json
from src.envs.bounce_lab import BounceLabEnv
from src.harness import OpenAIHarness
from src.harness.openai import request_timeout_settings, request_retry_settings
from src.interact import InteractionRecord, run_interaction
from src.evaluate import run_evaluation, EvaluationRecord
from src.tasks.identify_bounce import IdentifyBounceTask
from src.evaluation.visual import build_image_choice_content
from src.simulation.balance_batch import question_complete
from src.simulation.bounce_scene import build_question


REPO = Path(__file__).resolve().parents[1]


def validate_inputs(record_path, batch_dir):
    root = Path(batch_dir).resolve()
    batch = json.loads((root/'batch.json').read_text())
    record = None
    if record_path is None:
        if batch.get('schema_version') != 2:
            raise ValueError('Fresh interaction requires a paired-world batch; use --record for legacy batches.')
        primary = next((entry for entry in batch['worlds'] if entry['key'] == 'world_001'), None)
        if primary is None:
            raise ValueError('Paired-world batch is missing world_001.')
        manifest_path = root/primary['folder']/'private_manifest.json'
    else:
        record_path = Path(record_path).resolve()
        record = InteractionRecord.load(str(record_path))
        if record.task_name != 'identify_bounce':
            raise ValueError('Use an identify_bounce interaction record.')
        manifest_path = record_path.parent/'private_manifest.json'
    env = BounceLabEnv.from_private_manifest(json.loads(manifest_path.read_text()))
    private = env.private_manifest()
    expected = {'world_id': private['world_id'], 'object_registry_id': private['object_registry_id'],
                'contact_registry_id': private['contact_registry']['registry_id']}
    if batch.get('format') != 'bounce_prediction_batch' or any(batch.get(k) != v for k, v in expected.items()):
        raise ValueError('Image batch physics differs from the interaction world, objects or contacts.')
    questions = json.loads((root/'questions.json').read_text())
    if not questions or len(questions) != len(batch['questions']):
        raise ValueError('Question list does not match the batch.')
    worlds = {}
    if batch.get('schema_version') == 2:
        for entry in batch['worlds']:
            wenv = BounceLabEnv.from_private_manifest(json.loads((root/entry['folder']/'private_manifest.json').read_text()))
            p = wenv.private_manifest()
            ids = {'world_id': p['world_id'], 'object_registry_id': p['object_registry_id'],
                   'contact_registry_id': p['contact_registry']['registry_id']}
            if entry['key'] in worlds or any(entry.get(k) != v for k, v in ids.items()):
                raise ValueError('Invalid paired-world registry identity.')
            worlds[entry['key']] = ids
        if worlds.get('world_001') != expected:
            raise ValueError('The primary interaction does not match world_001.')
    for q, entry in zip(questions, batch['questions']):
        folder = root/entry['folder']
        manifest = json.loads((folder/'scene.json').read_text())
        question_ids = worlds[entry['experiment_world']] if worlds else expected
        if any(manifest.get(k) != v for k, v in question_ids.items()):
            raise ValueError('Question uses different physical records.')
        canonical = build_question(manifest)
        canonical['context_image'] = entry['folder']+'/'+canonical['context_image']
        for choice in canonical['choices']:
            choice['image'] = entry['folder']+'/'+choice['image']
        if canonical != q:
            raise ValueError('Question text, choices or answer differs from its scene.')
        if not question_complete(folder):
            raise FileNotFoundError(f'Render missing or stale: {folder}. Run scripts/render/render_bounce_prediction.sh first.')
        build_image_choice_content(q, root)
    return record, batch


def evaluate_bounce(model, record_path=None, batch_dir=REPO/'renders/lab_4/bounce_prediction',
                    output_dir=REPO/'results/bounce_evaluation', prepare_only=False, harness_factory=OpenAIHarness,
                    experiment_model=None, max_turns=32, world_records=None):
    record_path = Path(record_path).resolve() if record_path is not None else None
    root = Path(batch_dir).resolve()
    record, batch = validate_inputs(record_path, root)
    if batch.get('schema_version') == 2:
        return evaluate_paired_worlds(model, record_path, root, output_dir, prepare_only, harness_factory,
                                      experiment_model, max_turns, world_records or {}, record, batch)
    output = Path(output_dir).resolve()/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    output.mkdir(parents=True, exist_ok=False)
    write_json(output/'status.json', {'status': 'preparing'})
    try:
        shutil.copytree(root, output/'bounce_prediction', ignore=shutil.ignore_patterns('*.blend', '*.blend1', '*.blend2'))
        shutil.copy2(record_path, output/'interaction.json')
        shutil.copy2(record_path.parent/'private_manifest.json', output/'private_manifest.json')
        parameters = {'experiment_model': record.model, 'evaluation_model': model,
                      'record_source': str(record_path), 'record_sha256': hashlib.sha256(record_path.read_bytes()).hexdigest(),
                      'batch_source': str(root), 'question_count': len(batch['questions']),
                      'history_used': True, 'interaction_finished': record.finished,
                      'world_id': batch['world_id'], 'object_registry_id': batch['object_registry_id'],
                      'contact_registry_id': batch['contact_registry_id'],
                      'api_timeout': request_timeout_settings(), 'api_retry': request_retry_settings()}
        write_json(output/'run_parameters.json', parameters)
        (output/'parameters.md').write_text('# Bounce visual evaluation parameters (host-only)\n\n'
            'The vision model receives the public interaction transcript and five images per question. '
            'Ground-truth registries and answer keys remain host-only.\n\n```json\n'+json.dumps(parameters, indent=2)+'\n```\n')
        if prepare_only:
            write_json(output/'status.json', {'status': 'prepared', 'model_calls': 0})
            return output
        write_json(output/'status.json', {'status': 'running'})
        harness = RecordedHarness(harness_factory(model), output, 'bounce_image_evaluation')
        evaluation = run_evaluation('identify_bounce', harness, str(output/'bounce_prediction/questions.json'),
                                    record, with_history=True, output_dir=str(output))
        summary = {'status': 'complete', 'image_score': evaluation.score,
                   'questions_answered': len(evaluation.answers), 'questions_total': len(batch['questions'])}
        write_json(output/'summary.json', summary)
        write_json(output/'status.json', summary)
        (output/'summary.md').write_text(f"# Bounce visual evaluation\n\nAccuracy: {evaluation.score:.1%}. "
            f"Questions answered: {len(evaluation.answers)}.\n\n"
            'See evaluation_with_history.json for answers and model_responses.jsonl for full model responses.\n')
        return output
    except Exception as exc:
        write_json(output/'status.json', {'status': 'failed', 'error_type': type(exc).__name__})
        raise


def evaluate_paired_worlds(model, record_path, root, output_dir, prepare_only, harness_factory,
                           experiment_model, max_turns, world_records, primary_record, batch):
    if max_turns < 1:
        raise ValueError('max_turns must be positive.')
    known = {entry['key'] for entry in batch['worlds']}
    if set(world_records)-known or 'world_001' in world_records:
        raise ValueError('Use --record for world_001; --world-record must name another batch world.')
    records = {'world_001': primary_record} if primary_record is not None else {}
    experiment_model = experiment_model or (primary_record.model if primary_record is not None else model)
    envs = {}
    for entry in batch['worlds']:
        key = entry['key']
        env = BounceLabEnv.from_private_manifest(json.loads((root/entry['folder']/'private_manifest.json').read_text()))
        envs[key] = env
        if key in world_records:
            path = Path(world_records[key]).resolve()
            saved = InteractionRecord.load(str(path))
            p = json.loads((path.parent/'private_manifest.json').read_text())
            if saved.task_name != 'identify_bounce' or any(p.get(field) != env.private_manifest().get(field)
                                                         for field in ('world_id', 'object_registry_id', 'contact_registry')):
                raise ValueError(f'Interaction record does not match {key}.')
            records[key] = saved
    output = Path(output_dir).resolve()/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    output.mkdir(parents=True, exist_ok=False)
    write_json(output/'status.json', {'status': 'preparing'})
    questions = json.loads((root/'questions.json').read_text())
    try:
        shutil.copytree(root, output/'bounce_prediction', ignore=shutil.ignore_patterns('*.blend', '*.blend1', '*.blend2'))
        parameters = {'evaluation_model': model, 'experiment_model': experiment_model,
                      'primary_record_source': str(record_path) if record_path is not None else None,
                      'primary_record_sha256': hashlib.sha256(record_path.read_bytes()).hexdigest() if record_path is not None else None,
                      'additional_record_sources': {k: str(Path(v).resolve()) for k, v in world_records.items()},
                      'worlds_requiring_interaction': sorted(known-set(records)), 'max_turns': max_turns,
                      'question_count': len(questions), 'batch_source': str(root), 'worlds': batch['worlds'],
                      'history_scope': 'matching_world_only', 'api_timeout': request_timeout_settings(),
                      'api_retry': request_retry_settings()}
        write_json(output/'run_parameters.json', parameters)
        (output/'parameters.md').write_text('# Paired-world bounce evaluation (host-only)\n\n'
            'Each question receives only the interaction history for its own physical world. '
            'Missing world histories are acquired through new experiments, not fabricated or copied from another world.\n\n'
            '```json\n'+json.dumps(parameters, indent=2)+'\n```\n')
        for key, env in envs.items():
            target = output/'world_runs'/key
            target.mkdir(parents=True)
            IdentifyBounceTask(env).save_private_artifacts(target)
            if key in records:
                records[key].save(str(target/'interaction.json'))
        if prepare_only:
            write_json(output/'status.json', {'status': 'prepared', 'model_calls': 0,
                                              'worlds_requiring_interaction': parameters['worlds_requiring_interaction']})
            return output
        combined = EvaluationRecord(task_name='identify_bounce', model=model, with_history=True, questions=questions)
        for key, env in envs.items():
            target = output/'world_runs'/key
            if key not in records:
                write_json(output/'status.json', {'status': 'running', 'stage': 'experiments', 'world': key})
                print(f'NEW_WORLD_INTERACTION {key}', flush=True)
                harness = RecordedHarness(harness_factory(experiment_model), output, f'experiments_{key}')
                records[key] = run_interaction(IdentifyBounceTask(env), 'identify_bounce', harness, max_turns, str(target))
            selected = []
            for q, entry in zip(questions, batch['questions']):
                if entry['experiment_world'] == key:
                    item = deepcopy(q)
                    item['context_image'] = '../../bounce_prediction/'+item['context_image']
                    for choice in item['choices']:
                        choice['image'] = '../../bounce_prediction/'+choice['image']
                    selected.append(item)
            write_json(target/'questions.json', selected)
            write_json(output/'status.json', {'status': 'running', 'stage': 'image_evaluation', 'world': key})
            harness = RecordedHarness(harness_factory(model), output, f'image_evaluation_{key}')
            result = run_evaluation('identify_bounce', harness, str(target/'questions.json'), records[key],
                                    with_history=True, output_dir=str(target))
            combined.answers.extend(dict(answer, experiment_world=key) for answer in result.answers)
            combined.score = sum(a['correct'] for a in combined.answers)/len(questions)
            combined.save(str(output/'evaluation_with_history.json'))
        by_id = {a['question_id']: a for a in combined.answers}
        combined.answers = [by_id[q['id']] for q in questions]
        combined.save(str(output/'evaluation_with_history.json'))
        pairs = {}
        for entry in batch['questions']:
            pairs.setdefault(entry['pair_id'], []).append(by_id[entry['id']]['correct'])
        pair_score = sum(all(values) for values in pairs.values())/len(pairs)
        summary = {'status': 'complete', 'image_score': combined.score, 'paired_world_score': pair_score,
                   'questions_answered': len(combined.answers), 'questions_total': len(questions),
                   'per_world_score': {key: sum(a['correct'] for a in combined.answers if a['experiment_world'] == key)/
                                      sum(a['experiment_world'] == key for a in combined.answers) for key in envs}}
        write_json(output/'summary.json', summary)
        write_json(output/'status.json', summary)
        (output/'summary.md').write_text(f"# Hard bounce evaluation\n\nImage accuracy: {combined.score:.1%}. "
            f"Both-world pair accuracy: {pair_score:.1%}.\n\nWorld-specific interactions and answers are in world_runs/.\n")
        return output
    except Exception as exc:
        write_json(output/'status.json', {'status': 'failed', 'error_type': type(exc).__name__,
                                          'note': 'Per-world interaction and evaluation checkpoints remain in world_runs/.'})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True, help='Image-capable evaluation model; may differ from the experiment model.')
    parser.add_argument('--record', help='Reuse a saved world-1 interaction.json; omit to run fresh experiments for every world.')
    parser.add_argument('--batch-dir', default=str(REPO/'renders/lab_4/bounce_prediction'))
    parser.add_argument('--output-dir', default=str(REPO/'results/bounce_evaluation'))
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--experiment-model', help='Interaction model; defaults to the saved experiment model, or --model for a fresh run.')
    parser.add_argument('--max-turns', type=int, default=32)
    parser.add_argument('--world-record', action='append', default=[], metavar='WORLD=PATH',
                        help='Reuse an additional world interaction, e.g. world_002=.../interaction.json.')
    args = parser.parse_args()
    records = {}
    for value in args.world_record:
        if '=' not in value:
            parser.error('--world-record requires WORLD=PATH.')
        key, path = value.split('=', 1)
        if key in records or not path:
            parser.error('Duplicate world or empty record path.')
        records[key] = path
    output = evaluate_bounce(args.model, args.record, args.batch_dir, args.output_dir, args.prepare_only,
                             experiment_model=args.experiment_model, max_turns=args.max_turns, world_records=records)
    print(f'BOUNCE_EVALUATION_RESULTS {output}')


if __name__ == '__main__':
    main()
