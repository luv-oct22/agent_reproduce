"""Checkpoint and exam questions from the law-contrastive items.

Items of a condition alternate between the checkpoint pool (even positions) and the exam pool (odd
positions), so the two pools never share a scene. Images are the rendered law-contrastive frames,
downscaled for the multi-turn episode.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from PIL import Image

from src.law_contrastive.items import load_items
from src.law_contrastive.exam import question_text as _law_question_text
from src.simulation.attraction_visual import IMAGES

from .config import Config


def item_role(index: int) -> str:
    return 'checkpoint' if index % 2 == 0 else 'exam'


def pools(cfg: Config) -> dict:
    """{(group, rule, variant): {'checkpoint': [item, ...], 'exam': [item, ...]}}."""
    out = {}
    for g in cfg.groups:
        for rule in cfg.rules:
            for i, item in enumerate(json.loads((cfg.law.items_dir / f'{g}_{rule}.json').read_text())):
                for v in item['answers']:
                    out.setdefault((g, rule, v), dict(checkpoint=[], exam=[]))[item_role(i)].append(item)
    return out


def checkpoint_schedule(cfg: Config, pool: list) -> list:
    """Items asked at checkpoints 0..n; cycles through the pool if it is shorter than the schedule."""
    n = cfg.episode.budget // cfg.episode.checkpoint_every + 1
    return [pool[k % len(pool)] for k in range(n)] if pool else []


def question_text(item: dict) -> str:
    return _law_question_text(item, '').lstrip('\n')


def item_images(cfg: Config, item: dict) -> dict:
    """{'context': path, 'A': path, ...} of downscaled copies (cached on disk)."""
    src = cfg.law.item_renders(item['group'], item['rule'], item['id'])
    width = cfg.episode.checkpoint_image_width
    return {key: _downscaled(str(src / name), width) for key, name in
            (('context', IMAGES['context']), *((k, IMAGES[k]) for k in 'ABCD'))}


@lru_cache(maxsize=None)
def _downscaled(path: str, width: int) -> str:
    src = Path(path)
    if not src.exists():
        raise FileNotFoundError(f'Missing exam image {src}; render the law-contrastive exam first.')
    out = src.with_name(f'{src.stem}_w{width}.png')
    if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
        with Image.open(src) as im:
            h = round(im.height * width / im.width)
            im.convert('RGB').resize((width, h), Image.LANCZOS).save(out)
    return str(out)
