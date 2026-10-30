# Stage 2: gravity and bounce interaction

This task asks the model to infer a world's constant gravity and constant normal restitution for each specimen material–surface pair. The environment uses spherical specimens and a single stationary horizontal surface. Air drag, tangential friction, spin coupling and object–object collisions are absent. After interaction, use the [bounce visual prediction task](bounce_prediction.md) to render new launch scenes and evaluate with the saved history.

## Run the model

With the usual `OPENAI_BASE_URL` and `OPENAI_API_KEY` exported:

```bash
cd agent_reproduce
python eval.py \
  --tasks identify_bounce \
  --config configs/bounce_lab.yaml \
  --mode interact \
  --model 'YOUR_MODEL' \
  --max-turns 32 \
  --output-dir results/bounce_lab
```

No CUDA or rendering is needed. The model must support tool calling. The existing SDK timeout and retry settings also apply to this task. Measurement budget and model-turn budget are separate: the default configuration allows 16 valid measurements and the command allows 32 model turns.

For an offline reference demonstration without a model API:

```bash
python -m src.envs.bounce_lab --demo --config configs/bounce_lab.yaml
```

The reference policy measures two release heights per object, derives gravity and restitution only from the public readings, and submits estimates. It is a scripted policy, not an LLM evaluation. The CLI also accepts `--actions path/to/actions.jsonl` or one JSON action per line on stdin. `--output-dir` must name an empty directory.

## Public actions

`submit_action` supports `inspect`, `drop`, `bounce`, `balance`, `displace`, `submit_world_estimate`, `submit_contact_estimates`, and optional material `submit_estimates`. The separate `finish` tool ends an LLM interaction. Balance, displacement, drop and bounce share the measurement budget; inspect, submissions and malformed actions are free. Experiments are independent and return specimens to the bench; the notebook persists.

```json
{"operation":"bounce","specimen_id":"sample_A","surface_id":"surface_1","release_height_m":1.0}
```

The instrument reports first-impact time and first-rebound peak height, rounded to its public resolutions. It does not report gravity, restitution, impact velocities, hidden IDs or correctness. Release and rebound heights measure center displacement above the center's position at contact, equivalently the bottom-of-sphere clearance above the surface. They are not absolute center elevations.

In the default world this action reports 0.816 s and 0.360 m. The model can infer gravity and restitution using these observations and verify its estimates at other heights. The prompt states that coefficients are constant in this task but does not provide the inference formulas or numerical answers.

```json
{"operation":"submit_world_estimate","gravity_m_s2":3.0}
{"operation":"submit_contact_estimates","estimates":[{"specimen_id":"sample_A","surface_id":"surface_1","restitution":0.6}]}
```

Submissions acknowledge receipt without correctness feedback. Contact submissions can be partial and updated later; invalid batches are rejected atomically. A zero rebound reading may reflect a small rebound below instrument resolution.

## Host-only configuration and scoring

`configs/bounce_lab.yaml` specifies gravity 3.0 m/s², a 0.05–2.0 m release range, 0.001 s clock resolution, 0.001 m rebound-height resolution, and 16 measurements. Default contact coefficients on `surface_1` are A=0.60, B=0.85, C=0.35, D=0.75. These are authored synthetic values, not inferred from color or real material names. If coefficients are omitted, the environment generates a deterministic seeded assignment and records it.

The private score averages gravity accuracy and the fraction of correct contact pairs. Gravity uses a 3% relative tolerance; restitution uses an absolute tolerance of 0.03 so zero restitution remains evaluable. Missing estimates fail their component. Material-property estimates are optional and do not affect this task's score.

## Records and handoff

Before the first model request, each run saves:

- `world.json` / `world.md`: gravity and free-flight assumptions.
- `object_registry.json` / `object_registry.md`: exact colors, sphere geometry, masses, volumes and inertia.
- `contact_registry.json` / `contact_registry.md`: each specimen–surface coefficient and collision assumptions, linked to the exact world and object registry IDs.
- `private_manifest.json`: complete reproducible experiment configuration.
- `parameters.md` and `task_parameters.md`: apparatus and scoring settings.

The LLM runner checkpoints `interaction.json` and writes `private_evaluation.json` after interaction. The offline CLI writes `public_transcript.json`, `private_evaluation.json`, and `config_resolved.json`. Ground-truth records must never be included in the model history used for later visual prediction.

Reload the exact environment with `BounceLabEnv.from_private_manifest(...)`, or set all three paths in the YAML: `world_path`, `registry_path`, and `contact_registry_path`. Remove authored `gravity_m_s2` and `restitution_by_specimen` when using paths; set the matching `surface_id`. Inconsistent world/object/contact combinations are rejected. Existing records cannot be silently replaced by different physics.

The shared `UniformGravityWorld.advance` provides free flight. `ContactRegistry.impact_velocity` provides the instantaneous contact rule: horizontal velocity is unchanged and incoming vertical velocity is reversed and multiplied by restitution. The bounce apparatus and visual prediction scenes use these same primitives. The visual scene's `advance_bouncing` helper handles impact timing and repeated contacts.

Stage-1 `world_lab` / `identify_world` and the existing density image pipeline remain separate. The stage-2 catalog records spheres rather than modifying previously saved cube specimens.
