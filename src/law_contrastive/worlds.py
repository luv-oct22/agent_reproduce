"""Access to latent worlds: simulators, hidden laws, scenes, and interaction records."""
from __future__ import annotations

import json
import random
from functools import lru_cache
from pathlib import Path

from src.simulation.attraction_visual import CAMERA, projected
from src.worlds.attraction import AttractionWorld, DomainError
from src.worlds.definition import WorldInstance

from .config import Config

# Same frame bounds as attraction_visual.geometry: probe radius + caption bands.
_W, _H = CAMERA['resolution']
_PROBE_R_PX = .03 * _W / CAMERA['ortho_scale_m']
X_MARGIN_PX = _PROBE_R_PX + 8
Z_MARGIN_PX = _PROBE_R_PX + .28 * _W / CAMERA['ortho_scale_m'] + 8


def in_frame(px) -> bool:
    return X_MARGIN_PX <= px[0] <= _W - X_MARGIN_PX and Z_MARGIN_PX <= px[1] <= _H - Z_MARGIN_PX


def safe_model(model: str) -> str:
    return ''.join(c if c.isalnum() or c in '_.-' else '_' for c in model)


class Worlds:
    """Simulators and metadata for one family; cached per (group, rule, variant)."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._sim = {}
        self._histories = {}

    # Laws ---------------------------------------------------------------------------------
    def question(self, g: str, rule: str, variant: str) -> dict:
        return _read(self.cfg.world_dir(g, rule, variant) / 'q01/instance.json')

    def hidden_law(self, g: str, rule: str, variant: str) -> dict:
        # Combined worlds carry both an equation and a field; the simulator takes them merged
        # (as src/envs/combined_attraction_bench.py does). Items built before this fix used the equation only.
        q = self.question(g, rule, variant)['question']
        law = dict(q.get('hidden_equation_parameters') or {}, **(q.get('hidden_force_function') or {}))
        return law or None

    def constants(self, g: str, rule: str | None = None, variant: str | None = None) -> dict:
        """Regime constants, read from the baseline world (same for every rule and variant)."""
        world = _read(self.cfg.world_dir(g) / 'baseline/instance.json')['payload']['world']['payload']
        law = world['laws'][0]['payload']['parameters']
        return dict(strength_N=world['fields'][0]['payload']['parameters']['value'],
                    reference_distance_m=law['reference_distance_m'], reference_mass_kg=law['reference_mass_kg'],
                    minimum_distance_m=law['minimum_distance_m'], baseline_exponent_p=law['exponent'])

    def variants(self, g: str, rule: str) -> list[str]:
        return sorted(p.name for p in self.cfg.world_dir(g, rule).glob('variant_*') if p.is_dir())

    def simulator(self, g: str, rule: str | None = None, variant: str | None = None) -> AttractionWorld:
        """Canonical simulator when rule/variant are None, otherwise the hidden-law simulator."""
        key = (g, rule, variant)
        if key not in self._sim:
            payload = _read(self.cfg.world_dir(g) / 'baseline/instance.json')['payload']
            eq = self.hidden_law(g, rule, variant) if variant else None
            self._sim[key] = AttractionWorld(WorldInstance(payload), equation=eq)
        return self._sim[key]

    # Simulation ---------------------------------------------------------------------------
    @staticmethod
    def outcome(sim: AttractionWorld, anchor, launch: dict, dt: float, check_frame: bool = True):
        """Advance the probe; return (state, projected pixel). Raises DomainError if invalid."""
        s0 = sim.make_state({'anchor': anchor, 'probe': launch['position_m']},
                            {'anchor': [0., 0., 0.], 'probe': launch['velocity_m_s']}, launch['start_time_s'])
        state = sim.advance(s0, dt)
        px = projected(state.payload['objects']['probe']['position_m'])[:2]
        if check_frame and not in_frame(px):
            raise DomainError('outcome leaves the frame')
        return state, px

    # Existing scenes ----------------------------------------------------------------------
    def existing_scenes(self, g: str, rule: str):
        """Scenes of the existing renders, in hierarchy order (their context geometry is reused)."""
        root = self.cfg.source_renders_dir / self.cfg.family / self.cfg.group_name(g) / rule
        for scene in sorted(root.glob('variant_*/q*/scene.json')):
            d = _read(scene)
            L = d['launch']
            yield dict(anchor=d['initial_state']['payload']['objects']['anchor']['position_m'],
                       launch={k: L[k] for k in ('position_m', 'velocity_m_s', 'start_time_s')},
                       objects=d['objects'],
                       source=dict(kind='existing_render', scene=str(scene.parent.relative_to(root))))

    def object_catalog(self, g: str) -> list:
        root = self.cfg.source_renders_dir / self.cfg.family / self.cfg.group_name(g)
        return _read(next(root.glob('*/variant_*/q*/scene.json')))['objects']

    # Interaction records ------------------------------------------------------------------
    def histories(self, model: str, g: str, rule: str, variant: str) -> list[Path]:
        """Completed interaction records of `model` in one world (scanned once per world)."""
        key = (model, g, rule, variant)
        if key not in self._histories:
            base = self.cfg.interactions_dir / self.cfg.family / self.cfg.group_name(g) / rule / variant
            self._histories[key] = [p for p in sorted(base.glob(f'q*/interaction/{safe_model(model)}_*/interaction.json'))
                                    if record_completed(p, self.cfg.exam.max_turns)]
        return self._histories[key]

    def history(self, model: str, g: str, rule: str, variant: str, seed: int) -> Path | None:
        records = self.histories(model, g, rule, variant)
        if not records:
            return None
        return records[random.Random(f'{seed}-{g}-{rule}-{variant}').randrange(len(records))]


def record_completed(path: Path, max_turns: int = 8) -> bool:
    try:
        rec = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return False
    turns = sum(m.get('role') == 'assistant' for m in rec.get('messages', [])) + len(rec.get('skipped_turns', []))
    return bool(rec.get('finished')) or turns >= max_turns


@lru_cache(maxsize=4096)
def _read_cached(path: str, mtime: float) -> str:
    return Path(path).read_text()


def _read(path: Path) -> dict:
    path = Path(path)
    return json.loads(_read_cached(str(path), path.stat().st_mtime))
