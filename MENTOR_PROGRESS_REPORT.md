# Progress report: learning physics through interaction and transferring it to visual prediction

Prepared: 2026-09-22. Reporting scope: the supplied development conversation and locally saved artifacts inspected on this date.

Updated on 2026-09-22 to include completed `gpt-5-mini` NewtonBench and bounce-pipeline runs. The model identifier in these records is `gpt-5-mini`, not `gpt-5.5-mini`.

## Research objective and current finding

We are building an evaluation in which a model first performs experiments to learn hidden object properties or world parameters, then uses those observations to predict a new visually presented situation. The intended contribution relative to equation-discovery benchmarks is the transfer from experimental evidence to scene interpretation and physical prediction.

The infrastructure now supports this process for material density and constant-gravity bounce dynamics. The earlier `qwen3.8-max` runs saturated the harder balance and bounce batches. Newly collected `gpt-5-mini` results show a different pattern: it correctly identified gravity and restitution in both bounce worlds but answered only **5/16 visual questions (31.25%)**, with **2/8 pairs fully correct (25%)**. On the separate NewtonBench hard task, it recovered **0/3 laws**, versus Qwen's 3/3. We now have an initial observed model difference and a useful separation between parameter identification and subsequent visual prediction. The priority is to diagnose this difference under controlled conditions, while addressing the remaining ceiling for Qwen.

This report separates implemented work, measured results, and proposed extensions. It does not claim a broad model comparison or established novelty. Some earlier assistant messages are missing from the supplied history; saved records were used to verify outcomes. No fresh evaluation, rendering, or test suite was run to prepare this report.

## 1. Development trajectory

### A. Starting point: controllable robot-lab rendering

The initial work concerned a Panda robot scene with a thrown ball and a cup. We explored changing scene parameters while preserving other settings, increasing the cup distance, avoiding visible ball/cup clipping, and slowing playback to a 10-second video. Render outputs were reorganized under `renders/lab_1/`, and the user selected the final `far_distance/` version while removing other render variants.

The retained scene has a 1.5 m horizontal release-to-cup distance. Its saved video is [simulation_10s.mp4](renders/lab_1/far_distance/simulation_10s.mp4), with detailed [parameters](renders/lab_1/far_distance/simulation_10s_parameters.md). The slow-motion effect retimes playback rather than changing the simulated release velocity. Automatic per-output Markdown records were added so scene changes could be audited and reproduced.

This established reusable scene assets, rendering commands, output organization, and parameter recording. It remains a visualization with approximate ball/contact physics and kinematic robot animation; it is not evidence of a physically validated robot controller. The user normally executes rendering on CUDA rather than asking the assistant to render during development.

### B. From rendering to experimental property discovery

The research direction then shifted to unknown objects whose properties must be inferred experimentally. A headless material laboratory was implemented with an equal-arm balance, calibrated reference weights, and water displacement measurements. The agent chooses measurements, maintains a public observation history, and submits mass, volume, and density estimates.

The apparatus returns qualitative balance outcomes and graduated water levels rather than directly returning hidden properties. It has an experiment budget, finite instrument resolution, and private end-of-run scoring. Offline demos are scripted reference policies; model evaluations use the actual tool-calling harness.

A shared object registry was introduced to ensure the later visual scenes use the same recorded identities, material properties, shapes, and colors. Registry JSON and Markdown are saved before the first model request, so records survive early API failure. Ground-truth files remain separate from the model's public transcript.

This resolved an important consistency issue: learning and visual evaluation must refer to the same physical materials rather than independently resampled objects.

### C. Density transfer through balance images

The first visual task replaced video with a context image and four candidate images. The context shows a beam held level before release. The options represent left down, right down, level, and an Unknown card. Recorded cube appearances are preserved, and visible volumes are equal, making density rather than the original specimen mass decisive.

Question text was revised to omit colors and identities so the model must inspect the images. Question batches were organized into separate folders, and the material interaction and image evaluation were combined into one pipeline. The experiment and vision stages may use different models; the vision stage receives the public experiment history, while the two stages share the configured API endpoint and credentials.

After the initial six-question set proved easy, a 32-question batch was built with 1–3 objects on each pan, known-material mass sums, unseen materials, and cancellation of identical unknown amounts. The grader distinguishes a physically sampled outcome from what is inferable from the supplied evidence. Unseen densities are unspecified positive values, so an ambiguous comparison is graded Unknown even if the host has sampled a numerical density.

