"""Run the drag reference demo or one JSON experiment per input line."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

import yaml

from src.envs.drag_lab import DragLabEnv
from src.envs.drag_lab.demo import run_demo
from src.tasks.identify_drag import IdentifyDragTask


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='configs/drag_lab.yaml')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--demo', action='store_true')
    mode.add_argument('--actions', type=Path, help='JSONL actions; otherwise read stdin.')
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    config = yaml.safe_load(Path(args.config).read_text())
    if config['env']['type'] != 'drag_lab' or config['task']['type'] != 'identify_drag':
        parser.error('Use a drag_lab / identify_drag configuration.')
    env = DragLabEnv(**config['env'].get('params', {}))
    task = IdentifyDragTask(env, **config['task'].get('params', {}))
    directory = args.output_dir or Path('results/drag_lab')/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    if directory.exists() and any(directory.iterdir()):
        parser.error('Output directory must be empty.')
    directory.mkdir(parents=True, exist_ok=True)
    task.save_private_artifacts(directory)
    (directory/'config_resolved.json').write_text(json.dumps(config, indent=2)+'\n')
    initial, events = env.observe(), []
    def checkpoint():
        (directory/'public_transcript.json').write_text(json.dumps({
            'policy': 'offline_reference_policy' if args.demo else 'jsonl_actions',
            'initial_observation': initial, 'events': events}, indent=2)+'\n')
    def submit(action):
        task.apply_action(action)
        result = task.evaluate()
        event = {'action': action, 'result': result}
        events.append(event)
        checkpoint()
        print(json.dumps(event), flush=True)
        return result
    print(json.dumps({'initial_observation': initial}), flush=True)
    checkpoint()
    try:
        if args.demo:
            print('Fitting uses public measurements only; this is a scripted computational reference, not an LLM.', flush=True)
            run_demo(initial, submit)
        else:
            stream = args.actions.open() if args.actions else sys.stdin
            try:
                for line in stream:
                    if not line.strip():
                        continue
                    try:
                        action = json.loads(line)
                    except ValueError:
                        print(json.dumps({'success': False, 'error': 'Expected one JSON object per line.'}), flush=True)
                        continue
                    submit(action)
            finally:
                if args.actions:
                    stream.close()
    finally:
        score = task.get_private_evaluation()
        (directory/'private_evaluation.json').write_text(json.dumps(score, indent=2)+'\n')
        print(f'HOST_ONLY_PREDICTION_SCORE {score["score"]:.1%}', file=sys.stderr)
        print(f'DRAG_LAB_RESULTS {directory}', file=sys.stderr)


if __name__ == '__main__':
    main()
