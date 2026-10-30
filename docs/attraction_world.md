# Attraction worlds — step 3

The constant-coefficient attraction simulator is implemented in
`src/worlds/attraction.py`. `src/worlds/attraction_setup.py` prepares two matched
world instances and host-only force/trajectory previews. The subsequent
[step-4 apparatus](attraction_bench.md) now executes the shared tool catalog.
Image questions, rendering, and model evaluation remain later stages.

## Physical law

For a pair of bodies i and j:

```text
delta = position_j - position_i
r = norm(delta)

force_on_i = A * (mass_i / m_ref) * (mass_j / m_ref)
               * (r_ref / r)^p * delta / r
force_on_j = -force_on_i
acceleration_i = net_force_i / mass_i        # movable bodies
acceleration_i = 0                          # fixed supports
```

The runtime supports p=2 and p=3, constant nonnegative A in newtons, and equal
inertial/gravitational mass. Forces act between sphere centres; radii determine
the noncontact domain, not a volume-integrated force distribution.
The normalized representation keeps A's units
consistent across exponents. It changes the attraction law while retaining
F=ma. All pair forces are evaluated once and accumulated equally and oppositely.
The runtime supports multiple spheres with fixed or dynamic motion, not just
one probe. The prepared comparison uses one fixed source and one dynamic probe.

There is no additional uniform gravity, drag, contact response, or implicit
softening. Runtime construction rejects additional laws/fields/contacts, temporal
or spatial coefficients, unsupported exponents, unknown solver versions, and
unsupported numerical settings. A valid general record does not imply that this
particular runtime supports every feature that record schemas can describe.

## Matched instances

| Setting | Both worlds |
|---|---|
| Force strength A | 1.2 N, hidden |
| Reference distance / mass | 1 m / 1 kg, host law definition |
| Orange anchor | Fixed, 1 kg, radius 0.08 m; object properties calibrated |
| Blue probe | Dynamic, 0.1 kg, radius 0.03 m; object properties calibrated |
| Excluded centre separation | r <= 0.20 m |
| Clock | Explicit trial start times, domain [0, 30] seconds |
| Apparatus budget | 24 measurement units, 8 model turns |
| Numerical solver | RK4 v1, maximum step 0.002 s, minimum guarded step 1e-8 s, 200000-step cap per advance |

Only the exponent differs between the pair. Both public observations are checked
for exact equality, including tool descriptions, calibrations, costs, and clock
rules. Public information does not name the active equation, exponent, or force
strength, and does not recommend which experiments to perform.

Saved files:

```text
world_instances/
  attraction_pair_v1.json
  attraction_p2_v1/instance.json
  attraction_p2_v1/preview.json
  attraction_p3_v1/instance.json
  attraction_p3_v1/preview.json
```

These are host-only. The instance files contain complete hidden truth. Preview
files contain exact simulator force probes and trajectories, not measurements
collected by a model. The pair index preserves its step-3 creation status;
it is not a live runtime capability registry.

Prepare or reproduce the pair offline:

```bash
python -m src.worlds.attraction_setup --output-dir world_instances
```

Identical existing artifacts are preserved; different artifacts cause an error
before writing the bundle. To author another constant strength, choose a new
output directory and pass `--strength-n`, within the authored [0, 5] N range.
No random seed is needed for this fixed pair: the full parameters are recorded.

For these calibrated masses, the force magnitude at 1 m is 0.12 N in both worlds.
At 2 m it is 0.03 N for p=2 and 0.015 N for p=3. The shared 1 m value illustrates
why a single observation cannot identify the exponent. This is a host sanity
check, not a prescribed experiment sequence or a full identifiability audit.

## Runtime API

```python
from src.worlds.definition import WorldInstance
from src.worlds.attraction import AttractionWorld

instance = WorldInstance.load('world_instances/attraction_p2_v1/instance.json')
world = AttractionWorld(instance)
initial = world.make_state(
    positions_m={'anchor': [0., 0., 1.5], 'probe': [1.25, 0., 1.5]},
    velocities_m_s={'anchor': [0., 0., 0.], 'probe': [0., 0., .8]},
    time_s=0.,
)
forces = world.forces(initial)             # exact mutual force vectors, N
next_state = world.advance(initial, .75)
frames = world.trajectory(initial, [0., .25, .5, .75])  # absolute timestamps
diagnostics = world.diagnostics(next_state)
```

`MotionState` is an immutable, fingerprinted record binding all object positions
and velocities to the physical world ID and an absolute time. Positions and
velocities must specify every object exactly once. Fixed objects require zero
velocity. States from a different physical world are rejected; changing only
solver settings permits convergence comparisons using the same physical state.
`advance` returns a new state; failed integration never mutates the caller's
state or returns an accepted partial trajectory. Sample times must increase
strictly and all timestamps must lie within the protocol clock domain.

`forces` returns mutual forces on every body, including loads on fixed bodies,
but excludes the holding support's reaction. `accelerations` returns zero for
fixed bodies. The step-4 force sensor reports this external load after applying
the declared resolution/range, excludes the holding reaction, and does not expose
unrounded simulator internals.

## Numerical domain and validation

For every pair, the admissible separation is strictly greater than both the law
cutoff and the sum of physical radii. The engine never clips r, softens the force,
lets spheres overlap, or substitutes a bounce. Such cases need a separately
defined contact/softening law in a later version.

Each step is limited by the maximum timestep and a conservative travel bound:
relative speed plus a domain-wide acceleration bound must permit less than a
quarter of the remaining separation clearance. Every RK4 stage and endpoint is
also checked. This prevents large steps from jumping across the excluded region.
If the safe step becomes smaller than the configured numerical limit, the call
raises `DomainError`. This is a conservative admissibility failure, not an exact
collision timestamp; a very near-boundary trajectory may be rejected even when
it would subsequently move away. RK4 is not an adaptive error-tolerance solver;
step-convergence checks remain necessary when choosing future scenes.

Energy uses the pair potential `-force_magnitude*r/(p-1)`. For constant A and
stationary anchors, the kinetic-plus-potential diagnostic should remain constant
within integration error. Total linear momentum is expected to be conserved
only when all bodies move freely; fixed supports supply external reactions.
Angular momentum is reported about the coordinate origin; its conservation
depends on the support geometry, not just the presence of a central force.

Tests cover distance scaling and force directions, reference scales/masses,
analytic circular orbits, fourth-order convergence, split integration, energy
and momentum conservation for free pairs, zero-force inertial motion, fixed
anchors, time/world bindings, forbidden-region rejection (including high-speed
crossing), unsupported compositions, reproducibility, and public equivalence.

```bash
python -m unittest discover -s tests -p 'test_attraction.py' -v
python -m unittest discover -s tests -p 'test_world_definition.py' -v
python -m src.evaluation.drag_baseline verify --baseline baselines/drag_complex_close_v1
```

The [common bench apparatus](attraction_bench.md) enforces measurement
costs/precision and clock rules while letting the agent choose experiments.
The [learnability audit](attraction_audit.md) now checks quantized evidence and
held-out numerical predictions. The [paired image suite](attraction_prediction.md)
now prepares 16 questions with close candidates and a separate rendering command.
