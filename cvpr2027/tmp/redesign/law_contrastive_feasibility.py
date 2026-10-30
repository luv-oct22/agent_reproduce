"""Feasibility of law-contrastive candidates: own law, canonical law, two sibling laws, same scene."""
import json, math, sys
from collections import Counter
from src.worlds.definition import WorldInstance
from src.worlds.attraction import AttractionWorld, DomainError
from src.simulation.attraction_visual import projected
ROOT = 'world_instances/central_force_dynamics'
TARGET_PX = float(sys.argv[1]) if len(sys.argv) > 1 else 24.0  # min pairwise separation at 1920 px
DTS = [round(0.2 * k, 1) for k in range(1, 16)]  # 0.2 .. 3.0 s

def world(g, eq):
    base = json.load(open(f'{ROOT}/central_force_dynamics_{g}/baseline/instance.json'))['payload']
    return AttractionWorld(WorldInstance(base), equation=eq)

def eq(g, r, v):
    q = json.load(open(f'{ROOT}/central_force_dynamics_{g}/{r}/variant_{v}/q01/instance.json'))['question']
    return q.get('hidden_equation_parameters') or q.get('hidden_force_function')

stats = Counter(); chosen = []
for g in ['g1', 'g2', 'g3']:
    for r in ['rule_1', 'rule_2', 'combined_rule']:
        eqs = {v: eq(g, r, v) for v in range(1, 7)}
        worlds = {v: world(g, e) for v, e in eqs.items()}
        canon = world(g, None)
        for v in range(1, 7):
            sib = [((v + k - 1) % 6) + 1 for k in (1, 3)]  # two fixed siblings
            for qi in range(1, 16):
                d = json.load(open(f'renders/central_force_dynamics/central_force_dynamics_{g}/{r}/variant_{v}/q{qi:02d}/scene.json'))
                L = d['launch']; anchor = d['initial_state']['payload']['objects']['anchor']['position_m']
                ok = None
                for dt in DTS:
                    pts = []
                    try:
                        for w in [worlds[v], canon, worlds[sib[0]], worlds[sib[1]]]:
                            s = w.make_state({'anchor': anchor, 'probe': L['position_m']},
                                             {'anchor': [0, 0, 0], 'probe': L['velocity_m_s']}, L['start_time_s'])
                            pts.append(projected(w.advance(s, dt).payload['objects']['probe']['position_m'])[:2])
                    except DomainError:
                        break
                    sep = min(math.dist(a, b) for i, a in enumerate(pts) for b in pts[i + 1:])
                    if sep >= TARGET_PX and all(0 <= p[0] <= 1920 and 0 <= p[1] <= 1280 for p in pts):
                        ok = dt; break
                stats[(r, ok is not None)] += 1
                if ok: chosen.append(ok)
for k, n in sorted(stats.items()): print(k, n)
chosen.sort(); print('feasible', len(chosen), '/ 810; chosen dt p10/p50/p90', [chosen[int(len(chosen) * x)] for x in (.1, .5, .9)] if chosen else None)
