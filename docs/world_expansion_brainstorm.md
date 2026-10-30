# World expansion brainstorm

The attraction world is one concrete example of a broader benchmark generator.
The generator should create unfamiliar physical worlds by varying two mostly
independent rule axes:

1. a hidden function changes a physical quantity while the equation family stays
   structurally similar;
2. the governing equation itself changes.

Some tasks should vary only one rule. Harder tasks should combine exactly two
rules. Every generated instance must remain experimentally identifiable within
its declared tool and measurement budget.

## Rule axis 1: hidden functions

The equation form is retained, but a coefficient or physical quantity depends
on position, time, distance, direction, or object identity.

For attraction, the ordinary form can become:

```text
F = G(x, t) * m1 * m2 / r^2
```

Candidate functions include:

- constant coefficient: `G(x, t) = G0`;
- height-dependent coefficient: `G(z)`;
- radial coefficient: `G(r)`;
- piecewise region function;
- smooth transition across a boundary;
- sinusoidal time variation: `G(t)`;
- periodic spatial field;
- localized Gaussian field;
- direction-dependent coefficient: `G(theta)`;
- object-specific coupling: `G * q1 * q2`.

Example:

```text
G(z) = G_low,   z < z_boundary
       G_high,  z >= z_boundary
```

The model must discover where and how the coefficient changes. The function is
fixed in the world record and is shared by experiments, trajectories, rendering,
and evaluation.

## Rule axis 2: equation changes

The governing relationship itself changes. Candidate equation families include:

### Distance exponent

```text
F = G * m1 * m2 / r^p
```

Possible worlds use `p=2`, `p=3`, or another declared exponent. The coefficient
units must be recorded consistently for every exponent.

### Nonlinear mass coupling

```text
F = G * m1^alpha * m2^beta / r^p
```

The ordinary case is `alpha=beta=1`; alternatives can use square-root or
quadratic coupling. Independent mass measurements are required if the task asks
the model to identify coupling separately from mass.

### Velocity-dependent attraction or resistance

```text
F = G * m1 * m2 / r^2 * (1 + lambda * |v|)
F_drag = -b * v^n
```

The exponent `n=1` gives linear drag and `n=2` gives quadratic drag.

### Modified acceleration response

```text
a = F / m^gamma
```

`gamma=1` is the ordinary Newtonian response. Other values require calibrated
mass and force experiments; otherwise the problem can be underdetermined.

### Nonlinear restoring force

```text
F = -k * x
F = -k * x^3
```

This supports spring worlds with either a changed equation or a position-varying
stiffness function `k(x)`.

### Changed contact response

```text
v_after = -e * v_before
```

The equation can be altered through velocity-dependent restitution, nonlinear
friction, or a changed contact impulse rule.

## World families

### Attraction law family

```text
F = A * (m1 / m_ref) * (m2 / m_ref) * (r_ref / r)^p
```

Single-rule variants:

- inverse-square versus inverse-cube attraction;
- constant `A` versus height-dependent `A(z)`;
- constant `A` versus time-dependent `A(t)`;
- object-specific coupling versus equal coupling.

Combined variants can use `p=3` together with `A(z)`.

### Spatial gravity family

```text
F = G(z) * m1 * m2 / r^2
```

Scenes can move a probe through different height regions or across a smooth
field boundary. The agent must separate distance effects from location effects.

### Nonlinear drag family

```text
F_drag = -b(z) * v^n
```

Variants include linear versus quadratic drag, constant versus spatially varying
drag, and combinations of both.

### Modified mass-response family

```text
a = F / m^gamma
```

This family tests whether an agent distinguishes inertial mass from the mass
appearing in the interaction law.

### Spring family

```text
F = -k(x) * x^n
```

Possible changes are constant versus spatially varying stiffness and linear
versus nonlinear restoring force.

### Contact family

Possible hidden rules include restitution, friction, deformation, adhesion, and
velocity-dependent collision response. These should be added after the simpler
force families have stable identifiability audits.

## Difficulty gradient

