# Hidden height-dependent air drag

Two profiles are available: the original two-layer baseline in `configs/drag_lab.yaml`
and a fixed, smooth random function in `configs/drag_lab_complex.yaml`. The latter
is described below under **Complex random height function**. Both use the same
drop/bounce instruments and transfer the saved world to image evaluation.

This environment extends the experimental-learning stage with **two invisible
horizontal drag layers**. The agent chooses drop heights and receives only
first-impact times and first-rebound heights. It never receives a trajectory,
the actual layer boundary, or the actual drag coefficients from an instrument.

The first version uses one calibrated blue sphere (0.1 kg, radius 0.03 m), known
gravity (default 3 m/s²), and known normal restitution (default 0.8). These are
public calibration values so drag identification is not confounded with unknown
mass, gravity, or restitution. Colors do not encode drag.

## Run without an API

```bash
conda activate agent_reproduce
cd agent_reproduce
python -m src.envs.drag_lab --demo
```

The scripted computational reference policy takes four broad measurements,
fits candidate profiles using only public observations, then takes three further
measurements around its estimated boundary. It submits a refined profile. This
is a numerical-search reference, **not an LLM evaluation or proof of optimal
experiment selection**. It needs at least seven measurements. No SciPy, CUDA,
Blender or external API is required. Profile fitting can take several seconds.

To issue your own experiments, omit `--demo` and enter one JSON object per line,
or use `--actions path/to/actions.jsonl`. `--output-dir` must be empty.

```json
{"operation":"bounce","specimen_id":"sample_A","surface_id":"surface_1","release_height_m":1.2}
```

The response includes `time_to_first_impact_s` and `first_rebound_height_m`, rounded
to the public instrument resolutions (both 0.001 in the default configuration).
The observation also includes the requested release setting and remaining budget.

```json
{"operation":"drop","specimen_id":"sample_A","release_height_m":0.4}
{"operation":"inspect"}
```

`drop` returns only impact time. Both instruments use the same drag physics and
consume one measurement per valid action. `inspect`, invalid actions, and profile
submissions are free. Waiting does not expose intermediate states. Each trial
starts from rest with empty apparatus; the notebook and budget persist.

## Run a model

With your usual `OPENAI_BASE_URL` and `OPENAI_API_KEY` already configured:

```bash
bash scripts/interact/interact_drag_lab.sh --model 'YOUR_MODEL'
```

Equivalent command:

```bash
python eval.py \
  --tasks identify_drag \
  --config configs/drag_lab.yaml \
  --mode interact \
  --model 'YOUR_MODEL' \
  --max-turns 32 \
  --output-dir results/drag_lab
```

The model has `submit_action` and `finish`. It submits its inferred profile using:

```json
{"operation":"submit_drag_estimate","boundary_height_m":1.1,"lower_drag_kg_s":0.08,"upper_drag_kg_s":0.25}
```

These are illustrative submission values, not the configured truth. Submission
only acknowledges receipt. Models can update estimates without receiving score
feedback. The standard API timeout/retry settings apply. There is no Python tool
in this project's model interaction harness; the offline reference has numerical
search capability that the evaluated LLM does not automatically receive.

Default budget: 12 measurements. `--max-turns` limits model turns separately;
submissions also consume turns. Do not compare model results across different
budgets without recording that difference.

## Physics and height conventions

The synthetic stationary medium applies linear drag in all velocity components:

```text
F_drag = -b(z) v
dv/dt = (0, 0, -g) - b(z) v / mass
b(z) = b_lower below the hidden boundary, b_upper above it
```

`b` has units kg/s; `b/mass` has units 1/s. Either layer can have stronger drag.
The declared family has a boundary in [0.2, 1.8] m and coefficients in [0, 0.5]
kg/s. Authored episodes require a coefficient difference of at least 0.02 kg/s.
The model is told the family and parameter bounds, not episode-specific values.

**The field uses sphere-centre height above the floor.** Release and rebound
heights use bottom clearance. Thus a release height `h` starts at centre height
`h + radius`; floor contact occurs at centre height `radius`. Do not equate the
release setting with the field's centre-height coordinate.

The force opposes velocity on both descent and ascent. Consequently
`sqrt(rebound_height / release_height)` does not directly recover restitution.
At impact, vertical velocity becomes `-e * incoming_vertical_velocity`;
horizontal velocity is unchanged instantaneously but continues to experience
drag during flight. Buoyancy, spin and inter-object collisions are absent.

`src/worlds/layered_drag.py` solves motion analytically within each layer, locating
boundary crossings and floor impacts by bisection and treating apexes explicitly.
There is no fixed simulation step that can skip a thin layer. `advance(...)`
provides arbitrary-time 3D states with repeated collisions for subsequent visual
scenes. Very small normal rebounds (<1e-7 m/s) become sustained floor contact;
horizontal drag continues. This approximation and solver version are recorded.