This harder batch was also solved perfectly in the completed inspected run. Adding more objects and unknown colors increased task variety but did not produce errors for this model under the tested conditions.

### D. Liquid equilibrium as a second transfer scene

The next task places a known-material cube in a transparent cubic liquid container. Its submerged fraction, combined with the density learned during experiments, determines liquid density. The model then chooses the image in which all four specimens have the correct equilibrium positions.

The scene generator accounts for displaced liquid volume and updates the surface height. Upright guides and equal-height bands support measuring the submerged fraction. Context specimens are partially floating; fully sunken or neutrally buoyant contexts were excluded because they would not uniquely specify liquid density in this formulation.

The user found the initial liquid surface difficult to distinguish. The rendering was revised with a visible tinted surface, water-level outlines, reduced glass reflections, and refraction disabled for the measurement view. This change targets readability rather than making physics easier or harder.

Eight questions and 40 image files exist. The inspected model run contains only four completed image answers, all correct. A full liquid-task score has not been established from this record.

### E. Hidden world parameters and dynamic prediction

Static balance and buoyancy fraction are insensitive to the magnitude of positive uniform gravity because gravity cancels from their equilibrium equations. To test a learned gravity value, we therefore introduced timed drops and later bounce trajectories.

The initial hidden-gravity world uses `g = 3.0 m/s²`. This changes a physical parameter, not Newton's laws or the functional form of gravity. The world definition is saved separately from object properties so both experimental observations and visual trajectories use the same world.

The bounce environment adds spherical specimens with material–surface restitution. The model can measure first-impact time and rebound height, infer gravity and restitution, and submit estimates without correctness feedback during interaction. The same free-flight and impact rules generate the later visual predictions.

The first visual batch contained eight questions and achieved 8/8. It was replaced with 16 questions across two worlds. Each paired question uses the same scene and candidate images but different experimental evidence and a different correct answer. Every question contains two spheres, and the four options require jointly checking both. Launch heights/speeds come from the image, and multiple impacts must be tracked.

The revised batch initially achieved 16/16 and perfect paired accuracy with Qwen. This is consistent with successful use of world-specific evidence on the tested pairs, but a small saturated batch does not establish general robustness or rule out every shortcut. A subsequent fresh-interaction run with `gpt-5-mini` achieved 5/16 on the exact same questions and images, despite correct parameter estimates in both worlds. The detailed comparison and its protocol limitations are given below.

### F. NewtonBench comparison to find weaknesses

The user then chose to test NewtonBench directly before designing further difficulty. The separate repository was run on `m0_gravity` with a code-assisted agent. An easy run was followed by a hard-equation, complex-system run with three trials.

Operational problems included shell continuation syntax, an incorrect argument spelling, and an unavailable judge model. After switching the configured judge to an available model, Qwen's hard run completed successfully. A subsequent three-trial `gpt-5-mini` run used the same named task settings and completed without execution failures, but all three submitted laws were wrong. The saved traces now provide examples of both successful discovery and failed hypothesis fitting.

## 2. Measured pilot results

The table reports local records, not an exhaustive evaluation across models. Rows use `qwen3.8-max` unless explicitly labeled `gpt-5-mini`.

| Experiment | Measurements / trials | Recorded outcome | Evidence |
|---|---:|---|---|
| Original material identification | 46 measurements | Property score 100% | [Private evaluation](results/material_lab_eval/identify_material_20260917_121422/private_evaluation.json) |
| Initial balance pipeline | 39 measurements, 6 questions | Properties 100%; images 6/6 | [Summary](results/density_pipeline/20260917_140220_830401/summary.json) |
| Additional simple balance runs | 30 and 32 measurements | Both images 6/6; properties 100% | [Run 2](results/density_pipeline/20260917_141142_433050/summary.json), [run 3](results/density_pipeline/20260917_154458_439374/summary.json) |
| Harder balance pipeline | 46 measurements, 32 questions | Properties 100%; images 32/32 | [Summary](results/density_pipeline/20260917_162329_143006/summary.json) |
| Liquid pipeline | 39 measurements; 4 of 8 questions saved | Properties 100%; saved answers 4/4 correct; incomplete | [Partial evaluation](results/density_pipeline/20260918_200352_896919/evaluation_with_history.json) |
| Bounce identification | 10 measurements | Gravity and contact score 100% | [Private evaluation](results/bounce_lab/identify_bounce_20260920_162018/private_evaluation.json) |
| Original bounce images | 8 questions | 8/8 | [Summary](results/bounce_evaluation/20260920_164350_437670/summary.json) |
| Revised paired-world bounce images | 16 questions / 8 pairs | 16/16; both worlds 8/8; all pairs correct | [Summary](results/bounce_evaluation/20260920_180559_829666/summary.json) |
| `gpt-5-mini` fresh bounce pipeline | World 1: 6 measurements; world 2: 4; 16 image questions | Both parameter scores 100%; images 5/16 (31.25%); pairs 2/8 (25%) | [Summary](results/bounce_evaluation/20260922_103549_466816/summary.json) |

