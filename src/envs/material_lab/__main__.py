"""Run public JSON-line experiments or an offline reference demonstration."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

import yaml

from src.envs.material_lab import MaterialLabEnv
from src.envs.material_lab.demo import run_demo
from src.tasks.identify_material import IdentifyMaterialTask


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='configs/material_lab.yaml')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--demo', action='store_true', help='Run the public-interface reference policy; no model API needed.')
    mode.add_argument('--actions', type=Path, help='JSONL action file; otherwise read actions from stdin.')
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    config = yaml.safe_load(Path(args.config).read_text())
    if config['env']['type'] != 'material_lab' or config['task']['type'] != 'identify_material':
        parser.error('This CLI requires a material_lab / identify_material configuration.')
    env = MaterialLabEnv(**config['env'].get('params', {}))
    task = IdentifyMaterialTask(env=env, **config['task'].get('params', {}))
    directory = args.output_dir or Path('results/material_lab')/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    if directory.exists() and any(directory.iterdir()):
        parser.error('Output directory is not empty; choose a new directory.')
    directory.mkdir(parents=True, exist_ok=True)
    task.save_private_artifacts(directory)
    initial, events = env.observe(), []
    print(json.dumps({'initial_observation': initial}), flush=True)

    def submit(action):
        task.apply_action(action)
        result = task.evaluate()
        event = {'action': action, 'result': result}
        events.append(event)
        print(json.dumps(event), flush=True)
        return result

    try:
        if args.demo:
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
                        print(json.dumps({'success': False, 'error': 'Expected one JSON action per line.'}), flush=True)
                        continue
                    submit(action)
            finally:
                if args.actions:
                    stream.close()
    finally:
        (directory/'public_transcript.json').write_text(json.dumps({'initial_observation': initial, 'events': events}, indent=2)+'\n')
        (directory/'private_evaluation.json').write_text(json.dumps(task.get_private_evaluation(), indent=2)+'\n')
        env.export_private_manifest(directory/'private_manifest.json')
        print(f'Records saved to {directory}; private files are for the host only.', file=sys.stderr)


if __name__ == '__main__':
    main()