| Level | Rules changed | Example |
|---|---:|---|
| 0 | None | Ordinary inverse-square attraction |
| 1A | One hidden function | `G(z) / r^2` |
| 1B | One equation change | `1 / r^3` |
| 1C | One hidden object property | Unknown mass or coupling |
| 2A | Function plus equation | `G(z) / r^3` |
| 2B | Equation plus object property | `m^alpha / r^3` |
| 2C | Two hidden functions | `G(z,t) / r^2` |
| 3 | Three interacting unknowns | `G(z,t) * m^alpha / r^p` |

The first expansion should focus on Levels 1A, 1B, 2A, and 2B. Level 2C and
Level 3 worlds should not be admitted until host audits show that the chosen
tools identify the predictive behavior within budget.

## Matched world pairs

Matched worlds should differ in only the intended rule for single-rule tasks.
Their public appearances, object colors, tool names, schemas, budgets, clocks,
and instructions must be identical.

Example equation pair:

```text
world_A: p=2, constant A
world_B: p=3, constant A
```

Example function pair:

```text
world_A: p=2, constant A
world_B: p=2, height-dependent A(z)
```

Example combined pair:

```text
world_A: p=2, constant A
world_B: p=3, height-dependent A(z)
```

The pair must be checked for visual equality before the held-out scene is
created. A model must receive an interaction history generated in the same
world as the question it later answers.

## Instance organization

Each family should contain immutable, independently generated instances:

```text
world_instances/
  attraction_equation_v1/
    family_manifest.json
    train_001/
    train_002/
    validation_001/
    test_001/
  attraction_field_v1/
    ...
```

Every instance records:

- the executable equation and version;
- hidden function parameters and sampled values;
- object properties and visible appearance;
- available intrinsic and law-experiment tools;
- budgets, precision, ranges, and clock behavior;
- solver version and numerical limits;
- scene seeds and initial states;
- public projection and private answer key;
- provenance and source hashes.

World records must be immutable once used by an interaction or image suite.
Changing a law, object property, tool catalog, or solver requires a new version
or instance identifier.

## Initial suite size

The first expansion can use four families:

1. `attraction_equation_v1`: p=2 versus p=3;
2. `attraction_field_v1`: constant coefficient versus `A(z)`;
3. `attraction_combined_v1`: equation and coefficient-function changes;
4. `drag_equation_v1`: linear versus quadratic drag.

For each family, start with:

- four training world pairs;
- two validation world pairs;
- four held-out test pairs;
- 16 visual questions per world;
- separate interaction histories for each world.

This creates ten pairs per family, or 40 paired world instances across the first
four families. More instances should be added only after checking that failures
are not caused by a particular seed, color assignment, or scene geometry.

## Tool separation

Intrinsic tools measure one object:

- mass;
- volume;
- geometry;
- density;
- moment of inertia;
- material or contact attributes when applicable.

Law tools measure relationships or dynamic behavior:

- force between objects;
- motion trajectories;
- impulse response;
- collision events;
- drag or terminal velocity.

The combined autonomous bench may expose both catalogs in one episode. The agent
chooses which tools to call. The system must not automatically invoke a mass
measurement before force experiments, select a tool based on the hidden answer,
or return a private correctness signal.

## Generation and admission checks

Before a world enters a benchmark split, run these host-side checks:

1. record round-trip and fingerprint validation;
2. public-interface equality across matched worlds;
3. solver convergence and analytical-limit checks;
4. tool cost, precision, range, and clock checks;
5. experiment replay from the same saved world;
6. identifiability search against plausible alternative equations;
7. candidate trajectory validity and image similarity checks;
8. nearest-candidate and fixed-law shortcut baselines;
9. answer-label and truth-rank balance;
10. source, scene, image, and answer-key checksum validation.

If two plausible hypotheses fit the rounded measurements but produce different
held-out predictions, the instance should be marked ambiguous or moved to a
separate uncertainty benchmark. It should not be silently scored as a unique
answer.

## Recommended implementation order

