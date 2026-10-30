import base64
import json
from pathlib import Path
import tempfile
import unittest

from src.evaluate import run_evaluation
from src.evaluation.visual import build_image_choice_content
from src.harness.types import ChatResponse
from src.interact import InteractionRecord
from src.objects.registry import ObjectRegistry
from src.objects.specimen import Specimen
from src.simulation.balance_scene import build_manifest, build_question, prepare_bundle


class DensityBalanceTests(unittest.TestCase):
    def setUp(self):
        # Original mass order is opposite to density order: equal-volume transfer matters.
        self.registry = ObjectRegistry((Specimen('A', .10, .0002, 'blue'),
                                        Specimen('B', .08, .00005, 'orange')))

    def test_equal_volume_transfer_preserves_density_identity_and_changes_mass(self):
        manifest = build_manifest(self.registry, 'A', 'B', 60)
        self.assertEqual(manifest['answer'], 'B')
        a, b = manifest['objects']['left'], manifest['objects']['right']
        self.assertAlmostEqual(a['mass_kg'], .03)
        self.assertAlmostEqual(b['mass_kg'], .096)
        self.assertEqual(a['volume_m3'], b['volume_m3'])
        self.assertEqual(a['shape'], 'cube')
        self.assertEqual(a['color_rgba'], list(self.registry.specimens[0].color_rgba))
        self.assertEqual(self.registry.specimens[0].mass_kg, .10)
        self.assertEqual(build_manifest(self.registry, 'B', 'A')['answer'], 'A')
        self.assertEqual(build_manifest(self.registry, 'A', 'A')['answer'], 'C')
        for volume in [0, -1, float('nan'), float('inf'), 1000]:
            with self.assertRaises(ValueError):
                build_manifest(self.registry, 'A', 'B', volume)

    def test_bundle_records_provenance_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.registry.save(root/'registry.json')
            out = root/'bundle'
            manifest = prepare_bundle(source, out, 'A', 'B')
            self.assertEqual(ObjectRegistry.load(out/'object_registry.json').registry_id, self.registry.registry_id)
            self.assertEqual(json.loads((out/'scene.json').read_text()), manifest)
            self.assertTrue((out/'parameters.md').is_file())
            self.assertFalse((out/'context.png').exists())
            self.assertNotIn('Expected choice', (out/'index.html').read_text())
            with self.assertRaises(FileExistsError):
                prepare_bundle(source, out, 'A', 'B')

    def test_multimodal_evaluation_sends_five_images_and_history_without_private_answer(self):
        question = build_question(build_manifest(self.registry, 'A', 'B'))
        question['private_sentinel'] = 'DO_NOT_SEND_THIS'
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ['context.png', 'choice_A.png', 'choice_B.png', 'choice_C.png', 'choice_D.png']:
                (root/name).write_bytes(png)
            questions = root/'questions.json'
            questions.write_text(json.dumps([question]))
            messages_seen = []
            class Harness:
                model_name = 'offline-vision-test'
                def generate(self, messages):
                    messages_seen.extend(messages)
                    return ChatResponse(content='B')
            history = InteractionRecord('identify_material', 'test',
                                        messages=[{'role': 'assistant', 'content': 'MEASURED_DENSITIES_FROM_EXPERIMENTS'}])
            record = run_evaluation('identify_material', Harness(), str(questions), history, output_dir=tmp)
            self.assertEqual(record.score, 1)
            self.assertTrue(record.with_history)
            content = messages_seen[-1].content
            self.assertEqual(sum(part['type'] == 'image_url' for part in content), 5)
            serialized = json.dumps([message.content for message in messages_seen])
            self.assertIn('MEASURED_DENSITIES_FROM_EXPERIMENTS', serialized)
            self.assertNotIn('DO_NOT_SEND_THIS', serialized)
            self.assertNotIn('"answer"', serialized)
            self.assertNotIn('source_mass_kg', serialized)
            self.assertNotIn('registry_id', serialized)
            self.assertNotIn('Left pan down', serialized)
            self.assertNotIn('Right pan down', serialized)
            for hidden_identity in ('blue', 'orange', 'made of the same material as A',
                                    'made of the same material as B'):
                self.assertNotIn(hidden_identity, serialized)
            self.assertTrue((root/'evaluation_with_history.json').is_file())
            (root/'choice_D.png').unlink()
            with self.assertRaisesRegex(FileNotFoundError, 'Render the balance bundle first'):
                build_image_choice_content(question, root)


if __name__ == '__main__':
    unittest.main()
