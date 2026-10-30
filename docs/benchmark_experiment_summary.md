# Physics World Benchmark: Current Experimental Design and Implemented Pipeline

## 1. Research objective

This project studies whether a multimodal agent can discover and use an unfamiliar physical rule from interaction, rather than answer a visual question by matching appearance or memorizing ordinary physics.

The benchmark presents a rendered scene containing colored objects and a next-frame prediction question. The governing physical law is partly hidden from the agent. The agent must plan experiments, call environment tools, infer the active law and world constants, and then select the candidate image showing the target object at the next frame.

The central scientific question is:

> Can an agent identify a latent physical world model from limited experiments and use that model to make a counterfactual visual prediction in a new state?

The benchmark is intended to distinguish three abilities:

1. **Visual state tracking:** identifying objects, colors, positions, and motion from images.
2. **Scientific discovery:** designing informative interventions and using measurements to infer hidden object properties, world constants, and equations.
3. **Model-based prediction:** applying the inferred rule to a new initial state and selecting the correct next-frame image.

The candidate images are constructed to be visually similar. The alternatives differ by a small displacement from the simulated answer, reducing the value of nearest-image or coarse motion heuristics.

There are currently no reported model results. The repository contains the benchmark generation, interaction, rendering, and evaluation infrastructure at different levels of completion.

## 2. Benchmark unit and visibility policy

Each question is a short physical episode. A question contains:

- a world family and group;
- a rule level and hidden variant;
- a generated multi-object scene;
- object intrinsic attributes such as mass, charge, volume, area, or spring stiffness;
- initial positions and velocities;
- a start time and prediction interval;
- a target object;
- four rendered candidate images, labelled A–D;
- one correct candidate, normally A in the generated manifests.

Host-only records contain the complete scene, constants, hidden equation parameters, and answer key. Public question records expose only the information intended for the agent. Object attributes can be queried through experiment tools rather than being directly revealed in the public prompt.

World constants are shared within a group. Object attributes are sampled per question, and different colored objects have different values. A baseline world records the group constants and standard equations before any hidden rule transformation is applied.

## 3. World-family and group hierarchy

The current canonical world families are:

```text
world_instances/
├── central_force_dynamics/
├── kinematics_dynamics/
├── fluid_mechanics/
├── contact_mechanics/
├── dissipative_dynamics/
├── field_interactions/
└── elastic_dynamics/
```

Every family now uses three groups: `g1`, `g2`, and `g3`. A group is a separate world instance with its own fixed constants. Group constants are not assumed to equal real-world constants; this prevents an agent from solving by recalling standard values such as Earth gravity.

Each group has this structure:

```text
<family>/<family>_g1/
├── baseline/instance.json
├── rule_1/
│   ├── README.md
│   └── variant_1 ... variant_6/
├── rule_2/
│   ├── README.md
│   └── variant_1 ... variant_6/
└── combined_rule/
    ├── README.md
    └── variant_1 ... variant_6/
```

Each variant contains `q01` through `q15`. Therefore one group contains:

```text
3 rule levels × 6 variants × 15 questions = 270 questions
```

The seven families and three groups produce:

```text
7 families × 3 groups × 270 questions = 5,670 questions
```

## 4. Rule and difficulty design

The benchmark separates three kinds of world transformation.

### Rule 1: changed equation

The equation form is changed while the scene remains visually familiar. Variants increase in complexity from single power changes to logarithmic, time-dependent, coupled, and nested transformations. Examples include changing an exponent, changing the dependence on distance or extension, or coupling two variables.

### Rule 2: hidden field or coefficient function

The nominal equation is retained, but a coefficient varies with position, time, or both. The function may be linear, quadratic, logarithmic, periodic, coupled, or nested. The function is not disclosed directly to the agent and must be inferred from experiments.

### Combined rule

The equation transformation and hidden coefficient function are active simultaneously. This is the highest intended difficulty level because the agent must distinguish changes in equation structure from changes in a spatial or temporal field.

