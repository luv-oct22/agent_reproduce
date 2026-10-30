# Shared world records — step 2

Implemented in `src/worlds/definition.py`, with a compatibility adapter in
`src/worlds/drag_adapter.py`. These are validated data contracts. The
[attraction runtime](attraction_world.md) now executes a supported subset;
generalized tools and temporal dynamics remain future work. Existing drag code,
result formats, and frozen assets remain unchanged.

## Components

| Record | Responsibility |
|---|---|
| `LawSpec` | Named/versioned force law, parameters, and coefficient-field references |
| `FieldSpec` | Constant or height/time function, units, bounds, and full sampled parameters |
| `ObjectSpec` | Visible identity/appearance, mass/volume, geometry family, fixed/dynamic status |
| `ContactSpec` | Object/surface identity, surface height, restitution and tangential friction |
| `SolverSpec` | Solver name/version and positive numerical settings |
| `ProtocolSpec` | Instructions, tool catalog, measurement limits, costs, budgets, clock and disclosures |
| `WorldSpec` | Physical composition, coefficient-unit checks and cross-reference validation |
| `WorldInstance` | A world bound to a protocol, solver and private provenance |

Object mass is inertial mass in kilograms. Volume is in cubic metres. Supported
objects reuse the existing sphere/cube `Specimen` validation and derived density
and size; density cannot be independently specified inconsistently. Object
charge and independent gravitational mass will require an explicit extension.
The current world frame is Cartesian, metres, z up; the motion equation is
`newton_second_law_v1`. These are explicit constraints, not hidden defaults.

Schema version 1 describes these law families:

- `uniform_gravity`: a unit direction and an acceleration field in m/s².
- `linear_drag`: a stationary or specified constant-velocity medium and a
  coefficient field in kg/s; coefficients must be nonnegative.
- `central_attraction`: positive exponent, reference distance/mass, minimum
  separation, midpoint coefficient sampling, and a strength field in newtons.
  The equation is the normalized attraction equation in the architecture guide.
  The step-3 runtime executes constant-strength p=2 and p=3 instances and
  explicitly rejects unsupported combinations.

Field kinds are `constant`, `smoothstep_height`, `layered_height`, and
`sinusoid_time`. Height fields reference a declared contact surface, use centre
height relative to it, and declare constant endpoint extrapolation. Smoothstep
samples are strictly increasing; each interval uses w(u)=3u²−2u³. The layered
field uses its lower value strictly below the boundary and its upper value at
or above it. A time sinusoid means
`offset + amplitude*sin(2*pi*(t-time_origin_s)/period_s + phase_rad)`.
Its entire amplitude range must fit within declared bounds. This is a schema
definition, not a new field evaluator. Arbitrary 3D fields, equations and other
law/field versions are rejected until explicitly supported.

`SolverSpec` stores a descriptor; a syntactically valid name is not evidence
that a solver is installed. Execution must use an explicit implementation
registry in the future runtime. Loading a record never evaluates expressions,
imports an implementation named by data, or executes code from the record.

## Serialization, identity and immutability

Construct each record with its validated payload. `to_dict()` returns a private
JSON envelope containing `format`, `schema_version`, `visibility`, `record_id`,
and `payload`. Nested records retain their own envelopes.

`record_id` is SHA-256 over canonical JSON of format, schema version and payload.
Object-key order is normalized; list order and numeric JSON representations are
retained. For example, authoring `1` versus `1.0` can change a fingerprint.
Use consistently serialized records rather than treating the hash as a proof of
physical equivalence. Fingerprints detect accidental inconsistency; they are
not authentication signatures.

The private representation is an immutable JSON string. Constructors copy
input data; payloads, serialized records and public views return fresh copies.
Mutating a returned nested dictionary cannot mutate the underlying record.
`from_dict()` checks fingerprints and rejects unsupported schema versions,
unknown keys, nonfinite values, missing references and incompatible field units.
`save()` accepts the same existing record but refuses to replace a different one.

Physical identity is the `WorldSpec.record_id`. A different protocol or solver
changes `WorldInstance.record_id` without changing the physical-world ID.
Seeds and original records live under instance provenance; all actual physical
values are serialized in the world. Replaying never requires resampling a seed.

## Public information and tool choice

