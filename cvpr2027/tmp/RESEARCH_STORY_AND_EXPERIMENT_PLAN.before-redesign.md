# Research Story and Experiment Plan

Updated: 2026-10-22. Companion to `cvpr2027/PAPER_PLAN.md` and the paper draft in
`cvpr2027/author-kit-CVPR2026-v1-latex-/`. Sections 1–4 summarize the agreed story and design.
Section 5 maps the design onto the current code. Section 6 lists blocking issues that were found while
mapping the code.

---

## 0. Writing principle for claims

State what the benchmark measures and what it adds directly, without overclaiming and without
defensive phrasing:

- Describe prior work by the question it studies, and our work by the question it opens up.
  Do not write "none of X does Y" or "we do not claim".
- Claim measurement, not capability: "tests whether" rather than "shows that agents learn".
- Every factual claim about the benchmark must be true of the implemented version, for example the
  number of families and choice permutation (see §6).

## 1. Scientific question

> **Can multimodal agents learn the physical world through interaction?**

Sub-questions:

| | Question | Measured by |
|---|---|---|
| RQ1 | Does interaction help? | Accuracy gain over no interaction (B = 0) and the online learning curve |
| RQ2 | Did the agent learn *this* world's laws? | Same- vs sibling-world (cross-realization) gap; canonical-physics baseline; breakdown by condition type |
| RQ3 | Where does learning break? | Measurement probe, law-informed ceiling, simulator oracle |

## 2. Story

1. **Human intuition.** Humans learn an unfamiliar physical world by acting in it. They push and drop
   things and watch what happens, and they form an understanding of the principles behind it. Then
   they carry that understanding back to vision: a glance at a new scene is enough to foresee how it
   will unfold.
2. **The gap.** Learning by interaction and visual understanding are evaluated separately:
   - Interactive physics benchmarks (PHYRE, I-PHYRE, DeepPHY, IPR-1) score task success, which can
     come from search.
   - Scientific-discovery benchmarks (NewtonBench, PhysGym, DiscoverPhysics) test laws in numbers and
     symbols.
   - Visual hidden-physics benchmarks (Physion++, ComPhy, InPhyRe) hand the evidence over passively.

   What remains open is whether interaction produces understanding that holds when the agent looks at
   a new scene. Early evidence is negative: VLMs trained through interaction do not transfer to related
   tasks (Schulze Buschoff et al.).
3. **Our idea: interaction and evaluation are the same visual experiment seen from two sides.** The
   unit is *scene + intervention + Δt → outcome frame*.
   - During interaction, the agent poses experiments and the world shows the outcome.
   - During the exam, the world poses new experiments and the agent must foresee the outcome.

   NewtonBench asks whether an agent can *write down* the law. We ask whether it can *see with* the
   law.
4. **Ruling out shortcuts.**

   | Design choice | Shortcut it rules out |
   |---|---|
   | Laws depart from textbook physics | Priors |
   | Exam uses new scenes | Memory |
   | Tools are frozen during the exam | Search |
   | Close rendered distractors, including the textbook-physics future | Appearance matching |
5. **Measurement.** Learning is *what interaction changes*:
   - the online learning curve during interaction;
   - the exam-accuracy gain over B = 0;
   - the gap between the agent's own world and a sibling world.

## 3. Expected results (hypotheses, not claims)

- **H1, some learning.** Accuracy rises above the B = 0 floor but stays well below the law-informed
  ceiling.
- **H2, weak specificity.** Part of the gain is generic familiarity with the scene type, so the
  same−cross gap is smaller than the raw gain. Coefficient-field changes (rule_2) are likely easier
  to learn than structural law changes (rule_1).
- **H3, the bottleneck is forming the law, not perceiving it.** The probe is decent and the
  law-informed ceiling is high. The loss is in turning experiments into a transferable law.
- **H4, predicting helps.** Predict-then-observe beats observe-only at equal budget.

Results that contradict these are also findings; the design separates every outcome.

## 4. Experiment design

### 4.1 Episode (method 3: predict-then-observe)

```
Interaction phase (budget B trials)                         Freeze    Final exam
agent chooses experiment → [text prediction] → sees            │   new scene + intervention
outcome frame;  checkpoint every k trials (4-way MCQ,          │   → choose future frame
host-posed, feedback shown)                                    │     (4-way, no feedback)
```

- **Per realization (variant):** 15 instances = **4 exploration + 4 checkpoint + 7 held-out exam**.
- **Agent trials:** the agent writes a text prediction, which is logged and not scored, and then sees
  the true outcome frame. Exactly one frame per trial.
- **Checkpoint trials:** host-posed at fixed indices (e.g. every 4 trials) with difficulty matched
  across positions. They are free and do not use budget. The checkpoint pool is disjoint from the
  exam.
- **Final exam:** each item is answered from the frozen history alone, with no feedback.

### 4.2 Rendering: all offline

| Item | When rendered | Online cost |
|---|---|---|
| Exam candidates (4 frames) | Offline (already exists; see §6 for fixes) | 0 |
| Checkpoint candidates (4 frames) | Offline, from current support instances | 0 |
| Outcomes of the agent's experiments (1 frame) | Offline over a discrete action grid (e.g. 5 speeds × 5 angles × 3 objects); a tool call becomes a cache lookup | 0 |
| Agent predictions | Text only | 0 |

