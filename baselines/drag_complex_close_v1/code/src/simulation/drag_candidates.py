"""Host-only constraints for close, physically simulated drag choices."""
from dataclasses import replace
from itertools import combinations
import math


CLOSE_POLICY = {
    'name': 'close_physics_v1',
    'minimum_separation_m': .02,
    'maximum_separation_m': .08,
    'minimum_separation_pixels': 6.,
    'same_motion_phase': True,
}


def motion_phase(state):
    vz = state['velocity_m_s'][2]
    return state['impacts'], 'up' if vz > 1e-5 else 'down' if vz < -1e-5 else 'rest'


def validate_candidate_geometry(manifest):
    """Validate bounds on EVERY pair, not just each distractor versus truth."""
    states = [f['objects'][0] for f in manifest['choices'].values()]
    distances = [math.dist(a['position_m'], b['position_m']) for a, b in combinations(states, 2)]
    policy = manifest.get('candidate_policy')
    if policy is None:  # Saved legacy batches remain evaluable.
        if min(distances) < .07:
            raise ValueError('Candidate images are too similar.')
        return
    if policy != CLOSE_POLICY:
        raise ValueError('Unsupported close candidate policy.')
    if not all(math.isfinite(d) for d in distances):
        raise ValueError('Non-finite candidate geometry.')
    if min(distances) < policy['minimum_separation_m'] - 1e-10:
        raise ValueError('Close candidates are too similar to distinguish.')
    if max(distances) > policy['maximum_separation_m'] + 1e-10:
        raise ValueError('Close candidates are too far apart.')
    if len({motion_phase(s) for s in states}) != 1:
        raise ValueError('Close candidates must share bounce count and motion direction.')


def validate_projected_candidates(manifest, frames):
    """Use actual Blender camera projections, including the chosen resolution."""
    if 'candidate_policy' not in manifest:
        return
    points = [frames[k]['objects'][0]['center_pixels'] for k in 'ABCD']
    minimum = min(math.dist(a, b) for a, b in combinations(points, 2))
    if not math.isfinite(minimum) or minimum < CLOSE_POLICY['minimum_separation_pixels']:
        raise ValueError('Candidate centres are less than 6 pixels apart; increase render resolution.')


def perturb_world(world, offset, direction):
    """Change a complete drag law; never displace a rendered sphere by hand."""
    from src.worlds.height_drag import HeightDragWorld
    if isinstance(world, HeightDragWorld):
        values = tuple(v*(1 + offset*d) for v, d in zip(world.coefficients_kg_s, direction))
        if any(not 0 <= v <= .5 for v in values):
            return None
        return replace(world, coefficients_kg_s=values, generation_seed=None)
    values = [v*(1 + offset*d) for v, d in zip((world.lower_drag_kg_s, world.upper_drag_kg_s), direction)]
    if any(not 0 <= v <= .5 for v in values):
        return None
    return replace(world, lower_drag_kg_s=values[0], upper_drag_kg_s=values[1])


def close_frames(world, obj, restitution, floor, window, truth_rank, rng, frame_state):
    """Pick a valid nearby cluster without consulting any model's predictions.

    The true law occupies a balanced, shuffled rank among four locally perturbed
    laws, so it is not systematically the middle or an extreme option.
    """
    count = len(world.coefficients_kg_s) if hasattr(world, 'coefficients_kg_s') else 2
    ticks = list(range(math.ceil(window[0]*100), math.floor(window[1]*100)+1, 2))
    rng.shuffle(ticks)
    for tick in ticks:
        elapsed = tick/100
        truth = dict(hypothesis='recorded_physics', world=world.to_dict(), restitution=restitution,
                     objects=[frame_state(world, obj, elapsed, restitution, floor)])
        direction = [rng.uniform(.5, 1.5) for _ in range(count)]
        step = .02
        for _ in range(12):
            frames = [truth]
            for rank in range(4):
                if rank == truth_rank:
                    continue
                candidate = perturb_world(world, (rank-truth_rank)*step, direction)
                if candidate is None:
                    break
                frames.append(dict(hypothesis=f'local_profile_{rank}', world=candidate.to_dict(),
                                   restitution=restitution,
                                   objects=[frame_state(candidate, obj, elapsed, restitution, floor)]))
            if len(frames) != 4:
                break
            points = [f['objects'][0]['position_m'] for f in frames]
            distances = [math.dist(a, b) for a, b in combinations(points, 2)]
            separation = min(distances)
            if separation < 1e-10:
                break
            if .02 <= separation and max(distances) <= .08:
                if (len({motion_phase(f['objects'][0]) for f in frames}) == 1
                        and all(-2 < p[0] < 2 and floor+obj['radius_m'] <= p[2] <= floor+2.55 for p in points)):
                    return separation, elapsed, frames
                break
            # Target 2.2 cm between neighbours, leaving room for curvature.
            step *= max(.5, min(2., .022/separation))
    raise ValueError('Cannot construct four same-phase candidates 2–8 cm apart; choose a new seed/world.')
