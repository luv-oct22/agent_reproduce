# Session handoff: experimental learning and visual physics prediction

Updated: 2026-09-24 (Asia/Hong_Kong). Project: `agent_reproduce`.

This document is for a new session agent. The companion [mentor report](MENTOR_PROGRESS_REPORT.md) explains the research progression, trials, findings, and limitations.

**Newest result:** see [September 24 continuation](#september-24-continuation-complex-drag-interaction-result): Qwen's complex-drag interaction scored **1/8 (12.5%)** on held-out numerical predictions; its image evaluation has not been verified for that run.

## Latest change: skip exhausted-timeout interaction turns (2026-09-24)

User requested that a model turn be skipped after timeout retries are exhausted,
instead of terminating the whole interaction. Implemented in `src/interact.py`:

- The harness still retries the same request using its existing timeout/retry settings.
- If `harness.generate` finally raises `APITimeoutError`, the runner records the
  skipped turn, saves a checkpoint immediately, and advances the bounded turn loop.
- No experiment is executed and measurement budget is unchanged. All completed
  public observations and task state remain. A brief user-role timeout notice
  tells the next model call to continue from completed observations.
- `InteractionRecord.skipped_turns` stores turn/error/reason/action_executed metadata.
  Old records without the field still load. Each skipped turn counts toward
  `max_turns`; all-timeout runs end with `finished: false` and private scoring of
  the latest estimate, if any. Inspect skip metadata before interpreting scores.
- Authentication/validation/programming errors are not swallowed. Image-question
  evaluation is unchanged; this change is for interaction turns.
- No new flag: restart the normal interaction command to load the changed code.
  **Automatic resume is still not implemented**; rerunning starts a fresh run.
- Added `tests/test_interact_timeout.py` for skip/continue/checkpoint behavior,
  exhausted retry integration, bounded all-timeout runs, old-record compatibility
  and propagation of other errors. No real API requests are needed for these tests.

This supersedes the September 23 failure-handling description below. No paid
evaluation or rendering was started for this change.

## Project state recorded on 2026-09-23

**The latest work is an invisible height-dependent drag environment, including a complex random smooth function, and its image-context multiple-choice evaluation.** The user wants models to discover physics through experiments and transfer the learned knowledge to visual situations. They rejected treating the two-layer constant-drag example as sufficiently complex, while retaining it as a baseline option.

**Current request:** preserve the key history before this session ends. This file is the requested handoff. Do not automatically launch a paid API run or scene rendering in the next session. The user normally runs those commands themselves on CUDA. No model evaluation or rendering was started for this documentation update.

The sections below titled “Earlier baseline snapshot” preserve older project history. The latest sections here supersede earlier statements that drag is only proposed, that no drag image result exists, or that all inspected models score 100%. The English and Chinese mentor reports cover earlier material/bounce/NewtonBench work; they have not been updated with the new drag work in this documentation-only turn.

### Latest verified results and interrupted run

| Record | Status / result | Meaning |
|---|---|---|
| `results/drag_lab/identify_drag_20260922_202456/` | Qwen `qwen3.8-max`, finished; 12 measurements; numerical prediction score **8/8 = 100%** | Original two-layer drag interaction. Estimated boundary 0.848 m, lower b=0.03, upper b=0.18 kg/s. True boundary 0.85 m. |
| `results/drag_evaluation/20260923_100826_886940/` | **Complete, image score 7/8 = 87.5%**, Qwen for both stages | Verified from `summary.json` and `run_parameters.json` during this handoff. Reuses the above two-layer interaction and `renders/lab_5/drag_prediction`. This is NOT the complex-curve task. |
| `results/drag_evaluation/20260923_095409_079204/` | Failed, `APITimeoutError` | Earlier image evaluation attempt; not a completed accuracy result. |
| `results/drag_lab/identify_drag_20260923_100643/` | Qwen complex-curve interaction; **3 assistant turns saved, `finished: false`** | User's latest run failed requesting turn 4/64 after all five retries. Saved world is `height_drag_world`, seed 42. No completed numerical or complex-image accuracy result. |
| `results/drag_worlds/smooth_random_seed42/` | Host-only world preview and curve artifacts | Not a model interaction or accuracy result. |

The earlier conversation said drag image accuracy was not yet known. That was true before the completed image run appeared; the saved **87.5%** result now supersedes it. A numerical interaction score of 100% does not imply 100% image accuracy.

Other model comparisons already documented in the mentor reports:

- NewtonBench hard `m0_gravity`, complex_system, v0, no noise, code-assisted: Qwen **3/3 exact**, raw RMSLE 0; `gpt-5-mini` **0/3 exact**, mean raw RMSLE about 1.241738. The name is `gpt-5-mini`, not `gpt-5.5-mini`.
- Paired-world bounce images: Qwen **16/16**; GPT mini **5/16 = 31.25%**, paired score **2/8 = 25%**, despite both GPT world parameter scores being 100%. GPT result: `results/bounce_evaluation/20260922_103549_466816/`. Interaction turn budgets differed, so this is not a fully controlled comparison.

### Drag physics: two implemented choices

Shared law: **F_drag = -b(z) v**, applied to all three velocity components. `z` is sphere-centre height above the impact surface, not absolute room height. `b` has units kg/s; acceleration from drag is `-b(z)*v/mass`. Mass 0.1 kg, sphere radius 0.03 m, known gravity 3 m/s², known normal restitution 0.8. At an impact, vertical velocity reverses and is scaled by restitution; horizontal velocity is continuous but continues to damp during subsequent flight. No buoyancy, spin coupling, tangential contact friction, or object-object collisions.

1. **Two-layer baseline** (`configs/drag_lab.yaml`, still the default): b=0.03 below centre height 0.85 m; b=0.18 above it. The original immutable world is solved analytically within each layer with explicit crossing/impact events. Preserve saved world identities and old results.
2. **Complex random smooth profile** (`configs/drag_lab_complex.yaml`): `profile_type: smooth_random`, seed 42, 13 control points at 0, 0.25, …, 3 m, values sampled uniformly from [0.01, 0.30] kg/s. It has multiple peaks/valleys and stays fixed throughout an episode. Do not resample drag each timestep or each experiment.

For the configured complex profile, for `0 <= z < 3`, set `i=floor(4*z)`, `u=4*z-i`:

```text
b(z) = b_i + (b_(i+1)-b_i) * (3*u^2 - 2*u^3)
```

Control values in kg/s (rounded here; exact floats are in private `world.json`):

```text
[0.195433772, 0.017253119, 0.089758502, 0.074731114,
 0.223576652, 0.206242851, 0.268732075, 0.035212261,
 0.132357328, 0.018641194, 0.073405013, 0.156553034,
 0.017695431]
```

Outside [0,3] m, use the endpoint coefficient. General profiles support 3–65 randomly generated control points; a changed seed creates another reproducible curve. Interpolation is C1 smoothstep and preserves nonnegative coefficients. Function records also capture interpolation, extrapolation, coordinate convention, seed, solver settings and identity. The complex solver uses RK4 with maximum 0.002 s timestep, additional spatial/damping step limits and bisected impact/apex events. Instruments and image states share the solver. Normal rebound speeds below 1e-7 m/s become sustained floor contact.

Private curve preview: [profile.md](results/drag_worlds/smooth_random_seed42/profile.md), [plot](results/drag_worlds/smooth_random_seed42/drag_profile.png), and `drag_profile.csv`. These are for the researcher and MUST NOT be passed as model evidence.

### Agent interface and scoring

- Tools: generic `submit_action` and `finish`. There is **no Python execution tool** in this project's model harness; NewtonBench's code-assisted backend is separate.
- Actions: `inspect`, `drop`, `bounce`, `submit_drag_estimate`.
- Drop/bounce arguments: specimen `sample_A`, release height 0.05–2.5 m; bounce also names `surface_1`. Release/rebound heights are **bottom clearances**, while the coefficient field uses **centre height**.
- Instruments return first-impact time, and for bounce also first-rebound height, rounded to 0.001 s / 0.001 m. No trajectory or direct drag readings.
- Baseline measurement budget 12; complex config budget **24**. Model turn budget is separate (64 in the suggested complex command).
- Baseline submits `boundary_height_m`, `lower_drag_kg_s`, `upper_drag_kg_s`.
- Complex submits `heights_m` and `coefficients_kg_s` arrays: 2–65 points, endpoints 0 and 3 m, minimum spacing 0.01 m, coefficients [0,0.5]. These define the model's own smoothstep approximation, not a request for the hidden grid.
- The complex public prompt describes a fixed unknown smooth function and public bounds/estimate format. It does not disclose actual seed, grid size/locations/values, world hashes or private scores. Public prompts were checked for equality across different hidden seeds/grid sizes.
- Private score: fraction of 8 unmeasured probe heights whose predicted impact time AND rebound height are within 0.005 s AND 0.005 m of ground truth. Probe heights close to measured settings are shifted. Submission only acknowledges receipt; no correctness feedback enters the conversation.
- Finite rounded observations may not uniquely identify a complex function. The score measures held-out predictive performance, not exact function recovery. More complexity alone does not establish scientific validity or model difficulty.
- The scripted fitted `--demo` policy supports the two-layer baseline only. Complex worlds support actual LLM interaction and JSONL experiments; do not claim that a complex reference fitting policy is implemented.

### Drag implementation map

| File | Responsibility |
|---|---|
| `src/worlds/layered_drag.py` | Original two-layer world, exact per-layer propagation, drop/rebound readouts, arbitrary-time states |
| `src/worlds/height_drag.py` | Smooth random function generation/serialization, coefficient lookup, RK4/event integration; `load_drag_world` supports both world formats |
| `src/envs/drag_lab/scene.py` | Public instruments/budget, two profile types, immutable private manifests and restoration |
| `src/tasks/identify_drag/task.py` | Public task/actions, profile submission, private prediction scoring |
| `src/envs/drag_lab/__main__.py`, `demo.py` | Offline JSONL CLI and two-layer reference fit |
| `src/simulation/drag_scene.py` | Prepare 8 context-plus-four-choice questions using the saved world; handles both profiles |
| `src/simulation/blender_bounce.py` | Shared bounce/drag renderer, larger drag measurement grid, sphere visibility/size/clipping checks |
| `src/simulation/balance_batch.py` | Batch rendering dispatch, image/parameter/digest completeness checks |
| `src/drag_evaluate.py` | Match saved history/world, recompute candidate physics, snapshot inputs, evaluate and record scores |
| `src/interact.py` | Checkpoint conversation BEFORE each model request; no automatic resumption |
| `src/harness/openai.py` | API client timeout and retry policy |
| `scripts/interact/interact_drag_lab.sh` | Interaction wrapper, accepts `--config`, `--model`, `--max-turns` |
| `scripts/render/render_drag_prediction.sh` | CUDA rendering wrapper, default resolution 1920×1280 |
| `scripts/eval/eval_drag_prediction.sh` | Vision evaluation from a matching saved interaction |
| `docs/drag_lab.md` | Complete profile details, scoring, persistence and commands |

### Image batch status and rules

- **Baseline:** `renders/lab_5/drag_prediction/`, 8 questions, **40 PNGs now exist** (count verified during this handoff). Completed Qwen image run above. Earlier assistant statements that images were not rendered are outdated for this directory.
- **Complex:** `renders/lab_5/drag_prediction_complex/`, 8 question manifests prepared from the seed-42 private preview; **0 PNGs currently**. No completed complex model evaluation. The original batch was not replaced.
- Each question has one held-launch context and four candidate frames. Read initial bottom clearance and horizontal launch velocity from the image. No textual color disclosure or drawn drag profile. The same calibrated sphere is used.
- Correct frames use the true saved function. Distractors use alternate complete drag profiles; mass/gravity/restitution/time/camera remain fixed. Pairwise candidate position separation is at least 0.07 m; answer labels are balanced and shuffled.
- Geometry includes a uniform 0.10 m major / 0.025 m minor grid, no drag boundary markings. Hidden layers/profile are not drawn. The complex batch contains falling, rebound and one two-impact situation.
- Renderer emits per-image Markdown parameters and private scene/build records. Evaluator checks record/world/object/contact identities, scene/question consistency, reconstructed candidate physics and stale/missing images before making API calls.
- Evaluation shares the public experiment transcript (including model inferences), even with a different vision model. Private manifests/curve/answer keys are not sent. Outputs go to `results/drag_evaluation/<timestamp>/` with `evaluation_with_history.json`, model request/response JSONL, parameters, summary/status and input snapshots.

### Exact continuation commands

```bash
conda activate agent_reproduce
cd agent_reproduce

# NEW complex-world interaction (does not resume the failed one).
# OPENAI_BASE_URL and OPENAI_API_KEY must already be set locally.
bash scripts/interact/interact_drag_lab.sh \
  --config configs/drag_lab_complex.yaml \
  --model 'qwen3.8-max' \
  --max-turns 64

# Render the already-prepared seed-42 complex batch on CUDA.
bash scripts/render/render_drag_prediction.sh \
  --output-dir renders/lab_5/drag_prediction_complex \
  --device CUDA

# After a matching complex interaction completes, use its actual path here.
bash scripts/eval/eval_drag_prediction.sh \
  --model 'YOUR_VISION_MODEL' \
  --record results/drag_lab/YOUR_COMPLETED_COMPLEX_RUN/interaction.json \
  --batch-dir renders/lab_5/drag_prediction_complex

# If seed/config changes, prepare a NEW batch from that new run first.
python -m src.simulation.drag_scene \
  --run-dir results/drag_lab/YOUR_NEW_RUN \
  --output-dir renders/lab_5/YOUR_NEW_BATCH
```

The baseline record `identify_drag_20260922_202456` cannot be used as evidence for the complex world. Omitting `--config` on the interaction wrapper still selects the original two-layer world. A run directory must contain its matching private manifest; don't move `interaction.json` alone and lose that linkage.

### Latest failure: diagnosis and unfinished reliability work

User reported turn 4/64 retrying 1/5 through 5/5, then `openai.APITimeoutError` caused by `httpcore2.ReadTimeout` / `httpx2.ReadTimeout` at `_receive_response_headers`. This is waiting for an API response after connection, not a simulation exception. The initial request plus five retries failed. Provider processing delay/congestion, gateway or network issues are possible; the traceback does not identify the root cause. No live provider test was performed and no new fix was applied after this error.

Drag wrappers default to **900 s read/write/pool timeout, 120 s connect timeout, 5 retries**, delays 5/10/20/30/30 s. Existing environment variables override defaults. Shared direct-Python harness defaults remain 600/60 s and 3 retries. These are per-network-operation/per-attempt limits, not a global run deadline. Increasing connect timeout does not address this particular read timeout; blindly adding retries is not a confirmed fix. SDK internal retries are disabled.

`results/drag_lab/identify_drag_20260923_100643/interaction.json` preserves the three completed assistant turns and public tool responses. `finished` is false and there is no `private_evaluation.json` for that interrupted run. Ground-truth world/object/contact records were saved before calls and remain available. **Automatic resume is not implemented.** Rerunning creates a fresh timestamped run. The next agent may investigate the endpoint or implement safe resume if requested; do not invent a resume flag or report the interrupted run as a physics failure/zero accuracy.

Other open work: run the complex evaluation, inspect why the baseline image run missed one item, compare models/budgets systematically, and distinguish insufficient evidence from visual or dynamical reasoning failures. These are open research directions, not automatic authorization to execute paid runs.

### Verification and environment notes

- During implementation, 6 `test_height_drag.py` tests and 12 `test_drag*.py` tests passed (18 total). Coverage: deterministic profile/record integrity, hidden-data boundaries, uniform-drag analytic reference, finer-step convergence, repeated impacts/energy loss, restoration, scoring, prior two-layer behavior, image history sharing and failure checkpoints.
- The baseline image implementation also passed 16 existing bounce tests; eight baseline Blender builds were checked without pixel rendering at that time. Complex image generation and matching validation were checked for all eight questions using temporary image fixtures. Fixtures are not real rendered scenes or model scores.
- No tests were rerun for this documentation update. Don't infer current completeness of all tests from those scoped earlier passes.
- Conda Python: `/home/brainpp/miniconda3/envs/agent_reproduce/bin/python`. Local Blender: `.tools/blender-3.6.23-linux-x64/blender`. Renderer honors `BLENDER_BIN`.
- For agent shell tools use `login: false`; shell startup may print environment data. Never dump credentials. `MPLCONFIGDIR=/tmp/agent_reproduce_mpl` avoids Matplotlib cache permission warnings.
- `git status` reported this project is not a Git repository. Avoid assuming commits/worktrees exist.
- Existing reports: `MENTOR_PROGRESS_REPORT.md`, `MENTOR_PROGRESS_REPORT_ZH.md`; prior advice: `newtonbench_experiment_advice.md`. The user requested a Chinese mentor version, which already exists. This handoff contains the newest drag state that those reports do not yet cover.

## Earlier baseline snapshot (2026-09-22)

The following sections preserve the earlier research history. For drag, model comparisons, latest results and next actions, use the 2026-09-23 sections above.

The research objective is to test whether a model can **learn hidden physical properties or world rules through experiments, then transfer that knowledge to a different, visually presented situation**. The experiment interface supplies observations, not ground-truth properties. The visual evaluation requires identifying objects and reading the scene from images.

The project has working material-identification, balance-image, liquid-equilibrium-image, gravity-identification, and bounce-identification/prediction components. The latest completed harder balance and bounce runs still score 100%. The next research decision is how to make discovery and transfer meaningfully harder. The user started testing the separate NewtonBench repository to identify useful model weaknesses before changing this environment further.

At the time of this earlier snapshot, the authorized task was documentation: create this handoff and a mentor report. Subsequent drag work is described above. Do not interpret historical requests as authorization to start a new render or paid evaluation automatically.

Evidence for this handoff is the supplied conversation history plus local source, documentation, manifests, and saved results inspected on 2026-09-22. Earlier assistant replies/tool outputs are incomplete in the supplied history. Historical requests, verified implementation, and proposed work are therefore distinguished. No model evaluation, render, or test suite was rerun while preparing these documents.

## User preferences and established constraints

- Work in `agent_reproduce`; the separate baseline repository is `../NewtonBench`.
- The user prefers to run expensive rendering on their CUDA machine. Provide executable commands when asked; do not silently launch rendering.
- Keep the accepted Panda ball-to-cup distance unchanged. Only `renders/lab_1/far_distance/` is retained as the Lab 1 render variant. The earlier `fra_distance` spelling was a typo.
- Save readable Markdown parameters for every render, including actual placement, physics, camera, and timing. Preserve question folders and run-specific snapshots.
- In evaluation question text, do not reveal object colors or identities. Recognition and counting should come from images. Public experiment observations may describe specimen colors/shapes so they can later be matched.
- Material scenes preserve recorded cube shapes and colors. Equal-volume evaluation samples share material density; their masses need not equal the original experimental specimen masses.
- Support separate experiment and vision model names. The user intends to specify these; do not assume the historical model is a permanent preference.
- Keep model responses, parameters, evidence, and scores under the project's results directory.
- Prefer immediate, concise replies and meaningful progress updates. The user became frustrated by long periods without responses and eventually canceled earlier work. Do not ask again about already settled distance/shape/model-separation preferences.

## Architecture and information boundaries

```text
Private object/world/contact records
          |                        |
          v                        v
Experimental apparatus       Scene/trajectory generation
          |                        |
Public measurements          Context + candidate images
          |                        |
          +--> experiment history -+--> vision model --> private grading
```

- `src/objects/registry.py`: immutable specimen properties, geometry, appearance, and registry identity. Saved as `object_registry.json` and `.md` before the first model request.
- `src/worlds/uniform_gravity.py`: shared constant-gravity world; saved as `world.json` and `.md`.
- `src/worlds/contact_registry.py`: specimen–surface restitution and contact assumptions; saved as `contact_registry.json` and `.md`.
- `src/worlds/bounce_motion.py`: free-flight/contact event propagation used for bounce scenes.
- `src/interact.py`: tool-calling interaction loop, public conversation record, private artifact persistence.
- `src/evaluate.py`: builds history context and image questions, parses answers, checkpoints scores. History includes assistant text, tool calls, and public tool observations; this is context transfer, not weight training or persistent model memory.
- `src/harness/openai.py`: Chat Completions harness with explicit network timeouts and bounded retries.
- `src/density_pipeline.py`: fresh material interaction followed by balance or liquid image evaluation.
- `src/bounce_evaluate.py`: validates/snapshots bounce batches, uses the matching history for each world, reports per-world and paired accuracy.

Ground-truth registries, private manifests, grading results, and answer keys are **host-only**. They must never be supplied to the evaluated model. A result JSON can contain both questions and answer keys for research bookkeeping without those keys being included in model requests; inspect request construction/logs when auditing leakage. These environments enforce a tool-interface boundary, not an OS sandbox against a model with host filesystem access.

## Current components

| Component | What the model does / what is rendered | Verified state |
|---|---|---|
| Panda scene, Lab 1 | Articulated robot throw visualization; ball/table/cup physics | Accepted far-distance scene and 10-second video exist |
| Material lab | Compare balance pans and reference weights; measure displaced water; infer mass, volume, density | Implemented; completed model runs |
| Balance images, Lab 2 | Match known materials, count equal-volume cubes, predict heavier pan or Unknown | Six-question baseline and 32-question harder batch rendered and evaluated |
| Liquid images, Lab 3 | Infer liquid density from a floating known cube; choose the image with all four equilibria correct | Eight questions rendered; inspected evaluation is incomplete |
| World lab | Infer constant gravity from timed drops | Implemented separately from density pipeline |
| Bounce lab | Infer gravity and constant restitution from drops/rebounds | Implemented; completed model interaction |
| Bounce images, Lab 4 | Infer launch geometry from images; predict both spheres after repeated impacts | Current 16-question paired-world batch rendered and evaluated |
| NewtonBench comparison | Discover an unfamiliar force equation using experiments and Python | Separate repository; three successful hard trials inspected |

### Lab 1: accepted render

Source: [render record](renders/lab_1/far_distance/simulation_10s_parameters.md), [configuration](configs/robotics_lab_panda_far_distance.yaml).

- Video: `renders/lab_1/far_distance/simulation_10s.mp4`.
- Ball release position `[-0.4, -0.12, 1.32]` m; velocity `[0.9, 0, 0.6]` m/s; radius `0.025` m; recorded mass `0.1` kg.
- Cup opening center `[1.1, -0.12, 1.08]` m; horizontal release-to-cup distance **1.5 m**; radius `0.085` m; height `0.22` m.
- Recorded gravity `[0, 0, -9.8]` m/s²; step `0.001` s; post-release simulation `1.2` s.
- Video: 10 seconds at 24 FPS, 1-second opening/closing holds, 8-second motion playback from 1.85 seconds of source animation. Slow playback does not change physical launch velocity.
- Clipping was a historical concern; cup geometry/contact handling and geometry tests exist. The renderer/physics still use an approximate contact model, and the robot animation is not a validated hardware controller. No fresh collision or video inspection was performed for this handoff.
- Some parameter records were backfilled from saved artifacts and workflow defaults; their provenance is explicitly recorded.

### Material and density tasks

Read [material lab](docs/material_lab.md), [registry contract](docs/object_registry.md), [combined pipeline](docs/density_pipeline.md), and [hard density suite](docs/density_balance_hard.md).

The public material actions are `inspect`, `balance`, `displace`, and `submit_estimates`, via `submit_action`; `finish` ends interaction. A scripted `--demo` is an offline reference policy, not an LLM score. Default apparatus: 48 measurements, 0.5 g balance tolerance, 1 mL cylinder graduation, 3% property-scoring tolerance. Invalid actions do not replenish the budget. Submission acknowledgements do not reveal correctness.

The balance context is held level before release; it does not imply equal mass. Choices show left down, right down, level, or an Unknown card with large text over a blurred level scene. The harder batch has 32 questions: 18 known-material sums, 8 ambiguous unseen-material cases, 6 unknown-material cancellation cases. Each pan holds 1–3 objects; default sample volume is 60 mL. Four outcomes each occur eight times. Unseen evaluation-only materials stay outside the experiment registry. Unknown is based on identifiability over unspecified positive densities, not the hidden density sampled for rendering metadata.

### Liquid task

Read [liquid scene documentation](docs/liquid_equilibrium.md). Batch: `renders/lab_3/liquid_equilibrium/`; 8 questions / 40 PNG files exist.

The context contains one partially floating known-material cube. For upright homogeneous cubes, `rho_liquid = rho_object / submerged_fraction`. Choices contain four cubes; one complete image has all four states correct. There is no Unknown card. The tank has a 0.28 m cubic interior; volume conservation updates the surface when objects displace liquid. Guides maintain upright cubes and horizontal bands aid depth reading. These are static equilibrium illustrations, not fluid-dynamics videos.

Liquid visibility was revised after user feedback: tinted surface, water-level outlines, subdued glass reflections, neutral background, and disabled refraction for this measurement view. Do not make the images harder by obscuring the surface.

### Gravity and bounce tasks

Read [world lab](docs/world_lab.md), [bounce lab](docs/bounce_lab.md), and [bounce image evaluation](docs/bounce_prediction.md).

Changing `g` to 3.0 **m/s²** changes a parameter; it does not discover a new functional law. Gravity cancels from ideal static balance and floating-fraction equations, so motion is required to evaluate learned gravity.

Bounce public operations include `inspect`, `drop`, `bounce`, `balance`, `displace`, `submit_world_estimate`, `submit_contact_estimates`, and optional material estimates. Default budget: 16 measurements; drop clock and rebound-height resolution: 0.001 s / 0.001 m. The model sees impact times and rebound heights, not hidden gravity/restitution. Heights denote bottom clearance above the surface, not absolute center elevation. Gravity tolerance is 3%; restitution tolerance is 0.03 absolute. Material score is diagnostic and does not affect bounce success.

Host-only primary world: `g=3.0`; restitution A/B/C/D = 0.60/0.85/0.35/0.75. Paired world: `g=4.05`; restitution A/B/C/D = 0.72/0.74/0.47/0.64. Same sphere appearances, different physics. Air drag, spin coupling, tangential friction, and object–object collisions are absent.

The current batch has 8 paired situations / 16 questions / 80 PNGs. Paired questions share images and wording but require different answers from world-specific evidence. Each question has two spheres; options are the four combinations of their two candidate states. Both must be checked. Initial clearances and speeds come from images. Multiple impacts, shuffled balanced answer positions, geometry checks, and visual measurement tolerances are implemented. The old eight-question batch is archived under `renders/lab_4/bounce_prediction_archive_20260920_174658_067054/`.

## Verified result index

All listed completed model runs below use `qwen3.8-max`; do not generalize them to all models.

| Record relative to this project | Observed result | Interpretation |
|---|---|---|
| `results/material_lab_eval/identify_material_20260917_121422/` | Property score 1.0; 46 experiments | Original material interaction |
| `results/density_pipeline/20260917_140220_830401/` | Properties 1.0; images 6/6; 39 experiments | Completed simple balance pipeline |
| `results/density_pipeline/20260917_141142_433050/` | Properties 1.0; images 6/6; 30 experiments | Another completed simple balance run |
| `results/density_pipeline/20260917_154458_439374/` | Properties 1.0; images 6/6; 32 experiments | Another completed simple balance run |
| `results/density_pipeline/20260917_162329_143006/` | Properties 1.0; images 32/32; 46 experiments | Harder balance still saturated |
| `results/density_pipeline/20260918_200352_896919/` | Properties 1.0; 39 experiments; 4 saved image answers, all correct | Incomplete liquid evaluation: 8 questions total, stored score 0.5 |
| `results/bounce_lab/identify_bounce_20260920_162018/` | Gravity/contact score 1.0; 10 experiments | Saved world-1 interaction |
| `results/bounce_evaluation/20260920_164350_437670/` | 8/8 | Original easier bounce batch |
| `results/bounce_evaluation/20260920_180559_829666/` | 16/16; each world 8/8; paired score 1.0 | Harder paired-world bounce still saturated |

For liquid, the evaluator checkpoints `correct / total_questions`; four correct out of eight planned questions yields 0.5 even though no answered item is wrong. `status.json` still says `running/image_evaluation`, and there is no completed summary. This is not evidence that a process is currently alive or that the final accuracy was 50%. The reason execution stopped is not established by these inspected files.

Successful density runs save public interaction, private scoring, parameters, image snapshots, model request/response logs, status, and summary. `.blend` files stay in the source render directory. Failed/partial runs also exist; status and answer counts must be checked before reporting a score.

## Commands for continuation

Existing Conda environment directories include `agent_reproduce` and `newtonbench` under `/home/brainpp/miniconda3/envs/`. Activation/package functionality was not retested for this documentation task. Shell commands below assume Conda is initialized. Rendering also needs Blender with an appropriate device; Python environment activation alone does not enable GPU rendering.

```bash
conda activate agent_reproduce
cd agent_reproduce

# Set your real endpoint/key locally; do not put credentials in reports.
export OPENAI_BASE_URL='https://YOUR_API_HOST/v1'
export OPENAI_API_KEY='YOUR_API_KEY'

# Fresh experiments plus all 32 balance questions; images already exist.
bash scripts/eval/run_density_pipeline.sh \
  --model 'YOUR_EXPERIMENT_MODEL' \
  --eval-model 'YOUR_VISION_MODEL' \
  --batch-dir renders/lab_2/density_balance_hard

# Fresh experiments plus liquid questions.
bash scripts/eval/run_density_pipeline.sh \
  --model 'YOUR_EXPERIMENT_MODEL' \
  --eval-model 'YOUR_VISION_MODEL' \
  --batch-dir renders/lab_3/liquid_equilibrium

# Bounce evaluation: reuse world 1, acquire a separate world-2 interaction.
bash scripts/eval/eval_bounce_prediction.sh \
  --model 'YOUR_VISION_MODEL' \
  --experiment-model 'YOUR_EXPERIMENT_MODEL' \
  --record results/bounce_lab/identify_bounce_20260920_162018/interaction.json

# Only when rendering is requested, on the CUDA machine:
bash scripts/render/render_bounce_prediction.sh --device CUDA
bash scripts/render/render_liquid_equilibrium.sh --device CUDA
```

In the density pipeline, omitting `--eval-model` uses `--model` for both stages. Both use the same environment-based URL/key and timeout/retry settings. Separate names do not prevent evidence sharing: the second model receives the public first-stage history. Separate provider credentials are not exposed as per-stage CLI options in this pipeline.

New invocations create new timestamped runs. Request retries do not automatically resume a failed run. Bounce can reuse a matching second-world record with `--world-record world_002=PATH/interaction.json`. See the task docs for `--prepare-only` and rendering options.

## API and command problems already encountered

| Problem | Diagnosis / implemented response | Remaining limitation |
|---|---|---|
| `httpx.ConnectTimeout` / `openai.APITimeoutError` | Connection/read failure; SDK timeout explicitly configured in `src/harness/openai.py` | Longer timeouts cannot fix an unavailable endpoint |
| HTTP 400 `Download multimodal file timed out` | Provider-side multimodal ingestion timeout; exact message included in retry predicate | Other invalid requests should still fail immediately |
| Retry warnings followed by a correct answer | Earlier attempts failed; a later attempt succeeded and was graded | Retries increase latency and may increase provider usage |
| Lost progress concern | Per-exchange/answer checkpoints and status files | No general automatic run resume |
| Bash lines ending in backslash plus spaces | Backslash must be the final character | Use clean copyable commands |
| NewtonBench `-agent_backend` rejected | Correct spelling: `--agent_backend` or `-b` | Argument syntax, not model failure |
| NewtonBench judge HTTP 503 `model_not_found` | Agent and judge are distinct calls; old `gpt41` alias requested unavailable `gpt-4.1-2025-04-14` | Judge failure still becomes Boolean False in upstream scoring code |

Current harness defaults: connect timeout 60 s; read/write/pool timeout 600 s; 3 retries after the initial attempt, delays 5/10/20 s. Overrides: `OPENAI_CONNECT_TIMEOUT`, `OPENAI_TIMEOUT`, `OPENAI_MAX_RETRIES`. SDK-internal retries are disabled to avoid multiplied retry budgets. Connection errors, HTTP 408/409/429/5xx, and the named image-download timeout are retried. These are per-operation/per-attempt limits, not an entire-run deadline.

## NewtonBench handoff

Repository: `../NewtonBench`. Existing conceptual notes: [NewtonBench experiment advice](newtonbench_experiment_advice.md). The earlier notes reference the paper; this handoff does not constitute a fresh paper/literature review.

```bash
conda activate newtonbench
cd ../NewtonBench
python run_experiments.py \
  --model_name qwen3.8-max \
  --module m0_gravity \
  --agent_backend code_assisted_agent \
  --equation_difficulty hard \
  --model_system complex_system \
  --law_version v0 \
  --noise 0.0 \
  --trials 3
```

The completed record is `evaluation_results/qwen3.8-max/m0_gravity/code_assisted_agent/hard/v0/complex_system_noise0_0_v2/`. All trials recovered `F = 6.674e-5 * (mass1 + mass2)^2 / distance^1.5`. Aggregate: RMSLE 0, exact accuracy 100%, 7.33 rounds, 27 experiments, 23,859.67 tokens per trial, 654.17 seconds total, no whole-trial retries. Trials 0/1/2 used 50/12/19 experiments and 9/6/7 rounds.

The model estimated acceleration from short-time velocity changes, multiplied by the moving mass to recover force, varied masses/distance, recognized squared total mass and a distance exponent of -1.5, and checked the relationship with Python. This suggests complex trajectory observations can still permit straightforward force identification when early velocity samples are precise.

Useful weaknesses visible despite correct final laws: large experiment-count variation; trial 0 produced some uninformative or numerically unsuitable experiments; trial 1 had attempted follow-up actions with no returned measurements; trial 2 received an action-format reminder. Distinguish proposed experiments from executed measurements. Do not assert the exact parser cause without further investigation.

Judge locations: `../NewtonBench/run_experiments.py` (currently assigns `judge_model_name = "qwen3.8-max"`, around line 227), `../NewtonBench/utils/call_llm_api.py` (model alias mapping), `../NewtonBench/modules/common/evaluation.py` (`llm_symbolic_equivalence_judge`, around line 149; returns False after failures). This is a hardcoded judge choice, not a documented new CLI flag.

The easy run `.../easy/v0/vanilla_equation_noise0_0_v1/` reports numeric RMSLE 0 but exact accuracy 0; its submitted expression matches the recorded law's form and it used `gpt41`. Treat this as a judge-disagreement/infrastructure audit item, not established failed law discovery. The exact cause for that specific easy record is not proven by its aggregate JSON.

## Unfinished work and recommended next decision

1. **Difficulty remains unresolved.** The harder density and paired-world bounce tasks are still solved perfectly in the inspected completed runs. These are small pilots, not broad capability or novelty evidence.
2. **Complete/audit the liquid evaluation.** Four correct saved answers are not a completed eight-question result. Check logs/process state before deciding whether to reuse evidence or run again.
3. **Analyze discovery efficiency and protocol failures.** NewtonBench exposes weaknesses beyond final correctness: wasted measurements, action formatting, and numerical experiment design. Quantify these before importing a new task design.
4. **Move from constants to relationships if authorized.** Speed-dependent restitution `e(v)`, controlled drag, competing hypotheses, restricted measurement budgets, and held-out physical regimes remain proposals; they are not implemented in the current bounce world.
5. **Run diagnostic controls deliberately.** Known-physics + images, evidence + exact numeric scene, fixed experiments, and budget curves could isolate perception, discovery, and transfer. Evidence removal is an information-ablation/shortcut control; it may make the task unidentifiable and must not be presented as an equally solvable exam.
6. **Improve reliability separately from science.** General resume and judge-error-versus-wrong-answer separation remain open. A functioning alternative judge is only a workaround for the earlier unavailable judge.
7. **Scale across independent worlds/runs.** The earlier suggested 12 worlds × 8 questions with repeated interactions is a proposal, not a completed study. Paired questions sharing a world/history are not independent discoveries.

Documentation drift: `docs/material_lab.md` still calls visual stage 2 future work; `docs/object_registry.md` describes the original cube-only stage. Later task docs, current code, and saved runs take precedence for implemented capabilities. This handoff supplements those files; it does not rewrite them.

Tests exist for registries, instruments, rendering records/geometry, balance/liquid/bounce batches, pipelines, timeouts, and retries under `tests/`. A conventional command is `python -m unittest discover -s tests -v`; no fresh pass is claimed here. Existing renders were counted, not visually reinspected during this task.

## September 24 continuation: complex-drag interaction result

Appended on 2026-09-24 at the user's request to preserve the newest conversation.
The result below was rechecked directly against `interaction.json` and
`private_evaluation.json` while writing this update. It supersedes statements
above that no scored complex-world interaction exists. It does not turn the
earlier September 23 interrupted run into a completed run.

### Timeout skipping is implemented and exercised

The user requested skipping a model turn after its API timeout retry budget is
exhausted. `src/interact.py` now does this, preserves experiment state/history,
adds a short continuation notice, and records `skipped_turns` in the saved
interaction. Skips consume the turn budget but no experiment budget. This is
bounded by `max_turns`; authentication and other non-timeout errors still raise.
Image-question timeout handling is unchanged. No automatic resume was added.

Five new timeout tests and 36 relevant regression tests passed during that code
change (**41 tests total**). These were offline tests, not API evaluations. No
tests or rendering were rerun for this append-only history update.

### New complex-world run: 12.5% numerical accuracy

Record directory: `results/drag_lab/identify_drag_20260924_114916/`.

| Item | Verified result |
|---|---|
| Model | `qwen3.8-max` |
| World | `height_drag_world`, complex smooth random profile, matching `configs/drag_lab_complex.yaml` and `renders/lab_5/drag_prediction_complex` at the previous input check |
| Interaction-stage score | **1/8 = 12.5%** |
| Meaning of a correct probe | Both first-impact-time error <=0.005 s and first-rebound-height error <=0.005 m |
| Experiments used | **24**, the configured measurement budget |
| Submitted estimate | Present: a 32-point `heights_m` / `coefficients_kg_s` approximation, recorded in `private_evaluation.json` |
| Termination | User log: `Max turns (8) reached`; saved `finished: false` |
| Timeout skip | **Turn 7**, `APITimeoutError`, `action_executed: false` |
| Image accuracy for this record | **Not yet verified**; do not report 12.5% as image accuracy |

The 12.5% score grades the last submitted function even though the model did not
call `finish`. All 24 measurements were used; the timeout did not erase them.
This is a run affected by an 8-turn limit and a skipped timeout, not proof that
all models fail to identify the function. The previously suggested command used
64 turns, but this actual run's log reports **8**; the reason for that change has
not been established. Preserve the actual run budget in comparisons.

Keep these three distinct results separate:

- Two-layer interaction: Qwen **8/8 numerical**, record `identify_drag_20260922_202456`.
- Two-layer image evaluation: Qwen **7/8 visual**, result `20260923_100826_886940`.
- Complex smooth-function interaction: Qwen **1/8 numerical**, record `identify_drag_20260924_114916`.

### User's preferred short interaction command

The user found the combined render/interaction/evaluation shell block too
complicated and preferred this familiar interaction-only command:

```bash
bash scripts/interact/interact_drag_lab.sh \
  --config configs/drag_lab_complex.yaml \
  --model 'qwen3.8-max' \
  --max-turns 64
```

This creates a fresh timestamped run under `results/drag_lab/`; it does not
render, run image evaluation, or resume an old interaction. The timeout-skip
behavior is enabled without a new flag.

### Next commands already given to the user

The saved 8-turn history can be used for visual evaluation even with
`finished: false`; label that protocol limitation when interpreting the result.
The last pre-evaluation check found **0/8 complete renders** for the complex
batch. Rendering/evaluation may have been started externally afterward, so
check current artifacts before declaring their present state.

From `agent_reproduce`, with the
`agent_reproduce` Conda environment active:

```bash
bash scripts/render/render_drag_prediction.sh \
  --output-dir renders/lab_5/drag_prediction_complex \
  --device CUDA

bash scripts/eval/eval_drag_prediction.sh \
  --model 'qwen3.8-max' \
  --record results/drag_lab/identify_drag_20260924_114916/interaction.json \
  --batch-dir renders/lab_5/drag_prediction_complex
```

Evaluation results go to `results/drag_evaluation/<timestamp>/`, reuse the
matching public interaction history, and record model responses and parameters.
No API evaluation or scene rendering was launched by the assistant while giving
these commands or appending this update. No new complex-image score is claimed.

## September 28: visual-score audit and close-candidate generator

The completed complex image evaluation in
`results/drag_evaluation/20260928_144241_206146/` scored **8/8**, using the
September 24 interaction whose numerical score was **1/8**. The old generator
maximized candidate separation. An offline exact-coordinate nearest-choice
check using that submitted curve also scored 8/8; private answers/curves were
not found in the recorded model requests. Audit artifacts are in
`results/analysis/drag_evaluation_20260928_144241_206146/`.

At the user's request, newly prepared drag batches now default to
`--candidate-mode close`. `src/simulation/drag_candidates.py` constructs complete
nearby drag profiles, simulates their outcomes, and enforces **2–8 cm separation
for every pair**, equal bounce count, and equal vertical motion direction.
Correct-profile ranks and answer letters are independently shuffled and
balanced. Candidate selection does not consult the submitted estimate.
The Blender renderer checks **at least 6 pixels** between candidate centres
before rendering; the evaluator checks physical bounds and saved projections.
`--candidate-mode legacy` preserves the original generation behavior; previously
saved legacy batches remain evaluable. Existing scenes/results were not changed.

Prepared eight new scenes in `renders/lab_5/drag_prediction_complex_close/`
from `results/drag_lab/identify_drag_20260924_114916/`. Its host-only
`candidate_audit.json` reports the saved estimate's nearest-choice result
**4/8**, constant-drag baselines **1–2/8**, true-world predictions **8/8**.
These bypass image perception and are not new LLM results. Similarity is
enforced geometrically; eliminating every guessing strategy is not guaranteed.

Verification: **27 offline tests passed** (17 drag, 6 height-drag, 4 bounce
prediction). A Blender 3.6.23 build-only check of Q1 in `/tmp` passed at
1920×1280, measuring 9.216 pixels minimum centre separation. This produced no
images. The new batch currently has **0 PNGs**; no paid API call was made.

Next: render with `bash scripts/render/render_drag_prediction.sh --output-dir
renders/lab_5/drag_prediction_complex_close --device CUDA`, then evaluate with
the September 24 interaction and `--batch-dir
renders/lab_5/drag_prediction_complex_close`. Full commands and limitations are
in `docs/drag_lab.md`, under “Close candidates”.

### September 28 follow-up: expanded to 16 questions

At the user's request, `renders/lab_5/drag_prediction_complex_close/` now has
**16 questions**, adding eight distinct launch heights. The first eight had
already been rendered by the user before this expansion: **all 128 original
question artifacts are byte-for-byte unchanged**, and all eight original
renders still pass completion checks. There are currently **40 PNGs**; the
new questions Q009–Q016 need 40 additional images, for 80 total.

`src.simulation.drag_scene --count 16` safely extends a matching eight-question
batch or prepares a fresh 16-question batch. Shuffling in fixed blocks preserves
the original scenes; each answer letter and correct-profile rank occurs four
times overall. The default remains eight. Different batches and shrinking an
existing batch are rejected. Similarity and motion-phase constraints are unchanged.

The expanded offline audit gives the submitted estimate **8/16**, constant-drag
baselines **4–6/16**, and the true world **16/16**. This is not a model evaluation.
**19 drag tests passed**, including prefix preservation and 16-question physics
and balance checks. Blender geometry/visibility/projection checks passed for
all eight new questions at 1920×1280 without rendering images or writing scene
artifacts. No model API call was made.

Run the same render command above: it skips Q001–Q008 and renders Q009–Q016.
The evaluation command/path is unchanged and now evaluates all 16 questions.

## September 30: architecture for multiple physical worlds

The user proposed three composable transformations: different physical equations
(e.g. inverse-cube attraction), object-specific properties that may be hidden
while color stays visible, and coefficients varying with space/time under
specified or hidden functions. The intended pipeline remains experiments,
history-conditioned prediction, and image evaluation in the same saved world.

Design recorded in `docs/world_benchmark_architecture.md` and linked from README.
It distinguishes law families, sampled world instances, scene initial conditions,
and model runs; proposes shared versioned law/field interfaces with existing
solvers retained; and specifies public/private projections, clock semantics,
calibration/identifiability audits, fixed evaluation suites, and staged migration.
The suggested first new family is constant-coefficient central attraction with
p=2 versus p=3 and calibrated objects, followed by hidden object properties and
spatial/temporal fields. These generalized components are **proposed, not yet
implemented**. No existing results were moved and no rendering/API run occurred
while writing the design.

The user additionally requires autonomous experimental-tool selection: provide
multiple interfaces, but do not tell the model which ones to use. Added
“Agent-selected experimental interfaces” to the architecture document. It
specifies a shared apparatus/tool catalog across matched worlds, neutral API
documentation, measurement-only feedback, explicit costs/clocks, and no
world-specific tool filtering or experiment recommendations. Private scoring
stays inaccessible. Tool choice and experiment design belong to the model.
The current disclosed-law drag interface remains a baseline; the common tools
and unguided discovery track are still design proposals, not runtime changes.

## September 30: first migration step completed — frozen drag baseline

Created `baselines/drag_complex_close_v1/`, an independent versioned snapshot of
the 16-question close-drag suite (80 PNGs, scene/world/object/contact records,
Blender files, build reports), matching historical evaluations and source
interactions, and current implementation/configuration files. The snapshot's
`baseline.json` records SHA-256 checksums for 459 files plus run provenance.
Existing working render/result folders were not moved or rewritten.

Historical completed image scores on this exact suite: Qwen **6/16**, GPT
**9/16**, Opus **10/16**. All three submitted-estimate numerical scores are
**1/8**. Actual measurements used: **24, 24, 11**, respectively; Qwen did not
finish its interaction, GPT and Opus did. Do not imply identical experimental
effort or infer unrecorded turn budgets. Incomplete matching evaluation attempts
are archived separately with their statuses and are not completed scores.

Added `src/evaluation/drag_baseline.py` with `freeze` and `verify` commands.
Verify checks all archived bytes and recomputes candidate physics using the
current implementation. It makes no API calls and performs no rendering.
Freezing refuses an existing destination. Files are independent copies, not
hard links; checksums detect changes but do not enforce filesystem immutability.

Run `python -m src.evaluation.drag_baseline verify --baseline
baselines/drag_complex_close_v1` in the project environment after relevant
physics/evaluation changes. Guide: `docs/drag_baseline.md`, linked from README.
Validation: freeze-time integrity/physics checks passed; **27 tests passed**
(21 drag tests, including corruption and overwrite protection, plus 6 height-drag
tests). All 269 working batch files also matched their frozen copies afterward.
Next planned step is the shared world-record contracts, not a new renderer yet.

## September 30: step 2 implemented — shared world-record contracts

Added `src/worlds/definition.py` with immutable, versioned JSON-backed records:
`LawSpec`, `FieldSpec`, `ObjectSpec`, `ContactSpec`, `SolverSpec`, `ProtocolSpec`,
`WorldSpec`, and `WorldInstance`. Validation checks component IDs/references,
coefficient units, finite/bounded values, sampled-height ordering, contact rules,
clock/reset consistency, budgets, tool-schema envelopes, instrument resolution,
and measurement costs. Standalone/nested records have SHA-256 fingerprints;
deserialization detects inconsistent fingerprints and unknown schema versions.
Input and returned dictionaries cannot mutate the internal record. Saving a
different record over an existing one is refused.

Public observations use explicit disclosure selectors; appearance remains public.
The law-discovery track rejects active-law/field disclosure. Protocol tool catalogs
are authored independently of hidden physics, and `require_same_public_interface`
checks matched worlds' entire public observations. Descriptions still need author
review; structural validation cannot detect all semantic hints in arbitrary prose.

Added `src/worlds/drag_adapter.py` to convert either legacy drag profile type and
restore the existing environment/solver after checking agreement. Legacy solvers,
prompts, evaluator paths, saved images and baseline records were not modified.
The adapter describes the original disclosed-law protocol; it does not implement
the planned common apparatus or change the legacy interaction harness.

Saved `world_instances/drag_complex_close_v1/instance.json` from the frozen
private manifest. Its turn limit is null because the world manifest does not
record a run's turn budget. Guide: `docs/world_records.md`, linked from README
and the architecture document. The contracts describe constant/height/time
fields and normalized central attraction, but new field evaluation, attraction
integration, tool execution/cost enforcement and scene clock handling remain
future implementation work. Solver names are descriptors, not dynamic imports.

Validation: **37 tests passed** (10 new contract/adapter tests, 21 drag tests,
6 height-drag tests). The new tests verify hidden-world public equivalence,
round trips/corruption, units/references/disclosures, clocks/measurement metadata,
and exact legacy instrument readings and trajectories. The frozen baseline's
459-file integrity and physics verification also passed. No rendering or model
API calls were performed. Next step: implement the attraction physics family
using these records, then bind the shared experimental tools.

## September 30: step 3 implemented — constant attraction physics

Added `src/worlds/attraction.py` with `AttractionWorld` and immutable, fingerprinted
`MotionState`. Runtime loads shared world instances and explicitly supports one
central-attraction law, p=2 or p=3, one constant coefficient field, spherical
objects, and fixed/dynamic bodies. It rejects unsupported compositions, solver
settings, spatial/temporal coefficients and contact rules. No dynamic imports
or fallback physics. Normalized strength A is in newtons; all pair forces are
equal/opposite and movable-body acceleration follows F=ma.

The engine exposes exact host-side forces, accelerations, RK4 advance, absolute-
time trajectories, and energy/momentum diagnostics. Fixed supports remain fixed.
States are bound to physical world IDs and validated against protocol clock
domains. Integration guards the strictly noncontact separation domain using
relative-speed/global-acceleration bounds and checks all stages/endpoints. It
raises `DomainError` when a safe step is too small or the iteration cap is hit;
it does not soften forces, bounce, accept partial trajectories, or mutate input
states. Conservative rejection near a boundary is not an exact collision time.

Added `src/worlds/attraction_setup.py`. Run `python -m src.worlds.attraction_setup
--output-dir world_instances` to reproduce two matched records:
`world_instances/attraction_p2_v1/instance.json` and
`world_instances/attraction_p3_v1/instance.json`. Both use a calibrated fixed
orange 1 kg sphere and dynamic blue 0.1 kg sphere, hidden A=1.2 N, centre cutoff
0.20 m, and the same public protocol/tool specifications. Public interfaces are
checked for exact equality; they do not disclose the exponent or strength or
recommend experiments. The common apparatus is still specified only, not
implemented. Pair metadata explicitly records that distinction.

Each folder contains a host-only `preview.json` with exact force probes and
four simulated states, not a model interaction or evaluation. At 1 m the probe
force is 0.12 N for both laws; at 2 m it is 0.03 N versus 0.015 N. No new images
or paid model calls were made. Existing attraction artifacts cannot be replaced
with different definitions by the preparation CLI.

Validation: **20 tests passed** (10 attraction, 10 existing contract/adapter).
Checks include analytical circular orbits, force scaling/reference units,
fourth-order timestep convergence, split trajectories, conserved quantities for
free pairs, inertial motion at zero strength, fixed supports, state/time binding,
high-speed forbidden-region rejection, supported-runtime guards and public
equivalence. Frozen drag baseline verification passed for all 459 files and
original candidate physics. Guide: `docs/attraction_world.md`.
Next step: implement the common experimental apparatus, including input handling,
sensor precision/costs and clock rules, before rendering/evaluating this family.

## September 30: step 4 implemented — autonomous experimental bench

Added `src/envs/attraction_bench.py` and `src/tasks/discover_world.py`. The saved
p=2/p=3 world instances now execute the same six named tools: inspect,
configure_trial, apply_impulse, measure_force, track_motion, finish. Initial
public prompts and tool catalogs are identical across the pair and contain no
active equation, exponent, strength, private fingerprints, or recommended
experiment sequence. The agent chooses tools and parameters itself.

The apparatus enforces the saved 24-unit budget and eight-turn cap. Impulses
cost one unit, force vectors cost one, and motion costs one per sampled position
vector. Sensors round at 0.001 N/m, clip to their recorded ranges, and return
per-component saturation flags. Exact evolved state remains private; inspection
only echoes the known commanded setup, calibration, clock and budget. Force
readings are instantaneous external loads excluding the holding reaction and
do not alter state/time. Tracking alone advances virtual time; explicit trial
configuration resets its start time without replenishing the episode budget.

Strict argument validation rejects missing/unknown fields, invalid IDs/types,
nonfinite numbers, out-of-range durations/counts, and malformed finish calls.
Unaffordable/malformed actions are free and do not execute. A valid paid action
that cannot complete within apparatus limits is charged in full with no partial
observations or state/time changes. Public failure messages omit private solver
diagnostics. Unsupported apparatus protocol/object arrangements fail at setup.
Broader law/object/field compositions remain future work.

`src/interact.py` now supports opt-in native tools via BaseTask hooks, preserves
the legacy submit_action path, caps protocol turns, records requested/effective
caps, dispatches batched calls in order, validates native finish arguments, and
saves the public conversation after completed batches. Existing timeout handling
continues to preserve state and charge skipped model turns without executing
actions. No answer key or score is returned by the new interaction task.

Each run saves interaction.json, public_initial_observation.json,
world_instance.json, initial_state.json, apparatus.json, run_parameters.json,
and an atomically replaced private_episode.json with current state, ordered
action journal, fingerprints and budget. Malformed actions remain in the public
conversation but are omitted from the private replay journal (which must remain
finite JSON). Valid failed requests are journaled. Tests replay readings,
impulses, trajectories, failures, time resets and final state/budget.

Use the project environment and existing credentials:

```bash
bash scripts/interact/interact_attraction.sh --model YOUR_MODEL \
  --config configs/attraction_p2.yaml --output-dir results/attraction_lab/p2
bash scripts/interact/interact_attraction.sh --model YOUR_MODEL \
  --config configs/attraction_p3.yaml --output-dir results/attraction_lab/p3
```

These commands are for the user to run; no paid API calls or rendering were
started. Existing world instances/previews and frozen baseline artifacts were
not changed. The pair index retains its historical step-3 creation flags;
`apparatus_implemented: false` there is not a live capability check.
Guide: `docs/attraction_bench.md`; README, architecture and runtime guides updated.

Validation: full unittest discovery passed **140 tests**; after final small
changes and adding one further replay test, **all 13 apparatus tests passed**.
Shell wrapper syntax checked. Frozen drag baseline verification passed all
459 files and original candidate physics (16 questions, three completed evals).
Next step: host-side learnability/identifiability audit with quantized readings
and the same budget, followed by held-out scene and image-question generation.
Do not supply the audit's reference experiment policy to evaluated agents.

## September 30: step 5 implemented — offline learnability audit

Added `src/evaluation/attraction_audit.py` and 12 regression tests in
`tests/test_attraction_audit.py`. Executed the host-only reference audit for both
saved attraction worlds, with results at
`results/attraction_audit/attraction_pair_v1/report.md` and `audit.json`.
The bundle also includes immutable input-world copies, artifact checksums, and
hashes of the audit/apparatus/physics/record/setup source files. Existing world
instances, public agent interfaces, and historical artifacts were preserved.

The search varies exponent p in {2, 3} and constant strength A continuously over
the saved [0, 5] N bounds, holding other physics fixed. Fitting inverts rounded
force bins into conservative strength intervals and intersects them for each
exponent. Force-per-strength coefficients come from the authoritative simulator.
Saturation supplies a one-sided bound, not an exact force. Closed bin edges and
a 1e-12 N guard cover numerical/rounding boundaries. Fitting does not read the
true exponent or strength; a test substitutes different hidden values while
holding evidence fixed and verifies unchanged fitted intervals.

Six predeclared reference controls use actual AttractionBenchEnv tools and
enforce its units/turn limits: no measurements; one reading at 1 m; 24 repeated
readings at 1 m over eight turns; readings at 1 and 2 m; four distances; and a
0.21 m near-sensor-limit reading. These are host policies, never injected into
agent prompts or tools. No model calls or rendering were performed.

For transfer checks, sample 17 strengths per surviving interval and retain only
hypotheses whose full public apparatus transcripts replay exactly. Simulate two
new diagnostic launch states; record all sampled predictions, maximum pairwise
spread, and two extremal witness indices. Halve the timestep for truth and those
extremal witnesses. Separately propagate full continuous strength intervals to
force ranges at held-out distances 1.3 and 1.7 m. Position-spread tolerance is
5 mm, tested timestep discrepancy tolerance 0.05 mm, force-span tolerance 0.001 N.
The launch states are numerical diagnostics, not a frozen image-question suite.

Results for the default 17-sample audit:

- No measurements: both exponents plausible, maximum sampled spread 419.483 mm.
- One reading at 1 m, or all 24 units repeatedly at 1 m: both exponents remain
  plausible, maximum sampled held-out position spread 42.037 mm.
- Two readings at 1 and 2 m: correct exponent uniquely retained in the searched
  family, A approximately [1.195, 1.205] N. Maximum sampled position spreads are
  0.700 mm for p=2 and 0.391 mm for p=3. Both transfer checks pass.
- Four distinct distances: sampled spreads tighten to 0.394 mm and 0.082 mm.
- Near sensor limit: both exponents remain plausible; p=3 saturation retains
  broad strength intervals and a 367.578 mm sampled spread.

Both worlds pass the two-distance/four-distance reference controls. This shows
feasibility for a well-chosen experiment policy within a restricted hypothesis
family, not autonomous model success or benchmark difficulty. Arbitrary laws,
hidden masses and varying fields were not searched. Continuous force bounds
are conservative; trajectory spread is sampled, not a certified supremum over
continuous strength. No image readability or shortcut claim is implied. The
current simple pair is a learnable control; harder instances should be versioned
separately, not silently substituted.

Reproduce offline using a fresh directory (existing output is refused):

```bash
python -m src.evaluation.attraction_audit \
  --output-dir results/attraction_audit/attraction_pair_v1_repeat
```

Validation: **153 tests passed** in full unittest discovery, including all 12
new audit tests. Frozen drag baseline verification passed all 459 files and
original candidate physics. The saved audit bundle and implementation source
checksums were verified. Guide: `docs/attraction_audit.md`, linked from README,
architecture, runtime and bench guides.

Next step: define held-out attraction scenes and prepare a 16-question image
suite driven by the same saved world instances, then check candidate similarity,
visual distinguishability and shortcut baselines before a model pilot. The user
normally runs expensive rendering/model commands; do not automatically launch
those merely because the host feasibility audit is complete.

## September 30: step 6 implemented — sixteen paired attraction scenes

Prepared `renders/central_force_dynamics/paired_close_v1`: 16 questions in eight matched
pairs, eight questions per saved world, requiring 80 PNGs after rendering.
Added `src/simulation/attraction_scene.py` (prepare/validate/render CLI),
`attraction_visual.py` (standard-library geometry/projection checks usable in
Blender), `blender_attraction.py`, and
`scripts/render/render_attraction_prediction.sh`. Existing drag code and saved
world instances were not modified. Guide: `docs/attraction_prediction.md`.

Each adjacent question pair has identical public context, launch conditions,
choices, calibrations and camera, but different correct labels for p=2 and p=3.
Both true-law states are included among four options; the other two are simulated
p=2 strength variants. Every candidate comes from the saved authoritative solver,
not a manually displaced pose. Initial position/velocity are displayed to six
decimals, elapsed time to four decimals, exactly matching simulation inputs.
The blue probe moves in the x–z plane about the fixed orange anchor at (0,0,1.5).
No hidden-law label, force arrow, trail or answer hint is rendered.

Candidate generation uses predeclared launch/rank assignments, not baseline
scores. Initial draft trajectories that mixed inward/outward motion or required
a negative-strength distractor were rejected; the final launch set avoids those
cases. All candidate pairs are between 0.0239968 and 0.0720336 m apart; all
choices share the same radial motion phase. Truth inward-displacement ranks
0–3 and labels A–D are balanced twice each within each world. Timestep-halving
discrepancy is at most 2.27e-11 m across the final candidate states.

The suite copies and binds the successful learnability audit. For each scene,
nine strengths spanning its two-reading reference interval are simulated;
all sampled hypotheses still select the same correct option. Results and
margins are saved in `evidence_transfer.json`. This is a sampled transfer audit,
not a proof over all continuous strengths, and no reference policy is given to
the agent. The new launch scenes differ from the step-5 diagnostic launches.

`candidate_audit.json` reports exact-coordinate shortcut scores: nearest initial
position, nearest inertial prediction, nearest anchor and nearest candidate
centroid each score 4/16. Fixed p=2/A=1.2 and p=3/A=1.2 assumptions each score
8/16. Identical paired visuals with distinct answers imply a 50% ceiling for
a deterministic world-independent visual rule over this paired suite, not a
claim that every possible shortcut is at 25%. These are host diagnostics, not
model scores; a later pilot needs per-world results and no-history controls.

Ran Blender **build-only** for all 16 questions, saving 16 scene.blend files and
build reports. All 80 planned frames passed actual camera projection, object
framing, minimum sphere diameter, centre-ray visibility and text-framing checks.
Candidate centres are at least 9.21 pixels apart at 1920x1280. **Zero PNGs exist;
no pixel rendering or model API calls were performed.** Build checks establish
geometric readability, not final rendered-image appearance. Inspect the PNGs
after GPU rendering before a model pilot.

Prepared records include world copies, audit copy, scene/state fingerprints,
source hashes, routing, public question payloads, shortcut/evidence/physics
diagnostics and checksums. Validation recomputes candidate physics, answer
binding, rank balance, public-question consistency and evidence margins.
Render validation additionally requires scene-bound PNG hashes and dimensions,
per-image parameter records, a saved .blend, and actual projection checks.
Build-only reports are explicitly rejected by image-required validation.
GPU reruns skip already complete questions only when verified render settings
match. Build-only does not downgrade a completed image render record.

User commands in the project environment:

```bash
bash scripts/render/render_attraction_prediction.sh --device CUDA
python -m src.simulation.attraction_scene validate \
  --output-dir renders/central_force_dynamics/paired_close_v1 --require-images
```

Preparation uses a fresh directory and refuses overwrites. Physics-only
validation is `python -m src.simulation.attraction_scene validate`. The script
supports `--dry-run` and `--device CPU --build-only`. The bundled Blender lacked
the model API package, so renderer geometry imports were separated into the
standard-library-only attraction_visual module; no new dependency was installed.

Validation: **163 tests passed**, including ten new scene tests covering physics,
paired balance, private/public separation, transfer margins, shortcuts, mutated
poses/answers/worlds/ranks, projected geometry, stale/missing renders, checksum
corruption, overwrite protection and dry-run behavior. All 16 actual Blender
builds passed. Frozen drag baseline verification again passed all 459 files and
original candidate physics. Shell wrapper syntax passed.

Next: the user can render the 80 PNGs on CUDA. Implement the dedicated paired
attraction evaluation pipeline, binding separate model interaction histories
to their exact worlds; do not reuse the drag evaluator or mix histories across
the pair. Pixel inspection and a history/no-history model pilot follow. The
current turn did not authorize launching paid API runs or expensive rendering.

## October 8: intrinsic object-attribute baseline added

Added `src/envs/object_attribute_bench.py` and
`src/tasks/characterize_objects.py` as a separate baseline experiment stage.
This stage measures properties belonging to one selected object and deliberately
does not execute or expose pair interactions. Its catalog is identical across
the p=2 and p=3 attraction records:

- `inspect_object` — public appearance and available intrinsic instruments,
- `measure_mass` — inertial mass in kg,
- `measure_volume` — geometric volume in m³,
- `measure_geometry` — sphere radius and diameter in m,
- `measure_density` — mass/volume in kg/m³,
- `measure_inertia` — solid-sphere centre-axis moment, 2/5 m r²,
- `finish`.

Measurement values are generated from the selected object alone, quantized with
declared ranges/resolutions and saturation flags, and charged one budget unit
per measurement. The default budget is 12 units and eight turns. Invalid IDs,
relational tools such as `measure_force`, and exhausted budgets fail without
changing state. Private checkpoints retain the world and ordered intrinsic
measurement journal; public messages do not include world fingerprints or hidden
law values. The existing attraction-law bench remains unchanged.

Configs and user command:

```bash
bash scripts/interact/interact_object_attributes.sh \
  --model YOUR_MODEL \
  --config configs/object_attributes_p2.yaml \
  --output-dir results/object_attributes/p2
```

Use `configs/object_attributes_p3.yaml` for the matched p=3 world. The current
pair has identical object properties in both worlds, so this baseline measures
the same intrinsic values while the law-discovery stage remains responsible for
distance-dependent force behavior. Guide: `docs/object_attribute_bench.md`.

Validation: all 6 new object-attribute tests passed, including matched public
catalog/prompt equality, exact quantized mass/volume/geometry/density/inertia
readings, independence from exponent, budget and invalid-input handling, native
finish, private replay records, and config construction. Shell syntax passed.
The frozen drag baseline verification again passed all 459 files and original
candidate physics. Full-suite execution began successfully but its long-running
output was interrupted before the summary; the targeted new suite and existing
baseline checks are the completed evidence for this change.

## October 8: combined autonomous experiment catalog

Integrated intrinsic-property tools into a new
`src/envs/autonomous_attraction_bench.py`. The default autonomous attraction
episode now exposes one catalog of 12 named tools:

```text
inspect, configure_trial, apply_impulse, measure_force, track_motion, finish,
inspect_object, measure_mass, measure_volume, measure_geometry,
measure_density, measure_inertia
```

The agent chooses the sequence and can characterize an object before measuring
world-law behavior, or skip characterization. There is no scripted baseline
action, router, recommendation, or hidden experiment policy. Intrinsic and law
measurements share the same 24-unit budget and episode state; an intrinsic
measurement does not advance or reset the attraction trajectory. The combined
environment removes the saved mass/radius disclosures, while retaining public
appearance and calibrated instrument rules, so obtaining those attributes is an
actual agent decision.

`src/tasks/discover_world.py` now reads the environment's combined catalog when
available. Added `configs/attraction_autonomous_p2.yaml` and p3, and changed
`scripts/interact/interact_attraction.sh` to use the combined autonomous p2
configuration by default. The preserved law-only comparison is
`scripts/interact/interact_attraction_law_only.sh`. The separate
`interact_object_attributes.sh` remains available as an attribute-only control.
Guide: `docs/autonomous_experiment_tools.md`.

Added five combined-bench tests covering identical public catalog/prompt across
matched laws, shared budgets, intrinsic/law result separation, trajectory
preservation, shared finish, agent-selected ordering, and config construction.
All **174 tests passed** in the final full suite. Frozen drag baseline
verification passed all 459 files and original candidate physics. Shell syntax
passed. No model API calls or rendering were started.

Use the combined episode with:

```bash
bash scripts/interact/interact_attraction.sh \
  --model YOUR_MODEL \
  --config configs/attraction_autonomous_p2.yaml \
  --output-dir results/attraction_lab/autonomous_p2
```

The next work is to bind these separate/combined interaction histories to the
attraction image evaluator and compare history/no-history performance. Do not
mix p=2 and p=3 histories or expose private world records.