This is an idealized two-layer dissipative medium, not a claim about ordinary
atmospheric stratification or a full fluid solver.

## Private scoring and records

The main score is predictive rather than exact parameter recovery: the submitted
profile predicts eight additional release heights, each counted correct when
both impact time and rebound height errors are at most 0.005 s and 0.005 m.
Probe settings close to measurements already taken are shifted to keep them
unmeasured. These probes and their outcomes remain host-only. Parameter errors
are separately recorded as diagnostics. Missing estimates score zero.

This is an **interaction-stage numerical transfer score**, not image accuracy.
Finite noisy/rounded observations do not guarantee unique profile recovery; the
score does not claim they do. Quantization is present; stochastic noise is not.

Every run records, before the first experiment/model request:

- `world.json` / `world.md`: exact hidden profile, gravity, units, solver and identity.
- `object_registry.json` / `.md`: sphere identity, appearance and geometry.
- `contact_registry.json` / `.md`: fixed restitution, world/object linkage, drag enabled.
- `private_manifest.json`: complete restorable episode and apparatus settings.
- `parameters.md`, `task_parameters.md`: physics, measurements and score definition.

The offline CLI adds `public_transcript.json`, `config_resolved.json`, and
`private_evaluation.json`. Model runs save `interaction.json` and private scoring
through the existing runner. API failure still leaves the episode and completed
conversation checkpoint. Reusing a directory with different physics is rejected.

### API timeout and retry settings

The `interact_drag_lab.sh` command defaults to **5 retries** after the initial
attempt (6 total attempts), a **120-second connection timeout**, and **900-second
read/write/pool timeouts**. It prints the resolved settings at startup. Retry
delays are 5, 10, 20, 30 and 30 seconds. These are per-network-operation limits,
not a total run deadline. SDK-internal retries remain disabled; the harness owns
the single retry budget.

Explicit environment variables override these script defaults:

```bash
OPENAI_MAX_RETRIES=5 OPENAI_CONNECT_TIMEOUT=120 OPENAI_TIMEOUT=900 \
  bash scripts/interact/interact_drag_lab.sh --model 'YOUR_MODEL'
```

Restart the command to apply changed settings; an already-running process keeps
its original client configuration. Direct `python eval.py` calls use the shared
harness defaults (3 retries, 60-second connect, 600-second read/write/pool) unless
these variables are set. This change does not add automatic run resumption.

As of 2026-09-24, **interaction turns are skipped after API timeout retries are
exhausted**. For example, after turn 4 fails its initial request and all 5 retries,
the runner records a skipped turn and proceeds to turn 5. Completed observations
and environment state are retained; no experiment is executed for the failed
request. The next model request receives a short timeout notice asking it to
continue from completed observations. The skipped turn consumes a model turn,
but no measurement budget. `interaction.json` includes a `skipped_turns` list
with turn number, error type, reason and `action_executed: false`.

This behavior is bounded by `--max-turns`. If all remaining requests time out,
the run ends at the turn limit with `finished: false`; its latest estimate, if
any, is still privately scored. A score of zero without an estimate is not by
itself evidence of failed physical reasoning; inspect skipped turns. Only
`APITimeoutError` is skipped: authentication, validation and programming errors
still propagate. The image-question evaluator's failure behavior is unchanged.
The previous interrupted run is not resumed automatically. Restart the normal
interaction command to use this behavior; no new CLI flag is needed.

Reload an episode for host-side simulation with
`DragLabEnv.from_private_manifest(json.loads(path.read_text()))`. The restored
world/object/contact combination must match exactly. These private records must
never be provided as model evidence; only the public interaction history may
transfer to the later visual task.

## Validation

Tests cover the vacuum limit, a uniform-drag closed form, independent RK4
integration, layer crossings in both directions, repeated impacts, energy
dissipation, arbitrary-time state consistency, hidden-data boundaries, malformed
actions, budgets, persistence, failed API checkpoints, and public-only reference
prediction in worlds with either ordering of layer strength.

There is also a controlled ambiguity check: two worlds with the same lower
layer and different upper layers produce identical low-drop readings, but
different high-drop readings. This establishes that experiment height can matter;
it does not establish a general benchmark difficulty or model accuracy result.

```bash
python -m unittest discover -s tests -p 'test_drag_lab.py' -v
```

## Image context question evaluation

The drag visual test is separate from the existing no-drag bounce batch. It uses
the saved `LayeredDragWorld` and the exact same specimen and contact registry.
Each of eight questions contains a context image and four candidate images at
one specified elapsed time. The initial height and horizontal velocity are read
from the context image. The text does not name the specimen color or disclose
the hidden profile. The uniform grid does not mark layer boundaries.

