"""Episodes and the frozen exam for every world, mode and evidence arm; resumable ledgers.

Exam evidence arms (each exam question is asked independently, tools disabled):
    none          no history: the rendered context and the prompt only.
    own           the full multimodal transcript of this world's episode, as the agent's own conversation.
    sibling       the transcript of an episode in another world of the same condition (wrong-world control).
    observations  a fresh agent shown this world's transcript as a record it did not produce (yoked passive).
    own_record    a fresh context with this world's transcript as a record of the agent's own experiments;
                  same format as `observations`, so own_record - observations isolates authorship, not format.
    sibling_told  the sibling transcript as in `sibling`, but the agent is told the tested world is a different
                  world with the same form of law and different hidden parameters (transfer to a variant world).
    law_text      no history: this world's hidden law and regime constants in text (ceiling for applying a known
                  law to images; law_text - own separates forming the law from applying it).
"""
from __future__ import annotations

import json
import random
import time
import traceback
from pathlib import Path
from typing import Callable

from src.harness.types import Message

from src.law_contrastive.exam import law_description
from src.law_contrastive.worlds import Worlds

from . import grid
from .config import MODES, NO_EPISODE, Config
from .episode import (SYSTEM, Episode, choice_content, encode, load, parse_letter, run_tool, FINISH, text)
from .items import pools

HarnessFactory = Callable[[str, Path], object]


def default_harness(model: str, out_dir: Path):
    from src.density_pipeline import RecordedHarness
    from src.harness import OpenAIHarness
    out_dir.mkdir(parents=True, exist_ok=True)
    return RecordedHarness(OpenAIHarness(model=model), out_dir, 'visual_interaction')


