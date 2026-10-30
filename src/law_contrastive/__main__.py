"""Command-line interface: python -m src.law_contrastive <stage> [options].

Stages (in order):
  prepare   build + export + validate + audit (no API calls, CPU only)
  render    print the manual render command and the current render coverage
  status    items, renders, history coverage and answered questions
  exam      one model under one or more arms
  run       every model x arm from the config
  analyze   result tables and paired contrasts
Individual offline stages: build, export, validate, audit.
"""
from __future__ import annotations

import argparse
import sys

from . import analysis, exam, items
from .config import ARMS, DEFAULT_CONFIG, RULES, load_config

RENDER_COMMAND = 'DEVICE=CUDA ./scripts/render_law_contrastive.sh > logs/render_law_contrastive.log 2>&1 &'


def _parser():
    p = argparse.ArgumentParser(prog='python -m src.law_contrastive', description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--config', default=str(DEFAULT_CONFIG), help='YAML config (default: %(default)s)')
    p.add_argument('--groups', nargs='+', help='subset of regimes, e.g. g1 g2')
    p.add_argument('--rules', nargs='+', choices=RULES, help='subset of conditions')
    sub = p.add_subparsers(dest='stage', required=True)
    for name in ('prepare', 'build', 'export', 'validate', 'audit', 'render'):
        sub.add_parser(name)
    s = sub.add_parser('status'); s.add_argument('--models', nargs='+')
    for name in ('exam', 'run'):
        s = sub.add_parser(name)
        if name == 'exam':
            s.add_argument('--model', required=True)
        else:
            s.add_argument('--models', nargs='+', help='override exam.models')
        s.add_argument('--arms', nargs='+', choices=ARMS, help='override exam.arms')
        s.add_argument('--history-model', help='use this model\'s interaction records as history')
        s.add_argument('--limit', type=int, default=0, help='max new questions per model x arm (pilot)')
        s.add_argument('--dry-run', action='store_true', help='resolve evidence and prompts; no API calls')
        s.add_argument('--temperature', type=float); s.add_argument('--max-completion-tokens', type=int)
    s = sub.add_parser('analyze'); s.add_argument('--models', nargs='+')
    return p


def main(argv=None) -> int:
    sys.stdout.reconfigure(line_buffering=True)  # stream progress into redirected logs
    a = _parser().parse_args(argv)
    cfg = load_config(a.config, groups=a.groups, rules=a.rules,
                      **{f'exam.{k}': getattr(a, k, None) for k in ('history_model', 'temperature', 'max_completion_tokens')})
    if a.stage in ('prepare', 'build'):
        items.build(cfg)
    if a.stage in ('prepare', 'export'):
        items.export(cfg)
    if a.stage in ('prepare', 'validate'):
        if not all(items.validate(cfg)['checks'].values()):
            return 1
    if a.stage in ('prepare', 'audit'):
        items.audit_source_exam(cfg)
    if a.stage in ('prepare', 'render'):
        st = analysis.status(cfg, models=[])
        if st and st['rendered_items'] < st['items']:
            print(f'[render] run manually on a GPU node:\n  {RENDER_COMMAND}')
    if a.stage == 'status':
        analysis.status(cfg, models=a.models)
    if a.stage in ('exam', 'run'):
        models = [a.model] if a.stage == 'exam' else a.models
        counts = exam.run_all(cfg, models=models, arms=a.arms, limit=a.limit, dry_run=a.dry_run)
        if any(c['skipped_render'] for c in counts.values()):
            print(f'[exam] some items are not rendered yet; run:\n  {RENDER_COMMAND}')
        return 1 if any(c['failed'] for c in counts.values()) else 0
    if a.stage == 'analyze':
        analysis.analyze(cfg, models=a.models)
    return 0


if __name__ == '__main__':
    sys.exit(main())
