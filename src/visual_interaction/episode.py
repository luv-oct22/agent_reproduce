"""One visual-interaction episode in one hidden-law world.

The agent runs up to `budget` experiments from the public menu, one per turn, with `run_experiment`.
In predicting modes it first states where it expects the probe to end. The world then returns the
outcome: a rendered strobe frame, numbers, or both, depending on the mode. Before the first experiment
and after every `checkpoint_every` experiments, the host shows a checkpoint question (a new scene and
four rendered candidate futures); the agent answers, then sees the true outcome. Checkpoint scenes never
appear in the exam.

Messages keep images as {'type': 'image_file', 'path': ...}; they are encoded only when sent to a model,
so a saved transcript can be replayed exactly (own-evidence exam, yoked-passive exam).
"""
from __future__ import annotations

import base64
import io
import json
import random
import re
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path

from PIL import Image

from src.harness.types import Message, ToolCall, ToolDef

from . import grid
from .config import MODES, Config
from .items import checkpoint_schedule, item_images, question_text

SYSTEM = 'You are a careful experimental physicist.'
INTRO = (
    "You are in an unfamiliar physical world. A heavy orange anchor is fixed at x = 0.000, z = 1.500 m; a light "
    "blue probe moves around it. Coordinates are sphere centres in metres, x right and z up, y = 0; the grid "
    "spacing is 0.10 m. The anchor has mass 1 kg and the probe 0.1 kg. The probe is attracted to the anchor, "
    "but the force law of this world may differ from familiar physics and may vary with distance and time.\n\n"
    "Your goal is to learn this world well enough to foresee how new scenes will unfold. Later, without any "
    "tools, you will see new scenes and choose which image shows the probe's future position.\n\n"
    "You may run up to {budget} experiments from the menu below, one per turn, with the tool run_experiment. "
    "Each experiment places the probe to the right of the anchor at a given distance, launches it with a given "
    "velocity at a given world time, and records it at {samples} equally spaced moments over the duration. "
    "{returns} If the probe reaches the anchor's minimum separation or leaves the field of view, the record "
    "stops there.{predict}\n\nFrom time to time you will also be shown a new scene in this world and four "
    "candidate futures; answer with one letter, then you will see the true outcome.\n\nExperiment menu:\n{menu}")
RETURNS = {
    (True, False): 'The world returns an image of the panel with the probe drawn at its start and at every '
                   'recorded moment, fading from faint (start) to solid (end).',
    (False, True): 'The world returns the recorded probe positions and times as numbers.',
    (True, True): 'The world returns an image of the panel with the probe drawn at its start and at every '
                  'recorded moment, fading from faint (start) to solid (end), and the recorded positions and '
                  'times as numbers.',
}
PREDICT = (' Before each experiment, give in the argument expected_end_m where you expect the probe to be at the '
           'end of the record ([x, z] in metres). It is recorded and not scored.')
STATUS = {'complete': 'complete', 'contact': 'stopped early: the probe reached the minimum separation',
          'left_view': 'stopped early: the probe left the field of view'}
LETTER = re.compile(r'\b([ABCD])\b')


# Message helpers ---------------------------------------------------------------------------
def image(path) -> dict:
    return {'type': 'image_file', 'path': str(path)}


def text(s: str) -> dict:
    return {'type': 'text', 'text': s}


def encode(messages: list[Message]) -> list[Message]:
    """Replace image_file parts by data URIs, as the harness expects."""
    out = []
    for m in messages:
        content = m.content
        if isinstance(content, list):
            content = [_encode_part(p) for p in content]
        out.append(Message(role=m.role, content=content, tool_calls=m.tool_calls, tool_call_id=m.tool_call_id))
    return out


def _encode_part(p: dict) -> dict:
    if p.get('type') != 'image_file':
        return p
    return {'type': 'image_url', 'image_url': {'url': _jpeg_uri(p['path']), 'detail': 'high'}}


@lru_cache(maxsize=4096)
def _jpeg_uri(path: str) -> str:
    """Episodes resend dozens of images every turn, so they are sent as JPEG (about 10x smaller than PNG)."""
    buf = io.BytesIO()
    with Image.open(path) as im:
        im.convert('RGB').save(buf, format='JPEG', quality=90)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()


