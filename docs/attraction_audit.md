# Attraction learnability audit — step 5

`src/evaluation/attraction_audit.py` performs an offline, host-only feasibility
audit of the saved attraction worlds. It collects actual quantized apparatus
readings under fixed reference policies, fits alternative hypotheses, and
checks their predictions on new numerical situations. No model API, renderer,
agent prompt change, or private scoring tool is involved.

The first report is saved at
`results/attraction_audit/attraction_pair_v1/report.md`; `audit.json` contains
the full evidence, intervals, competing-world witnesses and predictions.

## What is searched

The search varies p in {2, 3} and constant strength A continuously across the
saved field bounds [0, 5] N. All other physics, object properties, reference
scales and apparatus metadata remain those of the saved instance. These are
**host audit assumptions**, not extra information supplied to the agent.

For each force reading, invert the sensor's rounding bin to a compatible
strength interval. Intersect these intervals separately for each exponent.
The coefficient relating force to A comes from the same `AttractionWorld`
implementation used by the apparatus. Fitting does not use the true exponent
or true strength. A regression test changes those hidden values while holding
the evidence fixed and requires identical fitted intervals.

Bin boundaries are conservatively closed with a 1e-12 N floating-point guard.
A saturated reading gives a one-sided bound; it is not treated as an exact
force equal to the sensor limit. Unsaturated readings at the limit retain the
upper bound implied by the absence of saturation. Repeated deterministic
readings intersect the same bin and do not reduce quantization uncertainty.
This is continuous interval fitting, not a strength-grid search.

## Policies and budgets

Both worlds receive exactly the same predeclared reference policies:

| Control | Force measurements | Units | Scripted turns |
|---|---|---|---|
| No measurements | None | 0 | 1, to finish |
| One distance | 1 m | 1 | 1 |
| Repeat one distance | 24 readings at 1 m | 24 | 8 |
| Two distances | 1 m, 2 m | 2 | 2 |
| Four distances | 0.75 m, 1 m, 1.5 m, 2 m | 4 | 4 |
| Near sensor limit | 0.21 m | 1 | 1 |

Each scripted turn batches one configuration and its force readings. Finish is
included in the last batch. Every operation goes through `AttractionBenchEnv`;
the audit enforces the apparatus turn cap and measurement budget. These are
reference controls, not evaluated model turns or an optimal experiment policy.
The policy list is fixed before collecting either world's measurements.

## Transfer checks

The audit includes two diagnostic launch states, with separations of 1.4 m and
1.8 m, different initial velocities, start times and durations. Their full
definitions are recorded in the report. They are not image questions and do
not freeze a future render suite.

For each surviving interval, sample 17 equally spaced strengths including its
endpoints. Replay each candidate's complete reference transcript through the
actual apparatus and retain only exact public-result matches. This removes
marginal false matches introduced by conservative sensor-bin boundaries.
No true-parameter point is specially inserted into the sample set.

Run each retained hypothesis on the diagnostic launch states. Save the exact
host-side final positions, the maximum sampled pairwise distance, and the
indices of two witnesses achieving that distance. Compare timestep-halved
predictions for the true world and these extremal witnesses. A sampled
trajectory check passes when all sampled trajectories are valid, their spread
is at most **5 mm**, and the tested numerical discrepancy is at most **0.05 mm**.

Separately propagate the continuous fitted intervals to force magnitudes at
1.3 m and 1.7 m. These checks use the full interval bounds, not sampled
strengths. A force check passes when the combined range spans at most **0.001 N**.

A policy receives `pass_within_audit_scope` only if the true parameters remain
in the fitted intervals, exactly one exponent survives, replayable witnesses
exist, and both transfer checks pass. Empty/inconsistent results are not
accepted as successful identification. The pair passes the reference audit
when the two-distance and four-distance policies pass in both worlds.

## Interpretation

The current pair can be separated with two well-chosen force readings. In
contrast, even spending the full budget repeatedly at 1 m leaves both
exponents plausible and allows visibly different held-out motion. Sensor
saturation also leaves a broad set of possible strengths.

This establishes feasibility within the restricted family; it does not show
that a model can discover the family unaided or that the task is difficult.
Arbitrary alternative laws, varying coefficient fields, hidden masses and
other couplings are outside the search. Trajectory spread is sampled and is
**not a certified bound over every continuous strength value**. There is no
visual readability, candidate-distance, or nearest-choice shortcut audit yet.

The saved simple pair is a useful control for the next scene-building stage.
More difficult instances should be authored as separate versions rather than
changing the existing pair or feeding the audit's policy to evaluated agents.

## Reproduce

In the project Python environment:

```bash
python -m src.evaluation.attraction_audit \
  --output-dir results/attraction_audit/attraction_pair_v1_repeat

python -m unittest discover -s tests -p 'test_attraction_audit.py' -v
```

The command refuses an existing output directory. Use `--instances PATH PATH`
for another matched pair, or `--samples-per-interval N` to change the reported
trajectory sampling density. The built-in reference policies require the
standard eight-turn, 24-unit budget. The command exits nonzero if the pair
does not pass the reference audit; its completed report is still saved.

Each bundle contains `audit.json`, `report.md`, immutable source-world copies
`world_1.json`/`world_2.json`, and SHA-256 checksums of those artifacts. The JSON
also records hashes of the audit, apparatus, solver, setup and record-contract
source files, plus apparatus version, search scope, budgets, policies, full
public tool transcripts, continuous intervals and sampled witnesses. Keep all
of these files host-only. Original world records, public catalogs, historical
interactions and frozen drag baseline files are preserved.

The subsequent [paired scene suite](attraction_prediction.md) now prepares
16 questions from these same worlds, with candidate similarity, projection,
evidence-transfer and shortcut checks. PNG rendering and the model pilot follow.
