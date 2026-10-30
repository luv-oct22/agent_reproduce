import json
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from src.harness.types import ChatResponse, ToolCall
from src.law_contrastive.config import REPO
from src.visual_interaction import analysis, episode, grid, run
from src.visual_interaction.config import EVIDENCE, load_config
from src.visual_interaction.episode import encode
from src.visual_interaction.items import pools

PNG = REPO / 'renders/law_contrastive/central_force_dynamics/central_force_dynamics_g1/rule_1/g1_rule_1_item001/context.png'


class FakeHarness:
    """Runs the first allowed experiment when tools are offered, otherwise answers `letter`."""
    def __init__(self, letter='A'):
        self.letter, self.calls = letter, []

    @property
    def model_name(self):
        return 'fake'

    def generate(self, messages, tools=None, **kw):
        self.calls.append(dict(messages=messages, tools=tools, kw=kw))
        if tools and kw.get('tool_choice') != 'none':
            props = tools[0].parameters['properties']
            args = {'experiment_id': props['experiment_id']['enum'][len(self.calls) % len(props['experiment_id']['enum'])]}
            if 'expected_end_m' in props:
                args['expected_end_m'] = [1.0, 1.6]
            return ChatResponse(tool_calls=[ToolCall(id=f'c{len(self.calls)}', function_name='run_experiment',
                                                     arguments=json.dumps(args))])
        return ChatResponse(content=self.letter)


class VisualInteractionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cfg = load_config(groups=['g1'], rules=['rule_2'])
        cls.cfg = replace(cfg, frames_dir=cls.tmp / 'frames', results_dir=cls.tmp / 'results',
                          episode=replace(cfg.episode, budget=4, checkpoint_every=2, max_turns=6),
                          run=replace(cfg.run, models=('fake',)))
        grid.build(cls.cfg, log=lambda *_: None)
        for d in (cls.tmp / 'frames').glob('*/*/*/*'):
            for e in grid.menu(cls.cfg):
                shutil.copy(PNG, d / f"{e['id']}.png")
        cls.harnesses = []

        def factory(model, out):
            h = FakeHarness(); cls.harnesses.append(h); return h
        cls.factory = staticmethod(factory)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_1_menu_is_identical_and_outcomes_differ_between_worlds(self):
        worlds = sorted(w for w in pools(self.cfg))
        a, b = (grid.load_outcomes(self.cfg, *w) for w in worlds[:2])
        self.assertEqual(sorted(a), sorted(b))
        self.assertTrue(any(a[k]['samples'] != b[k]['samples'] for k in a))

    def test_2_pools_are_disjoint(self):
        for w, p in pools(self.cfg).items():
            self.assertFalse({i['id'] for i in p['checkpoint']} & {i['id'] for i in p['exam']}, w)

    def test_3_episode_budget_checkpoints_and_no_leak(self):
        c = run.run_episodes(self.cfg, 'fake', 'frames_predict', limit=2, harness_factory=self.factory, log=lambda *_: None)
        self.assertEqual(c['complete'], 2)
        world = sorted(pools(self.cfg))[0]
        ep = run.load_episode(self.cfg, 'fake', 'frames_predict', world)
        exps = [e for e in ep['events'] if e['kind'] == 'experiment']
        cps = [e for e in ep['events'] if e['kind'] == 'checkpoint']
        self.assertEqual(len(exps), 4)
        self.assertEqual([e['after_experiments'] for e in cps], [0, 2, 4])
        self.assertTrue(all(e['prediction'] == [1.0, 1.6] for e in exps))
        # What the model receives: every text part and tool payload, with images as encoded pixels only.
        from src.visual_interaction.episode import load
        sent = encode(load(ep['messages']))
        visible = json.dumps([[p.get('text') for p in m.content if p.get('type') == 'text']
                              if isinstance(m.content, list) else m.content for m in sent]
                             + [[t.arguments for t in m.tool_calls] for m in sent])
        self.assertFalse(any(p.get('type') == 'image_file' for m in sent if isinstance(m.content, list) for p in m.content))
        for secret in ('field_kind', 'amplitude', 'hidden', 'variant_', 'canonical', 'rule_', '/mnt/', '/tmp/'):
            self.assertNotIn(secret, visible)
        # every outcome image of the world is attached as a file part
        self.assertEqual(sum('"image_file"' in json.dumps(m['content']) and 'Outcome of' in json.dumps(m['content'])
                             for m in ep['messages']), 4)

    def test_4_checkpoints_are_asked_without_tool_calls(self):
        cp_calls = [c for h in self.harnesses for c in h.calls if c['kw'].get('tool_choice') == 'none']
        self.assertTrue(cp_calls)
        last = cp_calls[0]['messages'][-1].content
        self.assertTrue(any(p.get('type') == 'image_url' for p in last))  # encoded for the API

    def test_5_exam_arms_and_paired_analysis(self):
        c = run.run_exam(self.cfg, 'fake', 'frames_predict', evidence=EVIDENCE, harness_factory=self.factory,
                         log=lambda *_: None)
        self.assertEqual(c['failed'], 0)
        rows = run.Ledger(self.cfg.ledger('fake', 'frames_predict', 'exam'), ()).rows()
        arms = {r['evidence'] for r in rows}
        self.assertEqual(arms, set(EVIDENCE))
        law = [r for r in rows if r['evidence'] == 'law_text']
        self.assertTrue(law and all(r['source_world'] is None for r in law))
        law_calls = [c for h in self.harnesses for c in h.calls
                     if len(c['messages']) == 2 and 'governing law' in c['messages'][-1].content[0]['text']]
        self.assertTrue(law_calls and all(c['tools'] is None for c in law_calls))  # no history, no tools
        self.assertIn('coefficient field', law_calls[0]['messages'][-1].content[0]['text'])  # rule_2 law is stated
        sib = [r for r in rows if r['evidence'] == 'sibling']
        self.assertTrue(all(r['source_world'] != f"{r['group']}/{r['rule']}/{r['variant']}" for r in sib))
        own_rec = [r for r in rows if r['evidence'] == 'own_record']
        self.assertTrue(all(r['source_world'] == f"{r['group']}/{r['rule']}/{r['variant']}" for r in own_rec))
        # own_record and observations share the record format and differ only in the authorship framing.
        ep = run.load_episode(self.cfg, 'fake', 'frames_predict', tuple(own_rec[0]['source_world'].split('/')))
        a, b = (run.observation_record(episode.load(ep['messages']), arm) for arm in ('own_record', 'observations'))
        self.assertEqual(len(a), len(b))
        self.assertEqual(a[1].content[1:], b[1].content[1:])
        self.assertIn('your own', a[1].content[0]['text'])
        out = analysis.analyze(self.cfg, models=['fake'], modes=['frames_predict'], log=lambda *_: None)
        self.assertIn('fake|frames_predict', out['curves'])
        self.assertIn('fake|frames_predict|own-none', out['paired'])
        self.assertIn('fake|frames_predict|own_record-observations', out['paired'])
        told = {(r['group'], r['rule'], r['variant'], r['item']): r for r in rows if r['evidence'] == 'sibling_told'}
        for r in sib:  # same sibling history as the sibling arm; only the framing differs
            t = told[(r['group'], r['rule'], r['variant'], r['item'])]
            self.assertEqual((t['source_world'], t['sibling_answer']), (r['source_world'], r['sibling_answer']))
        self.assertIn('fake|frames_predict|sibling_told-none', out['paired'])
        self.assertIn('fake|frames_predict|law_text-own', out['paired'])

    def test_6_random_chooser_runs_assigned_experiment(self):
        c = run.run_episodes(self.cfg, 'fake', 'random_frames_predict', limit=1, harness_factory=self.factory,
                             log=lambda *_: None)
        self.assertEqual(c['complete'], 1)


if __name__ == '__main__':
    unittest.main()