1. Keep the current constant attraction pair as the Level 1 equation control.
2. Add spatial and temporal coefficient-field evaluators.
3. Add hidden object coupling with intrinsic measurement tools.
4. Add equation/function combinations and rerun identifiability audits.
5. Add nonlinear drag and contact families.
6. Generate scenes only after numerical transfer passes.
7. Evaluate history, no-history, fixed-policy, and random-policy controls.

The central design principle is to change one rule for simple tasks, combine two
controlled rules for medium difficulty, and reserve three-rule worlds for later
experiments. Every world must be executable, measurable, replayable, and
identifiable within its declared interface and budget.

## Multiple equations inside one world

The unit of variation should not be limited to one equation. A world can contain
an internally consistent rule package with several equation slots. A falling
object, for example, may use one modified equation to determine acceleration and
another modified equation to determine velocity from acceleration and time.

An example rule package is:

```text
F_g = G * m1 * m2 * q / r^p

g = F_g / m2

v(t) = g^q * t^p + v0
```

The simulator must define the exact meaning and units of every symbol. In the
first equation, if `m2` is the falling object's inertial mass, then the derived
acceleration is:

```text
g = G * m1 * q / r^p
```

The second equation is an intentionally modified kinematic law. Its parameters
must be normalized or given explicit units because arbitrary powers of `g` and
`t` are not dimensionally valid without additional reference scales. A safer
recorded form is:

```text
v(t) = v_ref * (g / g_ref)^q * (t / t_ref)^p + v0
```

The benchmark should never rely on an equation string evaluated dynamically.
Each equation slot needs a registered implementation, version, parameter schema,
units, valid domain, and numerical tests.

### Equation-slot representation

A world rule package can be represented as a dependency graph:

```text
world rule package
  force_law       -> force
  acceleration    -> acceleration
  kinematics      -> velocity and position
  contact         -> post-contact state
  field_function  -> coefficient values
```

Each slot can use the ordinary equation or a versioned alternative. For example:

```json
{
  "force_law": "central_attraction_v2",
  "acceleration_law": "mass_response_v1",
  "kinematics_law": "power_time_kinematics_v1",
  "field_function": "constant_v1"
}
```

The dependency graph must be acyclic or explicitly define an iterative solver.
Every changed slot is recorded in the private world definition and included in
the world fingerprint.

## World groups, worlds, scenes, and questions

A world group is a comparison and generation container. It is not a physical
world and it must not be used as the runtime parent of its variants. Every
variant is a complete, executable world with its own world-instance identifier.

The correct ownership structure is:

```text
world family
  -> world group
       ├── baseline world instance
       │     ├── scene instance -> question(s)
       │     └── scene instance -> question(s)
       ├── single-rule variant world instance
       │     ├── scene instance -> question(s)
       │     └── scene instance -> question(s)
       └── combined-rule variant world instance
             ├── scene instance -> question(s)
             └── scene instance -> question(s)
```

The world group stores the relationship between sibling worlds: shared constants,
intended rule differences, matching metadata, and split information. It does not
own physical state, execute equations, or receive model actions.

Each world instance independently contains:

- its complete rule package and equation-slot implementations;
- its concrete constant values;
- its object registry and properties;
- its field and contact definitions;
- its tool protocol and disclosures;
- its solver and numerical domain;
- its own immutable world fingerprint.

Each scene stores a direct `world_id` reference to exactly one world instance.
Each question stores a direct `scene_id` and world binding. An interaction record
also binds directly to the same world instance. The group ID is metadata for
analysis and pairing; it is never enough to reconstruct or select a world.

One complete world can therefore produce many scenes and questions when those
scenes use the same equation slots and world-level constants. If a scene
introduces a world constant that another scene does not have, split them into
separate world groups, each with its own baseline and matched variants. This
keeps the baseline associated with the actual scene physics instead of adding
irrelevant parameters to a control world.

For example, the attraction family can have two scene-bound groups:

```text
attraction family
  horizontal_projection group
    baseline_horizontal + projection scenes
    variants + matched projection scenes
  rough_surface group
    baseline_rough_surface (includes mu) + rough-surface scenes
    variants + matched rough-surface scenes
```

The rough-surface group contains the friction coefficient `mu`; the horizontal
projection group does not. The two groups may share object schemas and tool
interfaces, but they have distinct baseline world IDs and constants.

