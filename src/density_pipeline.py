"""Run material experiments followed by density image evaluation in one results folder."""
import argparse
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil

from src.harness import OpenAIHarness
from src.harness.openai import request_timeout_settings, request_retry_settings
from src.harness.base import ModelHarness
from src.interact import run_interaction
from src.evaluate import run_evaluation
from src.objects.registry import ObjectRegistry
from src.simulation.config import load_config, build_env_from_config, build_task_from_config
from src.simulation.balance_batch import render_experiment, question_complete
from src.evaluation.visual import build_image_choice_content


REPO = Path(__file__).resolve().parents[1]


def write_json(path, data):
    path = Path(path)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n')
    temporary.replace(path)


class RecordedHarness(ModelHarness):
    """Persist model responses immediately, without credentials or duplicated image bytes."""
    def __init__(self, delegate, directory, stage):
        self.delegate, self.directory, self.stage = delegate, Path(directory), stage
        self.call_index = 0

    @property
    def model_name(self):
        return self.delegate.model_name

    def supports_tools(self):
        return self.delegate.supports_tools()

    def generate(self, messages, tools=None, **kwargs):
        self.call_index += 1
        entry = {'stage': self.stage, 'call': self.call_index, 'model': self.model_name,
                 'time_utc': datetime.now(timezone.utc).isoformat()}
        request = [asdict(message) for message in messages]
        for message in request:
            if isinstance(message['content'], list):
                for part in message['content']:
                    if part.get('type') == 'image_url':
                        uri = part['image_url']['url']
                        part['image_url']['url'] = 'saved-image-data-uri:sha256:'+hashlib.sha256(uri.encode()).hexdigest()
        with (self.directory/'model_requests.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(entry, messages=request,
                                         tools=[asdict(tool) for tool in tools or []]), ensure_ascii=False)+'\n')
        try:
            response = self.delegate.generate(messages, tools=tools, **kwargs)
        except Exception as exc:
            with (self.directory/'model_responses.jsonl').open('a') as stream:
                stream.write(json.dumps(dict(entry, error_type=type(exc).__name__))+'\n')
            raise
        with (self.directory/'model_responses.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(entry, response=asdict(response)), ensure_ascii=False)+'\n')
        return response


def run_pipeline(model, eval_model=None, config_path=REPO/'configs/material_lab.yaml',
                 batch_dir=REPO/'renders/lab_2/density_balance', output_dir=REPO/'results/density_pipeline',
                 max_turns=64, render_missing=False, device='CUDA', samples=96,
                 resolution=(1536, 1024), prepare_only=False, harness_factory=OpenAIHarness):
    if max_turns < 1 or samples < 1 or min(resolution) < 64:
        raise ValueError('Invalid turn limit or render quality settings.')
    batch_dir = Path(batch_dir).resolve()
    config = deepcopy(load_config(config_path))
    if config['env']['type'] != 'material_lab' or config['task']['type'] != 'identify_material':
        raise ValueError('Density pipeline requires material_lab and identify_material.')
    registry = ObjectRegistry.load(batch_dir/'object_registry.json')
    batch = json.loads((batch_dir/'batch.json').read_text())
    questions = json.loads((batch_dir/'questions.json').read_text())
    # Evaluation-only materials never enter the experimental environment.
    evaluation_registry = None
    if batch.get('evaluation_registry_id'):
        evaluation_registry = ObjectRegistry.load(batch_dir/'evaluation_registry.json')
        if evaluation_registry.registry_id != batch['evaluation_registry_id']:
            raise ValueError('Evaluation-only registry identity mismatch.')
        catalog = {obj.specimen_id: obj for obj in evaluation_registry.specimens}
        if any(catalog.get(obj.specimen_id) != obj for obj in registry.specimens):
            raise ValueError('Evaluation registry changed an experimental material.')
    if (batch.get('format') not in ('density_balance_batch', 'liquid_equilibrium_batch') or not questions
            or batch['object_registry_id'] != registry.registry_id
            or len(questions) != len(batch['questions'])
            or any(q.get('object_registry_id') != registry.registry_id for q in questions)):
        raise ValueError('Image questions and batch must use the same object registry.')
    for item in batch['questions']:
        folder = batch_dir/item['folder']
        scene = json.loads((folder/'scene.json').read_text())
        if scene['object_registry_id'] != registry.registry_id:
            raise ValueError(f'Question registry mismatch: {folder}')
        if scene.get('schema_version', 1) >= 2:
            if evaluation_registry is None or scene.get('evaluation_registry_id') != evaluation_registry.registry_id:
                raise ValueError(f'Question evaluation registry mismatch: {folder}')
    pending = [item['folder'] for item in batch['questions'] if not question_complete(batch_dir/item['folder'])]
    if pending:
        if not render_missing:
            raise FileNotFoundError('Some question renders are incomplete. Render the batch first or pass --render-missing.')
        render_experiment(batch_dir, device, samples, resolution)
    # Catch missing/corrupt image inputs before paying for the experiment stage.
    for question in questions:
        build_image_choice_content(question, batch_dir)

    run_dir = Path(output_dir).resolve()/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    run_dir.mkdir(parents=True, exist_ok=False)
    print(f'PIPELINE_RESULTS {run_dir}', flush=True)
    write_json(run_dir/'status.json', {'status': 'preparing'})
    task = None
    try:
        snapshot_name = 'liquid_equilibrium' if batch['format'] == 'liquid_equilibrium_batch' else 'density_balance'
        # Snapshot questions, pixels and records; large editable Blender files stay in renders/.
        shutil.copytree(batch_dir, run_dir/snapshot_name, ignore=shutil.ignore_patterns('*.blend', '*.blend1', '*.blend2'))
        registry.save(run_dir/'object_registry.json')
        registry.write_markdown(run_dir/'object_registry.md')
        config['env'].setdefault('params', {})['registry_path'] = str(run_dir/'object_registry.json')
        write_json(run_dir/'config_resolved.json', config)
        env = build_env_from_config(config)
        task = build_task_from_config(config, env=env)
        task.save_private_artifacts(run_dir)
        parameters = {'experiment_model': model, 'evaluation_model': eval_model or model,
                      'max_turns': max_turns, 'history_used_for_image_evaluation': True,
                      'config_source': str(Path(config_path).resolve()), 'batch_source': str(batch_dir),
                      'object_registry_id': registry.registry_id, 'question_count': len(questions),
                      'image_task': batch['format'], 'image_snapshot_directory': snapshot_name,
                      'evaluation_registry_id': batch.get('evaluation_registry_id'),
                      'grading_basis': batch.get('grading', 'physical_outcome'),
                      'equal_volume_ml': batch['volume_ml'], 'include_reversed': batch['include_reversed'],
                      'render_missing': render_missing, 'render_device': device, 'render_samples': samples,
                      'render_resolution': list(resolution), 'rendered_pending_questions': pending,
                      'api_base_url_configured': bool(os.environ.get('OPENAI_BASE_URL')),
                      'api_timeout': request_timeout_settings(),
                      'api_retry': request_retry_settings(),
                      'resolved_config': config,
                      'note': 'Registry is authoritative for object identities. Existing image render settings are in each question folder.'}
        write_json(run_dir/'run_parameters.json', parameters)
        (run_dir/'parameters.md').write_text('# Density pipeline parameters (host-only)\n\n'
            'Material experiments → image-choice evaluation using the experiment history.\n\n'
            'Object properties are loaded from the image batch registry; seed-based generation is bypassed. '
            f'API credentials are not saved. The {snapshot_name} folder contains images and per-question parameters.\n\n'
            '```json\n'+json.dumps(parameters, indent=2)+'\n```\n')
        if prepare_only:
            write_json(run_dir/'status.json', {'status': 'prepared', 'model_calls': 0})
            print('Prepared and validated; no model requests were sent.')
            return run_dir
        write_json(run_dir/'status.json', {'status': 'running', 'stage': 'experiments'})
        experiment = RecordedHarness(harness_factory(model), run_dir, 'experiments')
        interaction = run_interaction(task, 'identify_material', experiment, max_turns, str(run_dir))
        write_json(run_dir/'status.json', {'status': 'running', 'stage': 'image_evaluation'})
        evaluator = RecordedHarness(harness_factory(eval_model or model), run_dir, 'image_evaluation')
        evaluation = run_evaluation('identify_material', evaluator,
                                    str(run_dir/snapshot_name/'questions.json'), interaction,
                                    with_history=True, output_dir=str(run_dir))
        private = task.get_private_evaluation()
        summary = {'status': 'complete', 'experiment_score': private['score'],
                   'experiments_used': private['experiments_used'], 'interaction_finished': interaction.finished,
                   'image_score': evaluation.score, 'image_questions_answered': len(evaluation.answers),
                   'image_questions_total': len(questions)}
        write_json(run_dir/'summary.json', summary)
        write_json(run_dir/'status.json', summary)
        (run_dir/'summary.md').write_text('# Density pipeline results\n\n'
            f"Experiment score: {private['score']:.1%}\n\nImage prediction score: {evaluation.score:.1%}\n\n"
            f"Experiments used: {private['experiments_used']}; questions answered: {len(evaluation.answers)}.\n\n"
            f"Agent called finish: {interaction.finished}.\n\n"
            'See interaction.json for experiments, evaluation_with_history.json for image answers, '
            'and model_responses.jsonl for model text, tool calls and usage from both stages.\n')
        print(f'PIPELINE_COMPLETE {run_dir}', flush=True)
        return run_dir
    except Exception as exc:
        if task is not None:
            write_json(run_dir/'private_evaluation.json', task.get_private_evaluation())
        write_json(run_dir/'status.json', {'status': 'failed', 'error_type': type(exc).__name__,
                                          'note': 'Completed model exchanges and available scores remain saved.'})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True, help='Experiment model; also used for image evaluation unless overridden.')
    parser.add_argument('--eval-model', help='Optional separate image-capable model.')
    parser.add_argument('--config', default=str(REPO/'configs/material_lab.yaml'))
    parser.add_argument('--batch-dir', default=str(REPO/'renders/lab_2/density_balance'))
    parser.add_argument('--output-dir', default=str(REPO/'results/density_pipeline'))
    parser.add_argument('--max-turns', type=int, default=64)
    parser.add_argument('--render-missing', action='store_true')
    parser.add_argument('--device', choices=['CUDA', 'OPTIX', 'CPU'], default='CUDA')
    parser.add_argument('--samples', type=int, default=96)
    parser.add_argument('--resolution', nargs=2, type=int, default=[1536, 1024])
    parser.add_argument('--prepare-only', action='store_true', help='Validate and save the run inputs without calling any model.')
    args = parser.parse_args()
    run_pipeline(args.model, args.eval_model, args.config, args.batch_dir, args.output_dir,
                 args.max_turns, args.render_missing, args.device, args.samples, args.resolution, args.prepare_only)


if __name__ == '__main__':
    main()