- **Reducing render cost** (Blender Cycles at 1920×1280 and 96 samples is the bottleneck):
  - Use Eevee or Workbench, or fewer samples.
  - Render at 512×512 or lower.
  - Render the final frame only.
  - Batch across GPUs.
- **Action-grid estimate:** about 75 × 4 × 378 ≈ 113k frames, rendered once and reused for every
  model and seed.

### 4.3 Experiments

| Exp. | Question | Manipulation | Output |
|---|---|---|---|
| **E0 Validity** | Is the exam fair? | Simulator oracle ≈ 100%; appearance heuristic and label-only classifier ≈ 25%; canonical-physics baseline well below the oracle; human pilot | Validation section |
| **E1 Learning** | Does interaction help? | B ∈ {0, B_small, B_full}; online checkpoint curve | Main table and learning curves |
| **E2 Specificity** | Did it learn *this* world? | Exam with same- vs sibling-variant history; optional world switch at B/2 (expect a drop, then recovery) | Gap table; switch curve |
| **E3 Interaction matters** | Do acting and predicting help? | Predict-observe vs observe-only vs yoked passive (a fresh agent given the same history), at equal budget | Comparison table |
| **E4 Diagnosis** | Where does it break? | Measurement probe (accuracy and tool calls); law-informed ceiling; oracle | Failure-decomposition bar chart |

### 4.4 Setup and statistics

- 4–6 multimodal models, each with a disclosed harness, evaluated as model–harness systems.
- 3 seeds.
- Cluster bootstrap over realizations; paired tests for same vs cross and for the E3 arms; a
  mixed-effects logistic fit for learning slopes.
- Breakdowns by family and by condition type (rule_1 / rule_2 / combined_rule).

---

## 5. Reuse map for the current project

Paths are relative to `agent_reproduce/`.

### 5.1 Hierarchy: reuse as is

| Paper level | Code | Count |
|---|---|---|
| Family | `world_instances/<family>/` | 7 |
| Regime | `<family>/g1..g3/` (`baseline/instance.json`, `group_manifest.json`) | 21 |
| Condition | `rule_1` (structural), `rule_2` (hidden field), `combined_rule` | 63 |
| Realization | `variant_1..6/` | 378 |
| Instance | `q01..q15/` (`question.json` public, `instance.json` host-only) | 5,670 |

Variants within a group share scene states (seeded by `sha256(group+variant+index)`), so siblings can
serve as the cross-realization pair directly. **Action:** add a split file per variant listing the
4 exploration, 4 checkpoint and 7 exam questions. This needs no new generation.

### 5.2 Interaction: reuse and extend

| Need | Existing | Change |
|---|---|---|
| Interaction loop | `src/interact.py::run_interaction`, `InteractionRecord`, timeout skipping | Keep. Add checkpoint injection every k turns and logging of text predictions |
| Tools and budget | `src/envs/attraction_bench.py`, `src/envs/autonomous_attraction_bench.py` (24 units / 8 turns) | Keep the numeric tools. Add a `run_experiment(action_id)` tool that returns a cached outcome frame. Discretize inputs to an action grid |
| Task wrapper | `src/tasks/discover_world.py` (`DiscoverWorldTask`) | Add the predict-before-observe prompt and the checkpoint question format |
| Entry point | `interaction.sh` → `scripts/pipeline/interact_question.sh` → `scripts/pipeline/run_interaction.py` | Add flags `--budget`, `--checkpoint-every`, `--mode {predict_observe, observe_only}` |
| Other families | `src/envs/world_family.py` (`WorldFamilyEnv`) exists but is **not routed** | Route `run_interaction.py` to `WorldFamilyEnv` for the 6 non-central families (see §6) |

**Existing interaction records** (~7,056, central family only, 5 models) were collected per question,
not per variant with a split. They are useful as pilot data and as an observe-only reference, but they
are not directly the E1–E3 arms (see §6.4).

### 5.3 Image evaluation: reuse with fixes

| Need | Existing | Change |
|---|---|---|
| 4-way image MCQ | `src/evaluation/visual.py::build_image_choice_content`; `src/evaluate.py::run_evaluation` | Keep. **Permute choices per instance** (see §6.1) |
| History injection | `src/evaluate.py::_build_history_context` (text transcript) | Keep. Also include outcome frames once tools return images |
| B = 0 / no history | `mode = no_history` in `src/evaluate.py` | Reuse directly for B = 0 |
| Cross-realization | — | Pass a sibling variant's history into the exam of this variant (a small change to the eval script) |
| Checkpoint MCQs | — | Reuse the same builder; show the answer frame after the response |
| Entry point | `eval.sh` → `scripts/eval/evaluate_attraction_visual.py` | Generalize to all families; the legacy `eval.py` fallback is not wired |

### 5.4 Rendering: reuse the pipeline, fix the truth