The liquid JSON stores `score: 0.5` because checkpoint scoring divides four correct answers by all eight planned questions. It is neither a completed 50% result nor an eight-question 100% result. Its status remains `running/image_evaluation`; the inspected artifacts do not explain why execution stopped or establish that a process is still running.

The new records support an initial two-model comparison for bounce and NewtonBench. The density results above remain Qwen-only evidence; no completed `gpt-5-mini` density result was found in the inspected result directories. A larger controlled model comparison remains to be conducted.

### New bounce result: correct identification, weak visual prediction

The completed new run is [20260922_103549_466816](results/bounce_evaluation/20260922_103549_466816/summary.json), with `gpt-5-mini` used for both fresh interaction and image evaluation. The snapshot's `batch.json`, `questions.json`, and all 80 PNG files were checked byte-for-byte against the earlier Qwen snapshot and are identical.

| Measure | World 1 | World 2 |
|---|---:|---:|
| Valid measurements | 6 | 4 |
| Estimated gravity (m/s²) | 3.00344 | 4.047 |
| Ground-truth gravity (m/s²) | 3.0 | 4.05 |
| Restitution estimates, A/B/C/D | 0.600 / 0.849 / 0.349 / 0.750 | 0.719 / 0.740 / 0.470 / 0.640 |
| Gravity and contact score | 100% | 100% |
| Explicitly called `finish` | No | Yes |
| Image accuracy | 2/8 (25%) | 3/8 (37.5%) |

Every submitted restitution estimate differs from its ground truth by at most 0.001. The world's gravity errors are also small (approximately 0.115% and 0.074%). Thus, poor image performance cannot be described simply as failure to identify the tested constant parameters. The saved image responses contain only choice letters, so they do not establish whether the main errors were visual measurement, object matching, repeated-impact calculation, use of the history, or matching predicted positions to options. Sensitivity near collisions also warrants checking before excluding an effect of small parameter errors.

The correct question IDs were `bounce_hard_001_w1`, `bounce_hard_001_w2`, `bounce_hard_003_w2`, `bounce_hard_008_w1`, and `bounce_hard_008_w2`. Only pairs 001 and 008 were fully correct. Full responses and expected answers are in the [evaluation record](results/bounce_evaluation/20260922_103549_466816/evaluation_with_history.json).

**Comparison limitation:** this run used `max_turns=8`; the earlier Qwen paired-world run recorded 32 turns as its limit and reused its saved first-world interaction. GPT reached the first-world turn limit after submitting both sets of estimates, without calling `finish`; its second-world interaction did call `finish`. Both image evaluations nevertheless completed. Identical test images make the outcome comparison useful, but different interaction budgets and histories prevent treating it as a fully matched causal comparison of model ability. A rerun with matched budgets and evidence is needed.

An earlier GPT attempt, `results/bounce_evaluation/20260922_103516_501283/`, has a saved `running/experiments/world_001` status and no completed summary. It is excluded from accuracy statistics. The status file alone does not establish whether that process remains alive.

## 3. NewtonBench: result and agent behavior

The verified hard run is [complex_system_noise0_0_v2](../NewtonBench/evaluation_results/qwen3.8-max/m0_gravity/code_assisted_agent/hard/v0/complex_system_noise0_0_v2/aggregated_results.json): `m0_gravity`, hard equation, complex system, law version `v0`, noise 0, code-assisted agent, model and judge both `qwen3.8-max`.

All three trials recovered:

```python
def discovered_law(mass1, mass2, distance):
    return 6.674e-5 * (mass1 + mass2) ** 2 / distance ** 1.5
```