Only `WorldInstance.public_dict()` is intended for an agent-facing initial
observation. Do not pass `to_dict()` or `payload` into model messages.

The public view contains protocol instructions, the complete tool catalog,
budget, clock, object appearance/fixed status, and explicitly disclosed values.
It excludes record fingerprints, solver settings and private provenance.
Tool ordering and availability are authored by the protocol, not selected from
the active hidden law. Descriptions must explain operations, not recommend an
experiment. Text authors remain responsible for avoiding hints in descriptions;
structural validation cannot determine whether arbitrary prose leaks an answer.

Disclosure examples:

```text
objects.sample_A.mass_kg  # one calibrated property
objects.sample_A.radius_m
laws.drag.family         # family/version, without parameter values
laws.drag                # complete law descriptor, not referenced field values
fields.g                 # complete field definition
contacts.floor_contact   # complete contact rule
```

The list defaults to no disclosures when authored that way; unknown selectors
are rejected. The `law_discovery` track forbids active-law/field disclosures.
The `disclosed_law` track permits explicit disclosure of those components.
Visible color and shape do not automatically disclose exact mass, radius or
volume. Rendering may still reveal geometric information, as intended by the
visual protocol.

`instance.require_same_public_interface(other)` verifies equality of the entire
public observation, including tool order, instructions, calibration and costs.
Use this for matched-world experiments in which hidden physics varies while
public initial information is controlled. It does not require every unrelated
world to have identical object appearances.

Tool records include a closed object-argument schema, measurement descriptors
(name, unit, positive resolution, optional finite range), a sample definition,
and costs per invocation, sample and simulated second. An empty measurement
list is appropriate for inspection/setup/control operations. Schema validation
checks the object envelope and required-property references; it is not a full
JSON Schema validator for arbitrary nested schemas or runtime tool arguments.
Step 4 must bind tools to actual apparatus, validate actions, define quantization
and saturation, and enforce their stated costs and sample limits.

## Clocks and budgets

`resettable` means trial start times are explicit. `continuous` means resetting
objects preserves world time. Contradictory reset rules are rejected. A clock
domain is mandatory when a sinusoidal time field is present, and its initial
time must lie in that domain. Scenes and actions must later supply absolute
start times and remain inside the domain; these contracts do not implement
clock advancement or scene-state validation yet.

Measurement budgets are positive integers. `max_turns: null` explicitly means
the turn limit is not recorded; it does not invent a historical limit or grant
an unlimited live run. A future runner must resolve its limit before executing.

## Adapt the existing drag world

A converted record is saved at
`world_instances/drag_complex_close_v1/instance.json`. Reproduce it with:

```bash
python -m src.worlds.drag_adapter \
  --manifest baselines/drag_complex_close_v1/batch/private_manifest.json \
  --output world_instances/drag_complex_close_v1/instance.json
```

The adapter supports both legacy two-layer and smooth-height worlds. It preserves
the original private manifest under provenance and describes its existing
disclosed-law protocol. One charged sample is one valid drop/bounce experiment,
including all its returned readings; inspection and submissions remain free.
This is descriptive metadata for the legacy behavior, not a replacement harness
or the new common experimental bench. The turn limit is left null unless
explicitly supplied with `--max-turns`.

```python
from src.worlds.definition import WorldInstance
from src.worlds.drag_adapter import restore_drag_env

instance = WorldInstance.load('world_instances/drag_complex_close_v1/instance.json')
public_observation = instance.public_dict()
env = restore_drag_env(instance)
```

Restoration verifies that the common records agree with the original manifest,
then loads the existing `DragLabEnv` and its solver. It rejects edits that would
silently make the shared definition and legacy execution disagree. Legacy
world IDs are preserved in provenance; the new composition has its own ID.

## Validation

```bash
python -m unittest discover -s tests -p 'test_world_definition.py' -v
python -m src.evaluation.drag_baseline verify --baseline baselines/drag_complex_close_v1
```

Tests cover serialization and corruption, immutable copies, overwrite protection,
public equivalence across hidden changes, disclosure rules, units/references,
clock/field constraints, measurement metadata and budgets, and exact legacy
instrument/trajectory compatibility. The frozen baseline checks original rendered
states against the unchanged implementation. No model call or render is needed.
