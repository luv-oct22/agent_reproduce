# Paper Plan — CVPR 2027

**Working title (candidate)**: *Do Multimodal Agents Learn Reusable Physics from Interaction? A Counterfactual Visual Prediction Benchmark under Latent Laws*

**One-sentence contribution**: We introduce a controlled evaluation protocol that, within a single latent physical world, separates an agent's task-level interaction from its ability to predict counterfactual future frames on held-out states — so that improvement on acted-on instances cannot be confused with reusable physical knowledge.

**Venue**: CVPR 2027 main track
**Type**: benchmark / empirical-diagnostic
**Date**: 2026-10-17
**Page budget**: 8 pages (main body to Conclusion end, references excluded) — CVPR standard
**Section count**: 8 sections (matches `sec/` files)
**Language**: proposal-tense only where experiments are not yet reported; empirical tense for results sections once numbers land

---

## Claims-Evidence Matrix

| # | Claim | Evidence | Status | Section |
|---|---|---|---|---|
| C1 | A benchmark that jointly controls (i) agent-selected experiments, (ii) hidden world constants and latent-law transformations, (iii) a hierarchical factorization of physical variation, (iv) support-to-held-out transfer under unchanged latent law, and (v) rendered future-frame MCQ as the final behavioral test — does not exist in prior interactive-physics or scientific-discovery benchmarks. | Related-work matrix (PHYRE, I-PHYRE, PhysGym, NewtonBench, Mars, PhysBench, LLF-Bench, Harness-Bench); explicit capability gap table | **Design-supported** (no "first" claim; framed as a *combination*) | §1, §7 |
| C2 | The protocol is implementable at scale: 7 phenomenon families × 3 world regimes × 3 latent-dynamics conditions × 6 latent-law realizations × 15 instances per realization = **5,670 instances**, with rendered observations and independently permuted candidate positions. | Simulator + renderer run end-to-end; instance counts and hierarchy validated | **Supported** (simulator exists) | §3 |
| C3 | Frontier multimodal agents, evaluated as full model+harness systems, leave a substantial headroom on held-out counterfactual prediction even when given a generous support budget; performance degrades under latent-dynamics condition shifts. | Baseline results across ≥3 frontier VLMs × support budgets; stratified by family/regime/condition | **Planned** — to be populated in W2–W3 | §6 |
| C4 | The support-to-held-out gap and the latent-dynamics shift jointly distinguish *transferable physical inference* from *appearance matching* or *memorized canonical physics*. | Ablation: same-realization held-out vs. cross-realization held-out; candidate-permutation sanity check; support-budget sweep | **Planned** | §6 |
| C5 | The benchmark passes validation controls: candidate-label permutation prevents shortcut, oracle-tool ceilings are achievable, weak baselines are separated from strong ones, and human performance under matched budget exceeds the MCQ floor. | Benchmark-validation subsection | **Planned** | §5 |

Every claim maps to evidence; every planned experiment supports a claim. No empirical claim appears in the manuscript until its evidence row is populated.

---

## Structure

### §0 Abstract (~180 words)

- **What we achieve**: introduce a benchmark that measures whether a multimodal agent converts finite virtual experiments into reusable physical knowledge transferable to held-out states.
- **Why it matters / is hard**: success on the acted-on instance can arise from appearance matching, memorized canonical physics, or local trajectory heuristics; existing interactive-physics and law-discovery benchmarks do not jointly control the support/held-out split under a *single* latent law with *rendered* counterfactual queries.
- **How we do it**: a five-level hierarchy (Physical-Phenomenon Family → World-Parameter Regime → Latent-Dynamics Condition → Latent-Law Realization → Counterfactual Prediction Instance), a budgeted tool-mediated support phase, a frozen-feedback held-out 4-way future-frame prediction phase.
- **Evidence**: 7 families × 3 regimes × 3 conditions × 6 realizations × 15 instances = 5,670 instances; baseline evaluations on frontier multimodal agents; ablations on support budget and latent-dynamics shift.
- **Most remarkable result**: *(TBD — fill in W3 once baselines land; placeholder: "frontier multimodal agents achieve X% on held-out counterfactual prediction under the highest support budget, far below the human reference of Y%.")*
- **Estimated length**: 150–200 words
- **Self-contained check**: a reader must be able to answer "what does the benchmark measure that prior work does not?" after reading the abstract alone.

