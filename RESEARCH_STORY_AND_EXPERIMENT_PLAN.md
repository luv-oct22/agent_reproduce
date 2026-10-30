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

## 4. Experiment design (v2, redesigned 2026-10-22)

This version builds on the law-contrastive exam that already exists in `src/law_contrastive/`
(design: `cvpr2027/EXPERIMENT_REDESIGN.md`) and adds what the story still needs: interaction that
happens *in images* and an exam that is the *same experiment* the agent ran. The superseded v1 plan is
in `cvpr2027/tmp/RESEARCH_STORY_AND_EXPERIMENT_PLAN.before-redesign.md`.

### 4.1 What the story requires, and whether the current code meets it

| Requirement from the story | Current code | Verdict |
|---|---|---|
| Unfamiliar laws (priors are not enough) | Central-force worlds: rule_1 (structural), rule_2 (hidden field), combined; canonical law always a wrong candidate in the law-contrastive exam (canonical baseline 0%) | **Meets** |
| The exam tests *this* world, not generic knowledge | Law-contrastive items: the 4 candidates are canonical + 3 sibling laws; the same images answer differently per world, so world-blind ≤ 33% | **Meets**, and stronger than a separate cross-realization run |
| A fair exam (no position/appearance shortcuts) | Validation: oracle 100%, appearance 26.3%, label prior 25.9%, answers uniform over A–D | **Meets** |
| Interaction and evaluation are the *same visual experiment* | Interaction tools (`configure_trial`, `apply_impulse`, `measure_force`, `track_motion`) return **numbers only**; the exam asks about **images** | **Gap**: the agent never sees the world during interaction |
| Exam experiments have the same form as interaction experiments | Exam = launch state + Δt; interaction = configure_trial + track_motion. Same physical form, but the agent sees a table in one and an image in the other | **Partial** |
| Learning is observed *as it happens* | No checkpoints; records are one-shot 8-turn episodes | **Gap** |
| Learning is attributable to interaction, and to *acting* | `no_history` / `own` / `sibling` / `law_text` arms; no observe-only or yoked arm | **Partial** |
| Scope beyond one family | Only central-force has hidden-law simulation and interaction | **Gap** (scope) |

Conclusion: **keep** the worlds, simulator, law-contrastive exam, validation and arms. **Replace**
the numeric-only interaction with a visual experiment tool, and **add** checkpoints. This is the
minimum change that makes the story true.

### 4.2 The unit: one visual experiment, used in both phases

An experiment in central-force is `(anchor, probe launch position, launch velocity, start time, Δt)`.
Its outcome is the probe position after Δt, rendered as a frame.

- **Interaction:** the agent chooses the experiment; the world returns the outcome **frame**
  (with an optional faint trajectory trace) plus the existing numeric measurement.
- **Checkpoint:** the host poses an experiment in law-contrastive form; the agent chooses one of four
  frames, then sees the true one.
- **Exam:** the host poses a new experiment in law-contrastive form; no feedback.

The same renderer, camera and scene layout are used in all three, so the exam asks the agent to use
what it learned in the form in which it learned it.

### 4.3 Episode protocol (one episode = one hidden-law world)

```
INTERACTION (budget B experiments)                       FREEZE        EXAM
 t=1..B : agent picks launch from grid → writes expected     │   law-contrastive items
          outcome (text) → sees outcome frame + numbers      │   of this world, 4-way,
 every k: CHECKPOINT (host-posed, law-contrastive, 4-way)    │   no feedback
          → answer → sees true frame                         │
```

- **Action grid (new):** discretize launches so every outcome can be pre-rendered, e.g. 6 launch
  positions × 4 speeds × 2 directions × 3 durations = 144 experiments per regime. The positions and the
  anchor are shared by sibling worlds, so one grid serves all worlds of a regime. The numeric tools
  stay available at their current cost.
- **Budget:** B ∈ {0, 4, 12} experiments (B_small, B_full to be calibrated in the pilot). Checkpoints
  are free.
- **Checkpoints:** every 3 experiments, drawn from a checkpoint pool of law-contrastive items that is
  disjoint from the exam pool, matched in duration across positions.
