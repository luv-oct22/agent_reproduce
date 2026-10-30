"""Build law-contrastive exam items for central-force worlds (simulation only, no pixels).

An item is one scene (launch + elapsed time) with four candidate outcomes, each produced by a
different law of the same family/regime/condition: the canonical law and three sibling
realizations. The same four images are an exam item for each of those three worlds, with a
different correct label per world, so any policy that ignores the world scores at most 1/3 and
canonical physics scores 0 by construction.

Scenes come first from the existing renders (their context.png is reused unchanged); new
in-plane launches are sampled only to fill coverage. Reuses AttractionWorld and the existing
camera projection. Output is host-only JSON; rendering is a separate step.
"""
import argparse, itertools, json, math, random
from collections import Counter
from pathlib import Path
from src.worlds.definition import WorldInstance
from src.worlds.attraction import AttractionWorld, DomainError
from src.simulation.attraction_visual import projected, ANCHOR

ROOT = Path('world_instances/central_force_dynamics')
RENDERS = Path('renders/central_force_dynamics')
RULES = ['rule_1', 'rule_2', 'combined_rule']
DTS = (.4, .6, .8, 1.0, 1.2, 1.5)
# Same bounds as attraction_visual.geometry: probe radius plus the caption bands at top and bottom.
PROBE_R_PX = .03 * 1920 / 5
X_MARGIN_PX, Z_MARGIN_PX = PROBE_R_PX + 8, PROBE_R_PX + .28 * 1920 / 5 + 8


def in_frame(px):
    return X_MARGIN_PX <= px[0] <= 1920 - X_MARGIN_PX and Z_MARGIN_PX <= px[1] <= 1280 - Z_MARGIN_PX


def world(g, eq):
    payload = json.loads((ROOT / f'central_force_dynamics_{g}/baseline/instance.json').read_text())['payload']
    return AttractionWorld(WorldInstance(payload), equation=eq)


def law(g, r, v):
    q = json.loads((ROOT / f'central_force_dynamics_{g}/{r}/variant_{v}/q01/instance.json').read_text())['question']
    return q.get('hidden_equation_parameters') or q.get('hidden_force_function')


def outcome(w, anchor, launch, dt):
    s = w.make_state({'anchor': anchor, 'probe': launch['position_m']},
                     {'anchor': [0, 0, 0], 'probe': launch['velocity_m_s']}, launch['start_time_s'])
    state = w.advance(s, dt)
    px = projected(state.payload['objects']['probe']['position_m'])[:2]
    if not in_frame(px):
        raise DomainError('outcome leaves the frame')
    return state, px


def existing_scenes(g, r):
    for v in range(1, 7):
        for q in range(1, 16):
            d = json.loads((RENDERS / f'central_force_dynamics_{g}/{r}/variant_{v}/q{q:02d}/scene.json').read_text())
            L = d['launch']
            yield dict(anchor=d['initial_state']['payload']['objects']['anchor']['position_m'],
                       launch={k: L[k] for k in ('position_m', 'velocity_m_s', 'start_time_s')},
                       source=dict(kind='existing_render', scene=f'{r}/variant_{v}/q{q:02d}',
                                   context_image=str(RENDERS / f'central_force_dynamics_{g}/{r}/variant_{v}/q{q:02d}/context.png')))


def sampled_scenes(rng):
    while True:
        rad, ang = rng.uniform(.6, 1.6), rng.uniform(0, 2 * math.pi)
        sp, turn = rng.uniform(.1, .6), rng.choice([1, -1]) * rng.uniform(.6, 1.2)
        yield dict(anchor=list(ANCHOR),
                   launch=dict(position_m=[round(ANCHOR[0] + rad * math.cos(ang), 3), 0., round(ANCHOR[2] + rad * math.sin(ang), 3)],
                               velocity_m_s=[round(sp * math.cos(ang + math.pi / 2 * turn), 3), 0.,
                                             round(sp * math.sin(ang + math.pi / 2 * turn), 3)],
                               start_time_s=round(rng.uniform(0, 5), 1)),
                   source=dict(kind='sampled', context_image=None))