### §1 Introduction (1.25–1.5 pages)

- **Opening hook** (2 sentences): Multimodal agents are increasingly deployed in interactive physical settings, yet a high task score after several trials is ambiguous — it can reflect reusable physical knowledge, or search, memorization, and appearance matching on the acted-on instance.
- **Gap / challenge**: Passive physical-reasoning benchmarks (PhysBench) skip interaction. Interactive physics puzzles (PHYRE, I-PHYRE) report success and sample efficiency but cannot separate knowledge from action search. Interactive law-discovery benchmarks (PhysGym, NewtonBench) target general law recovery rather than instance-level counterfactual prediction. Agent-feedback benchmarks (LLF-Bench) do not isolate physical dynamics. *None* jointly impose: agent-selected experiments + hidden latent law + rendered held-out counterfactual visual prediction under unchanged dynamics.
- **One-sentence contribution**: (see top of this plan).
- **Approach overview**: five-level latent-world hierarchy; budgeted tool-mediated support; frozen-feedback held-out MCQ over rendered future frames; candidate positions independently permuted per instance.
- **Key research questions**:
  - RQ1: Does support-budgeted interaction improve held-out counterfactual prediction?
  - RQ2: Does improvement survive latent-dynamics condition shifts (structural, coefficient-field, combined)?
  - RQ3: Where does the bottleneck lie — perception, evidence accumulation, hypothesis formation, or visual decoding?
- **Contributions** (3 bullets, falsifiable):
  1. A controlled benchmark that joins agent-selected physical experiments, hidden latent-law transformations, a hierarchical factorization of physical variation, support-to-held-out transfer, and rendered future-frame MCQ as the final behavioral test.
  2. A 5,670-instance implementation spanning 7 phenomenon families with rendered observations and per-instance candidate permutation.
  3. A stratified evaluation protocol and baseline study that separates transferable physical inference from appearance matching and memorized canonical physics.
- **Results preview**: *(TBD — single sentence, strongest quantitative headline.)*
- **Hero figure** (Figure 1, **critical**): A 2-row diagram.
  - *Top row*: one latent-law realization (e.g., a contact-dynamics family with a hidden restitution field); a support instance shown as an initial frame plus tool-call traces; the agent issues a budgeted sequence of measurements/interventions; arrows carry observations into the agent's memory.
  - *Bottom row*: feedback frozen; a held-out initial frame from the same realization; four rendered candidate future frames shown side-by-side, one correct; the agent must select.
  - *Visual contrast*: a side panel contrasting "matches the support instance by appearance" (wrong answer) vs. "applies inferred latent dynamics to a new state" (right answer).
  - *Caption draft*: "Our benchmark separates task-level interaction from transferable physical inference. **Top**: an agent interacts with support instances under a fixed tool budget. **Bottom**: with feedback frozen, the agent must select the correct counterfactual future frame on a held-out state governed by the same latent law. Improvement on the acted-on instance alone is insufficient evidence of reusable physical knowledge."
- **Key citations (§1)**: PHYRE, I-PHYRE, PhysGym, NewtonBench, PhysBench, LLF-Bench, Harness-Bench *(verify each before submission)*.

### §2 Benchmark Overview and Task Formalization (1.25 pages)

> **Status**: exists (`sec/2_benchmark.tex`); keep, tighten, and align notation with §3 and §4.

- Five-level hierarchy with formal latent world $\mathcal{W}=(f,\rho,c,\lambda)$.
- Prediction instance $e=(s_0,o^\star,\Delta t,\mathcal{C},y)$.
- Visibility boundary: agent-visible context vs. host-only world constants, latent-law parameters, answer keys.
- Agent objective $\hat y = A(x_e,\mathcal{C},h_B)$; exact-match scoring.
- Anti-shortcut: per-instance independent permutation of candidate positions.

### §3 Benchmark Construction (1.0–1.25 pages)

