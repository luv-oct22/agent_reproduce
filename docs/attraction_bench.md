# Attraction experimental bench — step 4

The saved p=2 and p=3 worlds now support autonomous tool interaction through
`src/envs/attraction_bench.py`, `src/tasks/discover_world.py`, and the existing
model runner. Both worlds expose identical initial prompts, tool descriptions,
schemas, ordering, calibration, budgets, and apparatus rules. The agent chooses
its experiments; the runner does not select or recommend instruments.

This stage collects experimental evidence. The host-only
[learnability audit](attraction_audit.md) is now implemented. Numerical model
evaluation, rendered questions, and model scoring are subsequent stages.
There is no prediction score for an interaction merely because it called finish.

## Run with a target model

From the project root, with the project Python environment and existing API
credentials configured:

```bash
conda activate agent_reproduce
bash scripts/interact/interact_attraction.sh --model YOUR_MODEL \
  --config configs/attraction_p2.yaml --output-dir results/attraction_lab/p2

bash scripts/interact/interact_attraction.sh --model YOUR_MODEL \
  --config configs/attraction_p3.yaml --output-dir results/attraction_lab/p3
```

These commands make model API calls. Each creates a separate
`discover_world_<timestamp>` directory. Configuration filenames and private
world records are never passed to the agent. The script defaults to p=2 and
interaction-only mode. A lower `--max-turns` is allowed; the runner always caps
it at the protocol's eight turns and records the requested and effective caps.
Timeouts after harness retries consume a turn without executing an action.
No model API call is required to run the offline tests below.

## Apparatus behavior

| Tool | Operation | Cost |
|---|---|---|
| `inspect` | Appearance, calibrated mass/radius, clock, remaining budget, last commanded setup | 0 |
| `configure_trial` | Set probe position/velocity and trial start time; anchor stays at (0, 0, 1.5) m | 0 |
| `apply_impulse` | Apply a known impulse to the probe; acknowledge input without measuring velocity | 1 unit |
| `measure_force` | Instantaneous vector load on anchor or probe, excluding holding reaction | 1 unit |
| `track_motion` | Probe positions over a duration at equally spaced times | 1 unit per position vector |
| `finish` | End interaction, with no answer key or correctness feedback | 0 |

The episode budget is **24 units and eight model turns**. Multiple tool calls
in a response execute in their returned order and each incurs its own cost.
After successful finish, remaining calls in that response do not execute.
Unknown tools, extra/missing arguments, incorrect types (including booleans in
numeric fields), nonfinite values, and invalid finish arguments are rejected.
The agent cannot replenish its budget by configuring another trial.

Force components have 0.001 N resolution and range [-10, 10] N. Position
components have 0.001 m resolution and range [-5, 5] m. Values are clipped to
range, rounded with half ties away from zero, and accompanied by per-component
saturation flags. Internal physics continues from its exact state. Free
inspection reports the known trial setup, never the current unmeasured state.

Motion sampling accepts durations in (0, 3] seconds and 1–24 samples. For a
duration d and sample count n, samples occur at start + d*k/n for k=1,...,n;
the initial position is not an additional sample. The virtual clock is paused
between calls. Only motion tracking advances it, and an explicit new trial
can reset it within [0, 30] seconds. Force readings do not alter position,
velocity, or time. Configuring a trial restores the fixed anchor placement.

A malformed or unaffordable request costs nothing. A valid paid experiment
that fails because its trajectory cannot be completed within apparatus limits
is charged in full, returns a generic failure without partial readings, and
leaves state/time unchanged. This includes separation-boundary and clock-domain
failures. Trial configurations outside the domain are also rejected without
changing state. Failure responses do not expose solver diagnostics or hidden
force parameters.

The apparatus explicitly supports the saved `common_bench_v1` protocol (with
optional budget changes) and its two-object arrangement. It rejects unsupported
protocol variants rather than advertising tools it cannot execute. Additional
laws, hidden object properties, and varying coefficients require subsequent
runtime/apparatus versions and their own tests.

## Run records and replay

| File | Purpose |
|---|---|
| `interaction.json` | Actual public model messages, tool requests/results, finish state and skipped turns |
| `public_initial_observation.json` | Initial model-visible world/apparatus information |
| `world_instance.json` | Immutable host-only world, law, fields, protocol and solver |
| `initial_state.json` | Exact host-only initial physical state |
| `apparatus.json` | Shared versioned execution semantics supplied in the public prompt |
| `run_parameters.json` | Model name, requested/effective turn caps and tool catalog |
| `private_episode.json` | Current exact state, state fingerprints, charged budget and ordered action journal |

Private episode checkpoints are atomically replaced after dispatched actions.
The public conversation is also saved after completed tool batches and before
model requests. Private world/state fingerprints and exact evolved values never
enter the model messages. Rejected malformed arguments remain in the public
conversation; they are omitted from the replay journal to avoid persisting
nonstandard JSON such as NaN. The journal includes valid requests that fail,
including insufficient-budget requests, so cost/state behavior can be replayed.

Load `world_instance.json` into `AttractionBenchEnv`, then call `execute` for
each journal entry in order. Compare each returned public result, before/after
state fingerprints, and final state/budget. An integration test exercises this
replay together with the real runner using an offline scripted harness.
Do not feed `private_episode.json` or `world_instance.json` to a model.

Saved step-3 world instances and previews are unchanged. The historical
`attraction_pair_v1.json` records what had been implemented at its creation;
its `apparatus_implemented: false` is not a current runtime capability flag.

## Offline validation

```bash
python -m unittest discover -s tests -p 'test_attraction_bench.py' -v
python -m unittest discover -s tests -p 'test_interact_timeout.py' -v
python -m src.evaluation.drag_baseline verify --baseline baselines/drag_complex_close_v1
```

The [host-side learnability audit](attraction_audit.md) uses available quantized
measurements and the same budget to check whether plausible hypotheses remain
indistinguishable while predicting different held-out outcomes. Its reference
policies remain separate from the evaluated agent's experiment choices.
The [paired image suite](attraction_prediction.md) now prepares held-out scenes;
pixel rendering and the dedicated paired-world model evaluator follow.
