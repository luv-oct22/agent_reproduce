"""Experiment configuration: one YAML file, typed and validated once."""
from __future__ import annotations

from dataclasses import dataclass, field, fields, replace
from pathlib import Path

import yaml

from src.law_contrastive.config import REPO, RULES, Config as LawConfig, load_config as load_law_config

DEFAULT_CONFIG = REPO / 'configs/visual_interaction.yaml'

# Interaction modes. Each mode fixes what an experiment returns, whether the agent predicts first,
# and who chooses the experiments.
MODES = {
    'frames_predict':         dict(frames=True,  numbers=False, predict=True,  chooser='agent'),
    'frames':                 dict(frames=True,  numbers=False, predict=False, chooser='agent'),
    'numbers_predict':        dict(frames=False, numbers=True,  predict=True,  chooser='agent'),
    'frames_numbers_predict': dict(frames=True,  numbers=True,  predict=True,  chooser='agent'),
    'random_frames_predict':  dict(frames=True,  numbers=False, predict=True,  chooser='random'),
}
EVIDENCE = ('none', 'own', 'sibling', 'observations', 'own_record', 'sibling_told', 'law_text')
NO_EPISODE = ('none', 'law_text')  # arms that need no interaction episode


@dataclass(frozen=True)
class GridConfig:
    radii_m: tuple = (.9, 1.2, 1.5)
    velocities_m_s: tuple = ((0., 0.), (0., .5), (0., 1.), (.5, 0.))
    start_times_s: tuple = (.5, 2.5, 4.5)
    durations_s: tuple = (.4, .8)
    samples: int = 6
    resolution: tuple = (960, 640)


@dataclass(frozen=True)
class EpisodeConfig:
    budget: int = 12
    checkpoint_every: int = 4
    max_turns: int = 20
    checkpoint_image_width: int = 960
    seed: int = 0


@dataclass(frozen=True)
class RunConfig:
    models: tuple = ()
    modes: tuple = ('frames_predict',)
    evidence: tuple = EVIDENCE
    temperature: float | None = .7
    max_completion_tokens: int | None = 16384
    tool_choice_none: bool = True


@dataclass(frozen=True)
class Config:
    law: LawConfig = field(default_factory=LawConfig)
    groups: tuple = ('g1', 'g2', 'g3')
    rules: tuple = RULES
    frames_dir: Path = REPO / 'renders/visual_interaction'
    results_dir: Path = REPO / 'results/visual_interaction'
    grid: GridConfig = field(default_factory=GridConfig)
    episode: EpisodeConfig = field(default_factory=EpisodeConfig)
    run: RunConfig = field(default_factory=RunConfig)

    def world_frames(self, g: str, rule: str, variant: str) -> Path:
        return self.frames_dir / self.law.family / self.law.group_name(g) / rule / variant

    def episode_dir(self, model: str, mode: str, g: str, rule: str, variant: str) -> Path:
        from src.law_contrastive.worlds import safe_model
        return self.results_dir / safe_model(model) / mode / 'episodes' / f'{g}_{rule}_{variant}'

    def ledger(self, model: str, mode: str, name: str) -> Path:
        from src.law_contrastive.worlds import safe_model
        return self.results_dir / safe_model(model) / mode / f'{name}.jsonl'


def _tuplify(value):
    return tuple(_tuplify(v) for v in value) if isinstance(value, list) else value


def _coerce(cls, raw: dict | None):
    raw = dict(raw or {})
    known = {f.name for f in fields(cls)}
    unknown = set(raw) - known
    if unknown:
        raise ValueError(f'Unknown {cls.__name__} keys: {sorted(unknown)}')
    return cls(**{k: _tuplify(v) for k, v in raw.items()})


def load_config(path: str | Path | None = None, **overrides) -> Config:
    """Load YAML, then apply non-None overrides: top-level keys or 'run.x' / 'episode.x' / 'grid.x'."""
    path = Path(path) if path else DEFAULT_CONFIG
    raw = (yaml.safe_load(path.read_text()) if path.exists() else {}) or {}
    sections = {name: raw.pop(name, {}) or {} for name in ('grid', 'episode', 'run')}
    for key, value in overrides.items():
        if value is None:
            continue
        section, _, name = key.rpartition('.')
        (sections[section] if section else raw)[name] = list(value) if isinstance(value, tuple) else value
    law_path = raw.pop('law_contrastive_config', None)
    law_path = (REPO / law_path) if law_path and not Path(law_path).is_absolute() else law_path
    groups, rules = tuple(raw.pop('groups', ('g1', 'g2', 'g3'))), tuple(raw.pop('rules', RULES))
    law = load_law_config(law_path, groups=list(groups), rules=list(rules))
    dirs = {k: (Path(v) if Path(v).is_absolute() else REPO / v) for k, v in raw.items() if k.endswith('_dir')}
    unknown = set(raw) - set(dirs)
    if unknown:
        raise ValueError(f'Unknown config keys: {sorted(unknown)}')
    cfg = Config(law=law, groups=groups, rules=rules, **dirs, grid=_coerce(GridConfig, sections['grid']),
                 episode=_coerce(EpisodeConfig, sections['episode']), run=_coerce(RunConfig, sections['run']))
    bad = [m for m in cfg.run.modes if m not in MODES]
    if bad:
        raise ValueError(f'Unknown modes {bad}; choose from {sorted(MODES)}')
    bad = [e for e in cfg.run.evidence if e not in EVIDENCE]
    if bad:
        raise ValueError(f'Unknown evidence {bad}; choose from {EVIDENCE}')
    if cfg.episode.budget < 1 or cfg.episode.checkpoint_every < 1 or cfg.episode.max_turns < cfg.episode.budget:
        raise ValueError('Need budget >= 1, checkpoint_every >= 1 and max_turns >= budget.')
    return cfg


def with_dirs(cfg: Config, **dirs) -> Config:
    """Copy with replaced directories (tests)."""
    return replace(cfg, **dirs)