- **Phenomenon families** (7): central-force, kinematics, fluid, contact, dissipative, field-interaction, elastic.
- **World-parameter regimes** (3 per family): shared hidden constants.
- **Latent-dynamics conditions** (3): structural equation change / hidden coefficient field / both.
- **Latent-law realizations** (6 per condition): the specific transformed equation/function.
- **Counterfactual prediction instances** (15 per realization): 8 support + 7 held-out (provisional allocation — finalize after budget calibration).
- **Tool interface**: the enumerated tools available during support; budget $B$; tool-output schema (object identities, attributes, positions, velocities, measurements, time).
- **Renderer and simulator**: stack description, determinism / seeding policy, image resolution.
- **Anti-shortcut engineering**: candidate-position permutation, distractor construction by nearby but physically distinct successor states, identifier randomization.
- **Splits**: train/val/test over realizations (not instances) to enforce generalization.

### §4 Evaluation Protocol (0.75–1.0 pages)

- **Episode protocol**: support phase → freeze → held-out prediction.
- **Agent-visible context**: prompt, rendered context, candidate images, tool outputs.
- **Metric**: exact-match accuracy; stratification axes (family, regime, condition, realization, budget).
- **Ablations built into the protocol**:
  - Same-realization held-out vs. cross-realization held-out (tests whether gains reflect within-law transfer or law-agnostic pattern matching).
  - Support budget $B \in \{0, B_{\rm small}, B_{\rm full}\}$ (tests the marginal value of interaction).
  - Candidate permutation sanity (tests shortcut robustness).
- **Statistical reporting**: per-cell mean and confidence interval; seed count; aggregation rules.

### §5 Benchmark Validation (0.5–0.75 pages)

- **Oracle ceiling**: performance when the host exposes the latent law directly (upper bound).
- **No-feedback floor**: performance at $B=0$.
- **Weak-vs-strong discrimination**: a trivial heuristic baseline (e.g., always pick the candidate with smallest appearance distance to the initial frame) must underperform a frontier agent.
- **Leakage tests**: candidate label, file naming, and rendering metadata must not predict $y$.
- **Human sanity** (optional, small $n$): a few human annotators under matched budget.

### §6 Experiments (1.5–1.75 pages) — *Results*

- **Setup**: model list (≥3 frontier multimodal models, full harness disclosed), budget, seed count.
- **Main result table (Table 1)**: rows = models × budgets; columns = same-realization held-out accuracy, cross-realization held-out accuracy, gap.
- **Stratified analysis (Table 2)**: accuracy by phenomenon family and latent-dynamics condition.
- **Ablations (Figure 3)**: support-budget sweep curve; candidate-permutation sanity; tool-ablation.
- **Bottleneck analysis**: qualitative cases mapping errors to perception / evidence accumulation / hypothesis formation / visual decoding (RQ3).

### §7 Related Work (0.75–1.0 pages)

Organized by *question asked*, not paper-by-paper:

- **Passive physical understanding**: PhysBench and related VLM physics benchmarks — measure physical concepts from given evidence; no interaction or belief update.
- **Interactive physics puzzles**: PHYRE, I-PHYRE — measure success and sample efficiency on action-driven puzzles; cannot separate knowledge from action search.
- **Interactive scientific law discovery**: PhysGym, NewtonBench — recover general equations/laws; do not test instance-level counterfactual visual prediction under an unchanged latent law.
- **Agents learning from feedback**: LLF-Bench, Mars — task-adaptation focus; do not isolate physical latent-law transfer.
- **Evaluation unit**: Harness-Bench — motivates reporting the full model+harness system.

End with a **capability-gap table** mapping each prior benchmark against the five controlled components we combine.

### §8 Limitations and Conclusion (0.5 pages)

- **Limitations**: simulator fidelity; rendered-image realism gap; MCQ format does not directly probe open-ended hypothesis language; harness sensitivity; latent-law coverage is sampled, not exhaustive.
- **Conclusion**: restate the diagnostic; summarize the headline result; outline two concrete extensions (broader families, richer intervention vocabulary).

---

## Figure Plan