A single falling world might include:

- a drop from rest;
- an upward launch;
- a downward launch;
- two objects with different masses;
- a drop at different source distances;
- a timed measurement at different starting times;
- a scene with a hidden coefficient boundary.

These are distinct scenes of one complete world instance. A second variant is a
different complete world instance, even when it copies every constant and object
from the first world. The model must receive interaction evidence from the exact
world instance referenced by the later question.

## Difficulty from equation composition

Difficulty should be indexed by changed equation slots, hidden parameters,
coupled dependencies, and observability rather than by the number of scenes
alone.

| Level | Changed slots | Example |
|---|---:|---|
| E0 | 0 | Ordinary force, acceleration, and kinematics |
| E1 | 1 | Change only the force exponent `p` |
| E1F | 1 | Keep equations fixed; change only `G(z)` or `G(t)` |
| E2 | 2 | Change force exponent and hidden coefficient function |
| E2K | 2 | Change force law and velocity-time kinematics |
| E3 | 3 | Change force, acceleration response, and kinematics |
| E3F | 3+ | Combine equation changes with spatial/time fields and hidden object properties |

Single-slot worlds should have at least one experiment that isolates the changed
slot. Multi-slot worlds should include scenes that distinguish the slots rather
than making all effects observationally identical.

For the falling example, a useful progression is:

1. ordinary `F=ma` and ordinary `v=v0+gt`;
2. modified force exponent only;
3. modified kinematic exponent only;
4. modified force and kinematic exponents together;
5. modified force, kinematics, and a hidden spatial coefficient;
6. add a hidden inertial/gravitational mass relationship only after the earlier
   parameters are independently measurable.

## Multiple worlds and scenes per world group

Every world group should generate several complete world variants, and every
variant should generate several scenes:

```text
falling_power_v1/
  group_manifest.json
  baseline_world/
    instance.json
    scenes/
      far_drop.json
      upward_launch.json
  force_variant_world/
    instance.json
    scenes/
      far_drop.json
      upward_launch.json
  combined_variant_world/
    instance.json
    scenes/
      field_boundary.json
      upward_launch.json
```

The group manifest records the sibling relationships and shared generation
inputs. Each `instance.json` independently records the copied constants after
validation. Scenes vary controlled factors such as source distance, initial
velocity, object mass, coefficient realization, start time, and camera framing.
A test split can hold out parameter combinations, object combinations, scenes,
or entire equation-slot compositions.

Do not treat a group ID as a physical world ID. Record all three identifiers
separately: `group_id` for comparison, `world_id` for executable physics, and
`scene_id` for initial conditions and camera. This supports both within-world
scene transfer and cross-world generalization without mixing histories.

## Admission checks for multi-equation worlds

Before admitting a composed world:

1. verify units and reference scales for every equation slot;
2. check that the dependency graph produces one deterministic trajectory;
3. compare solver convergence against smaller time steps;
4. test limiting cases where modified exponents reduce to ordinary behavior;
5. fit alternative rule packages using the declared tool budget;
6. reject worlds where different rule packages produce identical observations
   but different answer keys unless the task is explicitly an uncertainty task;
7. verify that each intended hidden slot affects at least one held-out scene;
8. audit that visual geometry does not reveal a changed equation directly.

The model can be allowed to invoke intrinsic-property tools and law tools in the
same autonomous episode. The system should still keep the equation-slot graph,
hidden parameters, and answer key private. Increasing the number of equations
is useful only when the experimental interface provides evidence that separates
their effects.

## Standard baseline world for every world group

Every group of related worlds should include a standard baseline world. The
baseline uses the ordinary equation and ordinary physical principle for that
family, but preserves the same group-level constant parameters as the modified
worlds.

The baseline is not required to use real-world constants. It is a structural
control for the benchmark, not a claim that the simulated world is Earth-like.
For example, a falling-world group can choose one group constant:

```text
group gravity constant: g0 = 4.0 m/s^2
```

and generate:

