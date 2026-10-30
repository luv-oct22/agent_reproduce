# Spring and elastic-response world family

This family models restoring forces, with stiffness possibly varying by object,
space, or time.

## Equation budget

Core equations (minimum two):

1. Restoring force: `F_s = -k(x,t) (x-x_eq)^n sign(x-x_eq)`.
2. Motion: `m d2x/dt2 = F_external + F_s`.

Optional equations (maximum four total):

3. Damping: `F_d = -c v`.
4. Oscillation period: `T = 2 pi sqrt(m/k_eff)`.

## Scene allocation

Compression or extension uses equations 1–2 together. A damped-motion scene adds
equation 3, and a period-measurement scene adds equation 4. The equations may
be combined in one scene or distributed over two or three scenes.
