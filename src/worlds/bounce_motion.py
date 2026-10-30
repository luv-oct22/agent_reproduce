"""Exact free flight and repeated impacts on a stationary horizontal plane."""
import math


def advance_bouncing(world, contacts, specimen_id, position_m, velocity_m_s, elapsed_s,
                     radius_m, surface_z_m):
    # Reuse validation and free flight from the experiment's world definition.
    free = world.advance(position_m, velocity_m_s, elapsed_s)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
           for v in (radius_m, surface_z_m)) or radius_m <= 0:
        raise ValueError('Invalid sphere or surface geometry.')
    floor = surface_z_m+radius_m
    height = position_m[2]-floor
    if height < -1e-12:
        raise ValueError('Sphere starts inside the impact surface.')
    height = max(height, 0)
    g, vz = world.gravity_m_s2, velocity_m_s[2]
    speed = math.sqrt(vz*vz+2*g*height)
    # Stable positive root, including upward launches from the surface.
    first = 2*height/(speed-vz) if vz < 0 and height else (vz+speed)/g
    e = dict(contacts.restitution)[specimen_id]
    if elapsed_s < first:
        return dict(free, impacts=0, settled=False)
    outgoing = contacts.impact_velocity(specimen_id, [velocity_m_s[0], velocity_m_s[1], -speed])
    up = outgoing[2]
    after = elapsed_s-first
    horizontal = [position_m[i]+velocity_m_s[i]*elapsed_s for i in (0, 1)]
    def resting(impacts):
        return {'position_m': [*horizontal, floor], 'velocity_m_s': [*velocity_m_s[:2], 0.0],
                'impacts': impacts, 'settled': True}
    if up == 0:
        return resting(1 if speed else 0)
    duration = 2*up/g
    if e == 1:
        completed = int(after//duration)
        phase = after-completed*duration
    else:
        limit = duration/(1-e)
        if after >= limit:
            return resting(None)  # Infinite ideal impacts have reached their finite-time limit.
        completed = max(0, int(math.floor(math.log1p(-after/limit)/math.log(e))))
        start = limit*(-math.expm1(completed*math.log(e)))
        phase = max(0.0, after-start)
        up *= e**completed
    vertical = world.advance([0, 0, floor], [0, 0, up], phase)
    return {'position_m': [*horizontal, max(floor, vertical['position_m'][2])],
            'velocity_m_s': [*velocity_m_s[:2], vertical['velocity_m_s'][2]],
            'impacts': completed+1, 'settled': False}