```text
baseline world: ordinary F = m*g0 and v = v0 + g0*t
modified world: changed force equation using the same g0
modified world: changed kinematic equation using the same g0
combined world: both equations changed, still using the same g0
```

Other groups can use `g0=6.0`, `g0=3.7`, `g0=4.9`, or another recorded value.
The value is part of the world instance, not a universal benchmark constant.
The generator must never silently substitute 9.8 m/s² merely because the scene
resembles a familiar falling experiment.

### What the baseline controls

The baseline lets us separate several sources of model error:

- failure to estimate the world constant;
- assuming a real-world constant without measuring it;
- misunderstanding the ordinary equation;
- failing to detect a changed equation;
- failing to combine multiple changed equations;
- relying on scene appearance instead of experimental evidence.

For an attraction group, the same rule applies. If the group chooses a strength
`A0=1.7 N`, then the control and modified worlds share that `A0`:

```text
baseline: F = A0 * m1*m2 / r^2
modified: F = A0 * m1*m2 / r^3
```

If the group uses a falling source mass, source distance, coefficient field, or
reference scale, those constants must also be held fixed when comparing the
baseline and modified worlds. Only the intended rule slot should change.

### Group record structure

Store the baseline and modified worlds under one immutable group record:

```text
falling_power_group_001/
  group_manifest.json
  baseline_world/
    instance.json
  force_equation_world/
    instance.json
  kinematic_equation_world/
    instance.json
  combined_world/
    instance.json
```

The group manifest records:

- `group_id`;
- the sampled constant parameters, such as `g0`, `A0`, reference scales, and
  calibrated object values;
- the ordinary baseline equation slots;
- the changed equation slots for each variant;
- the public interface and tool catalog fingerprint;
- which constants are visible, measurable, or hidden;
- the train/validation/test split;
- the world-instance fingerprints.

The baseline and all variants must have the same public object appearances,
initial-scene format, tool names, measurement precision, budget, and clock rules.
The baseline may use an intrinsic-property tool to measure object mass and a
law tool to estimate `g0`, while the modified worlds expose the same tools.

### Constant-parameter policy

Use three categories for every parameter:

1. **Object constants** — mass, radius, volume, density, and inertia. These can
   be measured with intrinsic-property tools.
2. **Group world constants** — `g0`, `A0`, reference distance, reference mass,
   initial field offset, or baseline stiffness. These belong to the world and
   must be copied across the group.
3. **Rule transformations** — exponent changes, nonlinear powers, spatial/time
   functions, or altered update equations. These are the intended hidden changes.

The generator should sample group constants once, then clone them into every
world variant before applying the selected rule transformations. A validation
check must compare all non-transformed constants and reject accidental changes.

### Difficulty using the baseline

The baseline makes the difficulty gradient more interpretable:

| Group level | Worlds in the group | Main question |
|---|---|---|
| B0 | Baseline only | Can the model estimate a non-real-world constant? |
| B1 | Baseline + one changed equation | Can it detect one rule transformation? |
| B2 | Baseline + two single-change variants | Can it identify which slot changed? |
| B3 | Baseline + combined two-rule variant | Can it infer two transformations together? |
| B4 | Baseline + field and object-property variants | Can it separate constants, fields, and equations? |

The baseline should appear in development and calibration splits. Test groups can
hold out new constant values, such as training on `g0=4.0` and `6.0` but testing
on `g0=3.7`, while keeping the same equation transformations. This tests whether
the model learned the rule rather than memorized a particular constant.

### Required baseline checks

Before generating scenes from a group:

1. verify that the baseline uses the ordinary registered equation;
2. verify that every variant copies the group constants exactly;
3. verify that object properties are unchanged unless object variation is the
   intended factor;
4. verify that public interfaces are identical;
5. audit that the baseline and variants are distinguishable with the tools and
   budget;
6. check that a real-world prior such as `g=9.8` is not needed for a correct
   answer;
7. record all constants and transformations privately for replay;
8. keep the baseline answer key and modified-world answer keys separate.

The baseline is therefore a required member of each world group, not an optional
extra scene. It anchors interpretation of every modified world and allows the
benchmark to test both constant estimation and principle discovery.

