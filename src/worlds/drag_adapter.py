"""Expose legacy drag worlds through shared records without replacing their solver."""
import argparse
import json
from pathlib import Path

from src.envs.drag_lab import DragLabEnv
from src.tasks.identify_drag import IdentifyDragTask
from src.worlds.height_drag import HeightDragWorld
from src.worlds.definition import (
    ContactSpec, FieldSpec, LawSpec, ObjectSpec, ProtocolSpec, SolverSpec, WorldSpec, WorldInstance,
)


def from_drag_manifest(manifest, max_turns=None):
    env = DragLabEnv.from_private_manifest(manifest)
    task = IdentifyDragTask(env)
    world, ball = env._world, env._ball
    fields = [FieldSpec(dict(id='g', kind='constant', version=1, unit='m/s^2',
                            bounds=[world.gravity_m_s2, world.gravity_m_s2],
                            parameters={'value': world.gravity_m_s2}))]
    params = dict(surface_id=env._contacts.surface_id, extrapolation='constant_endpoints')
    if isinstance(world, HeightDragWorld):
        kind = 'smoothstep_height'
        params.update(heights_m=list(world.heights_m), values=list(world.coefficients_kg_s))
        solver = SolverSpec(dict(kind='height_drag_rk4', version=1, parameters={'max_step_s': world.max_step_s}))
    else:
        kind = 'layered_height'
        params.update(boundary_height_m=world.boundary_height_m,
                      lower_value=world.lower_drag_kg_s, upper_value=world.upper_drag_kg_s)
        solver = SolverSpec(dict(kind='layered_drag_exact', version=1, parameters={}))
    fields.append(FieldSpec(dict(id='b', kind=kind, version=1, unit='kg/s', bounds=[0., .5], parameters=params)))
    laws = [LawSpec(dict(id='gravity', kind='uniform_gravity', version=1,
                        parameters={'direction': [0., 0., -1.]}, fields={'acceleration': 'g'})),
            LawSpec(dict(id='drag', kind='linear_drag', version=1,
                         parameters={'medium_velocity_m_s': [0., 0., 0.]}, fields={'coefficient': 'b'}))]
    obj = ObjectSpec(dict(id=ball.specimen_id, color=ball.color, color_rgba=list(ball.color_rgba),
                          shape=ball.shape, mass_kg=ball.mass_kg, volume_m3=ball.volume_m3, motion='dynamic'))
    contact = ContactSpec(dict(id='floor_contact', kind='normal_restitution', version=1,
                               object_id=ball.specimen_id, surface_id=env._contacts.surface_id,
                               surface_z_m=0., restitution=env._contacts.restitution[0][1], tangential_friction=0.))
    spec = WorldSpec(dict(coordinate_frame='cartesian_z_up_m', motion_law='newton_second_law_v1',
                          laws=[r.to_dict() for r in laws], fields=[f.to_dict() for f in fields],
                          objects=[obj.to_dict()], contacts=[contact.to_dict()]))
    # This adapter records the existing disclosed-law protocol. It does not claim
    # the legacy drop/bounce menu is the future unguided common apparatus.
    protocol = ProtocolSpec(dict(id='legacy_drag', track='disclosed_law', instructions=task.get_prompt(),
        tools=[dict(name='submit_action', description='Perform an experiment or submit estimates for this task.',
                    parameters=task.get_action_space(),
                    measurements=[dict(name='time_to_first_impact_s', unit='s', resolution=env.clock_resolution_s, range=None),
                                  dict(name='first_rebound_height_m', unit='m', resolution=env.height_resolution_m, range=None)],
                    sample_definition='One valid drop or bounce trial, including all returned readings. '
                                      'Inspection, invalid actions and estimate submissions produce no charged samples.',
                    cost=dict(base_units=0, per_sample_units=1, per_simulated_second_units=0)),
               dict(name='finish', description='End the interaction.',
                    parameters={'type': 'object', 'properties': {}, 'additionalProperties': False},
                    measurements=[], sample_definition='No measurement samples.',
                    cost=dict(base_units=0, per_sample_units=0, per_simulated_second_units=0))],
        budget=dict(measurement_units=env.max_experiments, max_turns=max_turns),
        clock=dict(mode='resettable', start_time_s=0., time_range_s=None, reset_behavior='explicit_start_time'),
        disclosures=['laws.gravity', 'laws.drag', 'fields.g', 'contacts.floor_contact',
                     f'objects.{ball.specimen_id}.mass_kg', f'objects.{ball.specimen_id}.radius_m']))
    return WorldInstance(dict(world=spec.to_dict(), protocol=protocol.to_dict(), solver=solver.to_dict(),
                              provenance={'adapter': 'legacy_drag_v1', 'legacy_manifest': manifest}))


def restore_drag_env(instance):
    """Reject disagreement between shared contracts and the saved legacy physics."""
    data = instance.payload
    provenance = data['provenance']
    if provenance.get('adapter') != 'legacy_drag_v1':
        raise ValueError('This adapter only executes recorded legacy drag worlds.')
    expected = from_drag_manifest(provenance['legacy_manifest'],
                                  max_turns=data['protocol']['payload']['budget']['max_turns'])
    if expected != instance:
        raise ValueError('Shared records disagree with their legacy drag source.')
    return DragLabEnv.from_private_manifest(provenance['legacy_manifest'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', required=True, help='New host-only world instance JSON path.')
    parser.add_argument('--max-turns', type=int, help='Optional protocol limit; omit if not recorded.')
    args = parser.parse_args()
    instance = from_drag_manifest(json.loads(Path(args.manifest).read_text()), args.max_turns)
    restore_drag_env(instance)
    instance.save(args.output)
    print(f'Saved shared world record: {args.output}')
    print(f'Instance: {instance.record_id}; physics: {instance.payload["world"]["record_id"]}')


if __name__ == '__main__':
    main()
