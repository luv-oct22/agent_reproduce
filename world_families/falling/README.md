# Falling world family

This family models vertical motion. Every world group has a standard baseline
with the same constants as its modified siblings. Object attributes may differ
between families, but remain fixed within a group.

## Equation budget

Core equations (minimum two):

1. Effective downward acceleration: `g_eff = G m_source q(x,t) / r^p`.
2. Velocity update: `v(t) = v0 + g_eff^q t^p`.

Optional equations (maximum four total):

3. Position update: `y(t) = y0 + v0 t + 0.5 g_eff t^2`.
4. Impact rule: `v_after = -e v_before`.

## Scene allocation

The basic drop scene uses equations 1–2 together. A trajectory scene can add
equation 3, and a floor-bounce scene adds equation 4. A question may therefore
test two equations in one scene or distribute three to four equations across
two or three scenes.
