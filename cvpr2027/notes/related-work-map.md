# Related-Work Map: Agent Interaction × Physical World × Multimodal

**Status:** working note for discussing §7 Related Work (CVPR 2027). Built 2026-10-18.
**Scope (agreed):** related work centres on three topics — **(I) agent interaction**, **(P) physical world**, **(M) multimodal perception**. Passive VQA, generic agent-feedback, and harness work are kept only as short supporting lists.

**Verification:** all 50 core papers below were checked with `verify_papers.py` (arXiv layer, 50/50 verified) and then cross-checked against the arXiv API for title + first author + first-version date (50/50 match; LLMPhy was retitled in a later version). Venues marked *(venue?)* were seen only in search snippets or arXiv comments and must be confirmed on the proceedings page before they go into `main.bib`. Raw verifier output: `.aris/verify-papers/verified_papers.json`.

Our own component flags, used throughout:
**A** agent-selected experiments · **L** hidden latent-law transformation · **H** hierarchical factorization of variation · **T** support → held-out transfer under the same hidden law, tools frozen · **R** rendered future-frame multiple choice.

---

## 1. One-paragraph takeaway

No paper found combines A+L+H+T+R. But every *pair or triple* of our components now has a 2025–2026 precedent, so the novelty claim must be the **combination evaluated on multimodal agents**, not any single element. The three most dangerous neighbours each sit at a different corner: **DiscoverPhysics** (I+P: experiments under altered laws, held-out trajectory prediction, but text/numeric only), **InPhyRe** (P+M: induce unseen collision laws from demonstration videos and predict new states, but passive), and **WorldTest/AutumnBench** (I+M: explore then answer masked-frame MCQ, but abstract grid worlds, not physics). On the full I∩P∩M intersection, existing work (DeepPHY, IPR-1, ICPRL, PhysMem, PhysMent, CHAIN) evaluates **task success under standard physics**, not whether interaction yields a law that transfers to new states. A 2026 ICML paper (Schulze Buschoff et al.) directly reports that interaction-trained VLMs do **not** transfer to related tasks — the strongest motivation for our question.

---

## 2. Core: I ∩ P ∩ M — multimodal agents acting in a physical world

These are the papers reviewers will treat as "the same area". None hides a counterfactual law and then freezes tools for a held-out visual prediction test.

