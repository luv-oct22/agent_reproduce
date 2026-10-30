# CVPR Paper Design: Physical Feedback as Reusable Knowledge

## Purpose

Create an anonymous CVPR 2027 paper draft for a diagnostic benchmark and protocol that asks whether general-purpose multimodal agents convert the physical feedback from their own actions into reusable knowledge. The paper must distinguish this question from low-level robotics, motion planning, embodiment, and sim-to-real transfer.

The central question is:

> Can general-purpose multimodal agents transform physical feedback from their own actions into reusable knowledge that extends beyond success on the current task?

## Narrative and Claim Boundary

The paper is a **protocol-first benchmark paper**, not a claim that a new agent-learning method already works. Its central contribution is a controlled diagnostic: final task success can arise from search, luck, or memorizing a locally useful action, whereas reusable physical knowledge should also support held-out action prediction and new-goal transfer after feedback is frozen.

Until experiments are complete, the manuscript will use proposal language (for example, “we propose,” “the protocol tests,” and “we will evaluate”) rather than empirical language (for example, “we show” or “our results demonstrate”). It will not make a “first benchmark” claim. It will state that related-work coverage remains subject to an exhaustive review.

The evaluated unit is the complete **model + agent harness + memory + reasoning loop**. The paper will retain the following scope statement verbatim:

> We study physical feedback as an executable information source for foundation-model agents, rather than physical interaction as a robot control problem.

## Paper Structure

1. **Abstract** — problem, diagnostic protocol, controlled feedback ladder, and evidence required for reusable knowledge. No result claim.
2. **Introduction** — motivate the success-versus-knowledge ambiguity, introduce the core diagnostic, list contributions, and define scope.
3. **Rebound-to-Cup Environment** — first prototype; high-level action choices (ball identity, launch speed, launch angle); hidden object-specific elasticity and friction.
4. **Feedback Diagnostic Protocol** — pre-interaction probe, fixed-budget interaction under one feedback modality, frozen feedback, held-out prediction, and moved-goal transfer.
5. **Metrics and Benchmark Validation** — task metrics, prediction/transfer metrics, knowledge gain, and reliability/discrimination/no-leakage/human-sanity requirements.
6. **Experimental Plan** — fixed controls, feedback ladder, agent/harness reporting, hypotheses, and planned analyses. This section becomes Results after experiments run.
7. **Related Work** — physical reasoning benchmarks, interactive physics and scientific discovery, situated induction, and model--harness evaluation.
8. **Limitations and Conclusion** — scope boundaries, simulator limitations, incomplete suite coverage, and what evidence would support or falsify the desired claim.

## Figures and Tables

- **Figure 1 (conceptual):** the evidence chain from physical feedback to updated belief, held-out outcome prediction, and new-goal transfer; visually contrast “task success only” with “reusable knowledge.”
- **Figure 2 (environment):** rebound-to-cup scene, action interface, hidden ball properties, and the five feedback channels. Create after the simulator specification is fixed.
- **Figure 3 (diagnostic plot):** task improvement on the x-axis and knowledge gain on the y-axis, with interpretations for all four quadrants. Populate only after experiments run.
- **Table 1 (protocol):** controlled variables and what each feedback condition reveals.
- **Table 2 (results placeholder):** model+harness, feedback modality, task success, prediction gain, transfer gain, and uncertainty. Do not insert numbers until raw runs and aggregation rules are available.

## Evidence Design

The prototype and all future modules share these controls:

- fixed geometry, task information, agent harness, and interaction budget within a comparison;
- feedback conditions: no feedback, binary success/failure, terminal coordinate, video, and oracle accurate state;
- held-out ball--speed--angle tuples that do not overlap interaction trajectories;
- transfer with the same hidden ball properties but a moved cup;
- feedback frozen before all post-interaction probes.

The central analysis compares current-task improvement against knowledge gain. A high task score without held-out prediction or transfer improvement is explicitly interpreted as evidence consistent with local search or action memorization, not as proof of reusable knowledge.

## LaTeX Implementation Plan

The working source remains `author-kit-CVPR2026-v1-latex-/` until an official CVPR 2027 author kit replaces it. The content will be separated into:

```text
main.tex
preamble.tex
sec/0_abstract.tex
sec/1_intro.tex
sec/2_environment.tex
sec/3_protocol.tex
sec/4_evaluation.tex
sec/5_experiments.tex
sec/6_related_work.tex
sec/7_limitations.tex
sec/8_conclusion.tex
main.bib
```

The initial rewrite will replace template prose with an anonymous paper scaffold and a complete protocol draft. The experimental section will contain clearly delimited pending items rather than fabricated results.

## Citation and Validation Policy

Every cited work must be checked against a primary source before its BibTeX entry is added. The current verified starting set covers PHYRE, I-PHYRE, PhysGym, NewtonBench, Mars, Harness-Bench, and action-conditioned video prediction. PhysBench and the robotics comparator remain in the related-work review queue until their exact positioning and metadata are finalized.

After each manuscript change, compile the main document and check for undefined references, bibliography errors, overflow, and accidental de-anonymization. Before submission, replace this preliminary CVPR 2026 style package with the official CVPR 2027 release if it differs.

## Decisions Still Required Before a Submission-Ready Paper

- simulator and renderer;
- action discretization and fixed interaction budget;
- agent/model/harness baselines and memory configuration;
- seed count, uncertainty reporting, and aggregation rules;
- benchmark validation controls and human-sanity protocol;
- final task-suite scope beyond rebound-to-cup;
- complete related-work and novelty verification.
