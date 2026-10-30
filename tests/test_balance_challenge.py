from collections import Counter
import json
from pathlib import Path
import tempfile
import unittest

from src.envs.material_lab import MaterialLabEnv
from src.objects.registry import ObjectRegistry
from src.objects.specimen import generate_specimens
from src.simulation.balance_challenge import evidence_answer, prepare_challenge


class ChallengeTests(unittest.TestCase):
    def setUp(self):
        self.registry = ObjectRegistry(tuple(generate_specimens(7)), seed=7)
        self.known = {obj.specimen_id: obj for obj in self.registry.specimens}

    def test_unseen_materials_are_not_automatically_unknown(self):
        self.assertEqual(evidence_answer(['new'], ['sample_A'], self.known)[0], 'D')
        self.assertEqual(evidence_answer(['new', 'sample_C'], ['new', 'sample_A'], self.known)[0], 'A')
        self.assertEqual(evidence_answer(['new', 'sample_A'], ['new', 'sample_C'], self.known)[0], 'B')
        self.assertEqual(evidence_answer(['new', 'sample_A'], ['new', 'sample_A'], self.known)[0], 'C')
        self.assertEqual(evidence_answer(['new', 'sample_A'], ['sample_A'], self.known)[0], 'A')
        self.assertEqual(evidence_answer(['sample_A'], ['new', 'sample_A'], self.known)[0], 'B')
        self.assertEqual(evidence_answer(['new1'], ['new2'], self.known)[0], 'D')
        self.assertEqual(evidence_answer(['sample_A', 'sample_A'], ['sample_C'], self.known)[0], 'C')

    def test_generated_suite_balances_answers_and_keeps_unseen_objects_out_of_experiments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.registry.save(root/'source.json')
            batch = prepare_challenge(source, root/'hard')
            self.assertEqual(batch['answer_counts'], dict(A=8, B=8, C=8, D=8))
            self.assertEqual(Counter(e['category'] for e in batch['questions']),
                             dict(known_mass_sum=18, unseen_ambiguous=8, unseen_cancels=6))
            env = MaterialLabEnv(registry_path=root/'hard/object_registry.json')
            public = json.dumps(env.observe())
            extended = ObjectRegistry.load(root/'hard/evaluation_registry.json')
            unseen = [obj for obj in extended.specimens if obj.specimen_id not in self.known]
            self.assertEqual(len(unseen), 2)
            for obj in unseen:
                self.assertNotIn(obj.specimen_id, public)
                self.assertNotIn('"'+obj.color+'"', public)
            texts = set()
            for entry in batch['questions']:
                folder = root/'hard'/entry['folder']
                scene = json.loads((folder/'scene.json').read_text())
                question = json.loads((folder/'questions.json').read_text())[0]
                texts.add(question['question'])
                self.assertFalse(scene['show_specimen_labels'])
                for obj in extended.specimens:
                    self.assertNotIn(obj.specimen_id, question['question'])
                    self.assertNotIn(' '+obj.color+' ', question['question'])
                for side in ('left', 'right'):
                    objects = scene['objects'][side]
                    self.assertTrue(1 <= len(objects) <= 3)
                    for a, b in zip(objects, objects[1:]):
                        self.assertGreater(b['pan_offset_m'][0]-a['pan_offset_m'][0], a['side_length_m'])
                if scene['answer'] == 'D':
                    self.assertIn(scene['grading']['physical_answer'], 'ABC')
                else:
                    self.assertEqual(scene['answer'], scene['grading']['physical_answer'])
            self.assertEqual(len(texts), 1)  # No category/answer-specific prompt clues.
            with self.assertRaises(FileExistsError):
                prepare_challenge(source, root/'hard')


if __name__ == '__main__':
    unittest.main()
