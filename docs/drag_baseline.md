# Frozen drag baseline

The first migration step preserves the current benchmark in
`baselines/drag_complex_close_v1/`. This is an independent local snapshot;
working render directories and historical result folders keep their original paths.

The baseline contains 16 close-candidate questions and 80 rendered PNGs, exact
scene/world/object/contact records, Blender files and build reports, the source
interaction, matching evaluation records and their source interactions, and a
copy of the current Python implementation and relevant configurations/scripts.
The snapshot records package versions at freeze time, not the necessarily
different environments used by historical model runs. It does not bundle Python
dependencies or the Blender executable.

`baseline.json` inventories files with SHA-256 checksums and records provenance.
Matching historical runs must have identical question, scene, physics, and PNG
content before inclusion. Duplicate image directories inside those runs are
represented by the shared `batch/` copy. Original paths inside archived JSON
remain provenance; the verifier uses the snapshot's own records and images.
Incomplete attempts are preserved with their recorded status, not scored as
completed evaluations. The snapshot includes private physics and answer keys
and must not be passed wholesale to an evaluated model.

Historical completed evaluations on this exact suite:

| Model | Image score | Interaction numerical score | Measurements used | Interaction finished |
|---|---:|---:|---:|---|
| qwen3.8-max | 6/16 | 1/8 | 24 | No |
| gpt-5.6-sol | 9/16 | 1/8 | 24 | Yes |
| claude-opus-5-5 | 10/16 | 1/8 | 11 | Yes |

These are reference observations, not new runs or a claim of equal experimental
effort. The configured measurement cap is 24; turn budgets are not consistently
stored in the records, and completion and measurement use differ. Image accuracy
and the numerical 5 ms / 5 mm held-out prediction score measure different things.

## Offline regression check

With the project's Conda environment active, from the repository root:

```bash
python -m src.evaluation.drag_baseline verify \
  --baseline baselines/drag_complex_close_v1
```

This checks snapshot file integrity, then uses the current implementation to
recompute candidate physics and validate rendered input records. It makes no
API calls and performs no rendering. Use it after changes to world loading,
simulation, candidate construction contracts, or evaluation input validation.
It does not replace instrument/solver unit tests or claim model outputs are
deterministic across future API runs.

Checksums detect changed, missing, or added files. They do not make the directory
filesystem-immutable or protect against coordinated edits to both files and the
manifest. Treat this version as frozen; do not regenerate images into it or edit
its metadata to make a failing check pass.

For an intentional new benchmark version, choose a new output directory:

```bash
python -m src.evaluation.drag_baseline freeze \
  --batch-dir renders/lab_5/drag_prediction_complex_close \
  --baseline baselines/drag_complex_close_v2
```

Freezing refuses an existing output directory. New world work should use new
configs, scenes, and result paths; the drag baseline remains the reference.
