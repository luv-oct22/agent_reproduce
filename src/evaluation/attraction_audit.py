"""Offline host-only learnability audit; never an agent tool or model score."""
import argparse
from copy import deepcopy
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path

from src.envs.attraction_bench import APPARATUS_RULES, AttractionBenchEnv
from src.worlds.attraction import AttractionWorld, DomainError
from src.worlds.definition import FieldSpec, LawSpec, SolverSpec, WorldInstance, WorldSpec


VERSION = 'attraction_learnability_v1'
FORCE_SLACK_N = 1e-12
POSITION_TOLERANCE_M = .005
FORCE_TOLERANCE_N = .001

# Fixed before collecting either world's evidence. These policies are host
# controls, not instructions exposed by the evaluated agent's task.
POLICIES = [
    dict(id='no_measurements', distances_m=[], repeats_per_distance=1),
    dict(id='one_distance', distances_m=[1.], repeats_per_distance=1),
    dict(id='repeat_one_distance_full_budget', distances_m=[1.] * 8, repeats_per_distance=3),
    dict(id='two_distances', distances_m=[1., 2.], repeats_per_distance=1),
    dict(id='four_distances', distances_m=[.75, 1., 1.5, 2.], repeats_per_distance=1),
    dict(id='near_sensor_limit', distances_m=[.21], repeats_per_distance=1),
]

# Diagnostic transfer states, not a frozen image suite or answer-choice set.
SCENES = [
    dict(id='oblique_launch', position_m=[1.4, 0., 1.5], velocity_m_s=[0., .35, .6],
         start_time_s=3., duration_s=.45),
    dict(id='inward_launch', position_m=[1.8, 0., 1.5], velocity_m_s=[-.1, 0., .45],
         start_time_s=7., duration_s=.7),
]
HELD_OUT_DISTANCES_M = [1.3, 1.7]


def hypothesis(instance, exponent, strength_n, half_step=False):
    """Vary only the two searched quantities, preserving other saved physics."""
    data = instance.payload
    world = data['world']['payload']
    law = world['laws'][0]['payload']
    law['parameters']['exponent'] = exponent
    world['laws'][0] = LawSpec(law).to_dict()
    field = world['fields'][0]['payload']
    field['parameters']['value'] = strength_n
    world['fields'][0] = FieldSpec(field).to_dict()
    data['world'] = WorldSpec(world).to_dict()
    if half_step:
        solver = data['solver']['payload']
        solver['parameters']['max_step_s'] /= 2
        data['solver'] = SolverSpec(solver).to_dict()
    return WorldInstance(data)


def collect_evidence(instance, policy):
    """One configure + repeated readings per scripted turn, finish in last turn."""
    env = AttractionBenchEnv(instance=instance)
    distances, repeats = policy['distances_m'], policy['repeats_per_distance']
    if type(repeats) is not int or repeats < 1:
        raise ValueError('The repetition count must be a positive integer.')
    turns = max(1, len(distances))  # Even the no-measurement control calls finish.
    cap = env.protocol['budget']['max_turns']
    if cap is not None and turns > cap:
        raise ValueError('Reference policy exceeds the protocol turn budget.')
    observations, transcript = [], []

    def call(turn, name, arguments):
        result = env.execute(name, arguments)
        transcript.append(dict(turn=turn, tool=name, arguments=arguments, result=result))
        if not result['success']:
            raise ValueError(f'Reference policy failed: {name}: {result["error"]}')
        return result

    for turn, distance in enumerate(distances, 1):
        call(turn, 'configure_trial', dict(object_id='probe', position_m=[distance, 0., 1.5],
                                         velocity_m_s=[0., 0., 0.], start_time_s=0.))
        for _ in range(repeats):
            result = call(turn, 'measure_force', dict(object_id='probe'))
            observations.append(dict(separation_m=distance, reading=result['force']))
    call(turns, 'finish', {})
    return dict(policy=deepcopy(policy), turns_used=turns, units_used=env.units_used,
                observations=observations, transcript=transcript)


