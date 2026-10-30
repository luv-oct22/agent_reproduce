"""Command-line interface: python -m src.visual_interaction <stage> [options]. See __init__.py."""
from __future__ import annotations

import argparse
import sys

from . import analysis, grid, run
from .config import DEFAULT_CONFIG, EVIDENCE, MODES, load_config

RENDER_COMMAND = 'DEVICE=CUDA ./scripts/render_visual_interaction.sh > logs/render_visual_interaction.log 2>&1 &'


def _parser():
    p = argparse.ArgumentParser(prog='python -m src.visual_interaction', description=__doc__)
    p.add_argument('--config', default=str(DEFAULT_CONFIG))
    p.add_argument('--groups', nargs='+'); p.add_argument('--rules', nargs='+')
    sub = p.add_subparsers(dest='stage', required=True)
    sub.add_parser('prepare')
    for name in ('status', 'analyze'):
        s = sub.add_parser(name); s.add_argument('--models', nargs='+'); s.add_argument('--modes', nargs='+', choices=sorted(MODES))
    for name in ('episodes', 'exam'):
        s = sub.add_parser(name)
        s.add_argument('--model', required=True)
        s.add_argument('--mode', default='frames_predict', choices=sorted(MODES))
        s.add_argument('--limit', type=int, default=0, help='max new episodes / exam questions (pilot)')
        if name == 'exam':
            s.add_argument('--evidence', nargs='+', choices=EVIDENCE)
    return p


def main(argv=None) -> int:
    sys.stdout.reconfigure(line_buffering=True)
    a = _parser().parse_args(argv)
    cfg = load_config(a.config, groups=a.groups, rules=a.rules)
    if a.stage == 'prepare':
        grid.build(cfg)
        st = analysis.status(cfg, models=[])
        if st['worlds_with_frames'] < st['worlds']:
            print(f'[prepare] render the outcome frames on a GPU node:\n  {RENDER_COMMAND}')
    elif a.stage == 'status':
        analysis.status(cfg, models=a.models, modes=a.modes)
    elif a.stage == 'episodes':
        c = run.run_episodes(cfg, a.model, a.mode, limit=a.limit)
        return 1 if c['failed'] else 0
    elif a.stage == 'exam':
        c = run.run_exam(cfg, a.model, a.mode, evidence=a.evidence, limit=a.limit)
        return 1 if c['failed'] else 0
    elif a.stage == 'analyze':
        analysis.analyze(cfg, models=a.models, modes=a.modes)
    return 0


if __name__ == '__main__':
    sys.exit(main())