| Trial | Experiments executed | Recorded rounds | Python calls recorded | Tokens | RMSLE | Exact accuracy |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 50 | 9 | 3 | 27,947 | 0 | 100% |
| 1 | 12 | 6 | 1 | 20,151 | 0 | 100% |
| 2 | 19 | 7 | 2 | 23,481 | 0 | 100% |
| Mean | 27 | 7.33 | 2 | 23,859.67 | 0 | 100% |

Total runtime was 654.17 seconds. No whole-trial retries or failed trials were recorded. These counts do not imply that every proposed action succeeded.

**What the agent learned.** It used short-time velocity changes to estimate acceleration, then recovered force by multiplying by the moving object's mass. Varying one mass or distance at a time revealed that doubling one mass from a symmetric baseline changed force by a factor of 2.25, consistent with squared total mass. Doubling distance gave a factor near `2^-1.5`. Python calculations checked the constant and exponents across measurements. The submitted law agrees with the saved ground truth and had zero recorded numerical error.

**Why the hard setting was still tractable.** The complex system provides trajectory observations, but precise early velocity samples allow the agent to approximate the local force directly. Noise was zero, the target law has a compact separable structure in total mass and distance, and the model could use Python. Thus, a complex observation setup did not necessarily force difficult long-horizon system identification. This is an interpretation supported by the traces, not a result for every NewtonBench module or difficulty setting.

**What final accuracy conceals.** Trial 0 used over four times as many measurements as trial 1. Some requested trajectories returned only an initial sample or moved too far for the intended small-time estimate; the agent adjusted its reasoning and experimental settings. Trial 1 attempted follow-up experiments but received generic reminders rather than new measurements. Trial 2 received an explicit action-format reminder before continuing. The exact parser causes need further inspection, but the missing measurement outputs and protocol feedback are visible in the saved conversations.

These observations suggest measuring experimental efficiency, validity of chosen settings, action-format reliability, and recovery from uninformative measurements in addition to final law accuracy.

The earlier [easy run](../NewtonBench/evaluation_results/qwen3.8-max/m0_gravity/code_assisted_agent/easy/v0/vanilla_equation_noise0_0_v1/aggregated_results.json) recorded RMSLE 0 but exact accuracy 0 with the old `gpt41` judge. Its submitted law has the same form as the recorded target. Separately, the conversation captured judge requests failing with HTTP 503 because that model was unavailable. The current judge implementation returns False after all exceptions, conflating infrastructure failure with a negative equivalence judgment. The specific easy-run result therefore requires a judge audit; its aggregate alone cannot prove the failure cause.

### New NewtonBench comparison: `gpt-5-mini`

Source: [GPT aggregate](../NewtonBench/evaluation_results/gpt-5-mini/m0_gravity/code_assisted_agent/hard/v0/complex_system_noise0_0_v2/aggregated_results.json) and its three `trials/trial*.json` files. Both model runs use `m0_gravity`, hard, complex system, `v0`, zero noise, code assistance, and the `qwen3.8-max` judge.

| Metric | `qwen3.8-max` | `gpt-5-mini` |
|---|---:|---:|
| Exact law accuracy | 3/3 (100%) | 0/3 (0%) |
| Mean raw RMSLE | 0 | 1.241738 |
| Mean experiments per trial | 27 | 27 |
| Mean recorded rounds | 7.33 | 6.00 |
| Mean tokens per trial | 23,859.67 | 17,452.33 |
| Total elapsed runtime (seconds) | 654.17 | 216.28 |
| Whole-trial retries / failed executions | 0 / 0 | 0 / 0 |

Recorded runtime and token counts describe these runs; they are not controlled latency or cost benchmarks. “Three successful trials” in the console means three completed executions, not three correct laws.

Using `K = 2.6696e-4`, GPT submitted the following incorrect expressions. The true law is `6.674e-5 * (m1 + m2)^2 / r^1.5`.

| Trial | Submitted force law | Experiments | Rounds | Python calls | Tokens | RMSLE |
|---|---|---:|---:|---:|---:|---:|
| 0 | `K * m1^1.75 * m2^0.25 / r^1.5` | 27 | 6 | 2 | 22,782 | 0.687831 |
| 1 | `K * (m1*m2)^1.5 / r^1.5` | 24 | 6 | 2 | 13,467 | 2.342763 |
| 2 | `K * m1*m2 / r` | 30 | 6 | 2 | 16,108 | 0.694621 |