def dump(messages: list[Message]) -> list[dict]:
    return [dict(role=m.role, content=m.content, tool_calls=[asdict(t) for t in m.tool_calls],
                 tool_call_id=m.tool_call_id) for m in messages]


def load(rows: list[dict]) -> list[Message]:
    return [Message(role=r['role'], content=r['content'], tool_calls=[ToolCall(**t) for t in r['tool_calls']],
                    tool_call_id=r['tool_call_id']) for r in rows]


def choice_content(cfg: Config, item: dict, lead: str) -> list:
    imgs = item_images(cfg, item)
    content = [text(f'{lead}\n{question_text(item)}'), text('Context frame'), image(imgs['context'])]
    for k in 'ABCD':
        content += [text(f'Choice {k}'), image(imgs[k])]
    return content + [text('Answer with just one letter: A, B, C, or D.')]


def parse_letter(s: str | None) -> str | None:
    m = LETTER.search((s or '').upper())
    return m.group(1) if m else None


# Tools -------------------------------------------------------------------------------------
def run_tool(cfg: Config, mode: dict, allowed: list[str] | None = None) -> ToolDef:
    props = {'experiment_id': {'type': 'string', 'enum': allowed or [e['id'] for e in grid.menu(cfg)],
                               'description': 'Experiment from the menu.'}}
    required = ['experiment_id']
    if mode['predict']:
        props['expected_end_m'] = {'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 2,
                                   'description': 'Expected final probe position [x, z] in metres.'}
        required.append('expected_end_m')
    return ToolDef(name='run_experiment', description='Run one experiment from the menu and observe its outcome.',
                   parameters={'type': 'object', 'properties': props, 'required': required,
                               'additionalProperties': False})


