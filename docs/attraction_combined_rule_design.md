# Attraction `combined_rule` design

`combined_rule` composes the two hidden transformations already defined for
`rule_1` and `rule_2`:

```text
F = G m1 m2 / r^p · q_equation · q_field(r,t)
a = F / m
```

The baseline group constants and object attributes remain unchanged. The
agent must first account for both the changed equation and the hidden spatial
or temporal coefficient field.

## Variant pairing

Combined variants are indexed to the existing variants:

| Combined variant | Equation component | Function component | Difficulty |
|---|---|---|---|
| variant_1 | rule_1 variant_1 | rule_2 variant_1: linear spatial | easiest composition |
| variant_2 | rule_1 variant_2 | rule_2 variant_2: linear temporal | simple two-factor inference |
| variant_3 | rule_1 variant_3 | rule_2 variant_3: quadratic spatial | nonlinear equation plus nonlinear field |
| variant_4 | rule_1 variant_4 | rule_2 variant_4: logarithmic temporal | nonlinear equation plus nonlinear time field |
| variant_5 | rule_1 variant_5 | rule_2 variant_5: coupled space-time | mass exponents plus coupled field |
| variant_6 | rule_1 variant_6 | rule_2 variant_6: nested nonlinear | maximum combined difficulty |

For variant `k`, the host combines the exact hidden parameters from
`rule_1/variant_k` and `rule_2/variant_k`. The model never receives either
parameter set directly.

## Question layout

Each combined variant contains `q01` through `q15`. The scene initialization is
copied from the matching `rule_1/variant_k/qNN` question. Thus a combined
question has the same anchor position, probe position, velocity, start time,
camera, and public prompt as its matched single-rule questions.

Every question asks the same visual next-frame task:

```text
Using the interaction history and rendered context, choose the image showing
the probe at the next frame. Answer A, B, C, or D.
```

The host-only `instance.json` records both hidden components:

```json
{
  "hidden_equation_parameters": {},
  "hidden_force_function": {},
  "scene_state": {}
}
```

The public `question.json` contains only identifiers and pairing metadata.

## Experiment difficulty

The agent has access to the same baseline and intrinsic-property tools as the
single-rule environments. Baseline force measurements estimate the ordinary
group law, while question-world force and motion measurements expose the
combined deviation. A single measurement is intentionally insufficient:

- Equation changes alter distance and mass scaling.
- The field changes the force ratio as position or time changes.
- Combined variants require separating these effects.

The 15 questions per variant reuse the matched single-rule initializations so
performance can be compared directly across `rule_1`, `rule_2`, and
`combined_rule`.

## Candidate images

The authoritative combined runtime generates the rollout and four close
candidate frames. Candidate spacing, radial phase, camera visibility, and
answer-label balancing use the same render policy as the single-rule suites.
The evaluation model receives only the matching interaction history and five
rendered images.
