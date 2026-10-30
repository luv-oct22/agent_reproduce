# Experiment Redesign: Law-Contrastive Visual Exam

Updated 2026-10-22. Companion to `PAPER_PLAN.md`, the draft in `author-kit-CVPR2026-v1-latex-/`,
and `../RESEARCH_STORY_AND_EXPERIMENT_PLAN.md`. Code lives in the `src/law_contrastive/` package; one entry point, `python -m src.law_contrastive`, configured by `configs/law_contrastive.yaml`.

## 1. Why the current exam cannot support the paper

Audit of the 810 central-force exam items in `renders/central_force_dynamics/` (all checks are
reproducible with `validate_law_contrastive.py` and the scripts in `cvpr2027/tmp/redesign/`).

| Finding | Evidence | Consequence for the paper |
|---|---|---|
| The answer is always A | 810/810 manifests have `answer: "A"`, `truth_rank: 0` | Position bias alone can score 100%; contradicts "candidates permuted" |
| The four choices are always in the same geometry | 810/810 have the order C-A-B-D on one straight line, A-B gap fixed at 9.6 px | A "pick the 2nd of 4 collinear dots" rule scores 100% without physics |
| Distractors are not laws | Distractors come from rescaling the *canonical* force strength until the dot lands 2.5 cm away | No candidate represents canonical physics or a sibling law; the exam cannot tell world-specific from generic knowledge |
| Canonical physics already answers most items | Simulating the regime's canonical law picks the correct choice in 62-83% of items per condition | The latent law is mostly not needed; rule_2 is the worst (83/90) |
| The hidden law is barely visible | Median distance between the true outcomes of the three rule worlds on the same scene is 4 px at 1920 px; 79% of pairs are closer than one distractor step | Exam differences are below what VLMs resolve; consistent with GLM's 16.9% |
| The model is never told the elapsed time or launch velocity | Renders use `--no-text`; the exam prompt says only "the next frame" | The task is under-specified even with a perfect law |
| Records are per question, not per world | 15 independent 8-turn records per variant, none with a split | Fine as reusable histories; not the planned exploration/checkpoint/exam split |

**Decision:** keep the worlds, scenes, simulator, renderer, interaction records and harness; replace
how the exam candidates are built and how the exam is asked.

## 2. The redesigned exam: law-contrastive items

An **item** is one existing scene (anchor, probe launch, start time) plus an elapsed time, with four
rendered candidates. Each candidate is the true outcome under a *different law* of the same family,
regime and condition:

- the canonical law of the regime (inverse-square, regime constants),
- three sibling realizations (`variant_i`, `variant_j`, `variant_k`) of the same condition.

The same four images are an exam question for each of the three sibling worlds, and the correct label
differs per world. Candidate labels are shuffled per item.

What this buys, by construction:

| Property | Old exam | Law-contrastive exam |
|---|---|---|
| Canonical-physics baseline | 62-83% | 0% (the canonical outcome is always a wrong candidate) |
| Best policy that ignores which world is tested | 100% (position) | 33% (same images, three different answers) |
| Answer position | always A | uniform over A-D |
| Min candidate separation | 9.6 px | >= 20 px at 1920 px (median about 25 px) |
| Distractors | arbitrary rescaled-strength points | physically meaningful alternative laws |
| Specificity test | needs a separate cross-realization run | built into every item (sibling answer is one of the wrong choices) |

Items are found by a deterministic search (`build_law_contrastive_items.py`): first the 90 existing
scenes per condition, then sampled in-plane launches only to fill coverage. The shortest elapsed time
in {0.4, 0.6, 0.8, 1.0, 1.2, 1.5} s that separates all four candidates is used. 153 of 176 items
reuse an existing scene and its existing `context.png` geometry.

**Coverage limit found during the search.** Two hidden laws are visually indistinguishable from the
canonical law at any reachable horizon: rule_1 / combined_rule `variant_3` (p = 2, q = 0.9, s = 0.4)
and rule_2 `variant_3` in g1/g3 (quadratic space field, amplitude 0.4). Their best-case separation from
canonical is 2-3 px median. They are reported as *not visually identifiable* and excluded from the exam,
which is a finding worth one sentence in the paper (an identifiability check the old exam lacked).

## 3. Arms and what each answers

All arms use the same items and the same prompt template; only the evidence differs.

