"""Exam items: selection by simulation, render manifests, and zero-API validation.

An item is one scene (anchor, probe launch, start time) plus an elapsed time, with four candidate
outcomes from four laws of the same family/regime/condition: the canonical law and three sibling
realizations. The item is a question for each of the three sibling worlds, with a different correct
label per world, so canonical physics always picks a wrong candidate and any world-blind policy is
capped at 1/3.
"""
from __future__ import annotations

import itertools
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

from src.simulation.attraction_visual import ANCHOR, CAMERA, IMAGES, LAW_CONTRASTIVE_POLICY, geometry
from src.worlds.attraction import DomainError

from .config import Config
from .worlds import Worlds, in_frame, projected

CANONICAL = 'canonical'


# Selection ---------------------------------------------------------------------------------
def _sampled_scenes(rng: random.Random, objects: list):
    while True:
        rad, ang = rng.uniform(.6, 1.6), rng.uniform(0, 2 * math.pi)
        sp, turn = rng.uniform(.1, .6), rng.choice([1, -1]) * rng.uniform(.6, 1.2)
        yield dict(anchor=list(ANCHOR), objects=objects, source=dict(kind='sampled'),
                   launch=dict(position_m=[round(ANCHOR[0] + rad * math.cos(ang), 3), 0.,
                                           round(ANCHOR[2] + rad * math.sin(ang), 3)],
                               velocity_m_s=[round(sp * math.cos(ang + math.pi / 2 * turn), 3), 0.,
                                             round(sp * math.sin(ang + math.pi / 2 * turn), 3)],
                               start_time_s=round(rng.uniform(0, 5), 1)))


def _select(worlds: Worlds, g, rule, scene, sims, cover, need, min_px, durations, rng):
    """Shortest duration giving a separable quadruple that covers an under-covered world."""
    if not in_frame(projected(scene['launch']['position_m'])[:2]):
        return None
    for dt in durations:
        try:
            states = {CANONICAL: worlds.outcome(worlds.simulator(g), scene['anchor'], scene['launch'], dt)}
            states.update({v: worlds.outcome(s, scene['anchor'], scene['launch'], dt) for v, s in sims.items()})
        except DomainError:
            return None
        order = sorted(sims, key=lambda v: (cover[v], rng.random()))
        for trio in itertools.combinations(order, 3):
            if all(cover[v] >= need for v in trio):
                continue
            pts = [states[CANONICAL][1]] + [states[v][1] for v in trio]
            if min(math.dist(a, b) for a, b in itertools.combinations(pts, 2)) >= min_px:
                return dt, states, trio
    return None


def build_condition(cfg: Config, worlds: Worlds, g: str, rule: str):
    ic = cfg.items
    rng = random.Random(f'{ic.seed}-{g}-{rule}')
    sims = {v: worlds.simulator(g, rule, v) for v in worlds.variants(g, rule)}
    cover, items, tried = Counter(), [], Counter()
    scenes = itertools.chain(worlds.existing_scenes(g, rule),
                             itertools.islice(_sampled_scenes(rng, worlds.object_catalog(g)), ic.max_sampled_scenes))
    for scene in scenes:
        if all(cover[v] >= ic.per_world for v in sims):
            break
        tried[scene['source']['kind']] += 1
        hit = _select(worlds, g, rule, scene, sims, cover, ic.per_world, ic.min_separation_px, ic.durations_s, rng)
        if not hit:
            continue
        dt, states, trio = hit
        labels = list('ABCD'); rng.shuffle(labels)
        choices = {lab: dict(law=m, state=states[m][0].to_dict(), pixel_1920=[round(x, 1) for x in states[m][1]])
                   for lab, m in zip(labels, [CANONICAL, *trio])}
        sep = min(math.dist(a['pixel_1920'], b['pixel_1920']) for a, b in itertools.combinations(choices.values(), 2))
        items.append(dict(
            format='law_contrastive_item', schema_version=2, visibility='host_only',
            id=f'{g}_{rule}_item{len(items) + 1:03d}', group=g, rule=rule,
            anchor_m=scene['anchor'], launch=dict(scene['launch'], duration_s=dt), objects=scene['objects'],
            source=scene['source'], choices=choices,
            answers={c['law']: lab for lab, c in choices.items() if c['law'] != CANONICAL},
            canonical_label=next(lab for lab, c in choices.items() if c['law'] == CANONICAL),
            min_separation_px_1920=round(sep, 1)))
        for v in trio:
            cover[v] += 1
    report = dict(items=len(items), scenes_tried=dict(tried),
                  items_reusing_existing_scene=sum(i['source']['kind'] == 'existing_render' for i in items),
                  coverage={v: cover[v] for v in sims},
                  unidentifiable=[v for v in sims if cover[v] == 0],
                  answer_positions=dict(sorted(Counter(l for i in items for l in i['answers'].values()).items())),
                  durations_s=dict(sorted(Counter(i['launch']['duration_s'] for i in items).items())))
    return items, report