def coefficient(instance, exponent, distance):
    """Get force per unit strength from the authoritative engine, not a second solver."""
    bounds = instance.payload['world']['payload']['fields'][0]['payload']['bounds']
    if bounds[1] <= 0:
        raise ValueError('Audit requires a strength range with positive upper bound.')
    world = AttractionWorld(hypothesis(instance, exponent, bounds[1]))
    state = world.make_state({'anchor': [0., 0., 1.5], 'probe': [distance, 0., 1.5]})
    return -world.forces(state)['probe'][0] / bounds[1]


def fit_intervals(instance, observations):
    """Continuous, conservative strength bounds for each supported exponent.

    Closed sensor-bin edges plus a 1e-12 N guard include rounding ties and
    floating-point error. These outer bounds can retain marginal false matches;
    every sampled witness is subsequently replayed through the real sensor.
    """
    env = AttractionBenchEnv(instance=instance)
    sensor = next(t for t in env.protocol['tools'] if t['name'] == 'measure_force')['measurements'][0]
    bounds = instance.payload['world']['payload']['fields'][0]['payload']['bounds']
    intervals = []
    for exponent in (2, 3):
        low, high = bounds
        for observation in observations:
            reading = observation['reading']
            values, saturated = reading['value'], reading['saturated']
            if (reading['unit'] != sensor['unit'] or reading['resolution'] != sensor['resolution']
                    or len(values) != 3 or len(saturated) != 3
                    or not all(type(v) in (int, float) and math.isfinite(v) for v in values)
                    or not all(type(v) is bool for v in saturated)
                    or not sensor['range'][0] <= values[0] <= 0
                    or values[1:] != [0., 0.] or saturated[1:] != [False, False]):
                raise ValueError('Audit requires valid axial force readings from this apparatus.')
            magnitude = -values[0]
            if saturated[0]:
                if values[0] != sensor['range'][0]:
                    raise ValueError('Saturation must coincide with the sensor limit.')
                force_low, force_high = magnitude - FORCE_SLACK_N, math.inf
            else:
                force_low = max(0., magnitude - sensor['resolution']/2 - FORCE_SLACK_N)
                force_high = min(-sensor['range'][0], magnitude + sensor['resolution']/2) + FORCE_SLACK_N
            scale = coefficient(instance, exponent, observation['separation_m'])
            if not math.isfinite(scale) or scale <= 0:
                raise ValueError('Unsupported force scale for interval fitting.')
            low, high = max(low, force_low / scale), min(high, force_high / scale)
        if low <= high:
            intervals.append(dict(exponent=exponent, strength_bounds_n=[low, high]))
    return intervals


def predict_position(instance, scene):
    world = AttractionWorld(instance)
    initial = world.make_state({'anchor': [0., 0., 1.5], 'probe': scene['position_m']},
                               {'anchor': [0., 0., 0.], 'probe': scene['velocity_m_s']}, scene['start_time_s'])
    return world.advance(initial, scene['duration_s']).payload['objects']['probe']['position_m']


