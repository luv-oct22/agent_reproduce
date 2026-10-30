from collections import Counter
from copy import deepcopy
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation.attraction_audit import run_audit, save_audit
from src.simulation.attraction_scene import (
    CAMERA, IMAGES, POLICY, digest, evidence_margin, geometry, initial_state,
    make_manifests, prepare, probe, projected, public_question, render_batch,
    shortcut_audit, simulate, validate_batch, validate_manifest, validate_projections,
    validate_render,
)
from src.worlds.attraction import MotionState
from src.worlds.attraction_setup import build_instance
from src.worlds.definition import WorldInstance


class AttractionSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        cls.root = Path(cls.work.name)
        cls.instances = [build_instance(p) for p in (2, 3)]
        cls.audit = run_audit(cls.instances, samples_per_interval=3)
        save_audit(cls.root/'audit', cls.audit, cls.instances)
        cls.batch = prepare(cls.root/'suite', cls.root/'audit')
        cls.manifests = [json.loads((cls.root/'suite'/e['folder']/'scene.json').read_text())
                         for e in cls.batch['questions']]

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def test_sixteen_paired_scenes_and_balanced_labels_and_ranks(self):
        self.assertEqual(len(self.manifests), 16)
        for a, b in zip(self.manifests[::2], self.manifests[1::2]):
            self.assertEqual(a['choices'], b['choices'])
            self.assertEqual(a['launch'], b['launch'])
            self.assertEqual(public_question(a), public_question(b))
            self.assertNotEqual(a['answer'], b['answer'])
            self.assertNotEqual(a['instance_id'], b['instance_id'])
        for index in (1, 2):
            group = [m for m in self.manifests if m['world_index'] == index]
            self.assertEqual(Counter(m['answer'] for m in group), Counter(dict.fromkeys('ABCD', 2)))
            self.assertEqual(Counter(m['truth_rank'] for m in group), Counter(dict.fromkeys(range(4), 2)))

    def test_all_choices_use_recorded_physics_and_remain_close(self):
        for m in self.manifests:
            instance = self.instances[m['world_index']-1]
            checks = validate_manifest(m, instance)
            self.assertLess(checks['max_step_halving_error_m'], 1e-7)
            positions = []
            for candidate in m['choices'].values():
                alternative = WorldInstance.from_dict(candidate['instance'])
                state = simulate(alternative, m['launch'])
                self.assertEqual(state.to_dict(), candidate['state'])
                positions.append(probe(state))
            for a, b in combinations(positions, 2):
                self.assertGreaterEqual(math.dist(a, b), .02)
                self.assertLessEqual(math.dist(a, b), .08)
            self.assertGreater(checks['minimum_separation_pixels'], 9.)

    def test_public_question_never_contains_law_or_answer_key(self):
        for m in self.manifests:
            text = json.dumps(public_question(m))
            for private in ('sha256:', 'exponent', 'strength', 'answer', 'truth_rank', 'world_index', 'hypothesis'):
                self.assertNotIn(private, text)
            self.assertIn(f'{m["launch"]["duration_s"]:.4f}', text)

    def test_measured_reference_uncertainty_keeps_unique_answer(self):
        for m in self.manifests:
            result = evidence_margin(m, self.instances[m['world_index']-1], self.audit)
            self.assertLess(result['maximum_truth_error_m'], .002)
            self.assertGreater(result['minimum_answer_margin_m'], .02)

    def test_shortcut_results_are_reported_honestly(self):
        audit = shortcut_audit(self.manifests)
        for name in ('nearest_initial', 'nearest_inertial', 'nearest_anchor', 'nearest_centroid'):
            self.assertEqual(audit['correct_equivalents'][name], 4)
        self.assertEqual(audit['correct_equivalents']['assume_p2_A1.2'], 8)
        self.assertEqual(audit['correct_equivalents']['assume_p3_A1.2'], 8)
        self.assertEqual(audit['image_only_pair_ceiling'], .5)

    def test_physics_tampering_wrong_answer_world_and_rank_rejected(self):
        for kind in ('position', 'answer', 'world', 'rank', 'mass'):
            m = deepcopy(self.manifests[0])
            if kind == 'position':
                c = m['choices']['A']
                d = c['state']['payload']
                d['objects']['probe']['position_m'][0] += .002
                c['state'] = MotionState(d).to_dict()
            elif kind == 'answer':
                m['answer'] = next(k for k in 'ABCD' if k != m['answer'])
            elif kind == 'world':
                m['instance_id'] = self.instances[1].record_id
            elif kind == 'rank':
                m['truth_rank'] = (m['truth_rank']+1) % 4
            else:
                m['objects'][0]['mass_kg'] *= 2
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                validate_manifest(m, self.instances[0])

    def test_geometry_rejects_wide_coincident_and_unreadable_candidates(self):
        for kind in ('wide', 'coincident', 'phase'):
            m = deepcopy(self.manifests[0])
            a, b = [m['choices'][k]['state']['payload']['objects']['probe'] for k in 'AB']
            if kind == 'wide':
                a['position_m'][0] += .5
            elif kind == 'coincident':
                a['position_m'] = b['position_m'][:]
            else:
                a['velocity_m_s'] = [-v for v in a['velocity_m_s']]
            with self.assertRaises(ValueError):
                geometry(m)
        with self.assertRaisesRegex(ValueError, 'pixels'):
            geometry(self.manifests[0], [640, 480])

    def test_projection_visibility_and_camera_match_checks(self):
        m = self.manifests[0]
        frames = self.frames(m)
        validate_projections(m, frames, CAMERA['resolution'])
        for kind in ('projection', 'visibility', 'size'):
            bad = deepcopy(frames)
            obj = bad['A']['objects']['probe']
            if kind == 'projection':
                obj['center_pixels'][0] += 1
            elif kind == 'visibility':
                obj['visible'] = False
            else:
                obj['diameter_pixels'] = 5
            with self.assertRaises(ValueError):
                validate_projections(m, bad, CAMERA['resolution'])

    @staticmethod
    def frames(m):
        result = {}
        for key in IMAGES:
            state = m['initial_state'] if key == 'context' else m['choices'][key]['state']
            result[key] = dict(objects={o['id']: dict(center_pixels=projected(state['payload']['objects'][o['id']]['position_m']),
                diameter_pixels=o['radius_m']*2*1920/5, visible=True) for o in m['objects']})
        return result

    def test_render_records_bind_images_and_do_not_accept_build_only(self):
        m = self.manifests[0]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hashes = {}
            # Minimal headers are fixtures for record validation, not rendered images.
            png = b'\x89PNG\r\n\x1a\n'+b'\x00\x00\x00\x0dIHDR'+struct.pack('>II', 1920, 1280)
            for key, name in IMAGES.items():
                (root/name).write_bytes(png)
                hashes[key] = hashlib.sha256(png).hexdigest()
                (root/(Path(name).stem+'_parameters.md')).write_text('fixture')
            (root/'scene.blend').write_bytes(b'fixture')
            report = dict(images_rendered=False, scene_digest=digest(m), frames=self.frames(m),
                          resolution=[1920, 1280], image_sha256=hashes)
            path = root/'build_report.json'
            path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, 'missing'):
                validate_render(root, m)
            report['images_rendered'] = True
            path.write_text(json.dumps(report))
            validate_render(root, m)
            (root/'choice_A.png').write_bytes(png+b'altered')
            with self.assertRaisesRegex(ValueError, 'bytes'):
                validate_render(root, m)

    def test_saved_batch_integrity_overwrite_and_dry_run(self):
        root = self.root/'suite'
        self.assertEqual(validate_batch(root), self.batch)
        with self.assertRaises(FileExistsError):
            prepare(root, self.root/'audit')
        with patch('src.simulation.attraction_scene.subprocess.run') as command:
            render_batch(root, dry_run=True)
            command.assert_not_called()
        path = root/'questions/q001/question.json'
        original = path.read_bytes()
        try:
            path.write_bytes(original+b' ')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                validate_batch(root)
        finally:
            path.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