| Arm | Evidence given | Answers | Reuses |
|---|---|---|---|
| `no_history` (B = 0) | rendered context, launch, elapsed time | Prior-only floor; should be at most about 33% | `run_evaluation(with_history=False)` |
| `own` | an existing completed interaction record of the tested world | Does interaction help? (RQ1: own minus no_history) | existing ~2,800 records |
| `sibling` | a record from a sibling world of the same condition | Is the gain world-specific? (RQ2: own minus sibling; also how often the model picks the sibling's answer) | same records, re-paired |
| `law_text` | the hidden law and regime constants in text, no history | Ceiling once the law is known (RQ3: law_text minus own = law-formation failure; 100 minus law_text = applying the law to images) | `law_text()` in the runner |
| oracle / canonical / appearance / label prior | none (computed) | Validity (E0) | `validate_law_contrastive.py` |

Every answer is also coded as *correct*, *picked canonical*, or *picked sibling world*. The canonical
pick rate measures reliance on textbook physics directly.

The online learning curve, predict-observe arm and measurement probe from the current draft are kept
as follow-ups (Section 6); they need new interaction runs. The arms above need no new interaction.

## 4. Scale and cost

| Quantity | Value |
|---|---|
| Items (central force, 3 regimes x 3 conditions) | 176 (153 reuse an existing scene) |
| Questions per arm per model (item x world) | 528 |
| Renders | 5 images per item, about 875 frames; 1 min per item on CPU at 16 samples, faster on GPU |
| Models with records in enough worlds | glm-5.3 (54/54 worlds), gpt-6.1-sol (45), qwen3.8-max (39), gpt-5.5-xhigh (27), deepseek-v4-pro (19) |
| API calls for 4 arms x 3 models | about 6,300 single-turn calls with 5 images each |

A pilot of 30 questions per arm on one model is enough to check that the arms separate before the
full run.

## 5. Reuse map

| Component | File | Status |
|---|---|---|
| Worlds, laws, scenes | `world_instances/central_force_dynamics/` | reused unchanged |
| Simulator | `src/worlds/attraction.py` (`AttractionWorld`, hidden `equation`) | reused unchanged |
| Renderer | `src/simulation/blender_attraction.py` | reused unchanged |
| Render validator | `src/simulation/attraction_visual.py` | **edited**: adds `LAW_CONTRASTIVE_POLICY` (>= 19 px separation, no radial-phase constraint); the old policy is unchanged and its tests pass |
| Config | `configs/law_contrastive.yaml` | new; groups, rules, paths, item search, models, arms, generation settings |
| Paths and config | `src/law_contrastive/config.py` | new; typed config with CLI overrides |
| World access | `src/law_contrastive/worlds.py` | new; simulators per law, existing scenes, interaction records |
| Items | `src/law_contrastive/items.py` | new; build, render manifests, validation, audit of the old exam |
| Exam | `src/law_contrastive/exam.py` | new; evidence arms, prompts, resumable ledger; wraps `run_evaluation`, `OpenAIHarness`, `RecordedHarness`, `InteractionRecord` |
| Analysis | `src/law_contrastive/analysis.py` | new; status, Table 1/2, paired contrasts, error composition |
| CLI | `src/law_contrastive/__main__.py` | new |
| Render (manual) | `scripts/render_law_contrastive.sh` | new; calls the existing Blender renderer |
| Tests | `tests/test_law_contrastive.py` | new; fake harness, no API |
| Interaction records | `results/central_force_dynamics/**/interaction/` | reused as histories |
| Old exam renders | `renders/central_force_dynamics/` | kept; reported only as the motivating audit |

## 6. Run order

All commands run from the repo root with `conda activate agent_reproduce` and `PYTHONPATH=.`.
Every stage is idempotent; exam stages resume from each arm's `ledger.jsonl`.

| Step | Command | API | Output |
|---|---|---|---|
| 1. Prepare | `python -m src.law_contrastive prepare` | no | items, render manifests, validation, audit of the old exam |
| 2. Render (manual, GPU) | `DEVICE=CUDA ./scripts/render_law_contrastive.sh > logs/render_law_contrastive.log 2>&1 &` | no | `renders/law_contrastive/**.png` |
| 3. Check | `python -m src.law_contrastive status` | no | render and history coverage per model |
| 4. Dry run | `python -m src.law_contrastive run --dry-run --limit 3` | no | resolves evidence and prompts |
| 5. Pilot | `python -m src.law_contrastive exam --model gpt-6.1-sol --limit 30` | yes | 30 questions per arm |
| 6. Full run | `python -m src.law_contrastive run` | yes | every model x arm in the config |
| 7. Analyze | `python -m src.law_contrastive analyze` | no | `results/law_contrastive/exam/analysis.json` |

Validation results (step 1): oracle 100%, canonical 0%, label prior 25.9%, appearance 26.3%,
world-blind max 33.3%; the old exam's canonical-physics accuracy is 80.6%.

Follow-ups needing new interaction runs: checkpoint curve, predict-observe vs observe-only,
measurement probe, and other families once their simulators implement the hidden law.

## 7. Paper changes this implies

- §3 and §4: describe candidates as outcomes of alternative laws (canonical + sibling realizations),
  not "nearby successor states"; state the identifiability filter and its two excluded laws.
- §4 split: the exam uses law-contrastive items on existing scenes; exploration evidence comes from the
  interaction episodes. Drop the 4/4/7 split claim until checkpoint runs exist.
- §5 metrics: add canonical-pick and sibling-pick rates; the cross-realization control becomes the
  `sibling` arm on identical items.
- §6 validation: report the old-exam audit in one paragraph as motivation for the design, then the E0
  table for the new items.
- §7: Table 1 = models x {no_history, own, sibling, law_text}; Table 2 = by condition; Figure = error
  composition.
- Scope: central-force only (9 conditions, 3 regimes) until other families implement hidden laws in
  their ground truth; the 7-family claim must be removed or moved to future work.