def build(cfg: Config, log=print) -> dict:
    """Select items for every configured condition and write items/<g>_<rule>.json."""
    worlds = Worlds(cfg)
    cfg.items_dir.mkdir(parents=True, exist_ok=True)
    report = {}
    for g in cfg.groups:
        for rule in cfg.rules:
            items, rep = build_condition(cfg, worlds, g, rule)
            (cfg.items_dir / f'{g}_{rule}.json').write_text(json.dumps(items, indent=1) + '\n')
            report[f'{g}/{rule}'] = rep
            log(f"[build] {g}/{rule}: {rep['items']} items, coverage {list(rep['coverage'].values())}"
                + (f", not identifiable: {rep['unidentifiable']}" if rep['unidentifiable'] else ''))
    _write(cfg.items_dir / 'build_report.json', dict(items_config=vars(cfg.items), conditions=report))
    return report


def load_items(cfg: Config):
    """Yield items of the configured groups and rules."""
    for g in cfg.groups:
        for rule in cfg.rules:
            path = cfg.items_dir / f'{g}_{rule}.json'
            if not path.exists():
                raise FileNotFoundError(f'{path} missing; run the build stage first.')
            yield from json.loads(path.read_text())


def questions(cfg: Config):
    """Yield (item, variant) pairs: one exam question per sibling world of each item."""
    for item in load_items(cfg):
        for variant in sorted(item['answers']):
            yield item, variant


# Render manifests ------------------------------------------------------------------------
def manifest(item: dict) -> dict:
    """Render manifest in the format of src/simulation/blender_attraction.py."""
    first = next(iter(item['choices'].values()))['state']
    initial = json.loads(json.dumps(first))
    initial['record_id'] = f"law_contrastive_initial:{item['id']}"
    initial['payload']['time_s'] = item['launch']['start_time_s']
    initial['payload']['objects'] = dict(
        anchor=dict(position_m=item['anchor_m'], velocity_m_s=[0., 0., 0.]),
        probe=dict(position_m=item['launch']['position_m'], velocity_m_s=item['launch']['velocity_m_s']))
    return dict(format='attraction_prediction_scene', schema_version=1, visibility='host_only',
                id=item['id'], pair_id=item['id'], instance_id=item['id'], world_index=0,
                launch=item['launch'], initial_state=initial, objects=item['objects'],
                choices={lab: dict(state=c['state']) for lab, c in sorted(item['choices'].items())},
                answer=None, answers=item['answers'], canonical_label=item['canonical_label'],
                camera=dict(CAMERA), candidate_policy=dict(LAW_CONTRASTIVE_POLICY), images=dict(IMAGES))


def export(cfg: Config, log=print) -> int:
    """Write scene.json per item; existing images are kept only if the manifest is unchanged."""
    n = stale = 0
    for item in load_items(cfg):
        m = manifest(item)
        geometry(m)  # fail now rather than in Blender
        d = cfg.item_renders(item['group'], item['rule'], item['id'])
        d.mkdir(parents=True, exist_ok=True)
        path, text = d / 'scene.json', json.dumps(m, indent=1) + '\n'
        if path.exists() and path.read_text() != text:
            for f in d.glob('*.png'):
                f.unlink()
            stale += 1
        path.write_text(text)
        n += 1
    log(f'[export] {n} manifests under {cfg.renders_dir}' + (f'; {stale} changed, old images removed' if stale else ''))
    return n


