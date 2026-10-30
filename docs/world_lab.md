# World lab: infer gravity experimentally

For stage 2, which adds specimen–surface restitution and rebound measurements, see [the bounce lab](bounce_lab.md). The gravity-only task documented here remains available separately.

The first world uses **g = 3.0 m/s²**, uniform and directed downward. Gravitational acceleration has units m/s². Newton's laws remain unchanged; this first step changes a world parameter, not the functional form of a physical law.

`UniformGravityWorld` is a reusable, immutable physical-world definition. Its host-only `world.json` contains the gravity vector, SI units, no-drag assumption and a content-derived world ID. Object properties remain in the separate `object_registry.json`, so future scenes can reuse the same objects under the same or another explicitly selected world.

## Model interaction

`world_lab` retains the beam balance and displacement cylinder and adds a vacuum drop tower. The model's initial observation describes the apparatus but does not reveal gravity, the config filename or the world ID. The model is told gravity is uniform and constant, without assuming an Earth value.

The `drop` action releases a chosen specimen from rest, lets it travel a calibrated distance, and reports the elapsed time rounded to the clock's 0.001-second resolution. Trials consume the shared experiment budget and appear in the notebook. No hidden numeric gravity is returned by the tool.

```json
{"operation":"drop","specimen_id":"sample_A","distance_m":1.5}
```

In this world the timer reads 1.000 s for that distance. An agent can infer gravity from repeated distance/time measurements and the free-fall relationship. It submits an estimate using:

```json
{"operation":"submit_world_estimate","gravity_m_s2":3.0}
```

Submission acknowledges receipt without exposing correctness. `private_evaluation.json` separately records material-property accuracy and gravity-estimate accuracy. The combined score averages those two scores; the default relative tolerance is 3%.

## Run the model

With your usual API environment variables exported:

```bash
cd agent_reproduce
python eval.py \
  --tasks identify_world \
  --config configs/world_lab_low_gravity.yaml \
  --mode interact \
  --model 'YOUR_MODEL' \
  --max-turns 80 \
  --output-dir results/world_lab
```

This stage needs tool calling but no images. Results include `interaction.json`, `private_evaluation.json`, `private_manifest.json`, `object_registry.json/.md`, and **`world.json/.md`**. World and object records are saved before the first model request.

To change gravity, edit the host-side `gravity_m_s2` in the YAML. To load an exact recorded world, remove that field and set `world_path` to its world.json instead. `registry_path` independently selects an exact recorded object catalog. The new task is separate from the existing density image pipeline.

## What the next stage can evaluate

The world definition supplies an exact free-flight `advance(position_m, velocity_m_s, elapsed_s)` operation for future motion scenes. It uses the recorded world gravity rather than a hardcoded Earth value. It does not include a collision, contact or fluid-motion solver.

The existing static balance and floating-fraction questions cannot distinguish different positive gravity values: gravity cancels from their equilibrium equations. Useful next questions would instead predict fall distance after a fixed time, flight time, projectile position or another gravity-sensitive motion outcome. No new video or image evaluation is implemented in this first world-building step.
