"""Aggregate law-contrastive exam ledgers into the paper tables.

Table 1: accuracy per model x arm with 95% cluster-bootstrap CI (clusters = items).
Table 2: accuracy per model x arm x condition (rule_1 / rule_2 / combined_rule).
Error composition: share of answers that are correct / canonical / sibling-world / other.
Paired contrasts on identical (item, world) questions: own - no_history, own - sibling, law_text - own.
"""
import argparse, json, random
from collections import defaultdict
from pathlib import Path

RESULTS = Path('results/law_contrastive')
ARMS = ['no_history', 'own', 'sibling', 'law_text']


def load():
    rows = []
    for ledger in RESULTS.glob('*/*/ledger.jsonl'):
        latest = {}
        for r in map(json.loads, ledger.read_text().splitlines()):
            if r.get('status') == 'complete':
                latest[(r['item'], r['variant'])] = r
        rows += latest.values()
    return rows


def boot(rows, stat, n=2000, seed=0):
    by = defaultdict(list)
    for r in rows: by[r['item']].append(r)
    keys = list(by); rng = random.Random(seed); vals = []
    for _ in range(n):
        sample = [r for k in (rng.choice(keys) for _ in keys) for r in by[k]]
        vals.append(stat(sample))
    vals.sort(); return vals[int(.025 * n)], vals[int(.975 * n)]


def acc(rows):
    return sum(r['correct'] for r in rows) / len(rows) if rows else float('nan')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='cvpr2027/experiments/law_contrastive_results.json')
    a = ap.parse_args()
    rows = load(); report = dict(table1={}, table2={}, errors={}, paired={})
    models = sorted({r['model'] for r in rows})
    for m in models:
        for arm in ARMS:
            R = [r for r in rows if r['model'] == m and r['arm'] == arm]
            if not R: continue
            lo, hi = boot(R, acc)
            report['table1'][f'{m}|{arm}'] = dict(n=len(R), acc=acc(R), ci95=[lo, hi])
            for rule in ('rule_1', 'rule_2', 'combined_rule'):
                S = [r for r in R if r['rule'] == rule]
                if S: report['table2'][f'{m}|{arm}|{rule}'] = dict(n=len(S), acc=acc(S))
            report['errors'][f'{m}|{arm}'] = dict(
                correct=acc(R), canonical=sum(r['picked_canonical'] for r in R) / len(R),
                sibling=(sum(bool(r.get('picked_sibling')) for r in R) / len(R)) if arm == 'sibling' else None)
        idx = {arm: {(r['item'], r['variant']): r for r in rows if r['model'] == m and r['arm'] == arm} for arm in ARMS}
        for x, y in (('own', 'no_history'), ('own', 'sibling'), ('law_text', 'own')):
            keys = sorted(set(idx[x]) & set(idx[y]))
            if not keys: continue
            P = [dict(item=k[0], correct=idx[x][k]['correct'] - idx[y][k]['correct']) for k in keys]
            d = sum(p['correct'] for p in P) / len(P); lo, hi = boot(P, lambda s: sum(p['correct'] for p in s) / len(s))
            report['paired'][f'{m}|{x}-{y}'] = dict(n=len(P), diff=d, ci95=[lo, hi])
    Path(a.out).write_text(json.dumps(report, indent=1) + '\n')
    for k, v in report['table1'].items(): print(f"{k:40s} n={v['n']:4d} acc={v['acc']:.3f} CI[{v['ci95'][0]:.3f},{v['ci95'][1]:.3f}]")
    for k, v in report['paired'].items(): print(f"{k:40s} n={v['n']:4d} diff={v['diff']:+.3f} CI[{v['ci95'][0]:+.3f},{v['ci95'][1]:+.3f}]")


if __name__ == '__main__':
    main()
