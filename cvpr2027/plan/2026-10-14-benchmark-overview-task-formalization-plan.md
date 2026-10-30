# Benchmark Overview and Task Formalization Implementation Plan

> **For agentic workers:** Implement this plan natively in the current session. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an anonymous CVPR manuscript section that formally defines the benchmark hierarchy, hidden information, tool-mediated interaction, and counterfactual visual prediction task.

**Architecture:** Create one self-contained LaTeX source file for the section and replace the template's formatting/final-copy includes with that source in `main.tex`. The section uses only standard LaTeX commands already provided by the CVPR template; it introduces no packages, citations, figures, experimental values, or new claims.

**Tech Stack:** LaTeX; existing CVPR review template.

**Spec:** `plan/2026-10-14-physical-feedback-cvpr-paper-design.md`

## Global Constraints

- Keep the paper anonymous and retain review mode.
- Use the five-level taxonomy: Physical-Phenomenon Family → World-Parameter Regime → Latent-Dynamics Condition → Latent-Law Realization → Counterfactual Prediction Instance.
- State only the implemented benchmark design; do not report model results, benchmark difficulty, or simulator-validation outcomes.
- Treat candidate-order randomization as a required anti-shortcut property for the final benchmark, not as a completed experimental result.
- Keep the unresolved allocation of support interactions to held-out prediction instances out of this section's claims; define it later in the evaluation protocol.
- Do not edit the unrelated ICLR manuscript.

## Review Focus

- **Hierarchy coverage:** each level must state exactly what changes there and what is held fixed below it.
- **Information boundary:** host-only latent laws and answer keys must be distinguished from agent-visible visual context and tool outputs.
- **Task boundary:** the agent must infer a next-frame answer through permitted interaction, never receive hidden parameters or the answer key.
- **Claim boundary:** the prose must not imply an unrun experiment, validated numerical simulator, or established transfer result.
- **Shortcut boundary:** candidate images may be visually close, but answer positions must not encode labels or hidden-law identity.

### Task 1: Draft the Benchmark Overview and Task Formalization Section

**Files:**
- Create: `author-kit-CVPR2026-v1-latex-/sec/2_benchmark.tex`

**Interfaces:**
- Consumes: the hierarchy and visibility policy from `notes/research-design-consensus.md` and the user-provided pipeline description.
- Produces: `sec/2_benchmark.tex`, which compiles after `sec/1_intro.tex` and defines label `sec:benchmark`.

- [ ] **Step 1: State the benchmark objective and hierarchy**

Write a subsection that introduces counterfactual visual prediction conditioned on discovering a latent physical world. Define the hierarchy in prose as:

```latex
\textit{Physical-Phenomenon Family}
\rightarrow \textit{World-Parameter Regime}
\rightarrow \textit{Latent-Dynamics Condition}
\rightarrow \textit{Latent-Law Realization}
\rightarrow \textit{Counterfactual Prediction Instance}.
```

Specify that physical-phenomenon families define baseline mechanisms; world-parameter regimes fix shared constants; latent-dynamics conditions select structural change, hidden coefficient field, or their combination; latent-law realizations fix the exact hidden equation/function; and prediction instances vary the scene state and visual query.

- [ ] **Step 2: Define a latent world and a prediction instance**

Introduce a latent world as `\mathcal{W}=(f,\rho,c,\lambda)`, where `f` is a physical-phenomenon family, `\rho` a world-parameter regime, `c` a latent-dynamics condition, and `\lambda` a latent-law realization. Define a prediction instance as `e=(s_0,o^\star,\Delta t,\mathcal{C},y)`, where `s_0` is the initial state, `o^\star` the target object, `\Delta t` the interval, `\mathcal{C}` the four candidate images, and `y` the host-only correct index. State that the simulator produces the target state from the latent transition dynamics but the agent sees rendered evidence rather than host records.

- [ ] **Step 3: Define the visibility and interaction boundary**

Describe public information (prompt, rendered context, candidate images at evaluation, and tool outputs), host-only information (world constants, hidden-law parameters, full scene state, answer key), and the fixed-budget tool-mediated interaction history `h_B`. State that tools reveal permitted object attributes or measurements, not hidden equations or answer labels.

- [ ] **Step 4: Define the agent objective and anti-shortcut requirement**

Specify the prediction objective `\hat y = A(x,\mathcal{C},h_B)` and exact-match scoring against `y`. State that the final benchmark independently permutes candidate positions and maintains the corresponding host answer key, so candidate labels cannot serve as a shortcut. State that candidate images differ by small physically meaningful displacements to require state-sensitive prediction.

- [ ] **Step 5: End with a forward reference to evaluation protocol**

Conclude by stating that questions sharing a latent-law realization naturally support in-realization generalization, while the allocation of interaction evidence and held-out prediction queries is defined in the subsequent evaluation protocol.

### Task 2: Integrate and Compile the Section

**Files:**
- Modify: `author-kit-CVPR2026-v1-latex-/main.tex`
- Test: `author-kit-CVPR2026-v1-latex-/main.pdf`

**Interfaces:**
- Consumes: `sec/2_benchmark.tex` from Task 1.
- Produces: a compiled review-mode PDF containing the new section after the current introduction source.

- [ ] **Step 1: Replace template-only body includes**

Replace the lines that input `sec/2_formatting` and `sec/3_finalcopy` with:

```latex
\input{sec/2_benchmark}
```

Keep bibliography commands unchanged.

- [ ] **Step 2: Compile the paper**

Run the project’s LaTeX build from `author-kit-CVPR2026-v1-latex-/` and inspect the resulting log for undefined control sequences, missing files, undefined references, bibliography errors, and overfull boxes caused by the new section.

- [ ] **Step 3: Repair only section-local LaTeX issues**

If the new source creates a compilation issue, correct the source in `sec/2_benchmark.tex` or its single include line in `main.tex`, then rebuild. Do not alter the CVPR style file or unrelated template sources.

## Self-Review

- **Spec coverage:** Task 1 implements the taxonomy, evidence boundary, interaction interface, and task objective; Task 2 makes the section visible and validates its LaTeX integration.
- **Placeholder scan:** The plan contains no incomplete implementation steps; the remaining support-to-query allocation is intentionally excluded by the global constraints.
- **Consistency:** The same variable names define the latent world and prediction instance throughout Task 1, and the section label is declared before later sections can reference it.
- **Review focus:** Task 1 explicitly covers the five listed risks; Task 2 checks the rendered document for layout or compilation regressions.
