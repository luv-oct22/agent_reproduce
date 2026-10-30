"""Law-contrastive exam: item invariants, manifests, arms, ledger resume, analysis (no API)."""
import json
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from src.harness.types import ChatResponse
from src.law_contrastive import analysis, exam, items
from src.law_contrastive.config import REPO, ItemConfig, load_config
from src.simulation.attraction_visual import IMAGES, geometry


class FakeHarness:
    """Always answers `letter`; records the messages it received."""
    def __init__(self, letter):
        self.letter, self.calls = letter, []

    @property
    def model_name(self):
        return 'fake'

    def supports_tools(self):
        return False

    def generate(self, messages, tools=None, **kwargs):
        self.calls.append(messages)
        return ChatResponse(content=self.letter)


class LawContrastiveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cfg = load_config(REPO / 'configs/law_contrastive.yaml', groups=['g1'], rules=['rule_1'])
        cls.cfg = replace(cfg, items_dir=cls.tmp / 'items', renders_dir=cls.tmp / 'renders',
                          results_dir=cls.tmp / 'exam', items=ItemConfig(per_world=2, max_sampled_scenes=40))
        items.build(cls.cfg, log=lambda *_: None)
        items.export(cls.cfg, log=lambda *_: None)
        cls.items = list(items.load_items(cls.cfg))
        # Fake renders for the first two items so the exam can run.
        png = (REPO / 'renders/central_force_dynamics/central_force_dynamics_g1/rule_1/variant_1/q01/context.png').read_bytes()
        for item in cls.items[:2]:
            d = cls.cfg.item_renders(item['group'], item['rule'], item['id'])
            for name in IMAGES.values():
                (d / name).write_bytes(png)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_item_invariants(self):
        self.assertTrue(self.items)
        for it in self.items:
            laws = [c['law'] for c in it['choices'].values()]
            self.assertEqual(sorted(it['choices']), list('ABCD'))
            self.assertEqual(laws.count('canonical'), 1)
            self.assertEqual(len(set(laws)), 4)
            self.assertEqual(len(set(it['answers'].values())), 3)
            self.assertNotIn(it['canonical_label'], it['answers'].values())
            self.assertGreaterEqual(it['min_separation_px_1920'], self.cfg.items.min_separation_px)

    def test_manifest_passes_render_geometry(self):
        for it in self.items:
            m = json.loads((self.cfg.item_renders(it['group'], it['rule'], it['id']) / 'scene.json').read_text())
            geometry(m)
            self.assertEqual(m['initial_state']['payload']['objects']['probe']['position_m'], it['launch']['position_m'])

    def test_validation_checks_pass(self):
        out = items.validate(self.cfg, log=lambda *_: None)
        self.assertTrue(all(out['checks'].values()), out)

    def test_law_text_mentions_hidden_parameters(self):
        from src.law_contrastive.worlds import Worlds
        w = Worlds(self.cfg)
        text = exam.law_description(w.constants('g1', 'rule_1', 'variant_1'), w.hidden_law('g1', 'rule_1', 'variant_1'))
        self.assertIn('(r_ref/r)^2.7', text)

    def test_law_text_uses_simulator_constants(self):
        from dataclasses import replace as rep
        from src.law_contrastive.worlds import Worlds
        w = Worlds(rep(self.cfg, groups=('g1', 'g2', 'g3')))
        for g in ('g1', 'g2', 'g3'):
            sim, c = w.simulator(g, 'combined_rule', 'variant_1'), w.constants(g)
            self.assertEqual((c['strength_N'], c['reference_distance_m'], c['reference_mass_kg']),
                             (sim._strength, sim._r_ref, sim._m_ref))

    def test_exam_arms_ledger_and_analysis(self):
        cfg = self.cfg
        model = 'bailian/glm-5.3'   # has records in every g1 rule_1 world
        rendered = {it['id'] for it in self.items[:2]}
        n_rendered_q = sum(len(it['answers']) for it in self.items if it['id'] in rendered)
        fakes = {}
        def factory(letter):
            def make(m, out):
                fakes.setdefault(letter, FakeHarness(letter)); return fakes[letter]
            return make
        c = exam.run_exam(cfg, model, 'own', harness_factory=factory('A'), log=lambda *_: None)
        self.assertEqual(c['answered'], n_rendered_q)
        self.assertGreater(c['skipped_render'], 0)
        first = fakes['A'].calls[0]
        self.assertIn('prior interaction', first[1].content)            # history injected
        self.assertIn('later?', first[-1].content[0]['text'])            # elapsed time stated
        # Resume: nothing new is asked.
        again = exam.run_exam(cfg, model, 'own', harness_factory=factory('A'), log=lambda *_: None)
        self.assertEqual(again['answered'], 0)
        self.assertEqual(again['skipped_done'], n_rendered_q)
        exam.run_exam(cfg, model, 'no_history', harness_factory=factory('B'), log=lambda *_: None)
        self.assertNotIn('prior interaction', str(fakes['B'].calls[0][1].content))
        sib = exam.run_exam(cfg, model, 'sibling', harness_factory=factory('C'), log=lambda *_: None)
        self.assertEqual(sib['answered'], n_rendered_q)
        rows = exam.ledger_for(cfg, model, 'sibling').rows()
        self.assertTrue(all(r['history_world'] != r['variant'] for r in rows))
        out = analysis.analyze(cfg, log=lambda *_: None)
        self.assertIn(f'{model}|own', out['table1'])
        self.assertIn(f'{model}|own-no_history', out['paired'])
        expected = sum(r['answer'] == 'A' for r in exam.ledger_for(cfg, model, 'own').rows()) / n_rendered_q
        self.assertAlmostEqual(out['table1'][f'{model}|own']['acc'], expected)

    def test_failed_calls_are_retried(self):
        cfg = replace(self.cfg, results_dir=self.tmp / 'exam_fail')
        class Boom(FakeHarness):
            def generate(self, *a, **k):
                raise ConnectionError('down')
        c = exam.run_exam(cfg, 'bailian/glm-5.3', 'law_text', harness_factory=lambda m, o: Boom('A'), log=lambda *_: None)
        self.assertGreater(c['failed'], 0)
        c = exam.run_exam(cfg, 'bailian/glm-5.3', 'law_text', harness_factory=lambda m, o: FakeHarness('A'), log=lambda *_: None)
        self.assertEqual(c['skipped_done'], 0)
        self.assertGreater(c['answered'], 0)


if __name__ == '__main__':
    unittest.main()
