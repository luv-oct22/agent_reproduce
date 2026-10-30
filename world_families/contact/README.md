# Contact and collision world family

This family models impacts and surface contact. A world can alter restitution,
friction, or the contact response while preserving the visible geometry.

## Equation budget

Core equations (minimum two):

1. Normal impulse: `J_n = -(1+e) m_eff v_rel,n`.
2. Post-impact velocity: `v_after = v_before + J_n / m`.

Optional equations (maximum four total):

3. Tangential friction: `|J_t| <= mu |J_n|`.
4. Deformation force: `F_n = k delta^p`.

## Scene allocation

A head-on collision uses equations 1–2. A sliding collision adds equation 3,
and a compression scene adds equation 4. The benchmark can test two equations
in one scene or spread the full set across two or three scenes.
