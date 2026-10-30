"""Cup body geometry shared by the contact solver and Blender lathe mesh."""
import math


WALL_THICKNESS = 0.008
BOTTOM_THICKNESS = 0.012


def cup_profile(radius, height):
    """Counterclockwise solid cross-section in (radial distance, rim-relative Z)."""
    outer = radius + WALL_THICKNESS
    return [(0, -height), (outer-0.008, -height), (outer, -height+0.008),
            (outer, -0.009), (outer-0.002, 0), (radius, 0),
            (radius, -0.012), (radius, -height+BOTTOM_THICKNESS),
            (0, -height+BOTTOM_THICKNESS)]


def cup_body_distance(position, center, profile):
    """Signed distance and outward unit normal for the revolved solid cup body.

    Positive distances are in free space, including the open interior. The
    segment on the revolution axis closes the polygon but is not a surface.
    """
    dx, dy = position[0]-center[0], position[1]-center[1]
    radial, z = math.hypot(dx, dy), position[2]-center[2]
    inside = False
    nearest = None
    for a, b in zip(profile, profile[1:] + profile[:1]):
        dr, dz = b[0]-a[0], b[1]-a[1]
        if (a[1] > z) != (b[1] > z):
            if radial < a[0] + (z-a[1])*dr/dz:
                inside = not inside
        if a[0] == b[0] == 0:
            continue
        length2 = dr*dr + dz*dz
        t = max(0.0, min(1.0, ((radial-a[0])*dr+(z-a[1])*dz)/length2))
        delta = (radial-a[0]-t*dr, z-a[1]-t*dz)
        distance = math.hypot(*delta)
        if nearest is None or distance < nearest[0]:
            length = math.sqrt(length2)
            nearest = (distance, delta, (dz/length, -dr/length))
    distance, delta, edge_normal = nearest
    if distance > 1e-12:
        sign = -1 if inside else 1
        nr, nz = sign*delta[0]/distance, sign*delta[1]/distance
    else:
        nr, nz = edge_normal
    ux, uy = (dx/radial, dy/radial) if radial > 1e-12 else (1.0, 0.0)
    return (-distance if inside else distance), (nr*ux, nr*uy, nz)