- **Exam:** 8 law-contrastive items per world (the current `per_world`), from the existing 176 items.

### 4.4 Experiments

| Exp. | Question | Arms / manipulation | Needs new interaction? | Output |
|---|---|---|---|---|
| **E0 Validity** | Is the exam fair? | Oracle, canonical, appearance, label prior, world-blind max (done); + identifiability filter (2 laws excluded); + small human pilot | No | Validation table (numbers exist) |
| **E1a Learning from existing records** | Does numeric interaction help? | `no_history` vs `own` vs `sibling` vs `law_text` on the 528 exam questions | **No**: reuses ~2,800 existing records | Main table, first result |
| **E1b Learning from visual interaction** | Does seeing the world during interaction help? | New episodes with the visual tool at B ∈ {0, 4, 12}; checkpoint curves | Yes | Learning curves + main table |
| **E2 Specificity** | Did it learn *this* world? | Built into every item: correct rate vs **sibling-pick rate** vs **canonical-pick rate**; plus the `sibling`-history arm | No (E1a) / Yes (E1b) | Error-composition figure |
| **E3 Modality and acting** | Which evidence and which mode of interaction teaches the world? | At equal budget: (i) numbers only (existing tools), (ii) frames only, (iii) frames + numbers; and (iv) yoked passive: a fresh agent receives the history of (iii) without acting | Yes | Comparison table |
| **E4 Diagnosis** | Where does it break? | `law_text` ceiling (applying a known law to images); oracle; measurement probe (`object_attribute_bench`); stated-law readout after interaction (analysis only) | Partly | Failure decomposition |

How the results read:

- `own > no_history` → interaction helped (RQ1).
- Errors that pick the **sibling** answer in the `own` arm → the agent learned "a modified law" but not
  *which*; picks of **canonical** → it fell back to textbook physics (RQ2).
- `law_text ≫ own` → the bottleneck is forming the law from evidence, not applying it to images
  (RQ3); `law_text` near chance → the bottleneck is reading the images.
- E3: frames > numbers → visual experience is what transfers to visual foresight; numbers > frames
  → agents learn better from measurements and fail to translate them into vision. Either is a finding
  about the interaction-to-vision link that is the paper's question.
- A checkpoint curve that rises and an exam score that matches it → learning that transfers; a curve
  that rises but an exam at the `no_history` level → local fitting without understanding.

### 4.5 Scale and cost

| Item | Count / cost |
|---|---|
| Worlds | Central force: 3 regimes × 3 conditions × 6 realizations = 54, minus non-identifiable ones |
| Exam | 176 items, 528 questions (existing); 5 Blender frames per item ≈ 880 frames |
| Checkpoint pool | about 4 per world ≈ 200 items, built by the same `items.build` search with a different seed and disjoint scenes |
| Action-grid outcome frames | 144 per regime × 54 worlds ≈ 7.8k frames; render with a fast setting (Eevee/Workbench or 16 samples, 960×640) |
| API, E1a | 528 questions × 4 arms × 3 models ≈ 6.3k single-turn calls (as planned in EXPERIMENT_REDESIGN.md) |
| API, E1b + E3 | per model: 54 worlds × (3 budgets + 3 modality arms + yoked) episodes, each ≤ 12 experiments + 4 checkpoints + 8 exam questions |

Pilot first: one regime (g1), one condition (rule_2, the most learnable), two models, B ∈ {0, 12}.

### 4.6 Setup and statistics

- 3–5 multimodal models with completed records (glm-5.3, gpt-6.1-sol, qwen3.8-max first), each with
  a disclosed harness, evaluated as model–harness systems.
- 3 seeds for E1b and E3.
- Cluster bootstrap over worlds; paired tests on identical exam questions for every arm contrast;
  a mixed-effects logistic fit for checkpoint slopes.
- Breakdowns by regime and by condition (rule_1 / rule_2 / combined_rule).
- Scope of the first submission: **central force**. Other families enter only after their simulators
  implement the hidden law (§6.2) and pass E0.

---

## 5. Implementation plan: keep, extend, replace

Paths are relative to `agent_reproduce/`.

### 5.1 Keep as is