Correct positions come from the same event-based solver as the instruments;
distractors use alternative drag profiles with the same gravity, mass and
restitution. The original **legacy** batch separates options by at least 0.07 m,
with balanced, shuffled answer labels. This first visual batch uses one sphere and tests falling/rebound states;
it is a transfer baseline, not evidence that the task will be difficult for every
model. Experiments were vertical drops, whereas these launches also require
applying the learned drag law to horizontal motion.

To reproduce the legacy batch from a saved interaction (no rendering or API call):

```bash
python -m src.simulation.drag_scene \
  --candidate-mode legacy \
  --run-dir results/drag_lab/identify_drag_20260922_202456 \
  --output-dir renders/lab_5/drag_prediction
```

Render 40 images on CUDA, preserving one folder per question and recording each
render's parameters in Markdown:

```bash
bash scripts/render/render_drag_prediction.sh --device CUDA
```

The wrapper uses 1920×1280 pixels. Open
`renders/lab_5/drag_prediction/index.html` to review the questions. Then evaluate:

```bash
bash scripts/eval/eval_drag_prediction.sh \
  --model 'YOUR_VISION_MODEL' \
  --record results/drag_lab/identify_drag_20260922_202456/interaction.json
```

This reuses the saved public experiment transcript, including the model's
inferences, even if the vision model differs from the experiment model. It does
not rerun experiments. Private world files, answer keys and interaction-stage
scores are not sent to the model. The same API environment variables are used;
the wrapper defaults to 5 retries, 120-second connect and 900-second read/write/
pool timeouts. Add `--prepare-only` after rendering to validate and snapshot the
inputs without calling a model.

Results appear in `results/drag_evaluation/<timestamp>/`:

- `evaluation_with_history.json`: answers, correctness and image accuracy.
- `model_requests.jsonl`, `model_responses.jsonl`: public inputs and full responses.
- `run_parameters.json`, `parameters.md`: source record hash, model names and settings.
- `drag_prediction/`: snapshot of rendered inputs, questions and private records.
- `interaction.json`: the reused experiment history.
- `summary.json`, `summary.md`, `status.json`: completion and image score.

The evaluator checks world identities, recomputes candidate trajectories, and
rejects missing/stale images before making API calls. With a new world, choose
a new batch output directory and pass it to both commands using `--output-dir`
(renderer) and `--batch-dir` (evaluator). The fixed launch design can reject a
world if it cannot produce four sufficiently separated outcomes.

Offline validation: `python -m unittest discover -s tests -p 'test_drag_prediction.py' -v`.

### Close candidates (default for newly prepared batches)

As of 2026-09-28, scene preparation defaults to `--candidate-mode close`.
It perturbs complete drag profiles near the saved truth and simulates all four
outcomes. Every pair of sphere centres must be **2–8 cm apart**, and all four
must have the same impact count and vertical motion direction. This removes
widely separated or different-bounce-phase distractors. It does not alter
gravity, restitution, launch state, sphere appearance, camera, or elapsed time.
The correct profile's rank among the four local perturbations is shuffled and
balanced; the truth is not always the centre option. Answer letters are also
balanced independently.

Blender checks actual camera projections before rendering and rejects centres
less than **6 pixels apart**. At the wrapper's 1920×1280 resolution, the prepared
seed-42 complex batch has minimum pairwise separations of about 9 pixels.
These are geometric readability checks, not a measured guarantee of model or
human perceptual accuracy. The evaluator rechecks the physical constraints and
recorded projections before any API call. Preparation fails if it cannot find
a valid cluster; it never silently falls back to easy distractors.

The complex close-candidate batch now contains **16 questions / 80 images**.
`--count 16` extends a matching eight-question batch in place while preserving
its original scenes and renders. Eight new launch heights are added; each answer
letter and each correct-profile rank occurs four times across the full batch.
The default count remains eight for compatibility. A changed seed, world, or
candidate policy still requires a new directory; shrinking a batch is rejected.

```bash
python -m src.simulation.drag_scene \
  --run-dir results/drag_lab/identify_drag_20260924_114916 \
  --output-dir renders/lab_5/drag_prediction_complex_close --count 16

bash scripts/render/render_drag_prediction.sh \
  --output-dir renders/lab_5/drag_prediction_complex_close --device CUDA

bash scripts/eval/eval_drag_prediction.sh \
  --model 'qwen3.8-max' \
  --record results/drag_lab/identify_drag_20260924_114916/interaction.json \
  --batch-dir renders/lab_5/drag_prediction_complex_close
```