def assess_transfer(instance, evidence, intervals, samples_per_interval=17):
    if type(samples_per_interval) is not int or samples_per_interval < 3:
        raise ValueError('Use at least three deterministic strength samples per interval.')
    witnesses, rejected = [], 0
    for interval in intervals:
        low, high = interval['strength_bounds_n']
        strengths = sorted({min(high, max(low, low + (high-low)*k/(samples_per_interval-1)))
                            for k in range(samples_per_interval)})
        for strength in strengths:
            candidate = hypothesis(instance, interval['exponent'], strength)
            replay = collect_evidence(candidate, evidence['policy'])
            if replay['transcript'] != evidence['transcript']:
                rejected += 1
                continue
            positions, failures = {}, []
            for scene in SCENES:
                try:
                    positions[scene['id']] = predict_position(candidate, scene)
                except DomainError:
                    failures.append(scene['id'])
            witnesses.append(dict(exponent=interval['exponent'], strength_n=strength,
                                  instance_id=candidate.record_id, positions_m=positions,
                                  trajectory_failures=failures))
    trajectory_checks = []
    truth = instance.payload['world']['payload']
    true_exponent = truth['laws'][0]['payload']['parameters']['exponent']
    true_strength = truth['fields'][0]['payload']['parameters']['value']
    for scene in SCENES:
        truth_position = predict_position(instance, scene)
        valid = [i for i, w in enumerate(witnesses) if scene['id'] in w['positions_m']]
        pairs = [(math.dist(witnesses[i]['positions_m'][scene['id']], witnesses[j]['positions_m'][scene['id']]), i, j)
                 for i, j in combinations(valid, 2)]
        spread, first, second = max(pairs, default=(0., valid[0] if valid else None, valid[0] if valid else None))
        refined_truth = predict_position(hypothesis(instance, true_exponent, true_strength, half_step=True), scene)
        convergence = [math.dist(truth_position, refined_truth)]
        for index in {first, second} - {None}:
            w = witnesses[index]
            refined = predict_position(hypothesis(instance, w['exponent'], w['strength_n'], half_step=True), scene)
            convergence.append(math.dist(w['positions_m'][scene['id']], refined))
        complete = bool(valid) and len(valid) == len(witnesses)
        trajectory_checks.append(dict(scene_id=scene['id'], true_position_m=truth_position,
            sampled_diameter_m=spread, diameter_witness_indices=[first, second],
            all_sampled_trajectories_valid=complete, max_step_halving_delta_m=max(convergence),
            sampled_prediction_stable=complete and spread <= POSITION_TOLERANCE_M
                and max(convergence) <= POSITION_TOLERANCE_M/100))
    force_checks = []
    for distance in HELD_OUT_DISTANCES_M:
        ranges = []
        for interval in intervals:
            scale = coefficient(instance, interval['exponent'], distance)
            ranges.append(dict(exponent=interval['exponent'], magnitude_bounds_n=[
                a*scale for a in interval['strength_bounds_n']]))
        span = (max(r['magnitude_bounds_n'][1] for r in ranges)
                - min(r['magnitude_bounds_n'][0] for r in ranges)) if ranges else None
        force_checks.append(dict(separation_m=distance, continuous_magnitude_ranges=ranges,
                                 span_n=span, stable=span is not None and span <= FORCE_TOLERANCE_N))
    return dict(samples_per_interval=samples_per_interval, rejected_sensor_boundary_samples=rejected,
                witnesses=witnesses, trajectory_checks=trajectory_checks, force_checks=force_checks)


def audit_case(instance, policy, samples_per_interval=17):
    evidence = collect_evidence(instance, policy)
    intervals = fit_intervals(instance, evidence['observations'])
    transfer = assess_transfer(instance, evidence, intervals, samples_per_interval)
    world = instance.payload['world']['payload']
    exponent = world['laws'][0]['payload']['parameters']['exponent']
    strength = world['fields'][0]['payload']['parameters']['value']
    truth_included = any(i['exponent'] == exponent and i['strength_bounds_n'][0] <= strength <= i['strength_bounds_n'][1]
                         for i in intervals)
    if not truth_included or not transfer['witnesses']:
        status = 'audit_inconclusive'
    elif len(intervals) > 1:
        status = 'law_ambiguous'
    elif not all(r['sampled_prediction_stable'] for r in transfer['trajectory_checks']) or not all(
            r['stable'] for r in transfer['force_checks']):
        status = 'transfer_ambiguous_or_unresolved'
    else:
        status = 'pass_within_audit_scope'
    return dict(policy_id=policy['id'], status=status, truth_included=truth_included,
                evidence=evidence, compatible_intervals=intervals, transfer=transfer)