FINISH = ToolDef(name='finish_experiments', description='End the experiments early.',
                 parameters={'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False})


def outcome_content(cfg: Config, mode: dict, world: tuple, experiment: dict, outcome: dict) -> tuple[dict, list | None]:
    """Tool result and, in frame modes, a user message carrying the outcome image."""
    status = STATUS[outcome['status']]
    result = dict(success=True, experiment_id=experiment['id'], status=status, recorded_samples=len(outcome['samples']))
    if mode['numbers']:
        result['positions'] = [dict(time_s=s['time_s'], x_m=s['position_m'][0], z_m=s['position_m'][2])
                               for s in outcome['samples']]
    content = None
    if mode['frames']:
        content = [text(f"Outcome of {experiment['id']} ({status})."),
                   image(grid.frame_path(cfg, *world, experiment['id']))]
    return result, content


# Episode -----------------------------------------------------------------------------------
class Episode:
    """Runs and records one episode; `harness.generate(messages, tools=..., **kw)` returns a ChatResponse."""

    def __init__(self, cfg: Config, mode_name: str, world: tuple, checkpoint_pool: list, harness, out_dir,
                 generation_kwargs: dict | None = None):
        self.cfg, self.mode_name, self.mode = cfg, mode_name, MODES[mode_name]
        self.world, self.harness, self.out = world, harness, Path(out_dir)
        self.kw = dict(generation_kwargs or {})
        self.menu = {e['id']: e for e in grid.menu(cfg)}
        self.outcomes = grid.load_outcomes(cfg, *world)
        self.checkpoints = checkpoint_schedule(cfg, checkpoint_pool)
        self.rng = random.Random(f'{cfg.episode.seed}-{mode_name}-{"-".join(world)}')
        self.messages: list[Message] = []
        self.events: list[dict] = []
        self.calls = 0

    def _generate(self, tools: list[ToolDef], answer_only: bool = False):
        self.calls += 1
        kw = dict(self.kw)
        if answer_only and self.cfg.run.tool_choice_none:
            kw['tool_choice'] = 'none'
        return self.harness.generate(encode(self.messages), tools=tools, **kw)

    def save(self, status: str = 'running'):
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out / 'episode.json').write_text(json.dumps(dict(
            format='visual_interaction_episode', schema_version=1, status=status, mode=self.mode_name,
            world=dict(zip(('group', 'rule', 'variant'), self.world)), model=self.harness.model_name,
            model_calls=self.calls, events=self.events, messages=dump(self.messages)), indent=1) + '\n')

    def checkpoint(self, k: int, done: int):
        item, variant = self.checkpoints[k], self.world[2]
        lead = (f'Checkpoint {k + 1} (after {done} experiments). A new scene in this same world; '
                'do not run an experiment now.')
        self.messages.append(Message(role='user', content=choice_content(self.cfg, item, lead)))
        resp = self._generate(self.tools(), answer_only=True)
        self.messages.append(Message(role='assistant', content=resp.content or ''))
        answer, truth = parse_letter(resp.content), item['answers'][variant]
        self.events.append(dict(kind='checkpoint', index=k, after_experiments=done, item=item['id'], answer=answer,
                                truth=truth, correct=answer == truth, picked_canonical=answer == item['canonical_label']))
        self.messages.append(Message(role='user', content=[
            text(f'The true outcome was {truth}, shown below. Continue with your experiments.'),
            image(item_images(self.cfg, item)[truth])]))
        self.save()

    def tools(self, allowed=None):
        return [run_tool(self.cfg, self.mode, allowed), FINISH]

    def run(self) -> dict:
        cfg, ep = self.cfg, self.cfg.episode
        intro = INTRO.format(budget=ep.budget, samples=cfg.grid.samples,
                             returns=RETURNS[(self.mode['frames'], self.mode['numbers'])],
                             predict=PREDICT if self.mode['predict'] else '', menu=grid.public_menu_text(cfg))
        self.messages = [Message(role='system', content=SYSTEM), Message(role='user', content=intro)]
        done, turns, cp, stop = 0, 0, 0, False
        if self.checkpoints:
            self.checkpoint(0, 0); cp = 1
        while done < ep.budget and turns < ep.max_turns and not stop:
            turns += 1
            if self.mode['chooser'] == 'random':
                used = {e['experiment'] for e in self.events if e['kind'] == 'experiment'}
                chosen = self.rng.choice([i for i in self.menu if i not in used] or list(self.menu))
                self.messages.append(Message(role='user', content=(
                    f'Experiments used: {done} of {ep.budget}. The next experiment was chosen for you: {chosen}. '
                    'Call run_experiment with it.')))
                tools = self.tools([chosen])
            else:
                self.messages.append(Message(role='user', content=(
                    f'Experiments used: {done} of {ep.budget}. Choose your next experiment.')))
                tools = self.tools()
            resp = self._generate(tools)
            self.messages.append(Message(role='assistant', content=resp.content or '', tool_calls=resp.tool_calls))
            if not resp.tool_calls:
                continue
            images = []
            for tc in resp.tool_calls:
                try:
                    args = json.loads(tc.arguments or '{}')
                except ValueError:
                    args = {}
                args = args if isinstance(args, dict) else {}
                allowed = tools[0].parameters['properties']['experiment_id']['enum']
                if tc.function_name == 'finish_experiments' and self.mode['chooser'] == 'agent':
                    result, stop = dict(success=True, status='experiments ended'), True
                elif tc.function_name != 'run_experiment' or args.get('experiment_id') not in allowed:
                    result = dict(success=False, error='Unknown tool or experiment id.')
                elif done >= ep.budget or stop:
                    result = dict(success=False, error='No experiment run: the budget is used or experiments ended.')
                else:
                    exp, done = self.menu[args['experiment_id']], done + 1
                    outcome = self.outcomes[exp['id']]
                    result, content = outcome_content(cfg, self.mode, self.world, exp, outcome)
                    end = outcome['samples'][-1]['position_m'] if outcome['samples'] else None
                    self.events.append(dict(kind='experiment', index=done, experiment=exp['id'],
                                            chooser=self.mode['chooser'], prediction=args.get('expected_end_m'),
                                            status=outcome['status'], end_m=[end[0], end[2]] if end else None))
                    if content:
                        images.append(content)
                self.messages.append(Message(role='tool', content=json.dumps(result), tool_call_id=tc.id))
            for content in images:
                self.messages.append(Message(role='user', content=content))
            self.save()
            while cp < len(self.checkpoints) and done >= cp * ep.checkpoint_every:
                self.checkpoint(cp, done); cp += 1
        # Checkpoints not reached (episode ended early) are asked now, so every episode has the same points.
        while cp < len(self.checkpoints):
            self.checkpoint(cp, done); cp += 1
        self.save('complete')
        return dict(experiments=done, turns=turns, model_calls=self.calls,
                    checkpoint_correct=[e['correct'] for e in self.events if e['kind'] == 'checkpoint'])
