# Electric-field interaction world family

This family models charged objects and electric fields. Charge and field
coefficients can be hidden intrinsic or world-level quantities.

## Equation budget

Core equations (minimum two):

1. Charge force: `F = K q1 q2 q(x,t) / r^p`.
2. Charge acceleration: `a = F / m`.

Optional equations (maximum four total):

3. Field definition: `E = F / q_test`.
4. Electric work/energy: `Delta K = q (phi_start - phi_end)`.

## Scene allocation

A two-charge scene uses equations 1–2. A probe-charge scene adds equation 3,
and a work/energy scene adds equation 4. The benchmark can combine all four in
one scene or distribute them across two or three scenes.
