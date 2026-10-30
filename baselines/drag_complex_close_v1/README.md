# Frozen drag baseline

16 questions; 80 PNG images. This is the disclosed-law, hidden-height-function benchmark.

| Model | Image score | Numerical score | Measurements used | Finished interaction |
|---|---:|---:|---:|---|
| qwen3.8-max | 37.50% | 12.50% | 24 | False |
| claude-opus-5-5 | 62.50% | 12.50% | 11 | True |
| gpt-5.6-sol | 56.25% | 12.50% | 24 | True |

These are historical observations, not new model runs. Completion and measurement use differ; turn limits are not consistently recorded, so do not infer identical run budgets. Incomplete attempts are preserved separately in baseline.json and are not aggregate scores.

batch/ contains the shared images, Blender scenes, physics, questions and render records. evaluations/ contains original per-run records and logs; their duplicate drag_prediction/ assets are represented by batch/, verified against each original snapshot before freezing. interactions/ contains source experiment records; code/ records the current implementation. Original absolute paths inside copied files are provenance, not rewritten runnable paths.

Files are independent copies with SHA-256 checksums; this is a versioned snapshot, not filesystem-enforced immutability or protection against edits to the checksum manifest. Use a new version for any intended benchmark change. No API secrets are captured from the environment.
