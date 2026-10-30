# Generalized world-family design

Attraction remains a specific family for central relational force. The other
six families use broad domain names so each can contain multiple scene types.

## Canonical families

| Canonical family | Former placeholder | Example scenes |
|---|---|---|
| `kinematics_dynamics` | falling | free fall, projectile motion, vertical launch |
| `fluid_mechanics` | buoyancy | flotation, submerged motion, fluid pressure |
| `contact_mechanics` | contact | collision, friction, normal force, rolling |
| `dissipative_dynamics` | drag | viscous drag, quadratic drag, damping |
| `field_interactions` | electric_field | electric force, potential fields, charged motion |
| `elastic_dynamics` | spring | springs, oscillators, coupled elastic bodies |

## Shared structure

```text
world_instances/<family>/<group_id>/
  README.md
  group_manifest.json
  baseline/instance.json
  rule_1/variant_1/q01–q15/
  rule_2/variant_1/q01–q15/
  combined_rule/variant_1/q01–q15/
```

The baseline fixes group constants and ordinary equations. `rule_1` changes
equation structure, `rule_2` hides a coefficient field or governing function,
and `combined_rule` composes both. Matched questions reuse the same q01–q15
initial states across the three branches.

## First groups

```text
kinematics_dynamics_g1
fluid_mechanics_g1
contact_mechanics_g1
dissipative_dynamics_g1
field_interactions_g1
elastic_dynamics_g1
```

Group constants are fixed within a group but may differ between groups. Object
attributes are measured through shared intrinsic-property tools. The baseline
and variants expose the same object catalog, colors, camera, and apparatus
limits.

## Migration map

```text
falling         -> kinematics_dynamics
buoyancy        -> fluid_mechanics
contact         -> contact_mechanics
drag            -> dissipative_dynamics
electric_field  -> field_interactions
spring          -> elastic_dynamics
```

New benchmark records should use the canonical names. Legacy experiments remain
addressable through their existing result paths and are not silently relabeled.
