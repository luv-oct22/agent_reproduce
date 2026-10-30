import json
import math
from pathlib import Path
import tempfile
import unittest

from src.envs.bounce_lab import BounceLabEnv
from src.envs.bounce_lab.demo import run_demo
from src.tasks.identify_bounce import IdentifyBounceTask
from src.objects.registry import ObjectRegistry
from src.worlds.contact_registry import ContactRegistry
from src.interact import run_interaction


COEFFICIENTS = {'sample_A': .6, 'sample_B': .85, 'sample_C': .35, 'sample_D': .75}


def bounce(key='sample_A', height=1):
    return {'operation': 'bounce', 'specimen_id': key, 'surface_id': 'surface_1', 'release_height_m': height}


class BounceLabTests(unittest.TestCase):
    def test_public_initial_state_and_schemas_do_not_depend_on_hidden_physics(self):
        a = IdentifyBounceTask(BounceLabEnv(gravity_m_s2=3, restitution_by_specimen=COEFFICIENTS))
        b = IdentifyBounceTask(BounceLabEnv(gravity_m_s2=12, restitution_by_specimen={k: .1 for k in COEFFICIENTS}))
        self.assertEqual(a.get_prompt(), b.get_prompt())
        self.assertEqual(a.get_action_space(), b.get_action_space())
        self.assertEqual(a.env.observe(), b.env.observe())
        self.assertEqual(a.env.get_state(), b.env.get_state())
        self.assertEqual(a.env.get_object('sample_A'), b.env.get_object('sample_A'))
        self.assertTrue(all(o['shape'] == 'sphere' for o in a.env.objects.values()))
        reading = a.env.experiment(bounce())['observation']
        self.assertEqual(set(reading), {'instrument', 'specimen_id', 'surface_id', 'release_height_m',
                                       'release_from_rest', 'time_to_first_impact_s', 'first_rebound_height_m'})
        self.assertEqual(reading['time_to_first_impact_s'], .816)
        self.assertEqual(reading['first_rebound_height_m'], .36)

    def test_rebound_height_scaling_and_passive_endpoints(self):
        env = BounceLabEnv(restitution_by_specimen={'sample_A': 0, 'sample_B': 1, 'sample_C': .5, 'sample_D': .5})
        for key, expected in [('sample_A', 0), ('sample_B', 2), ('sample_C', .5), ('sample_D', .5)]:
            self.assertEqual(env.experiment(bounce(key, 2))['observation']['first_rebound_height_m'], expected)
        self.assertEqual(env.experiment(bounce('sample_C', 1))['observation']['first_rebound_height_m'], .25)
        self.assertEqual(env._contacts.impact_velocity('sample_C', [1, 2, -4]), [1, 2, 2])
        with self.assertRaises(ValueError):
            env._contacts.impact_velocity('sample_C', [0, 0, 4])

    def test_bad_actions_are_free_and_valid_instruments_share_budget(self):
        env = BounceLabEnv(max_experiments=2)
        invalid = [dict(bounce(), release_height_m=v) for v in (-1, 0, .049, 2.01, True, float('nan'), float('inf'), '1')]
        invalid += [dict(bounce(), specimen_id=[]), dict(bounce(), surface_id='other'), dict(bounce(), extra=3)]
        invalid += [{k: v for k, v in bounce().items() if k != 'surface_id'}]
        for action in invalid:
            self.assertFalse(env.experiment(action)['success'], action)
        self.assertEqual(env.observe()['experiments_used'], 0)
        result = env.experiment(bounce())
        result['observation']['first_rebound_height_m'] = 999
        self.assertNotEqual(env.observe()['notebook'][0]['first_rebound_height_m'], 999)
        self.assertTrue(env.experiment({'operation': 'drop', 'specimen_id': 'sample_A', 'distance_m': 1})['success'])
        self.assertFalse(env.experiment(bounce())['success'])
        self.assertTrue(env.experiment({'operation': 'inspect'})['success'])
        contacts_before = env.private_manifest()['contact_registry']
        env.reset()
        self.assertEqual(env.observe()['experiments_used'], 0)
        self.assertEqual(env.private_manifest()['contact_registry'], contacts_before)

    def test_record_reload_identity_and_no_conflicting_overwrite(self):
        env = BounceLabEnv(restitution_by_specimen=COEFFICIENTS)
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            IdentifyBounceTask(env).save_private_artifacts(directory)
            manifest = json.loads((directory/'private_manifest.json').read_text())
            restored = BounceLabEnv.from_private_manifest(manifest)
            loaded = BounceLabEnv(world_path=directory/'world.json', registry_path=directory/'object_registry.json',
                                  contact_registry_path=directory/'contact_registry.json')
            self.assertEqual(env.private_manifest(), restored.private_manifest())
            self.assertEqual(env.private_manifest(), loaded.private_manifest())
            self.assertEqual(env.experiment(bounce()), loaded.experiment(bounce()))
            before = {p.name: p.read_bytes() for p in directory.iterdir()}
            with self.assertRaises(FileExistsError):
                BounceLabEnv(restitution_by_specimen={k: .2 for k in COEFFICIENTS}).export_private_artifacts(directory)
            self.assertEqual(before, {p.name: p.read_bytes() for p in directory.iterdir()})
            with self.assertRaises(ValueError):
                BounceLabEnv(gravity_m_s2=9.81, contact_registry_path=directory/'contact_registry.json')
            data = json.loads((directory/'contact_registry.json').read_text())
            data['pairs'][0]['restitution'] = .1
            with self.assertRaises(ValueError):
                ContactRegistry.from_dict(data)
            registry = ObjectRegistry.load(directory/'object_registry.json')
            for obj in registry.specimens:
                private = obj.private_dict()
                self.assertAlmostEqual(4*math.pi*obj.radius_m**3/3, obj.volume_m3)
                self.assertEqual(private['geometry']['collision_shape'], 'sphere')
                self.assertAlmostEqual(private['physics']['inertia_diagonal_kg_m2'][0], .4*obj.mass_kg*obj.radius_m**2)

    def test_contact_config_validation(self):
        for value in (-.1, 1.1, True, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                BounceLabEnv(restitution_by_specimen=dict(COEFFICIENTS, sample_A=value))
        with self.assertRaises(ValueError):
            BounceLabEnv(restitution_by_specimen={'sample_A': .6})
        for value in (0, True, float('nan'), .1):
            with self.assertRaises(ValueError):
                BounceLabEnv(bounce_height_resolution_m=value)

    def test_submissions_atomic_not_an_oracle_and_score_without_materials(self):
        task = IdentifyBounceTask(BounceLabEnv(restitution_by_specimen=COEFFICIENTS))
        correct = [{'specimen_id': k, 'surface_id': 'surface_1', 'restitution': v} for k, v in COEFFICIENTS.items()]
        task.apply_action({'operation': 'submit_contact_estimates', 'estimates': correct})
        receipt = task.evaluate()
        wrong = [dict(item, restitution=.1) for item in correct]
        task.apply_action({'operation': 'submit_contact_estimates', 'estimates': wrong})
        self.assertEqual(receipt, task.evaluate())
        self.assertEqual(task.get_private_evaluation()['contact_score'], 0)
        invalid = [dict(correct[0]), dict(correct[1], restitution=True)]
        task.apply_action({'operation': 'submit_contact_estimates', 'estimates': invalid})
        self.assertFalse(task.evaluate()['success'])
        self.assertEqual(task.get_private_evaluation()['contact_score'], 0)
        task.apply_action({'operation': 'submit_contact_estimates', 'estimates': correct})
        task.apply_action({'operation': 'submit_world_estimate', 'gravity_m_s2': 3})
        evaluation = task.get_private_evaluation()
        self.assertEqual(evaluation['score'], 1)
        self.assertEqual(evaluation['material_score'], 0)
        task.setup()
        self.assertEqual(task.get_private_evaluation()['score'], 0)

    def test_reference_policy_recovers_different_worlds_using_measurements(self):
        for gravity in (3, 9, 12):
            task = IdentifyBounceTask(BounceLabEnv(gravity_m_s2=gravity, restitution_by_specimen=COEFFICIENTS))
            def submit(action):
                task.apply_action(action)
                return task.evaluate()
            run_demo(task.env.observe(), submit)
            self.assertEqual(task.get_private_evaluation()['score'], 1)
            self.assertEqual(task.env.observe()['experiments_used'], 8)

    def test_records_exist_before_first_model_request(self):
        with tempfile.TemporaryDirectory() as d:
            outer = self
            class FailingHarness:
                model_name = 'test-no-network'
                def generate(self, messages, tools=None):
                    for name in ('world.json', 'object_registry.json', 'contact_registry.json', 'parameters.md', 'task_parameters.md'):
                        outer.assertTrue((Path(d)/name).exists())
                    text = json.dumps([m.content for m in messages])
                    outer.assertNotIn('contact_registry', text)
                    raise RuntimeError('simulated transport failure')
            with self.assertRaisesRegex(RuntimeError, 'simulated transport failure'):
                run_interaction(IdentifyBounceTask(), 'identify_bounce', FailingHarness(), output_dir=d)
            self.assertTrue((Path(d)/'interaction.json').exists())


if __name__ == '__main__':
    unittest.main()