Within every variant, `q01`–`q15` use the same hidden rule but different initial positions, velocities, object properties, start times, and prediction intervals. All questions ask the same core task: predict the next frame.

## 5. World families and intended phenomena

### Central-force dynamics

This is the most mature family and the original attraction benchmark. The baseline interaction uses a pair force and acceleration:

```text
F = G m1 m2 q(x,t) / r^p
a_i = F_i / m_i
```

An optional radial-motion relation is used for scene construction and analysis:

```text
r(t) = r0 + vr t + 0.5 ar t²
```

The group changes the strength, reference distance, reference mass, and minimum separation. Scenes use an anchor and a moving probe.

### Kinematics dynamics

This family uses multi-object motion under a group-level acceleration field. It deliberately uses oblique multi-object trajectories rather than repeating a falling-body scene. Questions vary positions, velocities, object counts, and the target object.

### Fluid mechanics

This family covers buoyancy and fluid-mediated vertical motion. Group constants include fluid density, gravity, surface height, reference depth, and a separation threshold. Object volume and mass determine the intrinsic buoyant response.

### Contact mechanics

This family covers contact with a plane, normal response, damping, and friction. Group constants include normal stiffness, damping, friction coefficient, plane height, and a contact threshold. Scenes vary object mass, radius, position, and velocity.

### Dissipative dynamics

This family covers linear and quadratic drag under an external acceleration:

```text
F_drag = -c v
F_drag,quadratic = -c2 |v| v
F_net = F_external + F_drag
a = F_net / m
```

Group constants include linear drag, quadratic drag, external acceleration, reference speed, and minimum separation. Object mass, drag area, velocity, and position vary by question.

### Field interactions

This family uses object-specific charge-like attributes interacting with a spatial or temporal field:

```text
F_i = q_i E(x_i,t)
a_i = F_i / m_i
```

The field direction, strength, gradient, reference position, and reference time belong to the group. Charge is an intrinsic object attribute that can be measured through tools.

### Elastic dynamics

This family covers restoring and damped elastic motion:

```text
F_s = -k (r - L0) r_hat
F_d = -c v
F_net = F_s + F_d
a = F_net / m
```

Group constants include stiffness, damping, rest length, anchor position, and minimum separation. Object mass, local stiffness, position, and velocity vary by question.

## 6. Agent and harness design

The agent is connected through a harness rather than receiving the host record directly. The harness manages:

- model selection;
- temperature, seed, timeout, retry, and completion-token settings;
- turn limits;
- tool-call requests and results;
- interaction history;
- per-run model metadata;
- persistent interaction records.

The OpenAI-compatible harness is implemented in `src/harness/`. The interaction entry points are:

```text
interaction.sh
scripts/pipeline/interact_question.sh
scripts/pipeline/run_interaction.py
```

Interaction records are stored under:

```text
results/<family>/<group>/<rule>/<variant>/<question>/interaction/<MODEL>_<TIMESTAMP>/
```

The recorded metadata includes model name, temperature, seed, maximum completion tokens, turn limit, timeout settings, retry settings, and generation arguments.

The intended agent loop is:

1. Receive the public world context.
2. Decide which experiment tool to call.
3. Inspect measured state, object attributes, or baseline constants.
4. Update an internal world hypothesis.
5. Repeat within the interaction budget.
6. Finish the interaction without receiving the answer key.
7. Use the rendered context and interaction history during visual evaluation.

## 7. Experiment tools

The tools are designed to separate observable object properties from hidden world laws.

Object-property tools can expose intrinsic properties such as:

- mass;
- volume;
- radius or size;
- charge-like attribute;
- drag area;
- spring stiffness;
- color and object identity;
- material or contact parameters when defined by the family.

World-level experiment tools expose measurements obtained by interventions and observations. The agent is allowed to plan tool calls but is not told which tool is the correct one for a particular family. This tests tool selection as part of scientific discovery.

## 8. Rendering pipeline

The global renderer is:

```text
scripts/render_missing.sh
```

It supports selectors:

