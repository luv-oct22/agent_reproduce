# Hard bounce visual prediction

The current batch replaces the eight-question baseline with **16 questions across two physical worlds**. It consists of eight paired visual situations: each pair has the same context, same four candidate frames and same question text, but a different correct answer because the experimental history comes from a different world.

Every question contains two specimens. The choices form all four combinations of two possible states per specimen. Each object alone matches exactly two choices; both objects must be checked to select the answer. Correct choice positions are shuffled and balanced within each world.

The initial height and horizontal launch speed must be read from the context image. Question text gives the requested elapsed time and physical assumptions, but no specimen colors, initial height values or launch-speed values. The image has a 0.10 m major grid, 0.025 m minor height lines and velocity labels at the launch stations.

## Current records

The primary world comes from `results/bounce_lab/identify_bounce_20260920_162018`. The second world keeps the same objects and appearance but uses different gravity and contact coefficients. Its history must be acquired by interaction; the first world's history must not be used to answer second-world questions.

World definitions and apparatus parameters are recorded in `worlds/world_001/` and `worlds/world_002/`. The batch root contains `batch.json`, aggregate `questions.json`, `parameters.md`, and a review `index.html`. Question folders are `questions/q001` through `q016`.

The old batch is archived beside the replacement in `bounce_prediction_archive_20260920_174658_067054`. Existing evaluation snapshots and scores are unchanged.

## Render on CUDA

```bash
conda activate agent_reproduce
cd agent_reproduce
bash scripts/render/render_bounce_prediction.sh --device CUDA
```

This renders 80 PNG files: one context and four choices per question. Paired questions intentionally duplicate image content. Each folder also gets `scene.blend`, a build report and Markdown parameters for every render. Quality defaults to 1536×1024 and 96 Cycles samples. Add `--samples 128`, `--resolution 1920 1280` or `--rerender` as needed. Set `BLENDER_BIN` if you use another Blender executable.

All 16 Blender geometry builds have been checked without rendering PNGs. Review `index.html` after rendering to check appearance. Completed renders are skipped; scene changes or build-only reports invalidate completion.

## Evaluate

Run fresh interactions and all 16 image questions with one command:

```bash
bash scripts/eval/eval_bounce_prediction.sh --model 'YOUR_MODEL'
```

With no `--record`, the pipeline loads each world's exact saved apparatus and
physics from the rendered batch, runs a fresh interaction, and evaluates that
world's eight questions using only its own public history. It checks all rendered
inputs before making model calls. No manual interaction path is needed.

For separate models, use `--model 'YOUR_VISION_MODEL'` and
`--experiment-model 'YOUR_EXPERIMENT_MODEL'`. Otherwise the same model is used
for both stages. `--max-turns 32` applies to each new interaction. Both worlds'
histories, private scores, model logs, parameters and image scores are saved in
one `results/bounce_evaluation/<timestamp>/` directory. `--prepare-only` validates
and snapshots inputs without any API calls. This fresh-interaction mode requires
the current paired-world batch; legacy single-world batches still require a record.

To reuse an existing world-1 interaction instead, supply `--record` as below.

With API environment variables already configured:

```bash
bash scripts/eval/eval_bounce_prediction.sh \
  --model 'YOUR_VISION_MODEL' \
  --record results/bounce_lab/identify_bounce_20260920_162018/interaction.json
```

For this paired-world batch, the command:

1. Validates rendered inputs and physical identities before model calls.
2. Reuses the saved interaction for world 1.
3. Runs a **new interaction for world 2**, using the original experiment model unless `--experiment-model` is supplied.
4. Evaluates each world's eight questions using only that world's public interaction history.
5. Records overall accuracy, accuracy per world, and paired accuracy (both answers in a pair must be correct).

`--max-turns 32` controls new-world interaction turns. API connection settings are shared. `--prepare-only` validates and snapshots already-rendered inputs with zero model calls. To reuse a matching second-world interaction from a previous evaluation, add:

```bash
--world-record world_002=results/bounce_evaluation/PREVIOUS_RUN/world_runs/world_002/interaction.json
```

A record from a different world is rejected. No ground-truth coefficients, private scene metadata, counterpart-world history or answer keys are sent to the vision model.

Results are saved under `results/bounce_evaluation/<timestamp>/`: the image batch snapshot, `world_runs/world_001/` and `world_runs/world_002/` with their interactions and per-question answers, top-level `evaluation_with_history.json`, model request/response logs, parameter Markdown, status and summary. Answers are checkpointed within each world after every question, and the combined record is updated after each world. Repeating the command creates a new run; it does not automatically resume a failed one.

## Difficulty and physical validity

The eight primary-world contexts include two cases spanning pre-impact/first impact, three cases mixing one and multiple impacts, and three cases where both objects have bounced repeatedly. The paired world's impact counts may differ. Current true states span zero through three impacts.

Each object's two candidate positions differ by 4.5–12 cm. Generation samples within this readable interval instead of maximizing separation. It rejects cases in which a +/-5 mm uncertainty in initial clearance changes a correct position by more than 1 cm. Sphere shape, color and size stay identical to the interaction registry. Horizontal velocities remain unchanged by the frictionless surface; this batch focuses on vertical event tracking and combining evidence for both objects.

Both worlds use the same tested free-flight and impact primitives as the experiment apparatus. Geometric checks cover sphere size in pixels, camera coverage, penetration, surface bounds and pairwise separation. The selected trajectories remain horizontally separated throughout their motion. Paired question rendering depends only on common scene geometry, object states and visual settings, so no world label appears in the pixels.

## Prepare another hard batch

```bash
python -m src.simulation.bounce_challenge \
  --run-dir results/bounce_lab/identify_bounce_20260920_162018 \
  --output-dir renders/lab_4/bounce_prediction \
  --replace
```

Preparation stages a complete new batch before archiving and replacing the current directory. `--seed` changes the deterministic question sampling and option order. Without `--replace`, a nonempty target is rejected. The legacy `src.simulation.bounce_scene` generator remains available for reproducing the easier schema-1 baseline in a separate folder.
