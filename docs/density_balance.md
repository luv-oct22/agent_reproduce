# Density transfer: image evaluation

For multi-object questions and unfamiliar colors, use the [32-question hard suite](density_balance_hard.md).

This is the second stage after material-lab experiments. It uses one context image and four image choices, with no video. Blender builds a realistic laboratory workbench using the existing robotics-room assets, a metal beam balance, and two registry-colored cubes (one per pan).

The source records currently define **cubes**, so the scene preserves cubes rather than changing them to balls. Both samples have equal physical volume, not just equal projected size. They are new samples made of the recorded materials: density, shape and RGBA are preserved; mass is recomputed as density × new volume. The original registry stays unchanged. The question explains this transfer to the model.

The context balance is held level before release. A level context therefore does not imply equal masses. Outcome images depict an ideal equal-arm balance with identical tared pans and symmetric travel stops at ±14°. They illustrate the settled direction; they are not frames from a dynamics solver.

Question text does not name colors or assign specimen IDs to either pan. The model must inspect the image to match the objects to its prior experimental knowledge. Color names in host-side folder names, manifests and the experiment index are not included in model messages; images are sent as embedded pixels. Prior experiment observations still provide the specimen/color associations needed for that match.

## Experiment folder layout

An experiment contains one folder per material pair. The original blue–orange images have been moved into `questions/q001_blue_orange/`.

```text
renders/lab_2/density_balance/
├── object_registry.json
├── questions.json              # all six questions, with relative image paths
├── batch.json
├── index.html                  # links to question review pages
└── questions/
    ├── q001_blue_orange/        # existing rendered question preserved
    ├── q002_blue_green/
    ├── q003_blue_purple/
    ├── q004_orange_green/
    ├── q005_orange_purple/
    └── q006_green_purple/
```

Each question contains its own `scene.json`, `questions.json`, `index.html`, registry copy, and parameter Markdown. Rendering adds `context.png`, choices A–D, `scene.blend`, and per-image Markdown records. All samples remain 60 mL by default and retain the recorded shapes, colors and densities. The registry calls the second color orange.

Render all pending questions on CUDA:

```bash
bash scripts/render/render_density_balance_batch.sh
```

Completed question folders are skipped. An incomplete question is rendered again as a whole. The command stops if Blender fails; rerun it to continue with pending questions. To preview the work without rendering:

```bash
bash scripts/render/render_density_balance_batch.sh --dry-run
```

To regenerate every question with explicit quality settings:

```bash
bash scripts/render/render_density_balance_batch.sh \
  --rerender --samples 128 --resolution 1536 1024
```

`--rerender` replaces images and their parameter records inside the existing question folders. Quality overrides apply only to questions actually rendered; use `--rerender` if you want the completed first question to use the new settings too.

For a new experiment, prepare all pairs from any compatible registry, then render:

```bash
python -m src.simulation.balance_batch prepare \
  --registry results/material_lab_eval/identify_material_20260917_121422/object_registry.json \
  --output-dir renders/lab_2/density_balance_new \
  --volume-ml 60

bash scripts/render/render_density_balance_batch.sh \
  --output-dir renders/lab_2/density_balance_new
```

Add `--include-reversed` when preparing a new experiment to generate 12 questions, including both left/right assignments for each pair. Repeating preparation with the same settings preserves existing question files. Changed registry, volume or batch settings require a different output directory.

## First question

`renders/lab_2/density_balance/questions/q001_blue_orange/` uses the registry from
`results/material_lab_eval/identify_material_20260917_121422/`.

| Pan | Material source | Color / shape | New volume | New mass | Density |
|---|---|---|---:|---:|---:|
| Left | sample_A | Blue cube | 60 mL | 48 g | 800 kg/m³ |
| Right | sample_B | Orange cube | 60 mL | 72 g | 1,200 kg/m³ |

Host answer: **B, right pan down**. The numerical properties and answer are not sent to the evaluated model.

## Render one question on CUDA

From the repository root, render the already prepared bundle:

```bash
bash scripts/render/render_density_balance.sh
```