def try_scene(scene, canon, worlds, cover, need, min_px, rng):
    """Return (dt, states, trio) for the shortest dt giving a separable quadruple with an under-covered world."""
    if not in_frame(projected(scene['launch']['position_m'])[:2]):
        return None
    for dt in DTS:
        try:
            states = {'canonical': outcome(canon, scene['anchor'], scene['launch'], dt)}
            states.update({v: outcome(w, scene['anchor'], scene['launch'], dt) for v, w in worlds.items()})
        except DomainError:
            return None
        order = sorted(worlds, key=lambda v: (cover[v], rng.random()))
        for trio in itertools.combinations(order, 3):
            if all(cover[v] >= need for v in trio):
                continue
            pts = [states['canonical'][1]] + [states[v][1] for v in trio]
            if min(math.dist(a, b) for a, b in itertools.combinations(pts, 2)) >= min_px:
                return dt, states, trio
    return None


def build(g, r, need, min_px, seed, max_sampled):
    rng = random.Random(f'{seed}-{g}-{r}')
    canon = world(g, None)
    worlds = {v: world(g, law(g, r, v)) for v in range(1, 7)}
    cover, items, used = Counter(), [], Counter()
    sources = itertools.chain(existing_scenes(g, r), itertools.islice(sampled_scenes(rng), max_sampled))
    for scene in sources:
        if all(cover[v] >= need for v in worlds):
            break
        used[scene['source']['kind']] += 1
        hit = try_scene(scene, canon, worlds, cover, need, min_px, rng)
        if not hit:
            continue
        dt, states, trio = hit
        members = ['canonical', *trio]
        labels = list('ABCD'); rng.shuffle(labels)  # candidate positions permuted per item
        choices = {lab: dict(law=m if m == 'canonical' else f'variant_{m}', state=states[m][0].to_dict(),
                             pixel_1920=[round(x, 1) for x in states[m][1]]) for lab, m in zip(labels, members)}
        answers = {c['law']: lab for lab, c in choices.items() if c['law'] != 'canonical'}
        sep = min(math.dist(a['pixel_1920'], b['pixel_1920']) for a, b in itertools.combinations(choices.values(), 2))
        items.append(dict(format='law_contrastive_item', schema_version=1, visibility='host_only',
                          id=f'{g}_{r}_item{len(items) + 1:03d}', group=f'central_force_dynamics_{g}', rule=r,
                          anchor_m=scene['anchor'], launch=dict(scene['launch'], duration_s=dt), source=scene['source'],
                          choices=choices, answers=answers,
                          canonical_label=next(l for l, c in choices.items() if c['law'] == 'canonical'),
                          min_separation_px_1920=round(sep, 1)))
        for v in trio:
            cover[v] += 1
    return items, cover, used


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', default='cvpr2027/experiments/law_contrastive_items')
    p.add_argument('--per-world', type=int, default=8, help='exam items per world (realization)')
    p.add_argument('--min-px', type=float, default=20., help='min pairwise candidate separation at 1920 px width')
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--max-sampled', type=int, default=600, help='new launches to try after existing scenes')
    a = p.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    report = {}
    for g in ['g1', 'g2', 'g3']:
        for r in RULES:
            items, cover, used = build(g, r, a.per_world, a.min_px, a.seed, a.max_sampled)
            (out / f'{g}_{r}.json').write_text(json.dumps(items, indent=1) + '\n')
            report[f'{g}/{r}'] = dict(
                items=len(items), scenes_tried=dict(used),
                items_reusing_existing_context=sum(it['source']['kind'] == 'existing_render' for it in items),
                coverage={f'variant_{v}': cover[v] for v in range(1, 7)},
                answer_positions=dict(sorted(Counter(l for it in items for l in it['answers'].values()).items())),
                canonical_positions=dict(sorted(Counter(it['canonical_label'] for it in items).items())),
                dt_s=dict(sorted(Counter(it['launch']['duration_s'] for it in items).items())))
            print(f'{g}/{r}:', json.dumps(report[f'{g}/{r}']), flush=True)
    (out / 'build_report.json').write_text(json.dumps(dict(args=vars(a), conditions=report), indent=2) + '\n')


if __name__ == '__main__':
    main()
