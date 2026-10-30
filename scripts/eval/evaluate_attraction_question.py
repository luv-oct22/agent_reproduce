#!/usr/bin/env python3
"""Offline protocol evaluation for one attraction interaction episode.

This stage audits the recorded experiment. Scientific prediction questions are
scored by a later question-set evaluator; an interaction record itself has no
single answer key.
"""
import argparse
import json
import os
from pathlib import Path
from src.path_display import display_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--question-file', required=True)
    parser.add_argument('--interaction-record', required=True)
    parser.add_argument('--world-instance', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()

    question_path = Path(args.question_file)
    host_path = question_path.with_name('instance.json')
    host = json.loads(host_path.read_text()) if host_path.exists() else json.loads(question_path.read_text())
    question = host.get('question', host)
    record = json.loads(Path(args.interaction_record).read_text())

    allowed = {'inspect', 'configure_trial', 'apply_impulse', 'measure_force',
               'track_motion', 'finish', 'measure_baseline_force',
               'inspect_object', 'measure_mass', 'measure_volume',
               'measure_geometry', 'measure_density', 'measure_inertia'}
    calls, tool_results, invalid = [], [], []
    for message in record.get('messages', []):
        for call in message.get('tool_calls', []) or []:
            name = call.get('function_name')
            calls.append(name)
            if name not in allowed:
                invalid.append(name)
        if message.get('role') == 'tool':
            try:
                tool_results.append(json.loads(message.get('content', '{}')))
            except json.JSONDecodeError:
                invalid.append('malformed_tool_result')

    successful = sum(result.get('success') is True for result in tool_results)
    finished = bool(record.get('finished')) and 'finish' in calls
    result = {
        'format': 'attraction_interaction_evaluation',
        'schema_version': 1,
        'question_id': question.get('question_id'),
        'group_id': question.get('group_id'),
        'variant_id': question.get('variant_id'),
        'model': record.get('model'),
        'interaction_record': os.path.relpath(Path(args.interaction_record).resolve(), Path.cwd()),
        'status': 'complete' if finished and not invalid else 'incomplete_or_invalid',
        'finished': finished,
        'tool_call_count': len(calls),
        'successful_tool_results': successful,
        'invalid_events': invalid,
        'skipped_turns': record.get('skipped_turns', []),
        'note': 'Protocol audit only; no scientific prediction answer is scored here.',
    }
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'evaluation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f"ATTRACTION_EVALUATION {result['status']}")
    print(f"Evaluation record saved to {display_path(output / 'evaluation.json')}")


if __name__ == '__main__':
    main()