| Paper | Year · Venue | arXiv | What the agent sees / does / is scored on | Flags | Difference from us |
|---|---|---|---|---|---|
| **Can VLMs Learn Intuitive Physics from Interaction?** (Schulze Buschoff et al.) | 2026 · ICML 2026 *(venue?)* | 2602.06033 | VLMs RL-trained by interacting in simulated physics tasks; interaction improves the trained task but **does not transfer** to related tasks sharing the same principles. | A, T(tested, fails) | Training study, standard physics. **Best motivation citation** for "success ≠ reusable physics". |
| **IPR-1: Interactive Physical Reasoner** (Zhang et al.) | 2025 · CVPR 2026 | 2511.15407 | VLM policy over 1000+ physics games (Game-to-Unseen); world-model rollouts reinforce the policy; PhysCode action space; scored by task success incl. unseen games. | A, T(across games) | Trained agent; no hidden law shared between support and test; reward not frame prediction. Most likely CVPR reviewer comparison. |
| **DeepPHY** (Xu et al.) | 2025 · arXiv (AAAI listing *(venue?)*) | 2508.05405 | VLM agents act from screenshots in PHYRE, I-PHYRE, Kinetix, Pooltool, Angry Birds, Cut the Rope; descriptive physics knowledge does not become predictive control. | A, H(envs) | Goal-reaching puzzles, standard physics, no frozen-tool transfer test. |
| **ICPRL** (Xu et al.) | 2026 · arXiv | 2603.13295 | Multi-episode in-context RL (GRPO) VLM policy + world model + PUCT; evaluated on DeepPHY and unseen environments. | A, T | Training method; task success, no latent law. |
| **PhysMem** (Li, You, Su, Guibas) | 2026 · arXiv | 2602.20323 | VLM robot planner forms hypotheses about physical properties, verifies them by targeted interaction, stores validated knowledge for later decisions (real + sim manipulation). | A, L(properties), T(partial) | Method; real physics; manipulation success; no controlled support/held-out split. Natural **baseline harness** ("verify-before-apply memory"). |
| **PhysMent** (Chan et al.) | 2026 · arXiv | 2609.13152 | 105 MuJoCo scenes; tools apply forces, query state, advance time, edit geometry; hidden-object category; 25–67% accuracy across 7 models. | A, (L hidden objects), H(difficulty) | **Nearly our tool interface.** Each question is answered on the same scene (no transfer), standard laws, text answers. Unclear from abstract whether models get images — check full text. |
| **New Evidence, Same Choice** (Saha et al.) | 2026 · PhysWorldAI @ NeurIPS 2026 workshop, under review | 2609.11022 | One measurement image + 4 candidate worlds (mass × friction/stiffness); VLM answers or picks cheapest disambiguating experiment; models repeat the same action on 95–100% of matched pairs. | A(selection only), L(params) | Single step, no real interaction, no held-out transfer. Strong evidence that **experiment selection is a weak link** — supports measuring A separately. |
| **CHAIN** (Wu et al.) | 2026 · arXiv | 2602.21015 | Interactive 3D physics puzzles (interlocking, stacking, packing); VLMs plan multi-step actions; scored by completion. | A, H(levels) | Visible standard physics; no latent law, no prediction test. Same "passive VQA → closed loop" motivation as ours. |
| **SIMPACT** (Liu et al.) | 2025 · CVPR 2026 | 2512.05955 | Builds a simulator from one RGB-D image; VLM proposes actions, inspects simulated rollouts, refines. | A(sim-tool) | Simulator assumes real physics → would fail under counterfactual laws unless calibrated. Good **baseline idea**. |
| **VDAWorld** (O'Mahony, Cipolla, Tewari) | 2025 · arXiv | 2512.11061 | VLM abstracts an image into a scene, picks a simulator, infers latent dynamics, predicts future states. | L(partial), R(partial) | No active experimentation, no transfer. Candidate program-synthesis baseline. |
| **PhysCaP** (Lin et al.) | 2026 · arXiv | 2608.21031 | Code-as-policy robot agent decides when to explore; estimates mass/stiffness from proprioception before manipulating. | A, L(properties) | Robotics, interaction-efficiency lens; no transfer protocol or frame test. |

---

## 3. I ∩ P (not multimodal) — agents experimenting on physical systems through text/numbers

This is where the **law-transformation** idea already lives. Our separation is multimodality (rendered observation + rendered answer) and the frozen-tool held-out test.

| Paper | Year · Venue | arXiv | What it does | Flags | Difference from us |
|---|---|---|---|---|---|
| **DiscoverPhysics** (Wiemann et al.) | 2026 · arXiv | 2605.26087 | 22 N-body worlds with non-standard laws (screened/fractional gravity, hidden species, time-varying couplings); agent chooses initial conditions over 2–16 rounds; submits explanation + Python law; scored by **trajectory MSE on held-out particles** + rubric. | A, L, T, (H weak) | **Biggest threat.** Text/CSV only, no rendering, no MCQ, no factorized hierarchy; scores submitted code, not the agent's own prediction. We must not claim "first held-out prediction under counterfactual laws". |
| **NewtonBench** (Zheng et al.) | 2025 · ICLR 2026 *(venue?)* | 2510.07172 | 324 tasks = 12 laws × counterfactual mutations × system settings × difficulty; ≤10 experiment rounds; scored by symbolic accuracy + RMSLE data fidelity; code interpreter induces premature exploitation. | A, L, H | Endpoint is law recovery, not instance prediction. **Open check:** whether its RMSLE points are held-out states (read appendix). |
| **PhysGym** (Chen et al.) | 2025 · NeurIPS 2025 D&B *(venue?)* | 2507.15550 | 97 problems; 100 experiments; **4 prior-knowledge levels** (full context → anonymized variables); hypothesis accuracy + fidelity on the agent's own data. | A, (L), H(prior levels) | Real laws, numeric, no held-out states. Prior-control ladder is directly reusable. |
| **Gravity-Bench-v1** (Koblischke et al.) | 2025 · ICML 2025 *(venue?)* | 2501.18411 | Agents plan observations of binary stars under a 100-observation budget; some tasks with altered gravity. | A, L | Numeric, single instance per task, no transfer test. |
| **HExA / Interphyre** (Chandra et al.) | 2026 · arXiv | 2606.29315 | In-context agent designs experiments and distils reusable skills; Interphyre = procedural physics tasks with intervention APIs and snapshot/restore. | A, T(skills) | **Open check:** abstract does not say whether observations are visual or whether there is held-out prediction — read full text. |
| **LLMPhy** (Cherian et al.) | 2024 · AISTATS 2026 *(venue?)* | 2411.08027 | LLM writes code to identify hidden friction/damping with a simulator in the loop, then predicts TraySim outcomes (MCQ). | A(sim), L(params), T | Standard physics, single scene type, not a benchmark of experiment choice. |
| **Learning to Perform Physics Experiments via Deep RL** (Denil et al.) | 2016 · ICLR 2017 *(venue?)* | 1611.01843 | RL agents manipulate objects to infer hidden mass/cohesion with an information–cost trade-off. | A, L(properties) | Origin of "experiments to reveal hidden properties"; no transfer. |
| **PHYRE** (Bakhtin et al.) / **I-PHYRE** (Li et al.) | 2019 / 2023 · *(venue?)* / ICLR 2024 *(venue?)* | 1908.05656 / 2312.03009 | Action-to-outcome 2D physics puzzles; within/cross-template generalization; I-PHYRE adds in-situ multi-step intervention. | A, H(templates) | Standard physics; success metric; action search confounds knowledge — our core critique. |
| **Phy-Q** (Xue et al.) | 2021 · *(venue?)* | 2108.13696 | Angry-Birds-like testbed, local vs broad generalization, human-normed score. | H, T | Human-normed score is a useful precedent. |
| **OPEn** (Gan et al.) | 2021 · IROS 2021 *(venue?)* | 2110.06912 | Task-free exploration in a physics world, then downstream physics tasks. | A, T | Explore-then-transfer protocol with RL representations, standard physics. |
| **Virtual Tools / SSUP** (Allen, Smith, Tenenbaum) | 2019 · PNAS 2020 *(venue?)* | 1907.09620 | Human trial-and-error tool use; Sample–Simulate–Update model. | A | Cognitive baseline for budgeted trial-and-error. |

Lower priority, same corner: ExplorationBench (2609.30199, altered rule systems in code/logic, not physics), BoxingGym (2501.01540, experiment design + "explain to a second agent" metric), Doing Experiments and Revising Rules (2402.06025, LLM-proposed experiments ≈ random), WorldCoder (2402.12275, code world models from interaction), Mind's Eye (2210.05359, simulator-in-the-loop LM).

---

## 4. P ∩ M (passive) — visual physical inference and prediction without agent choice

These own the **hidden-property / hidden-law + visual prediction** idea, but the evidence is given, not collected.

| Paper | Year · Venue | arXiv | What it does | Flags | Difference from us |
|---|---|---|---|---|---|
| **InPhyRe** (Sreekumar & Boddeti) | 2025 · TMLR *(venue?)* | 2509.12263 | 1–3 demonstration videos of collisions under unseen/law-violating physics; predict outcomes on new initial states; 4-option text MCQ; models show language bias. | L, T, (R text) | **Closest multimodal threat.** Demonstrations are given (no A), answers are text, single family (no H). Its language-bias finding motivates our rendered-frame answers. |
| **ComPhy** (Chen et al.) | 2022 · ICLR 2022 *(venue?)* | 2205.01089 | Few reference videos reveal hidden mass/charge; answer predictive/counterfactual questions on a target video. | L(properties), T | Conceptual ancestor of our support → held-out split; passive, properties not laws, text QA. |
| **Physion++** (Tung et al.) | 2023 · NeurIPS 2023 D&B *(venue?)* | 2306.15668 | Outcome prediction requiring online inference of mass, friction, elasticity, deformability; human comparison. | L(properties) | Inference within one clip; no separate support set or tools. |
| **Physion** (Bear et al.) | 2021 · NeurIPS 2021 D&B *(venue?)* | 2106.08261 | Eight rendered 3D scenario families; humans vs models on contact prediction. | H(families) | Standard physics, passive. |
| **CoPhy** (Baradel et al.) / **Filtered-CoPhy** (Janny et al.) | 2019 / 2022 · *(venue?)* | 1909.12000 / 2202.00368 | Infer confounders (mass, friction) from an observed rollout, then predict a counterfactual outcome; Filtered-CoPhy does it in pixel space. | L(confounders), T, (R generation) | Model-learning papers, single passive observation. |
| **DynaPix** (Nguyen et al.) | 2026 · arXiv | 2608.05505 | Bullet video prefix; pick the exact future frame among close distractors; Qwen3-VL ≈ chance. | R | **Same final-test format as ours**, but passive and standard physics. R alone is not novel; borrow its distractor lessons. |
| **Physically Viable World Models** (Thorpe et al.) | 2026 · arXiv | 2605.30542 | Position + benchmarks holding the visible scene fixed while varying latent physics; observation-only predictors fail under intervention. | L | Makes our core argument ("same appearance, different hidden physics → must intervene"). Cite as conceptual support. |
| **PhySimCode** (Kundu et al.) | 2026 · arXiv | 2610.15722 | MLLMs watch physics videos (162 phenomena) and must name the law, recover parameters, write simulation code; best model recovers 7.7% of parameters. | L(params), H | Passive video-to-law; no held-out prediction. |
| **MPMWorlds** (Kovačič & Ellis) | 2026 · arXiv | 2606.01538 | Infer dynamics/parameters from MPM videos and extrapolate; code generation vs video diffusion. | L(partial), T | Passive. |
| **ACWM-Phys** (Xue et al.) | 2026 · arXiv | 2605.08567 | Action-conditioned video world models on rigid/kinematic/deformable/particle physics with ID/OOD splits. | T(OOD), H | Trained models, no hidden law, no agent. |
| **How Far is Video Generation from World Model** (Kang et al.) | 2024 · ICML 2025 *(venue?)* | 2411.02385 | Video diffusion models generalize in-distribution but fail OOD; "case-based" imitation. | T(OOD) | Motivates law-level transfer. |
| Essential passive benchmarks (one line each) | | | **PhysBench** (2501.16411, ICLR 2025 *(venue?)*): 10k video/image MCQ on physical understanding. **Physics-IQ** (2501.09038): video models continue real physics clips. | — | Static evaluation; cite only as the passive contrast. |

---

## 5. I ∩ M (not physics) — explore-then-test protocols for multimodal / world-model learning

| Paper | Year · Venue | arXiv | What it does | Flags | Difference from us |
|---|---|---|---|---|---|
| **Benchmarking World-Model Learning (WorldTest / AutumnBench)** (Warrier et al.) | 2025 · ICML 2026 *(venue?)* | 2510.19788 | Reward-free exploration, then a related test environment: masked-frame prediction (6-way MCQ), planning, change detection; 43 grid worlds; 517 humans beat frontier models. | A, T, (R in grids) | **Closest protocol.** Abstract grid programs (models see JSON grids), no physical constants or law transforms, no budget, no hierarchy. Reviewers may call us "WorldTest for physics" — we must say what physics adds (continuous parameters, identifiability, budgeted system ID). |
| **VisGym** (Wang et al.) | 2026 · *(venue?)* | 2601.16973 | 17 multimodal-agent environments; visual input often worse than symbolic; truncated history beats unbounded history. | A | Evidence for our observation-modality and memory-window ablations. |
| **Mars** (Tang et al.) | 2024 · NeurIPS 2024 D&B *(venue?)* | 2410.08126 | Counter-commonsense rules in a Crafter-like world; induce rules in context and exploit them. | A, L | Game rules, task reward, no held-out prediction. |

Background for world-model evaluation (cite briefly if at all): World-in-World (2510.18135, Jiahan Zhang et al., ICLR 2026 *(venue?)*), Finn et al. action-conditioned video prediction (1605.07157).

---

## 6. Supporting only (not part of the three-topic core)

- **Agent learning from feedback:** LLF-Bench (2312.06853).
- **Evaluation unit:** Harness-Bench (2605.27922, first author Yilun Yao; arXiv title "Evaluating Agent Harnesses across Models and Realistic Workflows").
- **Validity methodology — use in §5 Validation, not Related Work:** MVP minimal video pairs (2506.09987), Order Matters / position-invariant accuracy (2410.16983), MMStar blind baselines (2403.20330), Adding Error Bars to Evals (2411.00640). These were found but not run through the verifier; verify before citing.

---

## 7. Capability matrix (candidate replacement for Table 3 in §7)

Columns: our components. ✓ = present, ~ = partial. Topic columns show which of the three discussion topics each paper sits in.

| Benchmark | I | P | M | A | L | H | T | R |
|---|---|---|---|---|---|---|---|---|
| PHYRE / I-PHYRE | ✓ | ✓ | ~ | ✓ | | ~ | | |
| DeepPHY | ✓ | ✓ | ✓ | ✓ | | ~ | | |
| IPR-1 | ✓ | ✓ | ✓ | ✓ | | | ~ | |
| PhysMent | ✓ | ✓ | ? | ✓ | ~ | ~ | | |
| New Evidence, Same Choice | ~ | ✓ | ✓ | ~ | ~ | | | |
| NewtonBench | ✓ | ✓ | | ✓ | ✓ | ✓ | ? | |
| PhysGym | ✓ | ✓ | | ✓ | ~ | ~ | | |
| DiscoverPhysics | ✓ | ✓ | | ✓ | ✓ | ~ | ✓ | |
| InPhyRe | | ✓ | ✓ | | ✓ | | ✓ | ~ |
| ComPhy / Physion++ | | ✓ | ✓ | | ~ | | ✓ | ~ |
| DynaPix | | ✓ | ✓ | | | | | ✓ |
| WorldTest / AutumnBench | ✓ | | ~ | ✓ | | | ✓ | ~ |
| **Ours** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

"?" cells need a full-text check (PhysMent image input; NewtonBench held-out fidelity points). Every ✓ in a prior-work row must be re-checked against the paper before the table goes into the manuscript.

---

## 8. Revised novelty boundary (proposed wording for discussion)

**Safe:** "We do not claim that agent-selected experiments, counterfactual laws, held-out prediction, or future-frame multiple choice is new in isolation; each has recent precedents (DiscoverPhysics, NewtonBench, InPhyRe, WorldTest, DynaPix). The contribution is a benchmark in which a **multimodal** agent must collect its own evidence about a **hidden, transformed physical law**, and that evidence is tested — with tools frozen — on **rendered future frames of new states** governed by the same law, across a **factorized** hierarchy that separates structural law changes from hidden coefficient fields."

**No longer safe:**
- "first benchmark of held-out prediction under counterfactual laws" (DiscoverPhysics);
- "first explore-then-frame-prediction protocol" (WorldTest);
- "first test of hidden-law induction by multimodal models" (InPhyRe).

**Least contested component:** H (crossed factorization; only NewtonBench's domain × difficulty grid comes close).

---

## 9. Ideas from the literature to strengthen the benchmark

Ranked by how directly they answer a likely reviewer objection.

1. **Active vs passive support control.** Give the same support budget as (a) agent-chosen calls, (b) random calls, (c) oracle-informative experiments, and (d) passive demonstration rollouts (InPhyRe-style). Separates us from InPhyRe/ComPhy and tests the repeated finding that LLM-chosen experiments are near random (Piriyakulkij 2024; Explore-Then-Commit; New Evidence, Same Choice).
2. **Diagnostic distractors.** Render the three wrong candidates from the same initial state under (i) the untransformed canonical law, (ii) the right law with wrong constants or coefficient field, (iii) a law consistent with support data but wrong on the held-out state. The error mix then reports *which hierarchy level failed*. Agrees with the canonical-physics baseline already in §5.
3. **Prior-control ladder + matched standard-physics anchors.** Include an untransformed-law world per family and vary how much is told (family name vs nothing), following PhysGym's prior levels and InPhyRe's regular/irregular pairs. Report a prior-override score.
4. **Prediction vs explanation dissociation.** Before freezing tools, the agent writes a law card or parameter estimate; check whether it predicts held-out accuracy (DiscoverPhysics, BoxingGym). Also directly tests the reusable-knowledge claim.
5. **Observation-modality and memory ablations.** Frames only / frames + numeric state / numeric state only (VisGym; *Knowing Is Not Seeing*); full log vs truncated window vs agent-written law card (PhysMem, VisGym).
6. **Baseline harnesses from the I∩P∩M corner.** PhysMem-style verify-before-apply memory; SIMPACT/VDAWorld-style calibrated-simulator tool (upper bound) and uncalibrated variant (prior failure); WorldCoder-style code world model.
7. **Budget curves and a human reference.** Sweep 1/2/4/8/16 tool calls (DiscoverPhysics); small human study under matched budget (WorldTest, Phy-Q). Report non-monotone curves if they appear (ExplorationBench).

---

## 10. Open checks before writing §7

- [ ] NewtonBench: are the RMSLE "data fidelity" points held-out states? (appendix)
- [ ] PhysMent: do models receive rendered images?
- [ ] HExA/Interphyre: visual observations? held-out prediction?
- [ ] Confirm every *(venue?)* on the proceedings page; prefer publisher BibTeX.
- [ ] Re-check each ✓ in the capability matrix against the paper text.
- [ ] Decide whether §7 keeps the current five subsections or is restructured into the three topics (I∩P∩M core; I∩P law discovery; P∩M passive inference; I∩M explore-then-test).