| Need | Existing | Change |
|---|---|---|
| Central-force renders | `src/simulation/attraction_scene.py`, `blender_attraction.py`, `attraction_visual.py`; candidate policy `attraction_close_pairs_v1` | Keep; add the canonical-physics distractor |
| Other families | `scripts/pipeline/render_question.py::build_generic_manifest` → `src/simulation/blender_generic.py` | **Rewrite the truth computation** (see §6.2) |
| Close-candidate audit | `src/simulation/drag_candidates.py`, `candidate_audit.json` | Generalize as the E0 margin check |
| Outcome-frame cache | `src/simulation/render_scene.py`, `snapshot.py`, `render_record.py` | Render outcomes over the action grid into `renders/.../outcomes/<action_id>.png` |
| Speed | Blender Cycles, 1920×1280, 96 samples | Use Eevee/Workbench or fewer samples at ≤ 512 px for outcome and checkpoint frames |

### 5.5 Controls: mostly exist

| Control | Existing | Change |
|---|---|---|
| Measurement probe | `src/envs/object_attribute_bench.py`, `src/tasks/characterize_objects.py`, `scripts/interact/interact_object_attributes.sh` | Report relative-error accuracy within τ and tool calls; run in baseline worlds |
| Oracle, ceiling and reference policies | `src/evaluation/attraction_audit.py` (fixed policies with 0/1/2/4 readings) | Use as the template for the simulator oracle, law-informed ceiling and B = 0 reference |
| Canonical-physics baseline | `measure_baseline_force`; `baseline/instance.json` per group; `src/evaluation/drag_baseline.py` | Simulate exam scenes under baseline laws and pick the nearest candidate |
| Paired-world precedent | `src/bounce_evaluate.py`, `docs/bounce_prediction.md` | Pattern for cross-realization evaluation |
| Harness configs | `configs/harnesses/openai_default.yaml`, `configs/agents/default.yaml`, `src/harness/openai.py` | Keep; record per-system memory policy for the paper |
| Yoked passive arm | — | New: replay a recorded history into a fresh agent without tools |

### 5.6 Other existing material

- `newtonbench_experiment_advice.md` already recommends: a known-physics oracle, a no-experiment
  condition, paired worlds and budget curves. It is consistent with this plan.
- `SESSION_HANDOFF.md`: the drag result (1/8 numerical vs 8/8 images, a shortcut) motivated
  close candidates. Keep it as a validity lesson for E0.

---

## 6. Blocking issues found during code mapping (fix before any paper claim)

### 6.1 The answer is always position A

- All parsed `renders/**/scene.json` files have `answer: "A"`. All central ones have `truth_rank: 0`.
- The evaluator shows choices in A–D order.
- **Consequence:** a position bias alone can score up to 100%. This contradicts the paper's claim of
  independently permuted candidate positions.
- **Fix:** permute choices per instance with a seeded RNG at evaluation time, or re-label the
  manifests. Then re-score any existing evaluation.

### 6.2 Generic-family "truth" ignores the hidden law

- For the 6 non-central families, `build_generic_manifest` computes the correct frame as a
  constant-acceleration step from **baseline constants only**. It ignores the hidden
  `equation_parameters`.
- The distractors are fixed offsets (±3.5 cm in x, +3.5 cm in z).
- **Consequences:**
  - The "correct" answer equals the canonical-physics prediction, so the latent law is never tested.
  - The fixed-offset distractors are trivially recognizable.
- **Fix:**
  - Simulate each family under its realized law (`equation_parameters`, hidden field).
  - Generate distractors with the close-candidate policy, including the canonical-physics future as
    one distractor.
  - Re-render.
  - `docs/benchmark_experiment_summary.md` §11 already notes these simulators are unvalidated.

### 6.3 Interaction exists only for central-force

`run_interaction.py` always builds attraction environments. `WorldFamilyEnv` exists but is not
routed. Until it is routed and validated, the paper's 7-family claim cannot be supported by runs.

**Option:** scope the first submission to central-force plus 1–2 families that are validated end to
end.

### 6.4 Existing results

- Evaluations: only 67 completed (glm-5.3), with a mean image score of 16.4%, below chance.
  - That is consistent with issue 6.1 interacting with model position preferences, or with a
    pipeline bug.
  - Treat these runs as a debug signal, not a result.
- Interaction records: ~7,056 (central family only). They predate the split and the method-3
  protocol.

---

## 7. Suggested order of work

1. **Fix issues 6.1 and 6.2.** Choice permutation; real hidden-law simulation; close distractors
   including the canonical-physics future.
2. **E0 on central-force.** Oracle, appearance heuristic, label-only classifier, canonical-physics
   baseline.
3. **Add the per-variant split file**, and route the B = 0 / with-history / cross-history
   evaluation modes.
4. **Pilot E1 + E2** on central-force with 2 models; calibrate B and the distractor margin.
5. **Method 3:**
   - action grid and outcome cache (low-cost renders);
   - checkpoint injection and text predictions;
   - online curves;
   - E3 arms.
6. **Measurement probe (E4).**
7. **Extend to other families** as their simulators are validated (route `WorldFamilyEnv`).
8. **Update the paper** (Sections 3, 5 and 7) to match the implemented protocol.