| ID | Type | Description | Data source | Priority |
|---|---|---|---|---|
| **Fig 1** | Hero / concept | 2-row diagram: support interaction (top) vs. held-out counterfactual prediction (bottom); contrast panel for appearance matching vs. latent-dynamics transfer | manual (TikZ or vector) | **HIGH** |
| **Fig 2** | Environment grid | One panel per phenomenon family (7 panels), each showing initial frame and the 4 candidate future frames of one instance | rendered from simulator | **HIGH** |
| **Fig 3** | Line + bar | Support-budget sweep (line, x = budget, y = held-out accuracy, one curve per model) + per-condition bar chart | experiment JSON | **HIGH** |
| **Table 1** | Main results | Models × budgets; same-realization vs. cross-realization held-out accuracy + gap | experiment JSON | **HIGH** |
| **Table 2** | Stratified | Accuracy by family and by latent-dynamics condition | experiment JSON | **HIGH** |
| **Table 3** | Capability gap | Rows = prior benchmarks; columns = the 5 controlled components; checkmark matrix | manual | MEDIUM |
| **Fig 4** | Qualitative | 2–3 failure cases annotated with the bottleneck category | experiment JSON | MEDIUM |

**Hero figure detail (Fig 1)**: see §1 above. Must be readable at column width, legible in grayscale, and self-contained.

---

## Citation Plan

> **Strict rule**: no BibTeX from memory. Every entry verified by web search before inclusion; unverified entries marked `[VERIFY]` and listed for the author.

- **§1 Intro**: PHYRE (Bakhtin et al., 2019), I-PHYRE (2023), PhysGym (2025), NewtonBench (2025), PhysBench (2024), LLF-Bench (2023), Harness-Bench.
- **§2 Background**: action-conditioned video prediction (Finn et al., 2016); intuitive physics (Lake et al., 2017); benchmark design references.
- **§7 Related Work**: Mars (situated induction); embodied property discovery; additional VLM-physics citations identified during literature sweep.
- **§3 Construction**: simulator and renderer citations (engine, physics library).

Citation work plan: W1 builds the verified `.bib` skeleton with placeholder keys; W3 finalizes all entries.

---

## Reviewer Concerns to Preempt (in lieu of external cross-review)

1. **"Just another physics benchmark?"** — Head off via the capability-gap table (Table 3) and an explicit paragraph in §7 explaining what prior work cannot measure.
2. **"MCQ is too easy / gameable."** — Counter via candidate-permutation sanity ablation and distractor-construction description (§3, §4).
3. **"Simulator fidelity?"** — Acknowledge in §8; report oracle ceiling and human sanity as evidence the task is well-posed.
4. **"Generalization across realizations is the only interesting axis."** — Show the same-realization vs. cross-realization gap directly (Table 1, Fig 3).
5. **"Which component is the bottleneck?"** — Bottleneck analysis subsection (§6) and tool ablation.
6. **Page budget** — 8 pages is tight; §2–§5 together must not exceed ~3.75 pages. Move full tool schemas, additional qualitative examples, and per-realization breakdowns to the appendix.

---

## Next Steps (1-month execution)

- [ ] **W1 (Oct 17–23)**: build full LaTeX scaffold (all `sec/*.tex` files), draft Abstract + Intro + Related Work, verified `.bib` skeleton, Fig 1 sketch.
- [ ] **W2 (Oct 24–30)**: finalize §2–§5 prose; wire harness and launch baseline runs; populate Table 1 skeleton.
- [ ] **W3 (Oct 31–Nov 6)**: populate §6 with real numbers; render Fig 2–3; full first draft.
- [ ] **W4 (Nov 7–13)**: self-review pass (claims-evidence audit, citation verification, anonymity check, page-budget check); polish; compile clean; submit.

---

## Decisions Still Open

- Final support/held-out allocation (8/7 provisional) — confirm after budget calibration.
- Model list for baselines (recommend: 3 frontier VLMs + 1 open-source VLM).
- Seed count and CI method (recommend: ≥3 seeds, bootstrap CIs).
- Human sanity protocol scope (small-$n$, optional for the main paper).
- Whether to include the cross-realization ablation in the main table or appendix (recommend: main — it is the core diagnostic).