## Shared object attributes across all world families

Object attributes use one cross-family schema and measurement contract, but their
values are chosen per world family. A family may use a different mass, volume,
density, or inertia assignment from another family. Within one family, however,
the matched baseline and rule variants should keep the same object attributes so
that an equation comparison does not accidentally become an object-property
comparison.

The shared intrinsic schema should cover, as applicable:

```text
object_id
color and visible appearance
shape and geometry
radius / dimensions
volume
mass
density
inertial properties
material and contact properties
```

Each family chooses and records its own attribute assignment. All worlds in a
matched group inside that family copy the assignment. The attribute names, units,
object identity rules, and measurement semantics remain versioned and shared. A
world family can extend the schema only through an explicit protocol version.

For example:

```text
attraction family:
  orange anchor: mass=1.0 kg, radius=0.08 m
  blue probe:    mass=0.1 kg, radius=0.03 m

falling family:
  orange source: mass=2.0 kg, radius=0.10 m
  blue object:   mass=0.2 kg, radius=0.04 m
```

The values may differ between those families. The p=2 and p=3 attraction worlds
must retain the same orange/blue values.

Within each family, visible color is a stable object identity cue and different
colored objects must have different values for every attribute intended to be
distinguishable. If two colored objects intentionally share an attribute value,
that equality must be explicitly recorded as part of the task design rather than
arising accidentally from generation.

### Shared intrinsic tools

The autonomous experiment interface should include the applicable intrinsic
tools in every family:

```text
inspect_object
measure_mass
measure_volume
measure_geometry
measure_density
measure_inertia
```

Family-specific tools are added to the same catalog:

```text
falling world:       measure acceleration, track fall, measure event time
attraction world:    measure force, apply impulse, track motion
drag world:          release object, track motion, measure terminal behavior
spring world:        displace object, measure restoring force, track oscillation
contact world:       bounce test, slide test, measure impact response
```

The agent receives one combined tool catalog and plans the sequence itself. It
may measure mass before a force experiment, measure geometry before a collision
experiment, or decide that an attribute is unnecessary. The environment must
never call an attribute tool automatically, recommend a measurement based on
the hidden rule, or return a private correctness signal.

### Attribute visibility conditions

The object registry and tools must support explicit disclosure conditions:

| Condition | Public information | Experimental requirement |
|---|---|---|
| Calibrated | Selected attributes are shown initially | Tools remain available as a control |
| Hidden | Appearance is shown, physical value is withheld | Agent must measure or infer it |
| Partially disclosed | Bounds or one related value is shown | Agent measures the missing quantity |
| Relationally hidden | Object mass is known, coupling is hidden | Agent must use family-specific interaction tools |

The current autonomous attraction bench uses the hidden condition for mass and
radius and exposes both intrinsic and attraction tools. Other world families
should use the same pattern rather than inventing separate object-measurement
interfaces.

### Shared experiment record

Intrinsic and family-specific actions belong to the same interaction record:

```json
{
  "tool": "measure_mass",
  "object_id": "probe",
  "measurement": {"value": 0.1, "unit": "kg"},
  "cost_units": 1,
  "world_id": "..."
}
```

The record must distinguish intrinsic measurements from relational observations,
but they share the same budget, turn count, clock, replay journal, and world
binding. A later question must use the exact world instance whose object
attributes generated the interaction evidence.

### Cross-family acceptance checks

Every new family should verify:

1. the shared object schema round-trips with the world record;
2. intrinsic tools return values belonging to only the selected object;
3. intrinsic results do not depend on an unselected partner or hidden equation;
4. family-specific tools remain separate from intrinsic measurements;
5. matched worlds expose identical intrinsic tool catalogs and schemas;
6. matched worlds copy the family-level object assignment exactly;
7. different colored objects have distinct intended attribute values;
8. object-property changes are recorded separately from equation changes;
9. the agent can invoke every advertised tool in an offline replay;
10. no attribute measurement is inserted automatically by the runner.

This makes object characterization a reusable experiment component while keeping
each world family responsible for its own interaction laws.
