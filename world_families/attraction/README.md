# Central attraction world family

This family covers pairwise central attraction and its altered distance and
coefficient rules. The existing attraction benchmark is its first implementation.
Scenes are grouped by the constants and equations they require: a scene is
bound to a complete world instance, and each scene group has its own baseline
world. We do not force unrelated scenes to share one baseline.

## Equation budget

The attraction family is limited to three equation slots. A world uses the two
core slots at minimum and may enable the third for trajectory questions.

Core equations:

1. Pair force: `F = G m1 m2 q(x,t) / r^p`.
2. Acceleration: `a_i = F_i / m_i`.

Optional equation:

3. Radial motion: `r(t) = r0 + v_r t + 0.5 a_r t^2`.

## Scene-bound world groups

### attraction_g1: horizontal projection

- `baseline_horizontal`: the standard attraction law and its group constants.
- Variant worlds keep the group constants fixed and change only an equation
  rule such as `p` or a hidden principle such as `q(x,t)`.
- The horizontal-projection scene uses equations 1–2 together, with the
  attraction acceleration resolved into horizontal and vertical components.
- No surface-friction constant is present in this group.

### attraction_g2: motion on a rough horizontal surface

- `baseline_rough_surface`: the same type of attraction law, plus this group's
  surface constant `mu`.
- Variant worlds keep the scene geometry and object appearances matched while
  changing the declared attraction rule or the friction rule.
- The scene still uses only equations 1–2, and equation 3 when trajectory
  questions are required. Its net force `F_i` includes the surface response,
  whose world constant is `mu`; no fourth attraction equation is added.
- `mu` belongs to this world group only; it is not copied into the horizontal
  projection baseline.

The two groups may each contain one or several scenes, but every scene points
to its own complete baseline or variant `world_id`. This preserves the control
condition: a model compares a modified world with the correct baseline for that
scene, rather than with a baseline that contains unrelated constants.