def run_audit(instances, samples_per_interval=17):
    if len(instances) < 2:
        raise ValueError('Provide at least two matched world instances.')
    for instance in instances:
        instances[0].require_same_public_interface(instance)
        if AttractionBenchEnv(instance=instances[0]).observe() != AttractionBenchEnv(instance=instance).observe():
            raise ValueError('Apparatus observations differ across matched worlds.')
    reports = []
    for instance in instances:
        cases = [audit_case(instance, policy, samples_per_interval) for policy in POLICIES]
        data = instance.payload['world']['payload']
        reports.append(dict(instance_id=instance.record_id, world_id=instance.payload['world']['record_id'],
                            host_truth=dict(exponent=data['laws'][0]['payload']['parameters']['exponent'],
                                            strength_n=data['fields'][0]['payload']['parameters']['value']),
                            cases=cases, passes_reference_audit=all(c['status'] == 'pass_within_audit_scope'
                                for c in cases if c['policy_id'] in ('two_distances', 'four_distances'))))
    source_root = Path(__file__).resolve().parents[1]
    source_paths = ['evaluation/attraction_audit.py', 'envs/attraction_bench.py',
                    'worlds/attraction.py', 'worlds/definition.py', 'worlds/attraction_setup.py']
    report = dict(format=VERSION, visibility='host_only', public_interfaces_identical=True,
        implementation_sha256={name: hashlib.sha256((source_root/name).read_bytes()).hexdigest()
                               for name in source_paths},
        model_evaluated=False, rendered=False, apparatus=APPARATUS_RULES,
        scope=dict(exponents=[2, 3], strength_search='continuous within each saved field bounds',
            search_space_visibility='Host audit prior; not disclosed to the agent.',
            varied_parameters=['exponent', 'constant strength'], other_physics='fixed to each saved instance',
            interval_method='Conservative closed quantization-bin inversion; no strength grid in fitting.',
            force_slack_n=FORCE_SLACK_N, position_tolerance_m=POSITION_TOLERANCE_M,
            force_tolerance_n=FORCE_TOLERANCE_N, samples_per_interval=samples_per_interval,
            limitations=['A host reference policy shows feasibility, not autonomous model discovery or task difficulty.',
                         'Only p=2/p=3 constant-strength hypotheses are searched; arbitrary laws are not excluded.',
                         'Trajectory spread is sampled, not a certified bound over continuous strength.',
                         'Diagnostic scenes are not an image suite; no visual shortcut or readability audit is implied.']),
        diagnostic_scenes=SCENES, held_out_force_distances_m=HELD_OUT_DISTANCES_M,
        worlds=reports, passes_reference_audit=all(r['passes_reference_audit'] for r in reports))
    return report


def markdown_report(report):
    lines = ['# Attraction learnability audit', '', '**Host-only feasibility diagnostic; not a model evaluation.**', '',
             'Continuous strength fitting searches p=2 and p=3. Trajectory checks sample the surviving intervals.', '',
             '| World | Policy | Units / turns | Surviving p | Maximum sampled position spread | Result |',
             '|---|---|---|---|---|---|']
    for index, world in enumerate(report['worlds'], 1):
        for case in world['cases']:
            evidence = case['evidence']
            spread = max(r['sampled_diameter_m'] for r in case['transfer']['trajectory_checks'])
            exponents = ', '.join(str(i['exponent']) for i in case['compatible_intervals']) or 'none'
            lines.append(f'| {index} (p={world["host_truth"]["exponent"]}) | {case["policy_id"]} '
                         f'| {evidence["units_used"]} / {evidence["turns_used"]} '
                         f'| {exponents} | {spread*1000:.3f} mm | {case["status"]} |')
    lines += ['', 'Position tolerance: 5 mm. Held-out force-span tolerance: 0.001 N.', '',
              '## Limits', ''] + ['- ' + line for line in report['scope']['limitations']]
    return '\n'.join(lines) + '\n'


def save_audit(directory, report, instances):
    root = Path(directory)
    # Refuse overwrites: each audit is a separate reproducible artifact bundle.
    root.mkdir(parents=True, exist_ok=False)
    outputs = {'audit.json': json.dumps(report, indent=2, allow_nan=False) + '\n',
               'report.md': markdown_report(report)}
    for index, instance in enumerate(instances, 1):
        outputs[f'world_{index}.json'] = json.dumps(instance.to_dict(), indent=2, allow_nan=False) + '\n'
    digests = {}
    for name, content in outputs.items():
        (root/name).write_text(content)
        digests[name] = hashlib.sha256(content.encode()).hexdigest()
    (root/'checksums.json').write_text(json.dumps(digests, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instances', nargs='+', default=[
        'world_instances/attraction_p2_v1/instance.json', 'world_instances/attraction_p3_v1/instance.json'])
    parser.add_argument('--output-dir', default='results/attraction_audit/attraction_pair_v1')
    parser.add_argument('--samples-per-interval', type=int, default=17)
    args = parser.parse_args()
    if Path(args.output_dir).exists():
        parser.error('Output directory already exists; choose a new audit directory.')
    instances = [WorldInstance.load(path) for path in args.instances]
    report = run_audit(instances, args.samples_per_interval)
    save_audit(args.output_dir, report, instances)
    print(markdown_report(report))
    print(f'ATTRACTION_AUDIT_RESULTS {args.output_dir}')
    if not report['passes_reference_audit']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
