# Experiment advice: from NewtonBench to visual prediction

I read [NewtonBench, including its experimental protocol and discussion of future directions](https://arxiv.org/html/2510.07172v3). **Your strongest extension is to evaluate whether experimentally acquired knowledge transfers to predicting a new visual situation.** That is a clear distinction from its main evaluation, although establishing novelty across the wider literature would require a separate review.

NewtonBench has agents manipulate simulated systems to discover hidden equations. It changes the mathematical structure of physical laws, separates law complexity from experimental-system complexity, and evaluates symbolic correctness and numerical predictions. Other equations supporting the experiment are provided. Its central evaluation does not require identifying objects and predicting outcomes in rendered scenes. [Paper, §§2–3](https://arxiv.org/html/2510.07172v3#S2)

For your project, I would organize the experiments around this question:

> **Can a model discover how an unfamiliar world works through interaction, then use that knowledge to predict what it will see in a different situation?**

Here is what I recommend.

**1. Keep the gravity task as a baseline, then introduce a law that requires distinguishing hypotheses.**

Our current environment tells the model that gravity is constant and provides accurate drop times. One measurement almost determines the answer. Changing g from 9.81 to 3.0 tests parameter estimation, but offers little evidence of discovering a new relationship.

I suggest this progression:

| Stage | Hidden information | Useful experiment | New visual prediction |
|---|---|---|---|
| Baseline | Constant gravity g | Drop from different heights | Object positions after a stated time |
| Next | Gravity and surface restitution e | Drops followed by rebound measurements | Positions after hitting a surface |
| Harder | Restitution depends on impact speed, e(v) | Compare rebounds from several heights | Bounce outcomes at previously untested speeds |
| Later | Drag depends on speed and object properties | Compare motion across specimens and speeds | Several objects moving through air or liquid |

The third stage is particularly useful: a constant-restitution explanation and a speed-dependent explanation can agree on one trial but disagree on another. The model must choose an informative experiment.

Keep these worlds explicitly defined and internally consistent. For example, bound restitution between zero and one when modeling a passive surface.

**2. Make the evaluation a transfer to a new setup.**

For the next version, I would use:

- **Interaction:** vertical drops and rebound measurements.
- **Evaluation:** a sideways launch toward a surface, followed by a bounce.
- **Input:** a context image, a clearly specified launch velocity and elapsed time.
- **Answer:** one of four images showing the resulting object positions.

The model has never directly tested that exact launch. It must combine the learned gravity and bounce behavior with the new geometry.

Later, add multiple objects with different measured properties. Keep colors and identities in the images, as you intended; question text should not identify them for the model.

**3. Build paired worlds with identical visual questions but different correct answers.**

This would be one of your most convincing experiments.

For example, create two episodes:

| | World A | World B |
|---|---|---|
| Hidden gravity | 3 m/s² | 9 m/s² |
| Initial scene | Identical | Identical |
| Candidate images | Identical | Identical |
| Experimental evidence | Drop measurements from A | Drop measurements from B |
| Correct image | Small fall distance | Larger fall distance |

After 0.4 seconds from rest, the fall distances are 0.24 m and 0.72 m, respectively, before contact.

**The model must change its answer when the experimental evidence changes, even though the question images are unchanged.** This directly tests whether it uses the interaction history. Balance these pairs so appearance and answer position cannot reveal the world.

**4. Separate discovery failures from visual-transfer failures.**

Overall multiple-choice accuracy alone will not explain what the model learned. I would run these conditions:

| Condition | Evidence supplied | What it measures |
|---|---|---|
| Full pipeline | Model’s own experiment history + images | Overall ability |
| Known physics | Correct world laws and parameters + images | Visual prediction when discovery is solved |
| Numeric scene | Experiment history + exact scene measurements | Prediction when visual measurement is solved |
| Fixed experiments | A standard measurement set + images | Whether active experiment selection helps |
| No experiments | Images alone | Reliance on priors or visual shortcuts |

Your earlier objection about removing experiments is correct: **without the evidence, a particular world may be impossible to identify.** Treat that condition as an information-removal baseline, not a fair standalone physics exam. Low performance there is expected; unexpectedly high performance can reveal shortcuts.

If using separate experiment and vision models, explicitly record whether the vision model receives the full transcript or an agent-written notebook. Compare both while keeping the vision model fixed.

**5. Increase scientific difficulty while keeping the images readable.**

NewtonBench reports sensitivity to observational noise and discusses constrained experimentation as a future direction. [Paper, §4.2 and Appendix E.6](https://arxiv.org/html/2510.07172v3)

For your benchmark, I would first keep instrument readings clean and scenes visually clear, then vary these dimensions separately:

- Number of unknown physical quantities.
- Whether the model must identify a functional relationship.
- Experiment budget.
- Distance between experimental settings and evaluation settings.
- Number of objects and events to combine.

Your liquid-surface problem illustrates why this matters: unclear rendering can lower accuracy without testing deeper physical reasoning.

Also distinguish **unseen appearance** from **unknown physical behavior**. A new-colored object can still be predictable under universal gravity. A new material with unknown restitution may require additional evidence.

**6. Start with a small, controlled pilot.**

My recommended next experiment is:

> **Learn gravity and bounce behavior from a drop apparatus, then predict a frame after a new launch and bounce.**

Use approximately **12 worlds × 8 visual questions**, with several independent interaction runs per world. Include constant restitution first, then speed-dependent restitution. Reuse the same world definition for both experimental measurements and rendered trajectories.

Report separately:

- Accuracy of the inferred physics.
- Visual prediction accuracy.
- Accuracy on the paired-world questions.
- Measurements used.
- Accuracy as the experiment budget increases.

Analyze uncertainty across worlds and interaction runs; questions sharing one learned world are not independent experiments.

This gives your work a concrete experimental claim to test: **knowledge acquired through interaction supports prediction across both a change of setup and a change from numerical observations to visual scenes.**