The default Blender executable is `.tools/blender-3.6.23-linux-x64/blender`; set `BLENDER_BIN` to use another installation. Blender 3.6.23 is the validated version. The script defaults to CUDA and fails explicitly if no CUDA device is found. For another backend use `RENDER_DEVICE=OPTIX` or `RENDER_DEVICE=CPU`.

Override resolution and samples if needed:

```bash
bash scripts/render/render_density_balance.sh \
  renders/lab_2/density_balance/questions/q001_blue_orange/scene.json \
  --samples 128 --resolution 1536 1024
```

The outputs are:

| File | Meaning |
|---|---|
| `context.png` | Balance held level before release |
| `choice_A.png` | Left pan lower |
| `choice_B.png` | Right pan lower |
| `choice_C.png` | Both pans level; exact copy of context pixels |
| `choice_D.png` | Same context blurred and dimmed, with large sharp **Unknown** centered |
| `scene.blend` | Editable laboratory and Unknown overlay scenes |
| `index.html` | Local review page with context and four choices |
| `*_parameters.md` | Parameter record for each completed image and saved scene |
| `parameters.md` | Latest parameter record |
| `build_report.json` | Actual render settings and specimen/pan contact checks |

Rendering reuses the fixed camera, geometry, lighting and colors for every choice. Pans stay horizontal while their suspension follows the beam. The cube bottoms sit on the pan surfaces; suspension clearance and table clearance are checked. Unknown uses Blender's compositor on the exact context PNG. Choice filenames and labels are fixed, independent of the correct answer.

Build and validate geometry without rendering:

```bash
bash scripts/render/render_density_balance.sh \
  renders/lab_2/density_balance/questions/q001_blue_orange/scene.json --device CPU --build-only
```

The first question has already been rendered. The other five question definitions are prepared; their PNGs are produced by the batch render command.

## Evaluate using the previous experiments

To run new experiments and image evaluation together, use the [combined pipeline](density_pipeline.md):

```bash
bash scripts/eval/run_density_pipeline.sh --model 'YOUR_MODEL'
```

This saves both stages, their model responses, test parameters and image snapshots under `results/density_pipeline/<timestamp>/`. The command below instead reuses a previous interaction record.

Keep the API environment settings from the material-lab run and choose a model that accepts images through Chat Completions:

```bash
python eval.py \
  --tasks identify_material \
  --mode evaluate \
  --model 'YOUR_VISION_MODEL' \
  --record results/material_lab_eval/identify_material_20260917_121422/interaction.json \
  --questions renders/lab_2/density_balance/questions.json
```

The root questions.json evaluates all six comparisons. For each question, the model receives the prior experiment history followed by five PNGs (context + A–D). To evaluate only one question, point --questions to that question folder’s questions.json. The model sees only choice letters beside the images, not text descriptions of the tilt outcomes. The answer field, registry and render manifest stay host-only. No new experiments or rendering happen inside evaluation.

The evaluation writes `evaluation_with_history.json` alongside the source `interaction.json`. As in the existing runner, another evaluation in that directory replaces the file of the same name. `--no-history` performs the comparison without the experiment transcript and saves `evaluation_no_history.json`. Scoring uses the physical ground-truth outcome in both modes: Unknown is an abstention and does not receive credit when the physical answer is known. This example's full prior history is sufficient to answer.

## Prepare another pair

Use a fresh output directory:

```bash
python -m src.simulation.balance_scene \
  --registry results/material_lab_eval/identify_material_20260917_121422/object_registry.json \
  --left sample_C --right sample_D --volume-ml 60 \
  --output-dir renders/lab_2/density_C_D

bash scripts/render/render_density_balance.sh renders/lab_2/density_C_D/scene.json
```

Preparing does not render or call a model. It writes a copied source registry, `scene.json`, `questions.json`, Markdown parameters and the review page. Unknown IDs and unsafe sample sizes are rejected. Equal volumes up to 216 mL fit this apparatus. Selecting the same source on both pans creates two material samples with equal density and a level answer. Swapping sides changes the expected tilt. For a larger benchmark, use the batch preparation command above to vary material pairs and side assignments.
