# Combined material experiment and density-image pipeline

Run both stages with one command from `agent_reproduce`:

```bash
export OPENAI_API_KEY='YOUR_API_KEY'
export OPENAI_BASE_URL='https://YOUR_API_HOST/v1'

bash scripts/eval/run_density_pipeline.sh --model 'YOUR_MODEL'
```

For the official OpenAI endpoint, omit the URL override (unset it if previously configured). The experiment model must support tool calling; the image evaluation model must support image inputs through the existing Chat Completions harness. Credentials are read from your environment and are not saved in the results.

The SDK client explicitly allows 60 seconds to establish a connection and 600 seconds for each read, write or pool-wait operation. Both stages share these settings. Override them in your shell if needed:

```bash
export OPENAI_CONNECT_TIMEOUT=120
export OPENAI_TIMEOUT=900
```

These limits apply per network operation and per attempt, not to the entire pipeline or total retry duration. New run parameter records include the resolved timeout and retry settings.

Transient failures get **three retries** (four total attempts), waiting 5, 10 and 20 seconds. This includes connection/timeouts, HTTP 408/409/429/5xx, and the provider-specific HTTP 400 message `Download multimodal file timed out`. Other HTTP 400 errors and authentication errors fail immediately. The harness disables SDK-internal retries so both models use one bounded retry budget per request. Tool actions are executed only after a successful response, so a retry does not repeat an environment experiment.

```bash
export OPENAI_MAX_RETRIES=5
```

With five retries the delays are 5, 10, 20, 30 and 30 seconds. Set zero to disable retries. When retries are exhausted, the run fails with its existing checkpoints preserved; automatic run resumption is not added by this setting.

Select separate models:

```bash
bash scripts/eval/run_density_pipeline.sh \
  --model 'YOUR_EXPERIMENT_MODEL' \
  --eval-model 'YOUR_VISION_MODEL' \
  --max-turns 64
```

The pipeline validates the prepared question images, snapshots their inputs, runs new material-lab experiments, and then evaluates all six image questions using the resulting interaction history. It loads the experiment objects from the image batch's exact registry. This overrides seed-based object generation, so both stages refer to the same materials. The prior run's transcript is not reused: every normal pipeline invocation starts a fresh model interaction.

The default batch is `renders/lab_2/density_balance`, and results go to a new timestamped folder under **`agent_reproduce/results/density_pipeline/`**, regardless of the directory from which the Python module is invoked. The shell wrapper also changes to the repository root.

Select `--batch-dir renders/lab_2/density_balance_hard` for the [32-question multi-object suite](density_balance_hard.md). In that suite, `evaluation_registry.json` adds unseen materials for image tests only. The experiment still loads the original registry, so unfamiliar objects and their densities are never introduced during the learning stage. Unknown is scored using whether the outcome is identifiable from the known materials, including cancellation of equal unknown quantities.

Select `--batch-dir renders/lab_3/liquid_equilibrium` for the [liquid-density transfer task](liquid_equilibrium.md): infer the unknown liquid density from one floating object, then select the candidate image in which all four objects are at the correct equilibrium. These image snapshots use a `liquid_equilibrium/` subfolder in the results directory.

```text
results/density_pipeline/<timestamp>/
├── status.json                       # prepared, running, complete or failed
├── run_parameters.json               # models, limits, registry identity, batch settings
├── parameters.md                     # readable run settings
├── config_resolved.json              # config with exact registry_path
├── object_registry.json / .md        # host-only object properties
├── private_manifest.json             # object and apparatus ground truth
├── interaction.json                  # first-stage conversation and tool results
├── private_evaluation.json           # first-stage estimates and scores
├── evaluation_with_history.json      # second-stage answers and scores
├── model_requests.jsonl              # outgoing messages/tools, image data replaced by hashes
├── model_responses.jsonl             # model text, tool calls and usage, saved after every call
├── summary.json / .md                # both scores after successful completion
└── density_balance/                  # snapshot of the tested image batch
    ├── questions.json
    ├── batch.json
    ├── object_registry.json / .md
    ├── index.html
    └── questions/q001_.../ ...        # images, scene JSON, per-image parameter Markdown
```

Editable `.blend` files stay in the original render directory to avoid copying large files into every run. Evaluation images and their parameter records are copied, so later renders cannot change the inputs recorded for an earlier run. Request logs identify image data URIs by SHA-256 instead of repeating base64 pixels; exact images remain in the snapshot.

The private files and answer keys stay host-only. The model receives public experiment observations, the experiment transcript and image questions. It does not receive the registry, grading results or answer fields.

If a later API call fails, previously completed exchanges remain saved. `status.json` marks the run failed and records the error type; existing score files may be partial. `interaction.finished` and the summary indicate whether the experiment agent explicitly called finish. Reaching the configured turn limit still allows evaluation using the evidence gathered so far.

## Other batches and rendering

```bash
bash scripts/eval/run_density_pipeline.sh \
  --model 'YOUR_MODEL' \
  --batch-dir renders/lab_2/density_balance \
  --output-dir results/density_pipeline
```

By default the images must already be rendered. On your CUDA machine, `--render-missing` renders pending question folders before the model stages:

```bash
bash scripts/eval/run_density_pipeline.sh \
  --model 'YOUR_MODEL' --render-missing --device CUDA
```

`--samples` and `--resolution` apply only to newly rendered questions. Existing render parameters remain recorded in their question folders. To prepare a new batch or regenerate completed images, see [the image rendering guide](density_balance.md).

Validate and snapshot a run without making API calls:

```bash
bash scripts/eval/run_density_pipeline.sh --model 'YOUR_MODEL' --prepare-only
```

This creates a folder with status `prepared`; it is not a model evaluation and has no score. A later normal invocation creates a separate run folder.
