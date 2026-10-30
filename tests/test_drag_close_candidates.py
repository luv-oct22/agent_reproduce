from collections import Counter
from copy import deepcopy
from itertools import combinations
import json
import math
from pathlib import Path
import random
import shutil
import tempfile
import unittest

from src.envs.drag_lab import DragLabEnv
from src.interact import InteractionRecord
from src.drag_evaluate import validate_inputs
from src.simulation.bounce_scene import IMAGES, scene_digest
from src.simulation.drag_scene import prepare_batch, frame_state, make_manifest
from src.simulation.drag_candidates import (
    CLOSE_POLICY, motion_phase, validate_candidate_geometry, validate_projected_candidates,
)
from src.worlds.height_drag import load_drag_world


class CloseDragTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        cls.root = Path(cls.work.name)
        env = DragLabEnv(profile_type='smooth_random', profile_seed=42)
        env.export_private_artifacts(cls.root/'source')
        InteractionRecord('identify_drag', 'offline').save(str(cls.root/'source/interaction.json'))
        cls.batch = prepare_batch(cls.root/'source', cls.root/'batch')
        cls.manifests = [json.loads((cls.root/'batch'/e['folder']/'scene.json').read_text())
                         for e in cls.batch['questions']]

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def test_every_pair_close_same_phase_and_exact_physics(self):
        self.assertEqual(Counter(m['answer'] for m in self.manifests), dict.fromkeys('ABCD', 2))
        self.assertEqual(Counter(m['truth_profile_rank'] for m in self.manifests), dict.fromkeys(range(4), 2))
        for m in self.manifests:
            validate_candidate_geometry(m)
            states = [f['objects'][0] for f in m['choices'].values()]
            self.assertEqual(len({motion_phase(s) for s in states}), 1)
            for a, b in combinations(states, 2):
                self.assertGreaterEqual(math.dist(a['position_m'], b['position_m']), .02)
                self.assertLessEqual(math.dist(a['position_m'], b['position_m']), .08)
            for frame in m['choices'].values():
                expected = frame_state(load_drag_world(frame['world']), m['objects'][0], m['elapsed_s'],
                                       frame['restitution'], m['surface_z_m'])
                self.assertEqual(expected, frame['objects'][0])
        audit = json.loads((self.root/'batch/candidate_audit.json').read_text())
        self.assertEqual(audit['baselines']['true_world']['correct'], 8)
        self.assertLessEqual(max(v['correct'] for k, v in audit['baselines'].items() if k != 'true_world'), 3)

    def test_constraints_reject_wide_identical_or_different_phase_choices(self):
        for mutation, error in [('wide', 'far apart'), ('identical', 'too similar'), ('phase', 'bounce count')]:
            m = deepcopy(self.manifests[0])
            a, b = [f['objects'][0] for f in list(m['choices'].values())[:2]]
            if mutation == 'wide':
                a['position_m'][0] += .5
            elif mutation == 'identical':
                a['position_m'] = b['position_m'][:]
            else:
                a['impacts'] += 1
            with self.assertRaisesRegex(ValueError, error):
                validate_candidate_geometry(m)

    def test_projection_readability(self):
        frames = {k: {'objects': [{'center_pixels': [10*i, 20]}]} for i, k in enumerate('ABCD')}
        validate_projected_candidates(self.manifests[0], frames)
        frames['B']['objects'][0]['center_pixels'] = [5, 20]
        with self.assertRaisesRegex(ValueError, '6 pixels'):
            validate_projected_candidates(self.manifests[0], frames)

    def test_two_layer_support_and_determinism(self):
        env = DragLabEnv()
        a = make_manifest(env, 0, 'C', random.Random(42), truth_rank=1)
        b = make_manifest(env, 0, 'C', random.Random(42), truth_rank=1)
        self.assertEqual(a, b)
        self.assertEqual(a['candidate_policy'], CLOSE_POLICY)
        validate_candidate_geometry(a)

    def test_expand_preserves_prefix_artifacts_and_balances_sixteen_questions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)/'batch'
            shutil.copytree(self.root/'batch', root)
            # Rendering adds actual settings to this file: extension must preserve them.
            (root/'questions/q001/scene_parameters.md').write_text('actual render settings')
            before = {p.relative_to(root): p.read_bytes() for p in root.glob('questions/*/*') if p.is_file()}
            batch = prepare_batch(self.root/'source', root, count=16)
            self.assertEqual(len(batch['questions']), 16)
            self.assertEqual(batch['questions'][:8], self.batch['questions'])
            for path, content in before.items():
                self.assertEqual((root/path).read_bytes(), content)
            manifests = [json.loads((root/e['folder']/'scene.json').read_text()) for e in batch['questions']]
            self.assertEqual(Counter(m['answer'] for m in manifests), dict.fromkeys('ABCD', 4))
            self.assertEqual(Counter(m['truth_profile_rank'] for m in manifests), dict.fromkeys(range(4), 4))
            self.assertEqual(len({m['objects'][0]['release_height_m'] for m in manifests}), 16)
            for m in manifests[8:]:
                validate_candidate_geometry(m)
                for frame in m['choices'].values():
                    self.assertEqual(frame['objects'][0], frame_state(load_drag_world(frame['world']),
                        m['objects'][0], m['elapsed_s'], frame['restitution'], m['surface_z_m']))
            self.assertEqual(len(json.loads((root/'questions.json').read_text())), 16)
            audit = json.loads((root/'candidate_audit.json').read_text())
            self.assertEqual(audit['baselines']['true_world']['correct'], 16)
            self.assertIn('16 questions', (root/'batch_parameters.md').read_text())
            self.assertEqual(prepare_batch(self.root/'source', root, count=16), batch)
            with self.assertRaises(FileExistsError):
                prepare_batch(self.root/'source', root, count=8)

    def test_reject_unsupported_count(self):
        with self.assertRaisesRegex(ValueError, '8 or 16'):
            prepare_batch(self.root/'source', self.root/'invalid', count=12)

    def test_evaluator_accepts_close_policy_and_checks_render_projection(self):
        # Fake image artifacts exercise validation without rendering or API calls.
        for entry, m in zip(self.batch['questions'], self.manifests):
            folder = self.root/'batch'/entry['folder']
            for filename in IMAGES.values():
                (folder/filename).write_bytes(b'\x89PNG\r\n\x1a\nfixture')
                (folder/(Path(filename).stem+'_parameters.md')).write_text('fixture')
            (folder/'scene.blend').write_bytes(b'fixture')
            frames = {k: {'objects': [{'center_pixels': [p*1920/4.6 for p in
                      (f['objects'][0]['position_m'][0], f['objects'][0]['position_m'][2])]}]}
                      for k, f in m['choices'].items()}
            (folder/'build_report.json').write_text(json.dumps(dict(images_rendered=True,
                scene_digest=scene_digest(m), frames=frames)))
        validate_inputs(self.root/'source/interaction.json', self.root/'batch')
        path = self.root/'batch'/self.batch['questions'][0]['folder']/'build_report.json'
        original = path.read_text()
        report = json.loads(original)
        report['frames']['A']['objects'][0]['center_pixels'] = report['frames']['B']['objects'][0]['center_pixels']
        try:
            path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, '6 pixels'):
                validate_inputs(self.root/'source/interaction.json', self.root/'batch')
        finally:
            path.write_text(original)


if __name__ == '__main__':
    unittest.main()
