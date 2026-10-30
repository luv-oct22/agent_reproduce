"""Status, checkpoint learning curves, exam tables and paired contrasts."""
from __future__ import annotations

import json
import random
from collections import defaultdict

from . import grid
from .config import EVIDENCE, MODES, Config
from .items import pools
from .run import Ledger


def status(cfg: Config, models=None, modes=None, log=print) -> dict:
    pool = pools(cfg)
    worlds = sorted(w for w in pool if w[0] in cfg.groups and w[1] in cfg.rules)
    framed = sum(grid.frames_complete(cfg, *w) for w in worlds)
    exam_q = sum(len(pool[w]['exam']) for w in worlds)
    out = dict(worlds=len(worlds), worlds_with_frames=framed, exam_questions_per_arm=exam_q, runs={})
    log(f'[status] worlds {len(worlds)}, frames rendered for {framed}/{len(worlds)}, exam questions per arm {exam_q}'
        + ('' if framed == len(worlds) else '  -> run ./scripts/render_visual_interaction.sh'))
    for model in models or cfg.run.models:
        for mode in modes or cfg.run.modes:
            eps = Ledger(cfg.ledger(model, mode, 'episodes'), ('group', 'rule', 'variant')).done()
            exam = Ledger(cfg.ledger(model, mode, 'exam'), ('group', 'rule', 'variant', 'item', 'evidence')).done()
            by_arm = {a: sum(k[-1] == a for k in exam) for a in EVIDENCE}
            out['runs'][f'{model}|{mode}'] = dict(episodes=len(eps), exam=by_arm)
            log(f'[status] {model}|{mode}: episodes {len(eps)}/{len(worlds)}; exam '
                + ', '.join(f'{a} {n}/{exam_q}' for a, n in by_arm.items()))
    return out


def _bootstrap(rows, stat, key='world', n=2000, seed=0):
    by = defaultdict(list)
    for r in rows:
        by[r[key]].append(r)
    keys, rng, vals = list(by), random.Random(seed), []
    for _ in range(n):
        vals.append(stat([r for k in (rng.choice(keys) for _ in keys) for r in by[k]]))
    vals.sort()
    return [vals[int(.025 * n)], vals[int(.975 * n)]]


def _acc(rows):
    return sum(r['correct'] for r in rows) / len(rows) if rows else float('nan')


def analyze(cfg: Config, models=None, modes=None, log=print) -> dict:
    out = dict(curves={}, exam={}, by_rule={}, paired={})
    for model in models or cfg.run.models:
        for mode in modes or cfg.run.modes:
            tag = f'{model}|{mode}'
            # Checkpoint curves: accuracy by checkpoint index, pooled over worlds.
            pts = defaultdict(list)
            for row in Ledger(cfg.ledger(model, mode, 'episodes'), ()).rows():
                if row.get('status') != 'complete':
                    continue
                path = cfg.episode_dir(model, mode, row['group'], row['rule'], row['variant']) / 'episode.json'
                if not path.exists():
                    continue
                for e in json.loads(path.read_text())['events']:
                    if e['kind'] == 'checkpoint':
                        pts[e['index']].append(dict(correct=e['correct'], world=(row['group'], row['rule'], row['variant']),
                                                    rule=row['rule'], after=e['after_experiments']))
            if pts:
                out['curves'][tag] = {k: dict(n=len(v), acc=_acc(v), ci95=_bootstrap(v, _acc),
                                              by_rule={r: _acc([x for x in v if x['rule'] == r]) for r in cfg.rules})
                                      for k, v in sorted(pts.items())}
            # Exam.
            rows = [dict(r, world=(r['group'], r['rule'], r['variant']))
                    for r in Ledger(cfg.ledger(model, mode, 'exam'), ()).rows() if r.get('status') == 'complete']
            idx = {}
            for arm in EVIDENCE:
                R = [r for r in rows if r['evidence'] == arm]
                if not R:
                    continue
                idx[arm] = {(r['group'], r['rule'], r['variant'], r['item']): r for r in R}
                out['exam'][f'{tag}|{arm}'] = dict(
                    n=len(R), acc=_acc(R), ci95=_bootstrap(R, _acc),
                    canonical=sum(r['picked_canonical'] for r in R) / len(R),
                    sibling=(sum(bool(r.get('picked_sibling')) for r in R) / max(1, sum(r.get('sibling_answer') is not None for r in R))
                             if arm in ('sibling', 'sibling_told') else None))
                for rule in cfg.rules:
                    S = [r for r in R if r['rule'] == rule]
                    if S:
                        out['by_rule'][f'{tag}|{arm}|{rule}'] = dict(n=len(S), acc=_acc(S))
            for x, y in (('own', 'none'), ('own', 'sibling'), ('own', 'observations'),
                         ('own_record', 'none'), ('own_record', 'observations'), ('own_record', 'own'),
                         ('sibling_told', 'none'), ('sibling_told', 'sibling'),
                         ('law_text', 'none'), ('law_text', 'own'), ('law_text', 'own_record')):
                keys = sorted(set(idx.get(x, {})) & set(idx.get(y, {})))
                if keys:
                    P = [dict(world=k[:3], correct=idx[x][k]['correct'] - idx[y][k]['correct']) for k in keys]
                    out['paired'][f'{tag}|{x}-{y}'] = dict(n=len(P), diff=_acc(P), ci95=_bootstrap(P, _acc))
    path = cfg.results_dir / 'analysis.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=str) + '\n')
    for tag, curve in out['curves'].items():
        log(f'[analyze] {tag} checkpoints: ' + '  '.join(f"#{k} {v['acc']:.2f} (n={v['n']})" for k, v in curve.items()))
    for k, v in out['exam'].items():
        log(f"[analyze] {k:45s} n={v['n']:4d} acc={v['acc']:.3f} CI [{v['ci95'][0]:.3f}, {v['ci95'][1]:.3f}]"
            f" canonical={v['canonical']:.2f}" + (f" sibling={v['sibling']:.2f}" if v['sibling'] is not None else ''))
    for k, v in out['paired'].items():
        log(f"[analyze] {k:45s} n={v['n']:4d} diff={v['diff']:+.3f} CI [{v['ci95'][0]:+.3f}, {v['ci95'][1]:+.3f}]")
    log(f'[analyze] wrote {path}')
    return out