def render_complete(cfg: Config, item: dict) -> bool:
    d = cfg.item_renders(item['group'], item['rule'], item['id'])
    return all((d / name).exists() for name in IMAGES.values())


# Validation ------------------------------------------------------------------------------
def _nearest(state, choices) -> str:
    p = state.payload['objects']['probe']['position_m']
    return min(choices, key=lambda k: math.dist(p, choices[k]['state']['payload']['objects']['probe']['position_m']))


def validate(cfg: Config, log=print) -> dict:
    """Reference policies that need no model: oracle, canonical physics, appearance, label prior."""
    worlds = Worlds(cfg)
    rows = []
    for item in load_items(cfg):
        g, rule, L = item['group'], item['rule'], item['launch']
        canon, _ = worlds.outcome(worlds.simulator(g), item['anchor_m'], L, L['duration_s'], check_frame=False)
        canon_pick = _nearest(canon, item['choices'])
        p0 = L['position_m']
        appearance = min(item['choices'], key=lambda k: math.dist(
            p0, item['choices'][k]['state']['payload']['objects']['probe']['position_m']))
        for variant, ans in item['answers'].items():
            true, _ = worlds.outcome(worlds.simulator(g, rule, variant), item['anchor_m'], L, L['duration_s'], check_frame=False)
            rows.append(dict(item=item['id'], rule=rule, answer=ans, oracle=_nearest(true, item['choices']) == ans,
                             canonical=canon_pick == ans, appearance=appearance == ans))
    n = len(rows)
    per_item = defaultdict(Counter)
    for r in rows:
        per_item[r['item']][r['answer']] += 1
    labels = Counter(r['answer'] for r in rows)
    rate = lambda key, R=rows: sum(r[key] for r in R) / max(1, len(R))
    out = dict(questions=n, items=len(per_item), oracle=rate('oracle'), canonical_physics=rate('canonical'),
               appearance=rate('appearance'), label_prior=labels.most_common(1)[0][1] / n,
               world_blind_max=sum(max(c.values()) for c in per_item.values()) / n,
               answer_positions=dict(sorted(labels.items())),
               by_rule={rule: dict(questions=sum(r['rule'] == rule for r in rows),
                                   appearance=rate('appearance', [r for r in rows if r['rule'] == rule]))
                        for rule in cfg.rules})
    out['checks'] = dict(oracle_is_1=out['oracle'] == 1.0, canonical_is_0=out['canonical_physics'] == 0.0,
                         world_blind_at_most_one_third=out['world_blind_max'] <= 1 / 3 + 1e-9)
    _write(cfg.items_dir / 'validation.json', out)
    log('[validate] ' + ', '.join(f'{k}={out[k]:.3f}' for k in
                                  ('oracle', 'canonical_physics', 'appearance', 'label_prior', 'world_blind_max'))
        + f' over {n} questions; checks ' + ('PASS' if all(out['checks'].values()) else f"FAIL {out['checks']}"))
    return out


def audit_source_exam(cfg: Config, log=print) -> dict:
    """Audit the original exam renders: answer positions and canonical-physics accuracy."""
    worlds = Worlds(cfg)
    letters, hits, n = Counter(), 0, 0
    for g in cfg.groups:
        root = cfg.source_renders_dir / cfg.family / cfg.group_name(g)
        for path in root.glob('*/variant_*/q*/scene.json'):
            d = json.loads(path.read_text())
            letters[d['answer']] += 1
            L = d['launch']
            anchor = d['initial_state']['payload']['objects']['anchor']['position_m']
            try:
                s, _ = worlds.outcome(worlds.simulator(g), anchor, L, L['duration_s'], check_frame=False)
            except DomainError:
                continue
            n += 1
            hits += _nearest(s, d['choices']) == d['answer']
    out = dict(questions=sum(letters.values()), answer_positions=dict(letters), canonical_physics=hits / max(1, n))
    _write(cfg.items_dir / 'source_exam_audit.json', out)
    log(f"[audit] source exam: {out['questions']} questions, answers {dict(letters)}, canonical physics {out['canonical_physics']:.3f}")
    return out


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, default=str) + '\n')
