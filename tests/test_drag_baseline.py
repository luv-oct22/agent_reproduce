import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation.drag_baseline import freeze, inventory, verify_integrity


class DragBaselineTests(unittest.TestCase):
    def test_integrity_rejects_changed_missing_and_extra_files(self):
        for mutation in ('changed', 'missing', 'extra'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                artifact = root/'scene.json'
                artifact.write_text('{"elapsed_s": 1.2}')
                (root/'baseline.json').write_text(json.dumps({'files': inventory(root)}))
                verify_integrity(root)
                if mutation == 'changed':
                    artifact.write_text('{"elapsed_s": 1.3}')
                elif mutation == 'missing':
                    artifact.unlink()
                else:
                    (root/'extra.json').write_text('{}')
                with self.assertRaisesRegex(ValueError, 'missing, added or changed'):
                    verify_integrity(root)

    def test_freeze_never_overwrites_existing_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root/'keep.txt'
            marker.write_text('existing baseline')
            with patch('src.evaluation.drag_baseline.validate_inputs') as validate:
                with self.assertRaises(FileExistsError):
                    freeze(root/'unused', root)
                validate.assert_not_called()
            self.assertEqual(marker.read_text(), 'existing baseline')


if __name__ == '__main__':
    unittest.main()
