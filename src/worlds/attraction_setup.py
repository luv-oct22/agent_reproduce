"""Prepare two matched attraction-world records and offline physics previews."""
import argparse
import json
import math
from pathlib import Path

from src.worlds.attraction import AttractionWorld
from src.worlds.definition import FieldSpec, LawSpec, ObjectSpec, ProtocolSpec, SolverSpec, WorldSpec, WorldInstance


def bench_protocol():
    """Immutable shared tool specifications executed by AttractionBenchEnv."""
    vec = dict(type='array', items={'type': 'number'}, minItems=3, maxItems=3)
    specimen = {'type': 'string', 'enum': ['probe']}

    def tool(name, description, properties, required, measurements=(), base=0, sample=0):
        return dict(name=name, description=description,
                    parameters=dict(type='object', properties=properties, required=required, additionalProperties=False),
                    measurements=list(measurements), sample_definition='One recorded vector observation is one sample.',
                    cost=dict(base_units=base, per_sample_units=sample, per_simulated_second_units=0))

    tools = [
        tool('inspect', 'Read visible objects, apparatus calibration and current trial settings.', {}, []),
        tool('configure_trial', 'Set a movable specimen position and velocity and an absolute trial start time.',
             dict(object_id=specimen, position_m=vec, velocity_m_s=vec,
                  start_time_s={'type': 'number', 'minimum': 0, 'maximum': 30}),
             ['object_id', 'position_m', 'velocity_m_s', 'start_time_s']),
        tool('apply_impulse', 'Apply a calibrated impulse vector to a movable specimen.',
             dict(object_id=specimen, impulse_N_s=vec), ['object_id', 'impulse_N_s'], base=1),
        tool('measure_force', 'Read the external force vector on a held specimen in laboratory axes.',
             dict(object_id={'type': 'string', 'enum': ['anchor', 'probe']}), ['object_id'],
             [dict(name='force', unit='N', resolution=.001, range=[-10., 10.])], sample=1),
        tool('track_motion', 'Record specimen positions at equally spaced times over a duration.',
             dict(object_id=specimen, duration_s={'type': 'number', 'exclusiveMinimum': 0, 'maximum': 3},
                  sample_count={'type': 'integer', 'minimum': 1, 'maximum': 24}),
             ['object_id', 'duration_s', 'sample_count'],
             [dict(name='position', unit='m', resolution=.001, range=[-5., 5.])], sample=1),
        tool('finish', 'End the interaction when ready for subsequent prediction tasks.', {}, []),
    ]
    return ProtocolSpec(dict(id='common_bench_v1', track='law_discovery',
        instructions='You are in an unfamiliar physical environment. Choose your own experiments within the '
        'stated budget to gather evidence for later prediction tasks. Physical behavior may differ from familiar '
        'laws. Colors identify objects. Calibrated masses and radii are provided. The orange anchor remains fixed '
        'during each trial. Keep object centres more than 0.20 m apart. Trials use explicit start times; '
        'tool descriptions specify controls, measurement limits and costs.',
        tools=tools, budget=dict(measurement_units=24, max_turns=8),
        clock=dict(mode='resettable', start_time_s=0., time_range_s=[0., 30.], reset_behavior='explicit_start_time'),
        disclosures=['objects.anchor.mass_kg', 'objects.anchor.radius_m',
                     'objects.probe.mass_kg', 'objects.probe.radius_m']))


def build_instance(exponent, strength_n=1.2, max_step_s=.002):
    field = FieldSpec(dict(id='strength', kind='constant', version=1, unit='N',
                          bounds=[0., 5.], parameters={'value': strength_n}))
    law = LawSpec(dict(id='interaction', kind='central_attraction', version=1,
        fields={'strength': 'strength'}, parameters=dict(exponent=exponent, reference_distance_m=1.,
        reference_mass_kg=1., minimum_distance_m=.2, coefficient_sample='pair_midpoint', mass_coupling='inertial_mass')))
    objects = [ObjectSpec(dict(id=name, color=color, color_rgba=rgba, shape='sphere', mass_kg=mass,
                              volume_m3=4*math.pi*radius**3/3, motion=motion))
               for name, color, rgba, mass, radius, motion in (
                   ('anchor', 'orange', [1., .35, .05, 1.], 1., .08, 'fixed'),
                   ('probe', 'blue', [.08, .35, .8, 1.], .1, .03, 'dynamic'))]
    world = WorldSpec(dict(coordinate_frame='cartesian_z_up_m', motion_law='newton_second_law_v1',
                          laws=[law.to_dict()], fields=[field.to_dict()],
                          objects=[o.to_dict() for o in objects], contacts=[]))
    solver = SolverSpec(dict(kind='central_attraction_rk4', version=1,
        parameters=dict(max_step_s=max_step_s, min_step_s=1e-8, max_steps=200000)))
    instance = WorldInstance(dict(world=world.to_dict(), protocol=bench_protocol().to_dict(), solver=solver.to_dict(),
                                   provenance={'authoring_version': 'attraction_pair_v1'}))
    AttractionWorld(instance)  # Reject metadata unsupported by the actual runtime.
    return instance


def prepare_pair(output_dir, strength_n=1.2):
    root = Path(output_dir)
    instances = [build_instance(p, strength_n) for p in (2, 3)]
    instances[0].require_same_public_interface(instances[1])
    outputs, entries = {}, []
    for p, instance in zip((2, 3), instances):
        folder = f'attraction_p{p}_v1'
        world = AttractionWorld(instance)
        initial = world.make_state({'anchor': [0., 0., 1.5], 'probe': [1.25, 0., 1.5]},
                                   {'anchor': [0., 0., 0.], 'probe': [0., 0., .8]})
        frames = world.trajectory(initial, [0., .25, .5, .75])
        probes = []
        for distance in (.8, 1., 1.5, 2.):
            state = world.make_state({'anchor': [0., 0., 0.], 'probe': [distance, 0., 0.]})
            probes.append(dict(separation_m=distance, force_on_probe_n=world.forces(state)['probe']))
        preview = dict(visibility='host_only', kind='physics_preview_not_model_evaluation',
                       world_id=world.world_id, initial_state=initial.to_dict(),
                       frames=[f.to_dict() for f in frames], force_probes=probes,
                       diagnostics=[world.diagnostics(f) for f in frames])
        outputs[root/folder/'instance.json'] = instance.to_dict()
        outputs[root/folder/'preview.json'] = preview
        entries.append(dict(folder=folder, instance_id=instance.record_id, world_id=world.world_id))
    outputs[root/'attraction_pair_v1.json'] = dict(format='matched_attraction_pair', schema_version=1,
        visibility='host_only', public_interfaces_identical=True, worlds=entries,
        apparatus_implemented=False, rendered=False, model_evaluated=False)
    # Validate the entire bundle before writing; never partially overwrite another world.
    for path, value in outputs.items():
        if path.exists() and json.loads(path.read_text()) != value:
            raise FileExistsError(f'Different artifact already exists: {path}. Choose a new output directory.')
    for path, value in outputs.items():
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('x') as stream:
                json.dump(value, stream, indent=2, allow_nan=False)
                stream.write('\n')
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', default='world_instances')
    parser.add_argument('--strength-n', type=float, default=1.2)
    args = parser.parse_args()
    entries = prepare_pair(args.output_dir, args.strength_n)
    print(f'Prepared {len(entries)} matched physical worlds in {args.output_dir}.')
    print('Offline force/trajectory previews only; no apparatus execution, rendering or model calls.')


if __name__ == '__main__':
    main()