Each new batch includes host-only `candidate_audit.json`: integrate the saved
submitted estimate (when present in `private_evaluation.json`), several constant
drag baselines, and the true world, then pick the nearest candidate using exact
coordinates. These diagnostics bypass image perception and are **not model
evaluations**. They do not influence scene selection. On the prepared complex
16-question batch, the saved estimate gets **8/16**, constant baselines
get **4–6/16**, and the true world gets **16/16**. On its original eight questions,
the saved estimate got **4/8** (versus **8/8** on the older widely separated
batch). No finite multiple-choice test
can eliminate guessing or nearest-choice reasoning with an accurate prediction;
the enforced guarantee concerns candidate geometry. Fine-grained image accuracy
also remains distinct from the interaction's 5 ms / 5 mm numerical score.

Offline close-policy tests: `python -m unittest discover -s tests -p 'test_drag_close_candidates.py' -v`.

## Complex random height function

`configs/drag_lab_complex.yaml` selects `profile_type: smooth_random`. The host
draws 13 control values uniformly from [0.01, 0.30] kg/s at heights 0, 0.25, …,
3.0 m, with private seed 42. Between adjacent points `(z_i, b_i)` and
`(z_next, b_next)`, it defines:

```text
u = (z - z_i) / (z_next - z_i)
w = 3*u*u - 2*u*u*u
b(z) = (1-w)*b_i + w*b_next
F_drag = -b(z)*velocity
```

This yields a nonnegative, continuously differentiable curve with multiple
peaks and valleys. The coefficient at a given height is fixed: it is not drawn
again each time the ball visits that height. Outside [0, 3] m, endpoint values
remain constant. Changing `profile_seed` creates a different reproducible world;
changing `profile_knot_count` (3–65) changes its spatial complexity. Heights refer
to the sphere centre above the impact surface, not the room floor or bottom of
the sphere. Gravity remains 3 m/s² and restitution remains 0.8.

The system records the exact control points, interpolation, extrapolation, seed,
units and integration settings in private `world.json`/`world.md` and the private
manifest. A preview of the configured world is saved in
`results/drag_worlds/smooth_random_seed42/`, including `profile.md`,
`drag_profile.png`, and a sampled `drag_profile.csv`. This is a world preview,
not a completed model run. None of those files are model inputs.

The agent knows the stationary linear-drag law and public bounds [0, 0.5] kg/s,
but does not receive the private seed, number/location/value of control points,
plot, or trajectory. The instruments still return only first-impact time and
first-rebound height. Its estimate can use any permitted grid of 2–65 points,
with endpoints 0 and 3 m and minimum spacing 0.01 m:

```json
{"operation":"submit_drag_estimate","heights_m":[0,1,2,3],"coefficients_kg_s":[0.08,0.2,0.04,0.12]}
```

These are illustrative estimates, not ground truth. The public smoothstep rule
defines how the submitted approximation is evaluated between points. The host
does not require recovering the original grid. Scoring uses the same eight
held-out prediction checks, with 0.005 s / 0.005 m tolerances. The complex config
allows 24 measurements rather than the baseline's 12; report this budget when
comparing results. More complex functions may be underdetermined by a finite
set of rounded measurements. This implementation supports that investigation;
it does not assert that every private function is uniquely recoverable.

Run new experiments:

```bash
bash scripts/interact/interact_drag_lab.sh \
  --config configs/drag_lab_complex.yaml \
  --model 'qwen3.8-max' \
  --max-turns 64
```

The script still defaults to the original two-layer config when `--config` is
omitted. The existing fitted `--demo` policy is specific to two layers; use the
model or JSONL actions for the complex configuration.

For image evaluation, use a new batch directory. A batch for the configured
seed-42 preview is already prepared in `renders/lab_5/drag_prediction_complex`.
Its frames use the full saved smooth function, and its question text does not
claim that the world has two constant layers. For a changed seed/config, prepare
from that new interaction directory:

```bash
python -m src.simulation.drag_scene \
  --run-dir results/drag_lab/YOUR_NEW_RUN \
  --output-dir renders/lab_5/YOUR_NEW_BATCH
```

Render the prepared complex batch and evaluate it using a **matching new
complex-world interaction**, not the earlier two-layer interaction:

```bash
bash scripts/render/render_drag_prediction.sh \
  --output-dir renders/lab_5/drag_prediction_complex --device CUDA

bash scripts/eval/eval_drag_prediction.sh \
  --model 'YOUR_VISION_MODEL' \
  --record results/drag_lab/YOUR_NEW_RUN/interaction.json \
  --batch-dir renders/lab_5/drag_prediction_complex
```

`src/worlds/height_drag.py` integrates all velocity components with RK4, a
maximum 0.002 s step, additional spatial/damping step limits, and bisected floor
and apex events. Instruments, private prediction scoring, and image generation
share this implementation. The old two-layer solver and saved world identities
are retained. Numerical checks compare against uniform-drag analytic solutions,
smaller integration steps, split trajectories, and repeated impacts:

```bash
python -m unittest discover -s tests -p 'test_height_drag.py' -v
```