| Component | Path |
|---|---|
| Worlds, laws, scenes | `world_instances/central_force_dynamics/` |
| Simulator | `src/worlds/attraction.py` (`AttractionWorld`) |
| Exam items, validation, render manifests | `src/law_contrastive/items.py`; `results/law_contrastive/items/` |
| Exam arms and ledger | `src/law_contrastive/exam.py` (`no_history`, `own`, `sibling`, `law_text`) |
| Analysis | `src/law_contrastive/analysis.py` |
| Renderer | `src/simulation/blender_attraction.py`, `scripts/render_law_contrastive.sh` |
| Interaction loop | `src/interact.py` (`run_interaction`, `InteractionRecord`, timeout skipping) |
| Harness | `src/harness/openai.py`, `configs/harnesses/` |
| Measurement probe | `src/envs/object_attribute_bench.py`, `src/tasks/characterize_objects.py` |
| Existing ~2,800 completed records | `results/central_force_dynamics/**/interaction/` → E1a evidence |

### 5.2 Extend

| Change | Where | Notes |
|---|---|---|
| `run_experiment(grid_id)` tool that returns the cached outcome frame + the numeric reading | new env `src/envs/visual_attraction_bench.py`, subclassing `AutonomousAttractionBenchEnv` | Same budget accounting; image returned as a message attachment |
| Image observations in the interaction loop | `src/interact.py`, `src/harness/openai.py` | Tool results may carry images; harness memory policy disclosed (keep last N frames + text log) |
| Checkpoint injection and text predictions | `src/tasks/discover_world.py` (or a new `VisualDiscoverTask`) | Every k experiments, insert a law-contrastive item; log `expected_outcome` before each experiment |
| Checkpoint pool | `src/law_contrastive/items.py::build` with `pool='checkpoint'`, disjoint scenes | Same validation applied |
| Arms `frames_only`, `numbers_only`, `frames_numbers`, `yoked` | `src/law_contrastive/config.py` `ARMS`, `exam.py::evidence` | Yoked = replay a recorded visual history without tools |
| Online-curve analysis | `src/law_contrastive/analysis.py` | Checkpoint accuracy by index; logistic mixed-effects slope |

### 5.3 Replace

| Old | Replaced by | Reason |
|---|---|---|
| Old exam renders and candidates (`renders/central_force_dynamics/`, `attraction_close_pairs_v1`) | Law-contrastive exam | Answer always A, collinear fixed geometry, canonical physics answers 62–83% |
| Per-question 8-turn records as *the* protocol | Per-world episodes with checkpoints | The story needs learning within one world, observed over time |
| Numeric-only interaction as the main condition | Visual interaction (frames + numbers) as main; numeric-only becomes an E3 arm | Interaction and evaluation must be the same visual experiment |
| Generic-family ground truth (`build_generic_manifest`) | Out of scope for the first submission | Ignores the hidden law (§6.2) |
| 4/4/7 split of the 15 scenes per variant | Exam pool + checkpoint pool from the law-contrastive search; exploration via the action grid | Scenes are now chosen for identifiability, not by index |

### 5.4 New pre-render job

`scripts/render_action_grid.sh` (new): for each regime, simulate every grid experiment in every world
with `AttractionWorld`, write manifests, and render with the existing Blender script at a fast
setting. Outcome frames are stored as
`renders/action_grid/<g>/<rule>/<variant>/<grid_id>.png`; the tool only looks them up.

---

## 6. Status of the earlier blocking issues

| Issue | Status |
|---|---|
| 6.1 Answer always A | **Fixed for the law-contrastive exam** (answers uniform over A–D); the old exam is kept only as the audit that motivates the redesign |
| 6.2 Generic families ignore the hidden law | Open; out of scope for the first submission |
| 6.3 Interaction only for central force | Accepted as the first-submission scope |
| 6.4 Old results (glm-5.3, 16.4%) | Explained by the old exam's defects; not used as results |
| New: two hidden laws are not visually identifiable (rule_1/combined `variant_3`; rule_2 `variant_3` in g1/g3) | Excluded from the exam; reported as an identifiability finding |

---

## 7. Order of work

