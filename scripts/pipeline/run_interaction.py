#!/usr/bin/env python3
"""Run one agent interaction against one loaded world instance."""
import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from src.envs.rule1_attraction_bench import Rule1AttractionBenchEnv
from src.envs.rule2_attraction_bench import Rule2AttractionBenchEnv
from src.envs.combined_attraction_bench import CombinedAttractionBenchEnv
from src.harness import OpenAIHarness
from src.tasks.discover_world import DiscoverWorldTask
from src.interact import run_interaction


def load_host_question(path):
    """Prefer the sibling host-only record when a question folder has one."""
    candidate = path.with_name('instance.json')
    raw = json.loads(candidate.read_text()) if candidate.exists() else json.loads(path.read_text())
    if raw.get('format') == 'question_instance':
        return raw['question'], raw
    return raw, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--world-instance', required=True)
    parser.add_argument('--question-file', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--model', default='gpt-5.6')
    parser.add_argument('--agent-config')
    parser.add_argument('--harness-config')
    parser.add_argument('--temperature', type=float)
    parser.add_argument('--seed', type=int)
    parser.add_argument('--max-completion-tokens', type=int)
    args, _ = parser.parse_known_args()

    question_path = Path(args.question_file)
    question, host_record = load_host_question(question_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    public_context = {key: question[key] for key in
                      ('question_id', 'family', 'group_id', 'rule', 'variant_id') if key in question}
    (output_dir / 'question_context.json').write_text(json.dumps(public_context, indent=2) + '\n')
    env_class = (CombinedAttractionBenchEnv if question.get('rule') == 'combined_rule' else
                 Rule2AttractionBenchEnv if question.get('rule') == 'rule_2' else Rule1AttractionBenchEnv)
    env = env_class(instance_path=args.world_instance, question=question)
    task = DiscoverWorldTask(env)
    task.question_metadata = question
    harness = OpenAIHarness(model=args.model)
    generation_kwargs = {}
    if args.temperature is not None:
        generation_kwargs['temperature'] = args.temperature
    if args.seed is not None:
        generation_kwargs['seed'] = args.seed
    if args.max_completion_tokens is not None:
        generation_kwargs['max_completion_tokens'] = args.max_completion_tokens
    # /v1/responses does not accept temperature or seed; record what was actually sent.
    sent_kwargs = (OpenAIHarness.responses_call_kwargs(generation_kwargs)
                   if harness.api_mode == 'responses' else dict(generation_kwargs))
    (output_dir / 'model_parameters.json').write_text(json.dumps({
        'model': args.model,
        'api_mode': harness.api_mode,
        'temperature': args.temperature,
        'seed': args.seed,
        'max_completion_tokens': args.max_completion_tokens,
        'max_turns': env.protocol['budget']['max_turns'] or 8,
        'timeout_seconds': os.environ.get('OPENAI_TIMEOUT', '600'),
        'connect_timeout_seconds': os.environ.get('OPENAI_CONNECT_TIMEOUT', '60'),
        'max_retries': os.environ.get('OPENAI_MAX_RETRIES', '3'),
        'generation_kwargs': generation_kwargs,
        'generation_kwargs_sent': sent_kwargs,
    }, indent=2) + '\n')
    run_interaction(task, 'discover_world', harness,
                    max_turns=env.protocol['budget']['max_turns'] or 8,
                    output_dir=args.output_dir,
                    generation_kwargs=generation_kwargs)


if __name__ == '__main__':
    main()
