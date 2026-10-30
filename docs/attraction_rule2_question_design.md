# Attraction `rule_2` question design

`rule_2` hides a coefficient field inside the otherwise standard attraction
law. The baseline for `central_force_dynamics_g1` remains the ordinary inverse-square law:

```text
F_ij = G m_i m_j / r^2 · q(x, t)
```

The group constants, object attributes, camera, candidate policy, and solver
are shared with `rule_1`. Only the hidden coefficient function changes between
variants. The agent can probe the matched baseline world with
`measure_baseline_force`, measure object attributes with the intrinsic tools,
and use force or motion experiments in the question world.

## Fixed group contract

Every `rule_2` question uses the `central_force_dynamics_g1` baseline constants:

```text
strength G = 1.7 N
reference distance r_ref = 1.3 m
reference mass m_ref = 0.8 kg
minimum separation = 0.3 m
baseline exponent p = 2
```

The anchor and probe retain the group object attributes: anchor mass 1.0 kg,
probe mass 0.1 kg. The coefficient is evaluated at the probe position relative
to the anchor and at the trial's absolute start time. All generated scenes keep
`q(x,t)` positive so the force remains attractive.

## Six hidden-function variants

The coefficients below are fixed within a variant and hidden from the agent.
The numerical values are part of the host-only `instance.json` record.

### Variant 1: linear spatial field

```text
q_1(r) = 1.0 + 0.3 (r - r_ref) / r_ref
```

This is the easiest spatial rule. The ratio between force and baseline force
changes linearly with distance and is independent of time.

### Variant 2: linear temporal field

```text
q_2(t) = 1.0 + 0.2 (t - t_ref) / t_scale
```

Use `t_ref = 2.0 s` and `t_scale = 4.0 s`. The same position measured at two
start times reveals the hidden time dependence.

### Variant 3: quadratic spatial field

```text
q_3(r) = 1.0 + 0.4 ((r - r_ref) / r_ref)^2
```

The coefficient is symmetric around the reference distance. A single force
reading cannot distinguish it reliably from a linear rule; the agent must use
several distances on both sides of `r_ref`.

### Variant 4: logarithmic temporal field

```text
q_4(t) = 1.0 + 0.35 log(1 + |t - t_ref| / t_scale)
```

Use `t_ref = 2.0 s` and `t_scale = 2.0 s`. This produces a nonlinear time
response while remaining positive over the apparatus clock range.

### Variant 5: coupled spatial-temporal field

```text
q_5(r,t) = 1.0
           + 0.25 ((r - r_ref) / r_ref)
           + 0.20 sin(2π (t - t_ref) / 6.0)
```

Distance and time both matter. Matched measurements must vary one quantity at a
time; otherwise the two effects can be mistaken for one another.

### Variant 6: nested nonlinear field

```text
u = (r - r_ref) / r_ref
v = (t - t_ref) / 3.0

q_6(r,t) = 1.0 + 0.30 sin(πu + 0.5v)
                + 0.20 log(1 + u^2)
                + 0.15 v^2
```

This is the hardest rule. It combines an oscillatory phase, a nonlinear
distance term, and a nonlinear time term. The generator must restrict sampled
states to the clock and separation domains and reject any state for which the
coefficient is not positive.

## Question layout

Each rule_2 variant contains exactly `q01` through `q15`, matching the
corresponding rule_1 question IDs. The scene initialization for
`rule_2/variant_k/qNN` reuses the rule_1 `variant_k/qNN` position, velocity,
anchor placement, and start time. This makes the rule change the controlled
variable: the visual scene and question are matched, while the hidden force
function differs.

The question text is always the same next-frame task:

```text
Using the interaction history and the rendered context, choose the image that
shows the probe at the next frame. Answer with A, B, C, or D.
```

The host initializes the authoritative runtime from the copied scene values,
advances it for the configured short rollout, and generates four close
candidate frames. Object masses, colors, and baseline constants remain fixed
within the group. Store the complete resolved state and hidden function
parameters in the host-only `instance.json`; keep `question.json` limited to
public identifiers and pairing metadata.

## Candidate-image construction

The context image shows the question's initial state. Choices A–D are generated
by the authoritative `rule_2` runtime after a short rollout. Candidate centres
must remain 2–8 cm apart, share the same radial phase, and fit the camera. The
true rollout is assigned to a balanced answer label rather than always A.

The visual question asks which candidate is the next frame. The evaluation
model receives the rendered context, four candidate images, and the matching
interaction history. It never receives the host-only function expression,
variant parameters, scene manifest, or answer key.

## Difficulty controls

Difficulty increases through the variants. Because q01–q15 are scene-matched
to rule_1, differences in accuracy can be attributed to the hidden function
complexity rather than a different question distribution. A baseline-force
measurement is useful for all variants, but it does not reveal the hidden
coefficient function by itself.
