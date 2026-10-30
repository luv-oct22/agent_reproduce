from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from src.envs.attraction_bench import AttractionBenchEnv
from src.evaluation.attraction_audit import (
    POLICIES, SCENES, audit_case, collect_evidence, fit_intervals, hypothesis,
    predict_position, run_audit, save_audit,
)
from src.worlds.attraction_setup import build_instance
from src.worlds.definition import ProtocolSpec, WorldInstance


def policy(name):
    return deepcopy(next(p for p in POLICIES if p['id'] == name))


class AttractionAuditTests(unittest.TestCase):
    def test_continuous_strength_intervals_include_truth_and_reject_other_exponent(self):
        for exponent in (2, 3):
            instance = build_instance(exponent)
            evidence = collect_evidence(instance, policy('two_distances'))
            intervals = fit_intervals(instance, evidence['observations'])
            self.assertEqual([i['exponent'] for i in intervals], [exponent])
            low, high = intervals[0]['strength_bounds_n']
            self.assertLess(low, 1.2)
            self.assertGreater(high, 1.2)
            self.assertAlmostEqual(low, 1.195, places=9)
            self.assertAlmostEqual(high, 1.205, places=9)
            self.assertEqual(evidence['units_used'], 2)
            self.assertEqual(evidence['turns_used'], 2)

    def test_fit_does_not_read_true_strength_or_exponent(self):
        evidence = collect_evidence(build_instance(2), policy('two_distances'))
        fits = [fit_intervals(build_instance(p, strength_n=a), evidence['observations'])
                for p, a in ((2, 0.), (2, 5.), (3, .03127), (3, 4.981))]
        self.assertTrue(all(f == fits[0] for f in fits))

    def test_repeated_measurements_spend_budget_but_do_not_shrink_deterministic_bins(self):
        instance = build_instance(2)
        single = collect_evidence(instance, policy('one_distance'))
        repeat = collect_evidence(instance, policy('repeat_one_distance_full_budget'))
        self.assertEqual(repeat['units_used'], 24)
        self.assertEqual(repeat['turns_used'], 8)
        self.assertEqual(fit_intervals(instance, single['observations']),
                         fit_intervals(instance, repeat['observations']))
        self.assertEqual(len(fit_intervals(instance, repeat['observations'])), 2)

    def test_zero_strength_remains_law_ambiguous(self):
        instance = build_instance(3, strength_n=0.)
        evidence = collect_evidence(instance, policy('four_distances'))
        intervals = fit_intervals(instance, evidence['observations'])
        self.assertEqual(len(intervals), 2)
        self.assertTrue(all(i['strength_bounds_n'][0] == 0 for i in intervals))

    def test_saturation_is_a_lower_bound_not_a_point_reading(self):
        instance = build_instance(3)
        evidence = collect_evidence(instance, policy('near_sensor_limit'))
        self.assertEqual(evidence['observations'][0]['reading']['value'][0], -10.)
        self.assertTrue(evidence['observations'][0]['reading']['saturated'][0])
        intervals = fit_intervals(instance, evidence['observations'])
        self.assertEqual([i['exponent'] for i in intervals], [2, 3])
        self.assertAlmostEqual(intervals[0]['strength_bounds_n'][0], 4.41, places=9)
        self.assertAlmostEqual(intervals[1]['strength_bounds_n'][0], .9261, places=9)
        self.assertTrue(all(i['strength_bounds_n'][1] == 5. for i in intervals))

    def test_unsaturated_limit_and_quantization_ties_are_conservative(self):
        instance = build_instance(2)
        evidence = collect_evidence(instance, policy('one_distance'))
        observations = evidence['observations']
        # -0.12 N corresponds to a strength interval with both guarded tie edges.
        intervals = fit_intervals(instance, observations)
        self.assertLess(intervals[0]['strength_bounds_n'][0], 1.195)
        self.assertGreater(intervals[0]['strength_bounds_n'][1], 1.205)
        observations[0]['separation_m'] = .21
        observations[0]['reading']['value'][0] = -10.
        interval = next(i for i in fit_intervals(instance, observations) if i['exponent'] == 3)
        self.assertLess(interval['strength_bounds_n'][1], .927)
        observations[0]['reading']['saturated'][0] = True
        interval = next(i for i in fit_intervals(instance, observations) if i['exponent'] == 3)
        self.assertEqual(interval['strength_bounds_n'][1], 5.)

    def test_inconsistent_measurements_leave_no_hypotheses(self):
        instance = build_instance(2)
        evidence = collect_evidence(instance, policy('one_distance'))
        contradictory = deepcopy(evidence['observations'][0])
        contradictory['reading']['value'][0] = -.2
        self.assertEqual(fit_intervals(instance, evidence['observations'] + [contradictory]), [])

    def test_policy_budget_limits_and_invalid_readings_fail_closed(self):
        instance = build_instance(2)
        over_turns = dict(id='bad', distances_m=[1.] * 9, repeats_per_distance=1)
        over_units = dict(id='bad', distances_m=[1.], repeats_per_distance=25)
        for bad in (over_turns, over_units):
            with self.assertRaises(ValueError):
                collect_evidence(instance, bad)
        evidence = collect_evidence(instance, policy('one_distance'))
        evidence['observations'][0]['reading']['value'][1] = .001
        with self.assertRaises(ValueError):
            fit_intervals(instance, evidence['observations'])

    def test_transfer_witnesses_replay_and_use_same_physics(self):
        instance = build_instance(2)
        case = audit_case(instance, policy('one_distance'), samples_per_interval=3)
        self.assertEqual(case['status'], 'law_ambiguous')
        self.assertGreater(max(r['sampled_diameter_m'] for r in case['transfer']['trajectory_checks']), .03)
        for witness in case['transfer']['witnesses']:
            candidate = hypothesis(instance, witness['exponent'], witness['strength_n'])
            replay = collect_evidence(candidate, case['evidence']['policy'])
            self.assertEqual(replay['transcript'], case['evidence']['transcript'])
            for scene in SCENES:
                self.assertEqual(predict_position(candidate, scene), witness['positions_m'][scene['id']])

    def test_public_catalog_is_unchanged_by_host_audit_and_replay_is_deterministic(self):
        instance = build_instance(3)
        before = AttractionBenchEnv(instance=instance).observe()
        first = audit_case(instance, policy('two_distances'), samples_per_interval=3)
        second = audit_case(instance, policy('two_distances'), samples_per_interval=3)
        self.assertEqual(first, second)
        self.assertEqual(before, AttractionBenchEnv(instance=instance).observe())
        self.assertEqual(first['status'], 'pass_within_audit_scope')
        self.assertTrue(all(r['max_step_halving_delta_m'] < 1e-6 for r in first['transfer']['trajectory_checks']))

    def test_pair_report_artifact_checksums_and_overwrite_protection(self):
        instances = [build_instance(p) for p in (2, 3)]
        report = run_audit(instances, samples_per_interval=3)
        self.assertTrue(report['passes_reference_audit'])
        self.assertTrue(report['public_interfaces_identical'])
        self.assertFalse(report['model_evaluated'])
        self.assertEqual(len(report['worlds'][0]['cases']), 6)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/'audit'
            save_audit(root, report, instances)
            self.assertEqual(json.loads((root/'audit.json').read_text()), report)
            self.assertEqual(WorldInstance.load(root/'world_1.json'), instances[0])
            for name, digest in json.loads((root/'checksums.json').read_text()).items():
                self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(), digest)
            with self.assertRaises(FileExistsError):
                save_audit(root, report, instances)

    def test_mismatched_public_protocol_rejected(self):
        instance = build_instance(3)
        data = instance.payload
        protocol = data['protocol']['payload']
        protocol['budget']['measurement_units'] = 20
        data['protocol'] = ProtocolSpec(protocol).to_dict()
        with self.assertRaises(ValueError):
            run_audit([build_instance(2), WorldInstance(data)], samples_per_interval=3)


if __name__ == '__main__':
    unittest.main()
