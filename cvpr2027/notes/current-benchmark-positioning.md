# Current Benchmark Positioning and Protocol Decisions

**Status:** Current working record for the CVPR 2027 project. This file is
outside the LaTeX author kit and is the source of truth for subsequent paper
drafting. It records design decisions, not experimental findings.

## Central Question

> Can a multimodal agent infer an unfamiliar latent physical rule from finite
> virtual experiments and transfer that inferred rule to predict a future
> physical image in a new state?

The benchmark evaluates the following chain:

```text
observe -> intervene -> measure -> infer latent law -> predict counterfactual image
```

Its goal is to distinguish this capability from selecting an answer through
appearance matching, memorized canonical physics, or a local trajectory
heuristic.

## Agent-Visible and Hidden Information

During support interaction, tools may return complete **observable system
state**: object identities and attributes, positions, velocities, environmental
measurements, and time. The agent may select experiments and tools within a
fixed budget.

The following information remains hidden: world-level constants, the governing
equation, equation transformations, hidden coefficient or field functions, and
the answer key. Thus, state observations support system identification without
directly exposing the latent dynamics.

## Transfer Protocol

Each latent-law realization contains multiple instances with different initial
states, object attributes, target objects, and prediction intervals. The agent
first conducts experiments on support instances, then receives held-out
prediction instances governed by the same latent-law realization. Held-out
instances allow no additional tool calls or outcome feedback.

This support-to-held-out separation is required for the paper's transfer claim:
the prediction target must be a new state, not the same instance used for
experimentation. A provisional allocation is eight support instances and seven
held-out prediction instances from the 15 instances in a realization; finalize
this split after pilot-budget calibration.

## Benchmark Hierarchy

```text
Physical-Phenomenon Family
  -> World-Parameter Regime
    -> Latent-Dynamics Condition
      -> Latent-Law Realization
        -> Counterfactual Prediction Instance
```

- **Physical-Phenomenon Family:** baseline physical mechanism and visual
  setting.
- **World-Parameter Regime:** fixed but hidden world-level constants.
- **Latent-Dynamics Condition:** equation transformation, hidden coefficient
  field, or their combination.
- **Latent-Law Realization:** a specific transformed equation and/or function.
- **Counterfactual Prediction Instance:** a distinct physical state and visual
  query governed by that realization.

The implemented design contains seven physical-phenomenon families, three
world-parameter regimes per family, three latent-dynamics conditions, six
latent-law realizations per condition, and 15 instances per realization.

## Evaluation Task

For a held-out instance, the agent receives a rendered scene and four candidate
future-frame images. It selects the image depicting the target object at the
specified future time. Candidate positions must be independently permuted and
their answer keys retained only by the evaluator.

The principal measure is held-out future-frame prediction accuracy, reported
with stratification by family, regime, latent-dynamics condition, realization,
and interaction budget. No claim that models perform poorly should appear until
controlled experiments are completed.

## Contribution Boundary

The intended contribution is a controlled evaluation protocol that joins:

1. agent-selected physical experiments;
2. hidden world constants and structural or coefficient-law transformations;
3. a hierarchy that isolates the sources of physical variation;
4. support-to-held-out transfer under an unchanged latent-law realization; and
5. rendered future-frame multiple-choice prediction as the final behavioral
   test of the inferred dynamics.

The paper should not claim to be the first interactive physical-reasoning or
scientific-law-discovery benchmark. Related work already studies interactive
law discovery, situated rule induction, passive inductive visual physics, and
interactive physical reasoning. The paper instead asks whether a unified,
controlled protocol can measure active evidence collection and visual
generalization under the same hidden dynamics.

## Open Decisions

- Confirm the final support/held-out allocation and interaction budget.
- Define the exact world-level experiment tools and permitted interventions.
- Specify train, validation, and test splits across realizations, regimes, and
  families.
- Validate generic simulators, renderers, and end-to-end interaction coverage
  before making implementation-completeness claims.
- Complete a primary-source related-work matrix before finalizing novelty
  language or adding citations to the manuscript.
