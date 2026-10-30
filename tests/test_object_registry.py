from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.envs.material_lab import MaterialLabEnv
from src.harness.base import ModelHarness
from src.interact import run_interaction
from src.objects.registry import ObjectRegistry
from src.objects.specimen import Specimen
from src.tasks.identify_material import IdentifyMaterialTask


class ObjectRegistryTests(unittest.TestCase):
    def test_geometry_matches_mass_volume_and_uniform_cube_inertia(self):
        specimen = Specimen('sample', .08, .000125, 'blue')
        data = specimen.private_dict()
        self.assertAlmostEqual(data['geometry']['dimensions_m'][0], .05)
        self.assertAlmostEqual(data['density_kg_m3'], 640)
        self.assertEqual(data['geometry']['collision_shape'], 'box')
        self.assertAlmostEqual(data['physics']['inertia_diagonal_kg_m2'][0], .08*.05**2/6)
        self.assertFalse(data['physics']['absorbs_water'])
        self.assertNotIn('geometry', specimen.public_dict())
        with self.assertRaises(FrozenInstanceError):
            specimen.mass_kg = .1

    def test_registry_round_trip_preserves_every_object_field(self):
        specimen = Specimen('custom', .04, .00008, 'custom color', color_rgba=(.2, .3, .4, 1))
        original = ObjectRegistry((specimen,), seed=9)
        with tempfile.TemporaryDirectory() as directory:
            path = original.save(Path(directory)/'object_registry.json')
            restored = ObjectRegistry.load(path)
        self.assertEqual(restored.to_dict(), original.to_dict())
        self.assertEqual(restored.specimens, original.specimens)
        self.assertEqual(restored.registry_id, original.registry_id)
        objects = restored.simulation_objects()
        objects[0]['mass_kg'] = 100
        self.assertEqual(restored.specimens[0].mass_kg, .04)

    def test_conflicting_density_dimensions_and_changed_identity_are_rejected(self):
        original = ObjectRegistry((Specimen('A', .04, .00008, 'blue'),)).to_dict()
        mutations = [lambda d: d['objects'][0].update(density_kg_m3=900),
                     lambda d: d['objects'][0]['geometry']['dimensions_m'].__setitem__(0, .5),
                     lambda d: d.update(registry_id='sha256:wrong'),
                     lambda d: d['units'].update(mass='g')]
        for mutate in mutations:
            data = deepcopy(original)
            mutate(data)
            with self.assertRaises(ValueError):
                ObjectRegistry.from_dict(data)

    def test_conflicting_registry_cannot_overwrite_a_run(self):
        first = ObjectRegistry((Specimen('A', .04, .00008, 'blue'),))
        second = ObjectRegistry((Specimen('A', .08, .00008, 'blue'),))
        with tempfile.TemporaryDirectory() as directory:
            path = first.save(Path(directory)/'object_registry.json')
            before = path.read_bytes()
            first.save(path)
            with self.assertRaises(FileExistsError):
                second.save(path)
            self.assertEqual(path.read_bytes(), before)

    def test_loading_environment_registry_never_regenerates_objects(self):
        original = MaterialLabEnv(seed=17)
        with tempfile.TemporaryDirectory() as directory:
            original.export_private_artifacts(directory)
            with patch('src.envs.material_lab.scene.generate_specimens', side_effect=AssertionError('Must not resample')):
                restored = MaterialLabEnv(seed=999, registry_path=Path(directory)/'object_registry.json')
            self.assertEqual(restored.private_manifest(), original.private_manifest())
            self.assertEqual(restored.observe(), original.observe())
            self.assertTrue((Path(directory)/'object_registry.md').is_file())

    def test_registry_is_saved_before_model_call_and_survives_failure(self):
        task = IdentifyMaterialTask(MaterialLabEnv(seed=23))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            class FailingHarness(ModelHarness):
                model_name = 'offline-failure-test'

                def generate(self, messages, tools=None, **kwargs):
                    if not (root/'object_registry.json').is_file() or not (root/'private_manifest.json').is_file():
                        raise AssertionError('Registry must exist before the first model request')
                    serialized = json.dumps([message.content for message in messages])
                    if 'registry_id' in serialized or 'inertia_diagonal' in serialized or 'volume_m3' in serialized:
                        raise AssertionError('Private object metadata leaked to the model')
                    raise RuntimeError('Simulated model connection failure')
            with self.assertRaisesRegex(RuntimeError, 'Simulated model connection failure'):
                run_interaction(task, 'identify_material', FailingHarness(), output_dir=directory)
            saved = ObjectRegistry.load(root/'object_registry.json')
            self.assertEqual(saved.registry_id, task.env.private_manifest()['object_registry_id'])


if __name__ == '__main__':
    unittest.main()