```bash
./scripts/render_missing.sh \
  --w fluid_mechanics \
  --r rule_1 \
  --v variant_1 \
  --q q01
```

The renderer skips complete folders and resumes incomplete folders. CUDA is selected with `DEVICE=CUDA`; CPU can be selected with `DEVICE=CPU`.

The output layout is:

```text
renders/<family>/<group>/<rule>/<variant>/<question>/
├── scene.json
├── choice_A.png
├── choice_B.png
├── choice_C.png
└── choice_D.png
```

The central-force renderer uses the calibrated motion-laboratory scene. The other families use the generic multi-object physics renderer and family-dispatched manifests. The renderer keeps the image candidates geometrically close so simple visual similarity is insufficient.

## 9. Evaluation protocol

Evaluation is separate from interaction. The evaluator receives:

- the rendered context image;
- the four candidate images;
- the recorded experiment history;
- the public question prompt.

The requested response is exactly one candidate letter: A, B, C, or D. The evaluator compares the model's answer with the host answer key and records per-question accuracy.

Evaluation records are stored under:

```text
results/<family>/<group>/<rule>/<variant>/<question>/evaluation/<MODEL>_<TIMESTAMP>/
```

The intended metric is next-frame prediction accuracy. Results should also be stratified by:

- family;
- group constants;
- rule level;
- hidden variant difficulty;
- number and type of tool calls;
- interaction turns and measurement budget.

## 10. Resource-aware evaluation slice

Because the full benchmark contains 5,670 questions, a resource-limited experiment uses:

```text
variants: variant_1, variant_2, variant_3
questions: q01, q03, q05, q07, q09, q11
all groups, rules, and families
```

This gives:

```text
7 families × 3 groups × 3 rules × 3 variants × 6 questions = 1,134 interactions
```

The corresponding selectors are:

```bash
./interaction.sh \
  --v variant_1,variant_2,variant_3 \
  --q q01,q03,q05,q07,q09,q11 \
  --model qwen3.8-max \
  --temperature 0.7 \
  --seed 42 \
  --max-completion-tokens 8192

./eval.sh \
  --v variant_1,variant_2,variant_3 \
  --q q01,q03,q05,q07,q09,q11 \
  --model qwen3.8-max \
  --temperature 0.7 \
  --seed 42 \
  --max-completion-tokens 8192
```

The selector implementation treats the informal `q011` reference as `q11`.

## 11. Current implementation status and limitations

Implemented and usable:

- seven world-family directory hierarchies;
- three groups per family;
- baseline, rule, variant, and question records;
- hidden equation and hidden-function metadata;
- deterministic question generation;
- central-force world runtime and mature interaction environment;
- generic runtimes for the six additional families;
- object and world state representations;
- family-dispatched rendering;
- resumable rendering with CUDA/CPU selection;
- model-parameter recording;
- comma-separated interaction/evaluation selectors;
- visual candidate-image evaluation records.

Important limitations for the paper:

- The benchmark has not yet produced a final scientific result table.
- The generic family runtimes and generic renderer need validation against family-specific numerical reference trajectories before they should be described as fully validated physical simulators.
- Interaction-task wiring for all non-central families must be checked end-to-end before claiming equivalent tool-use coverage across every family.
- Rendered images and interaction records are large; auxiliary Blender artifacts should be removed or archived to stay within storage quotas.
- A pilot subset should be used first to verify that every selected question has images, an interaction record, and a valid evaluation record.

## 12. Intended paper contribution

The intended contribution is a controlled benchmark for interactive physical reasoning in which visual prediction is conditioned on discovering a latent world model. The benchmark varies the source of difficulty independently: unfamiliar constants, altered equations, hidden coefficient fields, object-specific attributes, and combinations of these transformations. Because questions within a variant share the same hidden law but differ in initial conditions, success requires rule inference and transfer rather than memorizing one trajectory.

The benchmark is therefore designed to test whether an agent can move from:

```text
observe → intervene → measure → infer latent law → predict counterfactual image
```

rather than merely:

```text
inspect image → choose the visually closest candidate
```
