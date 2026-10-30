# Drag interaction parameters (host-only)

One calibrated sphere; invisible height-dependent drag; impact time and rebound height only. World height is sphere-centre height; release/rebound heights are bottom clearance.

```json
{
  "format": "drag_lab_manifest",
  "schema_version": 1,
  "environment": "drag_lab",
  "world": {
    "format": "height_drag_world",
    "schema_version": 1,
    "visibility": "host_only",
    "world_id": "sha256:747b65729571eb4a53722f9ec6288d602b4fc7d1da995cf03b679cc87387129f",
    "gravity_m_s2": 3.0,
    "heights_m": [
      0.0,
      0.25,
      0.5,
      0.75,
      1.0,
      1.25,
      1.5,
      1.75,
      2.0,
      2.25,
      2.5,
      2.75,
      3.0
    ],
    "coefficients_kg_s": [
      0.1954337715527863,
      0.01725311901457341,
      0.08975850232704458,
      0.07473111406315859,
      0.22357665210756358,
      0.20624285135264428,
      0.2687320746344052,
      0.03521226146253068,
      0.1323573277087284,
      0.0186411936370404,
      0.07340501269304496,
      0.1565530335499751,
      0.017695431208320452
    ],
    "generation_seed": 42,
    "law": "F_drag = -b(z) * velocity",
    "interpolation": "smoothstep: w(u)=3*u^2-2*u^3",
    "extrapolation": "constant endpoint values",
    "coordinate": "sphere centre z above impact surface at z=0",
    "drag_units": "kg/s",
    "gravity_units": "m/s^2",
    "length_units": "m",
    "medium_stationary": true,
    "buoyancy": false,
    "spin_coupling": false,
    "object_object_collisions": false,
    "rest_normal_speed_threshold_m_s": 1e-07,
    "solver": "rk4_with_bisected_impact_and_apex_events_v1",
    "max_step_s": 0.002
  },
  "world_id": "sha256:747b65729571eb4a53722f9ec6288d602b4fc7d1da995cf03b679cc87387129f",
  "object_registry": {
    "format": "physics_object_registry",
    "schema_version": 1,
    "visibility": "host_only",
    "registry_id": "sha256:0d2a3200e6b9a059b1c01066f3187b82b68f9086f327d9dcc79cdf421ce5874b",
    "units": {
      "length": "m",
      "mass": "kg",
      "volume": "m^3",
      "density": "kg/m^3",
      "inertia": "kg*m^2"
    },
    "provenance": {
      "source_environment": "material_lab",
      "seed": null
    },
    "objects": [
      {
        "id": "sample_A",
        "color": "blue",
        "shape": "sphere",
        "mass_kg": 0.1,
        "volume_m3": 0.00011309733552923254,
        "density_kg_m3": 884.1941282883076,
        "geometry": {
          "dimensions_m": [
            0.06000000000000001,
            0.06000000000000001,
            0.06000000000000001
          ],
          "collision_shape": "sphere",
          "center_of_mass_local_m": [
            0,
            0,
            0
          ]
        },
        "appearance": {
          "color_rgba": [
            0.08,
            0.35,
            0.8,
            1
          ],
          "color_space": "linear_srgb"
        },
        "physics": {
          "rigid": true,
          "uniform_density": true,
          "porous": false,
          "absorbs_water": false,
          "inertia_diagonal_kg_m2": [
            3.600000000000002e-05,
            3.600000000000002e-05,
            3.600000000000002e-05
          ]
        }
      }
    ]
  },
  "object_registry_id": "sha256:0d2a3200e6b9a059b1c01066f3187b82b68f9086f327d9dcc79cdf421ce5874b",
  "contact_registry": {
    "format": "physics_contact_registry",
    "schema_version": 1,
    "visibility": "host_only",
    "registry_id": "sha256:377e7f188dbcbf36129058cfd3c7851ecf0c26b272fb98fdaf2dff6a22a284da",
    "world_id": "sha256:747b65729571eb4a53722f9ec6288d602b4fc7d1da995cf03b679cc87387129f",
    "object_registry_id": "sha256:0d2a3200e6b9a059b1c01066f3187b82b68f9086f327d9dcc79cdf421ce5874b",
    "surface": {
      "id": "surface_1",
      "stationary": true,
      "horizontal": true
    },
    "law": "constant_normal_restitution",
    "coefficient_units": "dimensionless",
    "tangential_friction": 0.0,
    "air_drag": true,
    "spin_coupling": false,
    "object_object_collisions": false,
    "pairs": [
      {
        "specimen_id": "sample_A",
        "surface_id": "surface_1",
        "restitution": 0.8
      }
    ]
  },
  "apparatus": {
    "max_experiments": 24,
    "clock_resolution_s": 0.001,
    "height_resolution_m": 0.001
  },
  "motion_contact_approximation": "normal rebound speed <1e-7 m/s becomes sustained floor contact"
}
```
