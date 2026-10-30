# Buoyancy and fluid-response world family

This family models immersed objects and fluid response. Fluid constants are
fixed within a world group and can differ between groups.

## Equation budget

Core equations (minimum two):

1. Buoyant force: `F_b = rho_f(x,t) V_displaced q g`.
2. Vertical motion: `m dv/dt = F_b - m g + F_other`.

Optional equations (maximum four total):

3. Displaced volume: `V_displaced = V_submerged`.
4. Fluid drag: `F_d = -c_f |v|^n sign(v)`.

## Scene allocation

The floating/sinking scene uses equations 1–2 together. A partially submerged
scene makes equation 3 explicit, and a moving-fluid scene adds equation 4.
They may appear in one scene or be divided across two or three scenes.
