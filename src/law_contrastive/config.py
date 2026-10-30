"""Experiment configuration: one YAML file, typed and validated once."""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO / 'configs/law_contrastive.yaml'
ARMS = ('no_history', 'own', 'sibling', 'law_text')
RULES = ('rule_1', 'rule_2', 'combined_rule')


@dataclass(frozen=True)
class ItemConfig:
    per_world: int = 8                 # exam items wanted per hidden-law world
    min_separation_px: float = 20.0    # min pairwise candidate distance at 1920 px width
    durations_s: tuple = (.4, .6, .8, 1.0, 1.2, 1.5)
    max_sampled_scenes: int = 600      # new launches tried after the existing scenes
    seed: int = 0


@dataclass(frozen=True)
class ExamConfig:
    models: tuple = ()
    arms: tuple = ARMS
    history_model: str | None = None   # None: each model uses its own interaction records
    temperature: float | None = 0.7
    max_completion_tokens: int | None = 16384
    seed: int = 0                      # selects which record serves as history
    max_turns: int = 8                 # completion criterion for interaction records


@dataclass(frozen=True)
class Config:
    family: str = 'central_force_dynamics'
    groups: tuple = ('g1', 'g2', 'g3')
    rules: tuple = RULES
    worlds_dir: Path = REPO / 'world_instances'
    source_renders_dir: Path = REPO / 'renders'
    interactions_dir: Path = REPO / 'results'
    items_dir: Path = REPO / 'results/law_contrastive/items'
    renders_dir: Path = REPO / 'renders/law_contrastive'
    results_dir: Path = REPO / 'results/law_contrastive/exam'
    items: ItemConfig = field(default_factory=ItemConfig)
    exam: ExamConfig = field(default_factory=ExamConfig)

    # Paths derived from the hierarchy.
    def group_name(self, g: str) -> str:
        return f'{self.family}_{g}'

    def world_dir(self, g: str, rule: str | None = None, variant: str | None = None) -> Path:
        parts = [self.worlds_dir, self.family, self.group_name(g)] + [p for p in (rule, variant) if p]
        return Path(*parts)

    def item_renders(self, g: str, rule: str, item_id: str) -> Path:
        return self.renders_dir / self.family / self.group_name(g) / rule / item_id


def _coerce(cls, raw: dict | None):
    raw = dict(raw or {})
    known = {f.name: f for f in fields(cls)}
    unknown = set(raw) - set(known)
    if unknown:
        raise ValueError(f'Unknown {cls.__name__} keys: {sorted(unknown)}')
    out = {}
    for name, value in raw.items():
        if isinstance(value, list):
            value = tuple(value)
        if name.endswith('_dir') and value is not None:
            value = Path(value) if Path(value).is_absolute() else REPO / value
        out[name] = value
    return cls(**out)


def load_config(path: str | Path | None = None, **overrides) -> Config:
    """Load YAML, then apply non-None CLI overrides (top-level or 'exam.x' / 'items.x')."""
    path = Path(path) if path else DEFAULT_CONFIG
    raw = yaml.safe_load(path.read_text()) if path.exists() else {}
    raw = raw or {}
    items, exam = raw.pop('items', {}), raw.pop('exam', {})
    for key, value in overrides.items():
        if value is None:
            continue
        section, _, name = key.rpartition('.')
        {'items': items, 'exam': exam}.get(section, raw)[name] = value
    cfg = _coerce(Config, raw)
    cfg = Config(**{**{f.name: getattr(cfg, f.name) for f in fields(Config)},
                    'items': _coerce(ItemConfig, items), 'exam': _coerce(ExamConfig, exam)})
    bad = [a for a in cfg.exam.arms if a not in ARMS]
    if bad:
        raise ValueError(f'Unknown arms {bad}; choose from {ARMS}')
    bad = [r for r in cfg.rules if r not in RULES]
    if bad:
        raise ValueError(f'Unknown rules {bad}; choose from {RULES}')
    return cfg
