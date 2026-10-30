# `kinematics_dynamics` family design

This family covers motion governed by acceleration fields rather than a single
specific falling scene. Its first group is `kinematics_dynamics_g1`.

## Baseline group

The baseline uses a constant oblique acceleration vector whose value belongs to
the world group. This is an open-space motion laboratory, not a drop or falling
scene:

```text
a0 = [1.2, -0.7, 0.4] m/s²
```

For a dynamic object:

```text
a = g0
v(t) = v0 + a t
x(t) = x0 + v0 t + 0.5 a t²
```

The group contains spherical objects with fixed intrinsic mass, radius, color,
and motion role. The baseline world exposes the same object catalog and
apparatus limits as every modified world in the group.

## Scene types

The first group contains three matched scene types:

1. **Free fall:** zero or small horizontal velocity, vertical displacement.
2. **Vertical launch:** positive or negative initial vertical velocity.
3. **Projectile motion:** nonzero horizontal and vertical velocity.

Each variant has q01–q15. The corresponding qNN in every rule branch reuses
the same initial positions, velocities, object attributes, and start time. Every
question asks the model to choose the rendered next frame.

## Hidden branches

### `rule_1`: equation changes

The six variants progressively modify the kinematic equations:

```text
variant_1: a = g0,                 v = v0 + a t
variant_2: a = g0 q,               v = v0 + a t
variant_3: a = g0,                 v = v0 + a t^p
variant_4: a = g0,                 x = x0 + v0 t + 0.5 a t^p
variant_5: a = g0 q^p,             v = v0 + a t^p
variant_6: a = g0 q^p,             x = x0 + v0 t^p + 0.5 a t^(2p)
```

The parameters `q` and `p` are fixed within a variant and hidden from the
agent. The baseline remains the ordinary `q=1`, `p=1` equations.

### `rule_2`: hidden acceleration field

The standard kinematic equations remain in force, but acceleration is modulated
by a hidden function:

```text
a(x,t) = g0 · q(x,t)
```

Variants 1–2 use simple spatial or temporal functions, variants 3–4 use
nonlinear functions, and variants 5–6 combine spatial and temporal terms.

### `combined_rule`: equation plus field

Each combined variant pairs the corresponding `rule_1` equation parameters and
`rule_2` acceleration field. The matched q01–q15 scenes are unchanged across
all three branches.

## Tools and evaluation

The agent can use intrinsic-property tools for mass, radius, volume, density,
and inertia. Family tools measure acceleration, velocity, position, and short
motion trajectories. A baseline acceleration experiment measures the standard
group world without revealing the hidden rule.

The visual evaluator receives the interaction history, one context image, and
four close candidate next-frame images. Host-only records contain the resolved
equations, field parameters, scene state, and answer key.