These failures are supported by nonzero numerical errors and visibly different functional forms, rather than only an LLM judge's label. Trial 0 incorrectly makes the mass dependence asymmetric; trial 1 uses a product power instead of squared total mass; trial 2 also uses the wrong distance exponent.

The transcripts show three concrete weaknesses:

- **Restricted hypothesis fitting:** GPT repeatedly fitted the family `C*m1^p*m2^q*r^s` by log-linear regression. Squared total mass is outside that family. Large residuals were printed, but the submitted laws still did not recover the additive mass structure.
- **Measurement transcription and association errors:** in trial 0, the measurement at `m1=m2=1, r=0.75` returned first-step velocity `-4.110118e-08`, but the later analysis copied `-4.271360e-07`. In trial 2, the second Python analysis labeled several different mass settings as `m1=m2=r=1`, corrupting the association between parameters and observations. These errors occur in the agent-written analysis, not in the saved raw measurements.
- **Insufficient rejection of contradicted candidates:** the Python output displayed substantial observed/predicted mismatches, yet a final law was submitted after two experiment batches and two analysis calls. Equal mean experiment counts therefore did not produce equal discovery quality.

This gives a more specific research direction than merely increasing the number of experiments: test whether a model preserves evidence accurately, detects model-family mismatch, and chooses experiments to reject incorrect hypotheses. It does not prove that any one of these factors alone caused the full performance gap.

## 4. Problems encountered and responses

| Problem | Response implemented or established | Current status |
|---|---|---|
| Ball appeared to pass through cup geometry | Cup geometry/contact handling and related checks were developed; parameters recorded | Approximate contact model remains; no fresh collision audit for this report |
| Render paths and multiple distance variants became confusing | Organized Lab 1 outputs; retained only the accepted far-distance render | Completed; canonical path is explicit |
| Video needed slower motion and longer duration | Retimed to 10 seconds with holds and cached frames | Completed; simulation velocity preserved |
| Later scenes could lose original object properties | Shared immutable registry, private manifests, identities, and Markdown records | Implemented |
| Text disclosed visual identities | Removed colors/IDs from evaluation prompts; appearances read from images | Implemented in current task designs |
| Single-object density comparisons were easy | Added 32 questions with multiple objects and unseen-material reasoning | Implemented; saturation remains |
| Unseen material does not determine a unique answer | Evidence-based Unknown grading and symbolic cancellation | Implemented |
| Liquid surface was hard to read | Revised surface/glass styling and measurement guides | Implemented; no new subjective visual review here |
| Changing gravity had no effect on static outcomes | Added timed-drop learning and dynamic bounce prediction | Implemented |
| Initial bounce task was too easy | Paired worlds, two-object conjunctions, image-read initial conditions, repeated impacts | Qwen still scores 16/16; GPT now scores 5/16 with correct parameter estimates |
| Correct parameter estimates did not yield correct visual answers | Identified the failure stage using separate private parameter scores and image scores | Observed in GPT; mechanism requires diagnostic controls |
| NewtonBench GPT analysis used the wrong law family and misassociated measurements | Audited submitted laws and agent-written Python against raw observations | Diagnosis recorded; no environment or analysis-tool changes made here |
| API connection/read timeouts | Explicit SDK timeouts and environment overrides | Mitigated; network availability remains external |
| Provider image-download timeout reported as HTTP 400 | Retry that specific transient error plus connection and standard transient HTTP errors | Implemented; does not fix every provider failure |
| Progress lost when a later request failed | Checkpoint interactions/answers and save run status and snapshots | Implemented; automatic resume remains open |
| NewtonBench shell commands failed | Remove spaces after continuation backslashes; use `--agent_backend` or `-b` | Syntax issue resolved |
| NewtonBench judge unavailable | Current runner selects available `qwen3.8-max` judge | Successful rerun; error-versus-wrong-answer distinction still unresolved |

The API harness currently allows 60 seconds for connection and 600 seconds for other network operations, with three retries after the first attempt and delays of 5, 10, and 20 seconds. A timeout warning followed by a correct answer means a later attempt succeeded; it is not inconsistent grading. Increasing timeout or retry limits does not cure an unreachable service, and retrying a request is different from resuming an interrupted experiment run.

## 5. What is completed, and what is not