1. **Render the law-contrastive exam** (`scripts/render_law_contrastive.sh`, GPU) — 0 of ~880 PNGs
   exist yet.
2. **E1a pilot, then full:** `python -m src.law_contrastive exam --model gpt-6.1-sol --limit 30`, then
   `run` and `analyze`. This is the **first real result** and needs no new interaction.
3. **Build the visual tool + action grid** (§5.2, §5.4) and the checkpoint pool; pre-render the grid.
4. **E1b pilot** on g1/rule_2 with two models, B ∈ {0, 12}; calibrate B and checkpoint spacing.
5. **E1b full + E3** (modality arms and yoked) on central force.
6. **E4**: `law_text` (from E1a), measurement probe, stated-law readout.
7. **Paper:** scope to central force; replace candidate description with law-contrastive candidates;
   add sibling-/canonical-pick rates; drop the 4/4/7 split; describe the visual tool and checkpoints.

---

## 8. Visual interaction: implemented (2026-10-26)

Package `src/visual_interaction/` (config `configs/visual_interaction.yaml`, tests
`tests/test_visual_interaction.py`, 6 tests passing). It reuses the law-contrastive worlds, simulator,
rendered items and harness. No API call or GPU render has been run yet.

**Episode, one per hidden-law world:**
- **Experiment menu, the same in every world:** 72 experiments.
  - start 0.9 / 1.2 / 1.5 m right of the anchor;
  - velocity: rest, upward 0.5 or 1.0, or outward 0.5 m/s;
  - start time 0.5 / 2.5 / 4.5 s;
  - duration 0.4 / 0.8 s.
- **Outcome:** each experiment returns a strobe frame showing the probe at its start and at 6 recorded
  moments, fading from faint to solid. Close-in runs stop at the minimum separation, and the outcome says
  so. Across the 54 worlds, 2873 runs are complete and 1015 stop early.
- **Prediction:** the agent states the expected end position before each experiment (`expected_end_m`).
  It is logged, not scored.
- **Budget:** 12 experiments.
- **Checkpoints:** after 0, 4, 8 and 12 experiments. Each is a law-contrastive question; the agent answers,
  then sees the true frame. Checkpoint items are the even-numbered items of a condition, and exam items the
  odd-numbered ones, so the two pools are disjoint.
- **Exam:** frozen, 258 questions per evidence arm. Images are sent as JPEG, so a full episode is about
  3 MB per request.

**Interaction modes** (`--mode`):

| Mode | Experiment returns | Predicts first | Who chooses experiments |
|---|---|---|---|
| `frames_predict` (main) | frames | yes | agent |
| `frames` | frames | no | agent |
| `numbers_predict` | numbers | yes | agent |
| `frames_numbers_predict` | frames + numbers | yes | agent |
| `random_frames_predict` | frames | yes | random |

**Exam evidence arms** (`--evidence`): `none`, `own`, `sibling` (another world of the same condition) and
`observations` (yoked passive: a fresh agent receives the same record without having acted).

**Analysis** (`analyze`):
- checkpoint learning curves, overall and per condition;
- exam accuracy per arm, with picks of the canonical and sibling answers;
- paired contrasts: own − none, own − sibling, own − observations.

**Run order:**
```bash
cd /mnt/shared-storage-user/chenliang1/agent_reproduce && conda activate agent_reproduce && export PYTHONPATH=.
python -m src.visual_interaction prepare          # done: manifests for 54 worlds x 72 experiments
DEVICE=CUDA ./scripts/render_visual_interaction.sh > logs/render_visual_interaction.log 2>&1 &   # 3,888 frames
python -m src.visual_interaction status
MODEL=gpt-6.1-sol MODE=frames_predict REGIMES=g1 RULES="rule_1 rule_2" EPISODES=6 \
  ./scripts/pilot_visual_interaction.sh > logs/pilot_visual_interaction.log 2>&1 &
```

**Cost per world, one model and mode:**
- episode: about 16 model calls (12 experiments and 4 checkpoints);
- exam: about 4 arms × ~5 items = 20 calls.

So the pilot (g1, rule_1 and rule_2, 6 worlds each) is roughly 12 × 36 ≈ 430 calls. Late episode turns
carry up to about 35 images.
