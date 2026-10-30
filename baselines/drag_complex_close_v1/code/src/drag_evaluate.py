"""Evaluate drag context-image questions with a matching saved experiment history."""
import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import shutil

from src.density_pipeline import RecordedHarness, write_json
from src.envs.drag_lab import DragLabEnv
from src.harness import OpenAIHarness
from src.harness.openai import request_timeout_settings, request_retry_settings
from src.interact import InteractionRecord
from src.evaluate import run_evaluation
from src.evaluation.visual import build_image_choice_content
from src.simulation.balance_batch import question_complete
from src.simulation.drag_scene import aggregate_question, frame_state
from src.simulation.drag_candidates import validate_candidate_geometry, validate_projected_candidates
from src.worlds.height_drag import load_drag_world


REPO = Path(__file__).resolve().parents[1]


def validate_inputs(record_path, batch_dir):
    record_path, root = Path(record_path).resolve(), Path(batch_dir).resolve()
    record = InteractionRecord.load(str(record_path))
    if record.task_name != 'identify_drag':
        raise ValueError('Use an identify_drag interaction record.')
    env = DragLabEnv.from_private_manifest(json.loads((record_path.parent/'private_manifest.json').read_text()))
    private = env.private_manifest()
    if json.loads((root/'private_manifest.json').read_text()) != private:
        raise ValueError('Image batch physics differs from the interaction world, objects or contacts.')
    batch = json.loads((root/'batch.json').read_text())
    ids = {'world_id': private['world_id'], 'object_registry_id': private['object_registry_id'],
           'contact_registry_id': private['contact_registry']['registry_id']}
    if batch.get('format') != 'drag_prediction_batch' or any(batch.get(k) != v for k, v in ids.items()):
        raise ValueError('Image batch does not match the saved drag world.')
    questions = json.loads((root/'questions.json').read_text())
    if not questions or len(questions) != len(batch['questions']) or len({q['id'] for q in questions}) != len(questions):
        raise ValueError('Invalid question list.')
    ball = env._ball
    for q, entry in zip(questions, batch['questions']):
        folder = root/entry['folder']
        manifest = json.loads((folder/'scene.json').read_text())
        if manifest.get('candidate_policy') != batch.get('candidate_policy'):
            raise ValueError('Scene candidate policy differs from its batch.')
        if (manifest.get('format') != 'drag_prediction_scene' or manifest['id'] != entry['id']
                or any(manifest.get(k) != v for k, v in ids.items())
                or q != aggregate_question(manifest, entry['folder'])):
            raise ValueError('Question does not match its recorded scene.')
        if len(manifest['objects']) != 1:
            raise ValueError('Expected the single calibrated specimen.')
        obj = manifest['objects'][0]
        expected = {'source_specimen_id': ball.specimen_id, 'mass_kg': ball.mass_kg,
                    'radius_m': ball.radius_m, 'color': ball.color, 'color_rgba': list(ball.color_rgba)}
        if any(obj.get(k) != v for k, v in expected.items()):
            raise ValueError('Scene specimen differs from the experimental specimen.')
        if (not math.isclose(obj['position_m'][2]-manifest['surface_z_m']-ball.radius_m,
                             obj['release_height_m'], abs_tol=1e-10)
                or obj['velocity_m_s'][1:] != [0, 0] or obj['position_m'][1] != 0):
            raise ValueError('Scene launch differs from its public description.')
        true_world = private['world']
        correct = []
        for label, frame in manifest['choices'].items():
            world = load_drag_world(frame['world'])
            restitution = env._contacts.restitution[0][1]
            if world.gravity_m_s2 != env._world.gravity_m_s2 or frame['restitution'] != restitution:
                raise ValueError('Only the drag profile may vary across candidates.')
            expected_state = frame_state(world, obj, manifest['elapsed_s'], restitution, manifest['surface_z_m'])
            state = frame['objects'][0]
            if (len(frame['objects']) != 1 or state['source_specimen_id'] != ball.specimen_id
                    or state['impacts'] != expected_state['impacts']
                    or any(not math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10)
                           for key in ('position_m', 'velocity_m_s')
                           for a, b in zip(state[key], expected_state[key]))):
                raise ValueError('Candidate position is inconsistent with the recorded physics.')
            if frame['world'] == true_world:
                correct.append(label)
        if correct != [manifest['answer']] or set(manifest['choices']) != set('ABCD'):
            raise ValueError('Exactly one choice must use the true world.')
        validate_candidate_geometry(manifest)
        if not question_complete(folder):
            raise FileNotFoundError(f'Render missing or stale: {folder}. Run scripts/render/render_drag_prediction.sh first.')
        if 'candidate_policy' in manifest:
            report = json.loads((folder/'build_report.json').read_text())
            validate_projected_candidates(manifest, report['frames'])
        build_image_choice_content(q, root)
    return record, batch