class Ledger:
    def __init__(self, path: Path, key: tuple):
        self.path, self.key = Path(path), key

    def rows(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(l) for l in self.path.read_text().splitlines() if l.strip()]

    def done(self) -> set:
        return {tuple(r[k] for k in self.key) for r in self.rows() if r.get('status') == 'complete'}

    def append(self, row: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open('a') as fh:
            fh.write(json.dumps(row) + '\n')


def generation_kwargs(cfg: Config) -> dict:
    return {k: v for k, v in dict(temperature=cfg.run.temperature,
                                  max_completion_tokens=cfg.run.max_completion_tokens).items() if v is not None}


def _worlds(cfg: Config, pool: dict):
    return sorted(w for w in pool if w[0] in cfg.groups and w[1] in cfg.rules)


def ready(cfg: Config, world: tuple) -> bool:
    return grid.frames_complete(cfg, *world)


# Episodes ----------------------------------------------------------------------------------
def run_episodes(cfg: Config, model: str, mode: str, *, limit: int = 0, harness_factory: HarnessFactory = default_harness,
                 log=print) -> dict:
    pool = pools(cfg)
    ledger = Ledger(cfg.ledger(model, mode, 'episodes'), ('group', 'rule', 'variant'))
    done = ledger.done()
    counts = dict(complete=0, skipped_done=0, skipped_frames=0, failed=0)
    for world in _worlds(cfg, pool):
        if world in done:
            counts['skipped_done'] += 1; continue
        if limit and counts['complete'] + counts['failed'] >= limit:
            break
        if MODES[mode]['frames'] and not ready(cfg, world):
            counts['skipped_frames'] += 1; continue
        out = cfg.episode_dir(model, mode, *world)
        if out.exists():  # an interrupted episode restarts from scratch
            for f in out.glob('*'):
                f.unlink()
        row = dict(group=world[0], rule=world[1], variant=world[2], model=model, mode=mode)
        t0 = time.time()
        try:
            ep = Episode(cfg, mode, world, pool[world]['checkpoint'], harness_factory(model, out), out,
                         generation_kwargs(cfg))
            res = ep.run()
            row.update(status='complete', **res)
            counts['complete'] += 1
        except Exception as exc:  # keep going; the next run retries this world
            row.update(status='failed', error=f'{type(exc).__name__}: {exc}'[:300])
            (out / 'error.txt').parent.mkdir(parents=True, exist_ok=True)
            (out / 'error.txt').write_text(traceback.format_exc())
            counts['failed'] += 1
        row.update(seconds=round(time.time() - t0, 1), time_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
        ledger.append(row)
        log(f"[episode {model}|{mode}] {'/'.join(world)}: {row['status']} "
            + (f"checkpoints {row.get('checkpoint_correct')}" if row['status'] == 'complete' else row.get('error', '')))
    log(f'[episode {model}|{mode}] ' + ', '.join(f'{k}={v}' for k, v in counts.items()))
    return counts


def load_episode(cfg: Config, model: str, mode: str, world: tuple) -> dict | None:
    path = cfg.episode_dir(model, mode, *world) / 'episode.json'
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return data if data.get('status') == 'complete' else None


# Exam --------------------------------------------------------------------------------------
LEAD = {
    'none': 'You have not run any experiments in this world. Use the rendered context only.',
    'own': 'The experiments are over and tools are disabled. A new scene in this same world:',
    'sibling': 'The experiments are over and tools are disabled. A new scene in this same world:',
    'sibling_told': ('The experiments are over and tools are disabled. You are now in a different world of the same '
                     'kind: its force law has the same form as in the world you explored, but its hidden parameters '
                     'differ. A new scene in this new world:'),
    'observations': 'Using the record above of experiments in this same world, answer about a new scene:',
    'own_record': 'Using the record above of your experiments in this same world, answer about a new scene:',
    'law_text': 'You have not run any experiments in this world. The governing law of this world is given below.',
}
SIBLING_ARMS = ('sibling', 'sibling_told')
RECORD_INTRO = {
    'observations': ("Below is the complete record of another agent's experiments in an unfamiliar physical "
                     "world, including every image it saw. You did not run these experiments."),
    'own_record': ("Below is the complete record of your own earlier experiments in an unfamiliar physical "
                   "world, including every image you saw. You chose and ran these experiments."),
}


def observation_record(messages: list[Message], arm: str = 'observations') -> list[Message]:
    """An episode as one record, with no actions to take: yoked passive, or the agent's own (fresh context)."""
    content = [text(RECORD_INTRO[arm])]
    for m in messages[1:]:
        tag = {'user': 'World', 'assistant': 'Agent', 'tool': 'Tool result'}[m.role]
        if isinstance(m.content, list):
            content += [p if p.get('type') != 'text' else text(f"[{tag}] {p['text']}") for p in m.content]
        elif m.content:
            content.append(text(f'[{tag}] {m.content}'))
        for t in m.tool_calls:
            content.append(text(f'[Agent action] {t.function_name}({t.arguments})'))
    content.append(text('End of record.'))
    return [Message(role='system', content=SYSTEM), Message(role='user', content=content),
            Message(role='assistant', content='I have studied the record.')]


def sibling_world(cfg: Config, model: str, mode: str, world: tuple, pool: dict) -> tuple | None:
    others = [w for w in _worlds(cfg, pool) if w[:2] == world[:2] and w != world]
    random.Random(f'{cfg.episode.seed}-sibling-{"-".join(world)}').shuffle(others)
    return next((w for w in others if load_episode(cfg, model, mode, w)), None)


def run_exam(cfg: Config, model: str, mode: str, *, evidence=None, limit: int = 0,
             harness_factory: HarnessFactory = default_harness, log=print) -> dict:
    pool = pools(cfg)
    ledger = Ledger(cfg.ledger(model, mode, 'exam'), ('group', 'rule', 'variant', 'item', 'evidence'))
    done = ledger.done()
    kw = generation_kwargs(cfg)
    counts = dict(answered=0, correct=0, skipped_done=0, skipped_episode=0, failed=0)
    worlds = Worlds(cfg.law)
    for world in _worlds(cfg, pool):
        own = load_episode(cfg, model, mode, world)
        for arm in evidence or cfg.run.evidence:
            source = world
            if arm in SIBLING_ARMS:
                source = sibling_world(cfg, model, mode, world, pool)
            if arm not in NO_EPISODE and (own is None or source is None):
                counts['skipped_episode'] += len(pool[world]['exam']); continue
            src_ep = load_episode(cfg, model, mode, source) if arm in SIBLING_ARMS else own
            record = arm in ('observations', 'own_record')
            base = ([Message(role='system', content=SYSTEM)] if arm in NO_EPISODE else
                    observation_record(load(src_ep['messages']), arm) if record else load(src_ep['messages']))
            tools = None if arm in NO_EPISODE or record else [run_tool(cfg, MODES[mode]), FINISH]
            lead = LEAD[arm]
            if arm == 'law_text':
                lead += ' ' + law_description(worlds.constants(*world), worlds.hidden_law(*world))
            for item in pool[world]['exam']:
                key = (*world, item['id'], arm)
                if key in done:
                    counts['skipped_done'] += 1; continue
                if limit and counts['answered'] + counts['failed'] >= limit:
                    return _finish(counts, model, mode, ledger, log)
                out = cfg.ledger(model, mode, 'exam').parent / 'exam' / '_'.join(key)
                truth = item['answers'][world[2]]
                sib_answer = item['answers'].get(source[2]) if arm in SIBLING_ARMS and source else None
                row = dict(group=world[0], rule=world[1], variant=world[2], item=item['id'], evidence=arm,
                           model=model, mode=mode, source_world='/'.join(source) if arm not in NO_EPISODE else None,
                           answer=truth, canonical_label=item['canonical_label'], sibling_answer=sib_answer)
                try:
                    msgs = base + [Message(role='user', content=choice_content(cfg, item, lead))]
                    call_kw = dict(kw, tool_choice='none') if tools and cfg.run.tool_choice_none else kw
                    resp = harness_factory(model, out).generate(encode(msgs), tools=tools, **call_kw)
                    ans = parse_letter(resp.content)
                    row.update(status='complete', agent_answer=ans, correct=ans == truth,
                               picked_canonical=ans == item['canonical_label'],
                               picked_sibling=(ans == sib_answer) if sib_answer else None)
                    counts['answered'] += 1; counts['correct'] += row['correct']
                except Exception as exc:
                    row.update(status='failed', error=f'{type(exc).__name__}: {exc}'[:300])
                    counts['failed'] += 1
                row['time_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                ledger.append(row)
                log(f"[exam {model}|{mode}|{arm}] {'/'.join(world)} {item['id']}: {row['status']} "
                    f"{row.get('agent_answer', '')} (answer {truth})")
    return _finish(counts, model, mode, ledger, log)


def _finish(counts, model, mode, ledger, log):
    log(f'[exam {model}|{mode}] ' + ', '.join(f'{k}={v}' for k, v in counts.items()) + f'; ledger {ledger.path}')
    return counts
