# Hard density evaluation

The prepared suite in `renders/lab_2/density_balance_hard` contains **32 questions**, each with one context image and four choices. Each pan holds **one to three objects**. Every object has the same physical volume (60 mL by default), so the model must count objects, recognize their materials visually and compare the sums of their masses.

| Question category | Count | What it tests |
|---|---:|---|
| Known-material mass sums | 18 | Combine measured densities across multiple objects; includes exact equalities and unequal counts |
| Unseen material, insufficient evidence | 8 | Recognize that the experiments do not determine the outcome |
| Unseen material cancels | 6 | Cancel identical quantities of an unknown material on opposite pans; solve the remainder |

There are eight correct answers for each choice: left down, right down, level, and Unknown. Question order is deterministically shuffled. The prompt is identical for every question, with no color names, specimen IDs, object counts, category hints or answer-specific text. Counts and appearances must be read from the images. New scenes omit the specimen-ID labels used in the original single-object scenes.

## Render and evaluate

Render all pending images on CUDA:

```bash
cd agent_reproduce
bash scripts/render/render_density_balance_batch.sh \
  --output-dir renders/lab_2/density_balance_hard
```

The 32 question folders (`questions/q001/` through `q032/`) each receive `context.png`, `choice_A.png` through `choice_D.png`, an editable Blender scene and parameter Markdown records. The complete suite contains 160 PNGs. This command skips completed questions; add `--rerender` to replace existing renders.

Run new material experiments followed by all 32 questions:

```bash
bash scripts/eval/run_density_pipeline.sh \
  --model 'YOUR_MODEL' \
  --batch-dir renders/lab_2/density_balance_hard
```

Or combine pending CUDA rendering with both model stages:

```bash
bash scripts/eval/run_density_pipeline.sh \
  --model 'YOUR_MODEL' \
  --batch-dir renders/lab_2/density_balance_hard \
  --render-missing --device CUDA
```

`--eval-model` remains available for a separate vision model. Both stages' records and the image-test snapshot are saved to `results/density_pipeline/<timestamp>/`.

## Unknown materials and grading

`object_registry.json` contains only the original four experimental materials. The experiment environment is initialized exclusively from this registry. `evaluation_registry.json` contains those same four plus two unseen materials. For the current source registry, the unseen colors are **red and yellow**, both represented as cubes. Their hidden densities are deterministic positive samples stored for reproducibility, not information supplied to either model.

The question states that visually matching samples share a material and density, and that unseen material densities can be any positive value. It does not assign a prior density based on color. The correct answer is based on what can be determined from the experimental materials, rather than the hidden numerical density of a new material.

For example, a new material on one pan and a known material on the other normally requires Unknown. Identical unknown objects on both pans cancel, so the known remaining objects may still determine a tilt or equality. An unknown object added to otherwise identical contents makes that pan heavier because its mass is positive. The grading function handles these cases symbolically, without consulting the unseen density values. The current generated suite includes cancellation controls; the positive-mass rule is also supported and tested.

Each scene records the evidence-based `answer`, the remaining unknown coefficients, and the host-only `physical_answer` implied by the hidden evaluation properties. On ambiguous questions the latter is A/B/C while the scored answer is D. These records, categories and answers are excluded from model messages.

This grading assumes the previously measured materials are available as experimental knowledge. A model that failed to measure them sufficiently may also be uncertain on known-material questions, but receives no automatic credit for abstaining on those questions.

## Generate another hard suite

```bash
python -m src.simulation.balance_challenge \
  --registry renders/lab_2/density_balance/object_registry.json \
  --output-dir renders/lab_2/density_balance_hard_new \
  --volume-ml 60 --seed 17
```

Use an empty output directory. Seed controls question selection/order and unseen material properties. The registry must have at least three visually distinct experimental materials, differing densities, and sufficient equal-mass combinations for the balanced suite. The generator refuses unsupported registries rather than silently reducing the question set. The original six-question batch remains available.

The renderer enlarges the pans, places objects in a separated row and checks pan support, suspension clearance, object separation, table clearance and camera framing. It produces idealized endpoint illustrations, not integrated balance dynamics.
