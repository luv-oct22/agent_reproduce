# Drag and resistance world family

This family models motion opposed by a resistance field. Variants may alter the
power of speed or make the coefficient depend on position or time.

## Equation budget

Core equations (minimum two):

1. Resistance: `F_d = -c(x,t) |v|^n sign(v)`.
2. Motion: `m dv/dt = F_external + F_d`.

Optional equations (maximum four total):

3. Position: `dx/dt = v`.
4. Terminal-speed condition: `F_external + F_d = 0`.

## Scene allocation

The drag trial uses equations 1–2 in one scene. A timed trajectory scene adds
equation 3, while a terminal-speed scene uses equation 4. The benchmark may
place all four in three scenes or keep only the two core equations in one.
