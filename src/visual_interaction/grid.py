"""The public experiment menu and its simulated outcomes in every world.

An experiment places the probe at distance r to the right of the fixed anchor, gives it a velocity
(radial, tangential) and a start time, and records the probe at `samples` equally spaced times over the
duration. The menu is identical in every world; only the outcomes differ. A trial that reaches the
minimum separation or leaves the field of view stops there, and the outcome says so.
"""
from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

from src.law_contrastive.worlds import Worlds, in_frame
from src.simulation.attraction_visual import projected
from src.worlds.attraction import DomainError

from .config import Config

ANCHOR = [0., 0., 1.5]
CANONICAL = 'canonical'


def menu(cfg: Config) -> list[dict]:
    """Experiments in a fixed order, with stable ids e01, e02, ..."""
    g = cfg.grid
    out = []
    for r, (vr, vt), t0, dt in itertools.product(g.radii_m, g.velocities_m_s, g.start_times_s, g.durations_s):
        out.append(dict(id=f'e{len(out) + 1:02d}', distance_m=r, radial_speed_m_s=vr, tangential_speed_m_s=vt,
                        start_time_s=t0, duration_s=dt,
                        position_m=[round(ANCHOR[0] + r, 6), 0., ANCHOR[2]],
                        velocity_m_s=[vr, 0., vt]))
    return out


def public_menu_text(cfg: Config) -> str:
    rows = [f"{e['id']}: start {e['distance_m']:.1f} m right of the anchor, velocity "
            f"(outward {e['radial_speed_m_s']:.1f}, upward {e['tangential_speed_m_s']:.1f}) m/s, "
            f"start time {e['start_time_s']:.1f} s, duration {e['duration_s']:.1f} s" for e in menu(cfg)]
    return '\n'.join(rows)


def simulate(sim, experiment: dict, samples: int) -> dict:
    """Probe positions at equally spaced times; stops at contact or when leaving the view."""
    state = sim.make_state({'anchor': ANCHOR, 'probe': experiment['position_m']},
                           {'anchor': [0., 0., 0.], 'probe': experiment['velocity_m_s']}, experiment['start_time_s'])
    step = experiment['duration_s'] / samples
    points, status = [], 'complete'
    for k in range(1, samples + 1):
        try:
            state = sim.advance(state, step)
        except DomainError:
            status = 'contact'
            break
        p = state.payload['objects']['probe']['position_m']
        if not in_frame(projected(p)[:2]):
            status = 'left_view'
            break
        points.append(dict(time_s=round(experiment['start_time_s'] + k * step, 6), position_m=[round(x, 6) for x in p]))
    return dict(id=experiment['id'], status=status, samples=points)


def worlds_of(cfg: Config, worlds: Worlds):
    """(group, rule, variant) of every hidden-law world in the configured conditions."""
    for g in cfg.groups:
        for rule in cfg.rules:
            for v in worlds.variants(g, rule):
                yield g, rule, v


def build(cfg: Config, log=print) -> dict:
    """Simulate the menu in every world; write outcomes.json and the render manifest per world."""
    worlds = Worlds(cfg.law)
    experiments = menu(cfg)
    report = {}
    for g, rule, v in worlds_of(cfg, worlds):
        sim = worlds.simulator(g, rule, v)
        outcomes = [simulate(sim, e, cfg.grid.samples) for e in experiments]
        d = cfg.world_frames(g, rule, v)
        d.mkdir(parents=True, exist_ok=True)
        _write_if_changed(d / 'outcomes.json', dict(format='visual_interaction_outcomes', visibility='host_only',
                                                    world=dict(group=g, rule=rule, variant=v),
                                                    experiments=experiments, outcomes=outcomes))
        _write_if_changed(d / 'frames.json', render_manifest(cfg, worlds, g, experiments, outcomes))
        counts = {s: sum(o['status'] == s for o in outcomes) for s in ('complete', 'contact', 'left_view')}
        report[f'{g}/{rule}/{v}'] = counts
    totals = {s: sum(c[s] for c in report.values()) for s in ('complete', 'contact', 'left_view')}
    log(f'[grid] {len(experiments)} experiments x {len(report)} worlds; outcomes {totals}')
    _write_if_changed(cfg.frames_dir / 'grid_report.json', dict(experiments=len(experiments), worlds=report, totals=totals))
    return report


def render_manifest(cfg: Config, worlds: Worlds, g: str, experiments: list, outcomes: list) -> dict:
    objects = worlds.object_catalog(g)
    frames = []
    for e, o in zip(experiments, outcomes):
        frames.append(dict(id=e['id'], image=f"{e['id']}.png", start_m=e['position_m'],
                           strobe_m=[s['position_m'] for s in o['samples']]))
    return dict(format='visual_interaction_frames', schema_version=1, visibility='host_only',
                anchor_m=ANCHOR, objects=objects, resolution=list(cfg.grid.resolution), frames=frames)


def load_outcomes(cfg: Config, g: str, rule: str, v: str) -> dict:
    path = cfg.world_frames(g, rule, v) / 'outcomes.json'
    if not path.exists():
        raise FileNotFoundError(f'{path} missing; run: python -m src.visual_interaction prepare')
    data = json.loads(path.read_text())
    return {o['id']: o for o in data['outcomes']}


def frame_path(cfg: Config, g: str, rule: str, v: str, experiment_id: str) -> Path:
    return cfg.world_frames(g, rule, v) / f'{experiment_id}.png'


def frames_complete(cfg: Config, g: str, rule: str, v: str) -> bool:
    return all(frame_path(cfg, g, rule, v, e['id']).exists() for e in menu(cfg))


def _write_if_changed(path: Path, data) -> None:
    text = json.dumps(data, indent=1) + '\n'
    if path.exists() and path.read_text() == text:
        return
    if path.name == 'frames.json':  # a changed manifest invalidates its images
        for f in path.parent.glob('e*.png'):
            f.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def distance_to_anchor(p) -> float:
    return math.dist(p, ANCHOR)
