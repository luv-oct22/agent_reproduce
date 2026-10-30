#!/usr/bin/env python3
"""Score one attraction question from rendered candidate images and history."""
import argparse
import json
import os
from pathlib import Path

from src.density_pipeline import RecordedHarness
from src.evaluate import run_evaluation
from src.harness import OpenAIHarness
from src.interact import InteractionRecord
from src.path_display import display_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--interaction-record', required=True)
    parser.add_argument('--render-dir', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--temperature', type=float)
    parser.add_argument('--seed', type=int)
    parser.add_argument('--max-completion-tokens', type=int)
    args = parser.parse_args()

    render_dir = Path(args.render_dir).resolve()
    output = Path(args.output_dir).resolve()
    scene = json.loads((render_dir / 'scene.json').read_text())
    choices = [{'label': label, 'image': os.path.relpath(render_dir / f'choice_{label}.png', output)}
               for label in 'ABCD']
    question = {
        'id': scene['id'],
        'type': 'image_multiple_choice',
        'question': ('Using the experiment history and the rendered context, choose the image '
                     'that shows the probe at the next frame. Do not explain your reasoning. '
                     'Return exactly one character: A, B, C, or D.'),
        'context_caption': 'Context frame',
        'context_image': os.path.relpath(render_dir / 'context.png', output),
        'choices': choices,
        'answer': scene['answer'],
    }
    output.mkdir(parents=True, exist_ok=True)
    for path in [Path(question['context_image']), *(Path(c['image']) for c in choices)]:
        if not (output / path).is_file():
            raise FileNotFoundError(f'Missing rendered image: {output / path}')

    record = InteractionRecord.load(args.interaction_record)
    generation_kwargs = {}
    if args.temperature is not None:
        generation_kwargs['temperature'] = args.temperature
    if args.seed is not None:
        generation_kwargs['seed'] = args.seed
    if args.max_completion_tokens is not None:
        generation_kwargs['max_completion_tokens'] = args.max_completion_tokens
    (output / 'model_parameters.json').write_text(json.dumps({
        'model': args.model,
        'interaction_model': record.model,
        'temperature': args.temperature,
        'seed': args.seed,
        'max_completion_tokens': args.max_completion_tokens,
        'max_turns': None,
        'timeout_seconds': os.environ.get('OPENAI_TIMEOUT', '600'),
        'connect_timeout_seconds': os.environ.get('OPENAI_CONNECT_TIMEOUT', '60'),
        'max_retries': os.environ.get('OPENAI_MAX_RETRIES', '3'),
        'history_used': True,
        'generation_kwargs': generation_kwargs,
    }, indent=2) + '\n')
    questions_path = output / 'questions.json'
    questions_path.write_text(json.dumps([question], indent=2) + '\n')
    harness = RecordedHarness(OpenAIHarness(model=args.model), output, 'attraction_image_evaluation')
    evaluation = run_evaluation('identify_attraction_next_frame', harness,
                                str(questions_path), record, with_history=True,
                                output_dir=str(output), generation_kwargs=generation_kwargs)
    summary = {'status': 'complete', 'image_score': evaluation.score,
               'questions_answered': len(evaluation.answers), 'questions_total': 1,
               'render_dir': os.path.relpath(render_dir, Path.cwd()),
               'interaction_record': os.path.relpath(Path(args.interaction_record).resolve(), Path.cwd())}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(f"ATTRACTION_VISUAL_EVALUATION {evaluation.score:.1%}")
    print(f"Evaluation record saved to {display_path(output / 'evaluation_with_history.json')}")


if __name__ == '__main__':
    main()
