"""E0 validation of law-contrastive items: zero-API baselines and leakage checks.

Reports, over all (item, world) questions:
  oracle              re-simulate under the true world law, pick nearest candidate (well-posedness).
  canonical_physics   simulate under the regime's canonical law, pick nearest candidate.
  appearance          pick the candidate whose probe lies closest to the initial probe position.
  label_prior         always the most frequent answer label (position-bias ceiling).
  world_blind_max     best accuracy any policy can get without knowing which world is tested
                      (same images are asked for 3 worlds with 3 different answers).
Also counts the old 810-question exam for comparison: answer at A, and canonical-physics accuracy.
"""
import json, math, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_law_contrastive_items import world, law, outcome
from src.worlds.attraction import DomainError

ITEMS = Path('cvpr2027/experiments/law_contrastive_items')


def nearest(state, choices):
    p = state.payload['objects']['probe']['position_m']
    return min(choices, key=lambda k: math.dist(p, choices[k]['state']['payload']['objects']['probe']['position_m']))


def main():
    rows = []; worlds = {}
    for f in sorted(ITEMS.glob('g*_*.json')):
        g, rule = f.stem.split('_', 1)
        for item in json.loads(f.read_text()):
            canon = worlds.setdefault((g, None), world(g, None))
            c_state, _ = outcome(canon, item['anchor_m'], item['launch'], item['launch']['duration_s'])
            c_pick = nearest(c_state, item['choices'])
            p0 = item['launch']['position_m']
            app = min(item['choices'], key=lambda k: math.dist(p0, item['choices'][k]['state']['payload']['objects']['probe']['position_m']))
            for variant, ans in item['answers'].items():
                v = int(variant.split('_')[1])
                w = worlds.setdefault((g, rule, v), world(g, law(g, rule, v)))
                o_state, _ = outcome(w, item['anchor_m'], item['launch'], item['launch']['duration_s'])
                rows.append(dict(cond=f'{g}/{rule}', rule=rule, item=item['id'], answer=ans,
                                 oracle=nearest(o_state, item['choices']) == ans, canonical=c_pick == ans,
                                 appearance=app == ans, sep=item['min_separation_px_1920']))
    n = len(rows)
    label = Counter(r['answer'] for r in rows).most_common(1)[0]
    per_item = defaultdict(Counter)
    for r in rows: per_item[r['item']][r['answer']] += 1
    blind = sum(max(c.values()) for c in per_item.values()) / n
    summary = dict(questions=n, items=len(per_item),
                   oracle=sum(r['oracle'] for r in rows) / n, canonical_physics=sum(r['canonical'] for r in rows) / n,
                   appearance=sum(r['appearance'] for r in rows) / n, label_prior=label[1] / n, label_prior_letter=label[0],
                   world_blind_max=blind, answer_positions=dict(sorted(Counter(r['answer'] for r in rows).items())),
                   min_separation_px_1920_median=sorted(r['sep'] for r in rows)[n // 2],
                   by_rule={rule: dict(questions=sum(r['rule'] == rule for r in rows),
                                       appearance=sum(r['appearance'] for r in rows if r['rule'] == rule) / max(1, sum(r['rule'] == rule for r in rows)))
                            for rule in ('rule_1', 'rule_2', 'combined_rule')})
    # Old exam: answer letter and canonical physics accuracy on the 810 existing items.
    old = Counter(); old_canon = old_n = 0
    for f in Path('renders/central_force_dynamics').glob('*/*/variant_*/q*/scene.json'):
        d = json.loads(f.read_text()); old[d['answer']] += 1
        g = f.parts[2][-2:]
        L = d['launch']; anchor = d['initial_state']['payload']['objects']['anchor']['position_m']
        w = worlds.setdefault((g, None), world(g, None))
        try:  # no frame check: the old items have their own camera bounds
            s = w.advance(w.make_state({'anchor': anchor, 'probe': L['position_m']},
                                       {'anchor': [0, 0, 0], 'probe': L['velocity_m_s']}, L['start_time_s']), L['duration_s'])
        except DomainError:
            continue
        old_n += 1; old_canon += nearest(s, d['choices']) == d['answer']
    summary['old_exam'] = dict(questions=sum(old.values()), answer_positions=dict(old), canonical_physics=old_canon / max(1, old_n))
    print(json.dumps(summary, indent=1))
    (ITEMS / 'validation_E0.json').write_text(json.dumps(summary, indent=1) + '\n')


if __name__ == '__main__':
    main()