**Completed infrastructure:** shared private records; public experiment tools; model harness; separate experiment/vision model selection; balance/liquid/bounce batch generation; reproducible rendering metadata; image snapshots; private scoring; per-answer logging; timeout/retry handling; current paired-world evaluation. Relevant source and regression tests exist, although they were not rerun for this report.

**Completed empirical pilots:** material identification, six- and 32-question balance evaluation, original and paired-world bounce evaluation, three-trial hard NewtonBench runs for both models, and a fresh GPT bounce pipeline. Image files exist for all current prepared batches.

**Not yet established:** a completed liquid evaluation from the inspected run; a controlled explanation for the new two-model difference; whether the bounce gap persists with matched budgets and evidence; generalization across many worlds and interaction seeds; the causal gain from active experimentation over fixed measurements; a broad model comparison; and novelty relative to the wider literature. The earlier blanket concern that all tested models score 100% must now be narrowed: Qwen still saturates these tasks, but GPT does not.

**Proposed but not implemented in the current bounce environment:** speed-dependent restitution, drag-law discovery, variable functional law families, a larger multiworld study, and systematic diagnostic ablations. The existing bounce model still uses constant gravity and constant material–surface restitution. The visual evaluation uses rendered candidate frames; general learned-law-to-video transfer has not been completed as a unified benchmark.

## 6. Recommended next experiments

1. **Finish measurement accounting first.** Resolve the incomplete liquid run and audit the NewtonBench judge discrepancy. Report question counts, completion status, and infrastructure failures separately from model errors.
2. **Diagnose GPT's bounce failure before further difficulty changes.** Repeat with the same interaction budget, then compare both vision models using the same public evidence. Add exact-parameter and numeric-scene controls to distinguish parameter precision, history use, visual reading, event tracking, and choice matching. The current 100% parameter scores versus 31.25% image score make this a direct test of the project's central transfer question.
3. **Use the NewtonBench traces to target discovery weaknesses.** Compare valid measurements, transcription/association errors, hypothesis-family changes, residual checking, protocol failures, and final law accuracy. A controlled comparison with structured access to measurements could test whether GPT's failures stem partly from manual data copying; the current evidence does not yet establish that cause.
4. **Introduce a law that requires distinguishing hypotheses.** A bounded speed-dependent restitution law remains a natural extension for the Qwen ceiling. Choose training measurements so constant and variable restitution can initially fit, then let well-chosen additional experiments disambiguate them. Evaluate at held-out impact speeds. This is a proposed design, not an already approved implementation.
5. **Separate the sources of difficulty.** Compare learned evidence + images, correct physics + images, learned evidence + exact numeric scene descriptions, and fixed experiment histories. These conditions isolate discovery, perception, calculation, and experimental choice.
6. **Retain paired-world controls and clear rendering.** Identical images with different evidence remain useful for showing evidence sensitivity. More difficulty should come from inference and transfer, not an unreadable liquid surface or tiny ambiguous visual differences.
7. **Scale independent evidence.** Expand across worlds, law parameters/families, and repeated interactions. The earlier suggested pilot of roughly 12 worlds × 8 questions is still a plan. Report uncertainty across worlds/runs rather than treating questions sharing a history as independent discoveries.

Removing experiments can make a hidden-world question underdetermined, as the user correctly noted. Such a condition is useful as an information-removal or shortcut control, not as a fair standalone task with the same identifiability. The main evaluation should provide an adequate experimental route to the correct answer.

The current evidence supports a functioning prototype, successful transfer by Qwen on the tested physical models, and a new case where GPT identifies parameters accurately but performs poorly on visual prediction. The next milestone is a controlled explanation of that gap and a reproducible demonstration of when better experimentation or better use of learned physics improves visual prediction.

## Supporting project records

- [New-session handoff and commands](SESSION_HANDOFF.md)
- [Original research advice and NewtonBench paper reference](newtonbench_experiment_advice.md)
- [Material laboratory](docs/material_lab.md) and [object registry](docs/object_registry.md)
- [Combined density pipeline](docs/density_pipeline.md) and [32-question suite](docs/density_balance_hard.md)
- [Liquid equilibrium task](docs/liquid_equilibrium.md)
- [World laboratory](docs/world_lab.md), [bounce laboratory](docs/bounce_lab.md), and [current bounce evaluation](docs/bounce_prediction.md)

Some early documents still describe the visual stage as future work. This report uses the later task documentation, current source, and saved results to distinguish that historical wording from the implemented state.
