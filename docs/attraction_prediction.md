# Paired attraction image questions — step 6

The prepared suite is `renders/central_force_dynamics/paired_close_v1`: **16 questions in
eight matched pairs**, with eight questions for each saved world. It uses the
same immutable instances as the apparatus and learnability audit. Scene and
candidate generation are complete; pixel rendering is a separate command.

## Render on your GPU

From the project root with the project Python environment active:

```bash
conda activate agent_reproduce
bash scripts/render/render_attraction_prediction.sh --device CUDA

python -m src.simulation.attraction_scene validate \
  --output-dir renders/central_force_dynamics/paired_close_v1 --require-images
```

The renderer defaults to 1920×1280, 96 Cycles samples, five images per question
(one context and choices A–D), for **80 PNGs**. Use `--device OPTIX` if that
backend is available, or `--device CPU` for CPU rendering. `BLENDER_BIN` can
select a different Blender executable; the default is the project's bundled
Blender 3.6.23. Completed, verified questions with matching render settings are
skipped on a repeated render command.

Useful offline commands:

```bash
# Recompute physics, world bindings, evidence margins and shortcut diagnostics.
python -m src.simulation.attraction_scene validate

# Check the render plan without starting Blender.
bash scripts/render/render_attraction_prediction.sh --dry-run

# Construct cameras/meshes, check projections and visibility, save .blend files.
# This makes no PNGs and must not replace completed image render records.
bash scripts/render/render_attraction_prediction.sh --device CPU --build-only

# Create a new independent suite directory; an existing directory is refused.
python -m src.simulation.attraction_scene prepare \
  --audit-dir results/attraction_audit/attraction_pair_v1 \
  --output-dir renders/central_force_dynamics/paired_close_v1_repeat
```

The dedicated paired-world model evaluator is the next stage. Do not use the
legacy drag evaluator for this suite. A model must interact separately with
each world and receive the matching history for each question; routing is
recorded privately in `batch.json` and `questions.json`.

## Scene design

Each pair has identical launch conditions, public question text, camera and
four candidate configurations, but different correct answers. The first member
uses p=2 and the second uses p=3. The implementation keeps that routing host-only;
the public question never names the law, strength, world index or answer.
All object appearance and calibrated properties remain those of the saved world.

The fixed orange anchor is at (0, 0, 1.5) m. The blue probe moves in the x–z
plane. The context and captions specify its initial centre and velocity, with
zero y position/velocity, world start time and elapsed time. A front-facing
orthographic camera and 0.10 m grid make scale consistent across all images.
No gravitational arrow, hidden-force label, trajectory trail, or answer hint
is drawn. The panel is visual calibration geometry, not a simulated collider.

Launches use eight different distances, orientations, velocities and start
times. Durations are selected to separate the two true-law predictions by the
predeclared gap between their candidate ranks. There are two true-world poses
and two distractors per pair. Distractors vary constant strength under p=2;
their positions come from the same authoritative simulator. No sphere is moved
by hand to create an answer choice.

Every pair of candidate centres must be **2–8 cm apart**, not just each
distractor versus the correct choice. The prepared suite achieves approximately
**2.400–7.203 cm**, corresponding to at least **9.21 pixels** at the default
resolution. Every candidate shares the same radial motion direction. The
correct answer's inward-displacement rank is balanced across 0, 1, 2 and 3,
and answer labels A–D occur twice per world, four times across the full suite.

Blender reads the saved poses and never runs its own physics. Before rendering
any pixels, it checks all five frames: actual camera projections agree with the
planned camera, sphere bounding boxes fit the image, projected sphere diameters
are at least 16 pixels, centre rays are unobstructed, and calibration text fits
inside the frame. The candidate centres must be at least six pixels apart.
Build-only checks establish geometric readability, not final rendered-image
quality; inspect the resulting PNGs before a model pilot.

## Physics, evidence and shortcut checks

`validate` reloads fingerprinted world/state records, recomputes every candidate
trajectory, requires exactly one candidate to match the question's world,
checks calibrated rendered objects, and compares integrations at half the
maximum timestep. No contacts, force softening or alternate Blender dynamics
are introduced. Public question text, aggregate routing and saved audit results
are also checked against the manifests.

For each new scene, nine strengths including the endpoints of the two-reading
reference audit's conservative fitted interval are simulated. All sampled
hypotheses must prefer the same correct choice. The report records the largest
position uncertainty and smallest margin to a competing answer. This checks
transfer of the available evidence; it is not a certified continuous bound and
the reference experiment policy is never given to the evaluated agent.

The following baselines use exact coordinates and bypass image perception:

| Rule | Correct / 16 |
|---|---|
| Nearest the initial probe position | 4 |
| Nearest a constant-velocity prediction | 4 |
| Nearest the anchor | 4 |
| Nearest the centroid of all four choices | 4 |
| Always assume p=2, A=1.2 | 8 |
| Always assume p=3, A=1.2 | 8 |

These scores are diagnostics, not model results. Generation uses predeclared
rank assignments and physical constraints, not these scores. Ties split credit.
Identical paired visuals with different correct answers limit a deterministic
world-independent visual rule to at most 50% on the full paired suite. They do
not guarantee that every possible shortcut performs at the four-choice chance
rate of 25%. In particular, a fixed-law prior reaches 50%. Report per-world and
paired results, including no-history controls, in the eventual model pilot.

## Files and visibility

```text
paired_close_v1/
  batch.json                    # host routing, instance IDs and scene digests
  world_1.json / world_2.json    # complete private world definitions
  learnability_audit.json       # copy of the bound reference audit
  candidate_audit.json           # baseline results and per-question distances
  physics_validation.json       # separation and timestep checks
  evidence_transfer.json        # sampled fitted-strength answer margins
  questions.json                # host routing plus public question payloads
  checksums.json                # immutable prepared-artifact checksums
  questions/q001/ ... q016/
    scene.json                  # private poses, candidate worlds and answer
    question.json               # only the public question and image filenames
    scene.blend                 # added by Blender build or render
    build_report.json           # actual camera, visibility and render state
    scene_parameters.md         # host render settings and geometry
    context.png / choice_A.png / ... / choice_D.png
    *_parameters.md             # host records for rendered PNGs
```

Only public question payloads, PNG pixels and the matching public interaction
history belong in a model request. Private JSON, `.blend` files, build reports
and parameter documents contain information unsuitable for the agent.

Prepared artifact hashes prevent accidental edits. Render records bind each
PNG's checksum and dimensions to the scene digest and camera checks.
`--require-images` rejects missing, stale or modified image artifacts and
build-only records; successful physics validation alone does not mean images
exist. Source-file hashes are recorded for preparation provenance.

Tests: `python -m unittest discover -s tests -p 'test_attraction_scene.py' -v`.
Existing drag render/evaluation code and the frozen baseline remain unchanged.