def evaluate_drag(model, record_path, batch_dir=REPO/'renders/lab_5/drag_prediction',
                  output_dir=REPO/'results/drag_evaluation', prepare_only=False, harness_factory=OpenAIHarness):
    record_path, root = Path(record_path).resolve(), Path(batch_dir).resolve()
    record, batch = validate_inputs(record_path, root)
    output = Path(output_dir).resolve()/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    output.mkdir(parents=True, exist_ok=False)
    write_json(output/'status.json', {'status': 'preparing'})
    try:
        shutil.copytree(root, output/'drag_prediction', ignore=shutil.ignore_patterns('*.blend', '*.blend1', '*.blend2'))
        shutil.copy2(record_path, output/'interaction.json')
        shutil.copy2(record_path.parent/'private_manifest.json', output/'private_manifest.json')
        if (record_path.parent/'private_evaluation.json').exists():
            shutil.copy2(record_path.parent/'private_evaluation.json', output/'experiment_private_evaluation.json')
        parameters = {'experiment_model': record.model, 'evaluation_model': model,
                      'record_source': str(record_path), 'record_sha256': hashlib.sha256(record_path.read_bytes()).hexdigest(),
                      'batch_source': str(root), 'question_count': len(batch['questions']),
                      'history_used': True, 'interaction_finished': record.finished,
                      **{k: batch[k] for k in ('world_id', 'object_registry_id', 'contact_registry_id')},
                      'api_timeout': request_timeout_settings(), 'api_retry': request_retry_settings()}
        write_json(output/'run_parameters.json', parameters)
        (output/'parameters.md').write_text('# Drag visual evaluation parameters (host-only)\n\n'
            'The model receives the public experiment history and five images per question. '
            'Private manifests, true drag profiles and answer keys are excluded. '
            'Image accuracy is separate from interaction-stage numerical prediction accuracy.\n\n```json\n'
            +json.dumps(parameters, indent=2)+'\n```\n')
        if prepare_only:
            write_json(output/'status.json', {'status': 'prepared', 'model_calls': 0})
            return output
        write_json(output/'status.json', {'status': 'running'})
        harness = RecordedHarness(harness_factory(model), output, 'drag_image_evaluation')
        evaluation = run_evaluation('identify_drag', harness, str(output/'drag_prediction/questions.json'),
                                    record, with_history=True, output_dir=str(output))
        summary = {'status': 'complete', 'image_score': evaluation.score,
                   'questions_answered': len(evaluation.answers), 'questions_total': len(batch['questions'])}
        write_json(output/'summary.json', summary)
        write_json(output/'status.json', summary)
        (output/'summary.md').write_text(f'# Drag visual evaluation\n\nImage accuracy: {evaluation.score:.1%}. '
            f'Questions answered: {len(evaluation.answers)}.\n\n'
            'See evaluation_with_history.json for scores and model_responses.jsonl for responses.\n')
        return output
    except Exception as exc:
        write_json(output/'status.json', {'status': 'failed', 'error_type': type(exc).__name__})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True, help='Image-capable model; experiment history is shared even if this model differs.')
    parser.add_argument('--record', required=True, help='Saved identify_drag interaction.json.')
    parser.add_argument('--batch-dir', default=str(REPO/'renders/lab_5/drag_prediction'))
    parser.add_argument('--output-dir', default=str(REPO/'results/drag_evaluation'))
    parser.add_argument('--prepare-only', action='store_true', help='Validate and snapshot rendered inputs without model calls.')
    args = parser.parse_args()
    output = evaluate_drag(args.model, args.record, args.batch_dir, args.output_dir, args.prepare_only)
    print(f'DRAG_EVALUATION_RESULTS {output}')


if __name__ == '__main__':
    main()
