from collections import Counter
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.objects.registry import ObjectRegistry
from src.objects.specimen import generate_specimens
from src.simulation.liquid_scene import equilibrium, build_liquid_manifest, build_liquid_question, prepare_liquid_batch, liquid_visual_settings
from src.simulation.balance_batch import render_experiment, question_complete


class LiquidSceneTests(unittest.TestCase):
    def setUp(self):
        self.registry = ObjectRegistry(tuple(generate_specimens(7)), seed=7)

    def test_archimedes_and_context_liquid_density_recovery(self):
        self.assertEqual(equilibrium(500, 1000), {'mode': 'floating', 'submerged_fraction': .5})
        self.assertEqual(equilibrium(1200, 1000), {'mode': 'bottom', 'submerged_fraction': 1})
        with self.assertRaisesRegex(ValueError, 'Neutral buoyancy'):
            equilibrium(1000, 1000)
        for index, density in enumerate((900, 1000, 1100, 1300, 1400, 1500, 1800, 2000)):
            scene = build_liquid_manifest(self.registry, density, index)
            state, obj = scene['context_states'][0], scene['context_objects'][0]
            self.assertEqual(state['mode'], 'floating')
            self.assertAlmostEqual(obj['density_kg_m3']/state['submerged_fraction'], density)

    def test_old_visual_renders_are_not_reused_after_surface_visibility_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = build_liquid_manifest(self.registry, 1000)
            (root/'scene.json').write_text(json.dumps(manifest))
            for filename in manifest['images'].values():
                (root/filename).write_bytes(b'\x89PNG\r\n\x1a\nfixture')
                (root/f'{Path(filename).stem}_parameters.md').write_text('record')
            (root/'scene.blend').write_bytes(b'fixture')
            (root/'scene_parameters.md').write_text('record')
            (root/'build_report.json').write_text(json.dumps({'images_rendered': True}))
            self.assertFalse(question_complete(root))
            (root/'build_report.json').write_text(json.dumps({
                'images_rendered': True, 'visual_settings': liquid_visual_settings(manifest)}))
            self.assertTrue(question_complete(root))

    def test_exactly_one_all_correct_frame_and_conserved_liquid_volume(self):
        scene = build_liquid_manifest(self.registry, 1000)
        expected = [equilibrium(obj['density_kg_m3'], 1000) for obj in scene['objects']]
        self.assertEqual([letter for letter, states in scene['choice_states'].items() if states == expected], [scene['answer']])
        area = scene['tank']['inner_side_m']**2
        initial_volume = area*scene['tank']['initial_liquid_depth_m']
        for key, frame in scene['frames'].items():
            self.assertAlmostEqual(area*frame['liquid_depth_m']-frame['displaced_volume_m3'], initial_volume)
            for obj in frame['objects']:
                bottom = obj['center_m'][2]-obj['side_length_m']/2
                if obj['mode'] == 'bottom':
                    self.assertAlmostEqual(bottom, scene['tank']['floor_z_m'])
                else:
                    fraction = (frame['surface_z_m']-bottom)/obj['side_length_m']
                    self.assertAlmostEqual(fraction, obj['submerged_fraction'])
                if key == scene['answer']:
                    buoyancy = 1000*9.81*obj['volume_m3']*obj['submerged_fraction']
                    weight = obj['mass_kg']*9.81
                    if obj['mode'] == 'floating':
                        self.assertAlmostEqual(buoyancy, weight)
                    else:
                        self.assertLess(buoyancy, weight)

    def test_question_no_identity_or_density_leak_and_renderer_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.registry.save(root/'registry.json')
            batch = prepare_liquid_batch(source, root/'liquid')
            questions = json.loads((root/'liquid/questions.json').read_text())
            self.assertEqual(Counter(q['answer'] for q in questions), dict(A=2, B=2, C=2, D=2))
            self.assertEqual(len({q['question'] for q in questions}), 1)
            for question in questions:
                text = question['question']
                for obj in self.registry.specimens:
                    self.assertNotIn(obj.specimen_id, text)
                    self.assertNotIn(' '+obj.color+' ', text)
                self.assertNotIn('before release', question['context_caption'])
                self.assertNotIn('kg', text)
            with patch('src.simulation.balance_batch.subprocess.run') as run:
                render_experiment(root/'liquid')
                self.assertEqual(run.call_count, 8)
                self.assertTrue(all(any('blender_liquid.py' in arg for arg in call.args[0]) for call in run.call_args_list))


if __name__ == '__main__':
    unittest.main()
