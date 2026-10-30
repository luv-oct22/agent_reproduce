# Autonomous experiment tool selection

Each Rule 1 question is an independent episode. Its question file supplies the
initial position, velocity, and start time; the group baseline instance supplies
the fixed world constants; and the hidden equation parameters are applied only
inside that episode. The agent plans the sequence and invokes tools through the
normal native-tool interface. The runner does not call a measurement
automatically or recommend which tool to use.

The combined catalog is:

```text
inspect
configure_trial
apply_impulse
measure_force
track_motion
finish
measure_baseline_force
inspect_object
measure_mass
measure_volume
measure_geometry
measure_density
measure_inertia
```

`measure_baseline_force` probes the matched standard world at a position chosen
by the agent. It is the baseline experiment for recovering group-level
constants; it does not expose the hidden Rule 1 equation. Intrinsic tools read
one object in isolation. Law tools read forces or motion in the attraction
world. A mass measurement therefore does not itself reveal an attraction force,
and a force measurement remains relational. All measurements consume the same
24-unit episode budget. The environment removes saved-world mass/radius
disclosures so the agent can choose to measure them.

Run the autonomous version:

```bash
./interaction.sh --w central_force_dynamics --r rule_1 --v variant_1 --q q01 \
  --model YOUR_MODEL
```

To run the complete Rule 1 batch, omit `--v` and `--q`:

```bash
./interaction.sh --w central_force_dynamics --r rule_1 --model YOUR_MODEL
```

The resulting record is written under
`results/central_force_dynamics/central_force_dynamics_g1/rule_1/variant_1/q01/interaction/`.

Private checkpoints store the exact shared state, charged budget and ordered
tool journal. The public conversation contains only the selected tool calls and
their sensor results. No model API call is made by the offline tests.
