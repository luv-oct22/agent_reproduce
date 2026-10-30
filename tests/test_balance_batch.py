import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.objects.registry import ObjectRegistry
from src.objects.specimen import generate_specimens
from src.simulation.balance_batch import prepare_experiment, render_experiment
from src.simulation.balance_scene import prepare_bundle, IMAGES
from src.evaluation.visual import build_image_choice_content


class BalanceBatchTests(unittest.TestCase):
    def test_migration_preserves_assets_and_aggregate_paths_resolve(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = ObjectRegistry(tuple(generate_specimens(7))).save(root/'registry.json')
            out = root/'experiment'
            prepare_bundle(source, out)
            # A marker representing an existing rendered asset must survive byte-for-byte.
            (out/'context.png').write_bytes(b'original-render')
            with self.assertRaisesRegex(ValueError, 'migrate-flat'):
                prepare_experiment(source, out)
            batch = prepare_experiment(source, out, migrate_flat=True)
            self.assertEqual(len(batch['questions']), 6)
            first = out/batch['questions'][0]['folder']
            self.assertEqual((first/'context.png').read_bytes(), b'original-render')
            self.assertFalse((out/'scene.json').exists())
            self.assertEqual(len(json.loads((out/'questions.json').read_text())), 6)
            prepare_experiment(source, out)  # Idempotent, existing assets retained.
            self.assertEqual((first/'context.png').read_bytes(), b'original-render')
            for entry in batch['questions']:
                for image in IMAGES.values():
                    (out/entry['folder']/image).write_bytes(b'\x89PNG\r\n\x1a\nfixture')
            for q in json.loads((out/'questions.json').read_text()):
                parts = build_image_choice_content(q, out)
                self.assertEqual(sum(p['type'] == 'image_url' for p in parts), 5)
            with self.assertRaisesRegex(ValueError, 'settings changed'):
                prepare_experiment(source, out, volume_ml=80)

    def test_reversed_pairs_and_render_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = ObjectRegistry(tuple(generate_specimens(7))).save(root/'registry.json')
            out = root/'experiment'
            batch = prepare_experiment(source, out, include_reversed=True)
            self.assertEqual(len(batch['questions']), 12)
            self.assertEqual(len({(q['left'], q['right']) for q in batch['questions']}), 12)
            folder = out/batch['questions'][0]['folder']
            for image in IMAGES.values():
                (folder/image).write_bytes(b'\x89PNG\r\n\x1a\nfixture')
                (folder/f'{Path(image).stem}_parameters.md').write_text('record')
            (folder/'scene.blend').write_bytes(b'fixture')
            with patch('src.simulation.balance_batch.subprocess.run') as run:
                render_experiment(out, dry_run=True)
                run.assert_not_called()
                render_experiment(out)
                self.assertEqual(run.call_count, 11)
                for call in run.call_args_list:
                    command = call.args[0]
                    self.assertNotEqual(command[command.index('--manifest')+1], str(folder/'scene.json'))
                    self.assertTrue(call.kwargs['check'])
                run.reset_mock()
                render_experiment(out, rerender=True)
                self.assertEqual(run.call_count, 12)


if __name__ == '__main__':
    unittest.main()
