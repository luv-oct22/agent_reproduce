"""Coverage status and result tables."""
from __future__ import annotations

import json
import random
from collections import defaultdict

from .config import ARMS, Config
from .exam import ledger_for
from .items import load_items, questions, render_complete
from .worlds import Worlds, safe_model


def status(cfg: Config, models=None, log=print) -> dict:
    """Items, renders, history coverage and answered questions per model and arm."""
    try:
        items = list(load_items(cfg))
    except FileNotFoundError as exc:
        log(f'[status] {exc}'); return {}
    rendered = sum(render_complete(cfg, i) for i in items)
    total_q = sum(len(i['answers']) for i in items)
    out = dict(items=len(items), questions=total_q, rendered_items=rendered, models={})
    log(f'[status] items {len(items)}, questions {total_q}, rendered {rendered}/{len(items)}'
        + ('' if rendered == len(items) else '  -> run ./scripts/render_law_contrastive.sh'))
    worlds = Worlds(cfg)
    for model in (cfg.exam.models if models is None else models):
        hist_model = cfg.exam.history_model or model
        worlds_needed = {(i['group'], i['rule'], v) for i in items for v in i['answers']}
        with_hist = sum(bool(worlds.histories(hist_model, *w)) for w in worlds_needed)
        own_q = sum(bool(worlds.histories(hist_model, i['group'], i['rule'], v)) for i, v in questions(cfg))
        arms = {arm: len(ledger_for(cfg, model, arm).completed()) for arm in ARMS}
        out['models'][model] = dict(worlds_with_history=f'{with_hist}/{len(worlds_needed)}',
                                    own_arm_questions=own_q, answered=arms)
        log(f'[status] {model}: history in {with_hist}/{len(worlds_needed)} worlds ({own_q} own-arm questions); '
            f'answered ' + ', '.join(f'{a} {n}/{total_q}' for a, n in arms.items()))
    return out


def _bootstrap(rows, stat, n=2000, seed=0):
    by = defaultdict(list)
    for r in rows:
        by[r['item']].append(r)
    keys, rng, vals = list(by), random.Random(seed), []
    for _ in range(n):
        vals.append(stat([r for k in (rng.choice(keys) for _ in keys) for r in by[k]]))
    vals.sort()
    return [vals[int(.025 * n)], vals[int(.975 * n)]]


def _acc(rows):
    return sum(r['correct'] for r in rows) / len(rows)


def analyze(cfg: Config, models=None, log=print) -> dict:
    """Table 1 (model x arm, cluster bootstrap CI), Table 2 (by condition), errors, paired contrasts."""
    rows = []
    for d in sorted(cfg.results_dir.glob('*/*/ledger.jsonl')):
        rows += [r for r in ledger_for(cfg, d.parent.parent.name, d.parent.name).rows() if r.get('status') == 'complete']
    if models:
        rows = [r for r in rows if r['model'] in models or safe_model(r['model']) in models]
    out = dict(table1={}, table2={}, errors={}, paired={})
    for model in sorted({r['model'] for r in rows}):
        idx = {}
        for arm in ARMS:
            R = [r for r in rows if r['model'] == model and r['arm'] == arm]
            if not R:
                continue
            idx[arm] = {(r['item'], r['variant']): r for r in R}
            out['table1'][f'{model}|{arm}'] = dict(n=len(R), acc=_acc(R), ci95=_bootstrap(R, _acc))
            for rule in cfg.rules:
                S = [r for r in R if r['rule'] == rule]
                if S:
                    out['table2'][f'{model}|{arm}|{rule}'] = dict(n=len(S), acc=_acc(S))
            out['errors'][f'{model}|{arm}'] = dict(
                correct=_acc(R), canonical=sum(r['picked_canonical'] for r in R) / len(R),
                sibling=sum(bool(r.get('picked_sibling')) for r in R) / len(R) if arm == 'sibling' else None)
        for x, y in (('own', 'no_history'), ('own', 'sibling'), ('law_text', 'own')):
            keys = sorted(set(idx.get(x, {})) & set(idx.get(y, {})))
            if keys:
                P = [dict(item=k[0], correct=idx[x][k]['correct'] - idx[y][k]['correct']) for k in keys]
                out['paired'][f'{model}|{x}-{y}'] = dict(n=len(P), diff=_acc(P), ci95=_bootstrap(P, _acc))
    path = cfg.results_dir / 'analysis.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1) + '\n')
    for k, v in out['table1'].items():
        log(f"[analyze] {k:40s} n={v['n']:4d} acc={v['acc']:.3f} CI [{v['ci95'][0]:.3f}, {v['ci95'][1]:.3f}]")
    for k, v in out['paired'].items():
        log(f"[analyze] {k:40s} n={v['n']:4d} diff={v['diff']:+.3f} CI [{v['ci95'][0]:+.3f}, {v['ci95'][1]:+.3f}]")
    if not rows:
        log(f'[analyze] no completed answers under {cfg.results_dir}')
    log(f'[analyze] wrote {path}')
    return out
