# Shared object registry

`src/objects/registry.py` is the common object-data component for experimental
environments and subsequent video simulations. The generated objects are fixed
for an episode. The agent sees only descriptors and experimental readings; the
host saves the full ground truth for reuse.

## Lifecycle

1. The environment generates specimens or loads an existing `ObjectRegistry`.
2. The environment's instruments use those immutable specimen instances.
3. Before the first model call, the run writes `object_registry.json` and
   `object_registry.md`, alongside the instrument-specific `private_manifest.json`.
4. The private evaluation records the same `object_registry_id`.
5. A later scene loads that JSON registry and adds scene-specific placement and
   motion. It does not regenerate properties or substitute the agent's estimates.

Every run gets its own registry files. Reusing an output directory for a different
registry raises an error rather than replacing the earlier objects. The registry
ID is a content fingerprint for consistency checks, not an authentication token.

## Recorded object data

| Field | Meaning |
|---|---|
| `id` | Stable identity shared between experiment and video |
| `mass_kg` | Ground-truth mass |
| `volume_m3` | External volume |
| `density_kg_m3` | Mass divided by external volume |
| `shape` | Currently `cube` |
| `color` | Public color label |
| `geometry.dimensions_m` | Three cube dimensions, derived from volume |
| `geometry.collision_shape` | `box` |
| `geometry.center_of_mass_local_m` | Local center of mass, at the cube center |
| `appearance.color_rgba` | Four linear-sRGB channels in [0, 1] |
| `appearance.color_space` | `linear_srgb` |
| `physics.inertia_diagonal_kg_m2` | Uniform-cube inertia about its center of mass |
| `physics.rigid` | True |
| `physics.uniform_density` | True |
| `physics.porous` | False |
| `physics.absorbs_water` | False |

For side length `s`, `s³ = volume_m3` and each diagonal inertia component is
`mass_kg * s² / 6`. Derived fields are checked when a registry is loaded.
Standard color labels have fixed RGBA values; unrecognized labels default to gray
unless the author supplies explicit `color_rgba` values.

The top-level JSON includes the format, schema version, SI units, registry ID,
source environment, and generation seed. The Markdown companion gives a readable
parameter table. All currently defined specimen properties are recorded; these
are ground-truth files and must stay outside the model's inputs.

Initial position, orientation, velocity, gravity, fluid properties, camera, and
render settings are chosen for the later scene. Contact and fluid-model
coefficients have not been assigned by this experimental environment and must be
specified when that simulator is implemented.

## Load in the future scene builder

```python
from src.objects.registry import ObjectRegistry

registry = ObjectRegistry.load("results/material_lab_registry_demo/object_registry.json")
objects = registry.simulation_objects()

for obj in objects:
    object_id = obj["id"]
    dimensions = obj["geometry"]["dimensions_m"]
    mass = obj["mass_kg"]
    density = obj["density_kg_m3"]
    rgba = obj["appearance"]["color_rgba"]
    # Build the mesh and physics body from these exact values.
    # Set this scene's initial pose and velocity separately.
```

The returned dictionaries are independent copies; editing a scene definition
does not mutate the registry. Save `registry.registry_id` with future simulation
and render metadata to connect it to its experimental episode.

## Reuse in another experimental run

```yaml
env:
  type: material_lab
  params:
    registry_path: results/material_lab_registry_demo/object_registry.json
    max_experiments: 48
task:
  type: identify_material
```

Paths are resolved relative to the working directory. This loads the stored
objects without resampling, regardless of an additional seed setting. The
model-facing observations still contain no masses, volumes, dimensions, densities,
or registry fingerprints.
