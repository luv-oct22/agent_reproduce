# Drag scene parameters (host-only)

Exact recorded objects, gravity and contact rules; do not include this file in model context. Heights in the public instructions are sphere-bottom clearances. All options depict the same elapsed time.

```json
{
  "scene": {
    "format": "drag_prediction_scene",
    "schema_version": 2,
    "visual_version": 2,
    "id": "drag_004",
    "world_id": "sha256:747b65729571eb4a53722f9ec6288d602b4fc7d1da995cf03b679cc87387129f",
    "object_registry_id": "sha256:0d2a3200e6b9a059b1c01066f3187b82b68f9086f327d9dcc79cdf421ce5874b",
    "contact_registry_id": "sha256:377e7f188dbcbf36129058cfd3c7851ecf0c26b272fb98fdaf2dff6a22a284da",
    "surface_id": "surface_1",
    "surface_z_m": 0.86,
    "objects": [
      {
        "station": "1",
        "source_specimen_id": "sample_A",
        "color": "blue",
        "color_rgba": [
          0.08,
          0.35,
          0.8,
          1
        ],
        "radius_m": 0.030000000000000006,
        "mass_kg": 0.1,
        "release_height_m": 1.725,
        "position_m": [
          -1.5,
          0,
          2.615
        ],
        "velocity_m_s": [
          0.7,
          0,
          0
        ]
      }
    ],
    "elapsed_s": 1.0,
    "choices": {
      "A": {
        "hypothesis": "local_profile_1",
        "world": {
          "format": "height_drag_world",
          "schema_version": 1,
          "visibility": "host_only",
          "world_id": "sha256:39aa940d8cbf695a56422aea515a2e17b7892bce635f9d22a91cf3e90f1410bd",
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
            0.20250584807527577,
            0.018152578680210182,
            0.09229582842086359,
            0.07922771125080501,
            0.2379478975598494,
            0.2211314278663229,
            0.28228711052130656,
            0.036288494864808785,
            0.1398548380712064,
            0.019958543787192133,
            0.07578971770440791,
            0.1644111988811993,
            0.018651862604708018
          ],
          "generation_seed": null,
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
        "restitution": 0.8,
        "objects": [
          {
            "source_specimen_id": "sample_A",
            "position_m": [
              -1.107345670716273,
              0.0,
              1.7668862043849893
            ],
            "velocity_m_s": [
              0.10995113124847483,
              0.0,
              -1.1919632499144133
            ],
            "impacts": 0
          }
        ]
      },
      "B": {
        "hypothesis": "local_profile_3",
        "world": {
          "format": "height_drag_world",
          "schema_version": 1,
          "visibility": "host_only",
          "world_id": "sha256:c1b060ca9337284703a4e215ea25cbf7c2592c380c758e4d8733f9fe6d4b951b",
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
            0.21665000112025481,
            0.019951498011483725,
            0.0973704806085016,
            0.08822090562609787,
            0.2666903884644211,
            0.25090858089368007,
            0.3093971822951095,
            0.03844096166936499,
            0.15484985879616242,
            0.0225932440874956,
            0.08055912772713379,
            0.1801275295436477,
            0.020564725397483146
          ],
          "generation_seed": null,
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
        "restitution": 0.8,
        "objects": [
          {
            "source_specimen_id": "sample_A",
            "position_m": [
              -1.122789556635428,
              0.0,
              1.8082398447131118
            ],
            "velocity_m_s": [
              0.08854733246855286,
              0.0,
              -1.0814075476888305
            ],
            "impacts": 0
          }
        ]
      },
      "C": {
        "hypothesis": "local_profile_2",
        "world": {
          "format": "height_drag_world",
          "schema_version": 1,
          "visibility": "host_only",
          "world_id": "sha256:0ea21e71cc7df8ca3d641230c27abc6681a50d2c079d52c01dd8412bcd564dbd",
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
            0.2095779245977653,
            0.019052038345846956,
            0.09483315451468259,
            0.08372430843845144,
            0.25231914301213526,
            0.23602000438000148,
            0.295842146408208,
            0.03736472826708689,
            0.14735234843368442,
            0.02127589393734387,
            0.07817442271577084,
            0.1722693642124235,
            0.019608294001095584
          ],
          "generation_seed": null,
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
        "restitution": 0.8,
        "objects": [
          {
            "source_specimen_id": "sample_A",
            "position_m": [
              -1.1152917881562499,
              0.0,
              1.7881141808961556
            ],
            "velocity_m_s": [
              0.09855654154221367,
              0.0,
              -1.1335676102679282
            ],
            "impacts": 0
          }
        ]
      },
      "D": {
        "hypothesis": "recorded_physics",
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
        "restitution": 0.8,
        "objects": [
          {
            "source_specimen_id": "sample_A",
            "position_m": [
              -1.09891193630749,
              0.0,
              1.7444475918842544
            ],
            "velocity_m_s": [
              0.12294190256339237,
              0.0,
              -1.257218506415168
            ],
            "impacts": 0
          }
        ]
      }
    },
    "answer": "D",
    "images": {
      "context": "context.png",
      "A": "choice_A.png",
      "B": "choice_B.png",
      "C": "choice_C.png",
      "D": "choice_D.png"
    },
    "minimum_candidate_separation_m": 0.021476938241762934,
    "truth_impacts": 0,
    "scene": {
      "camera_position_m": [
        0,
        -7,
        2.16
      ],
      "camera_target_m": [
        0,
        0,
        2.16
      ],
      "ortho_scale_m": 4.6,
      "grid_spacing_m": 0.1,
      "minor_grid_spacing_m": 0.025,
      "grid_height_m": 2.6,
      "grid_half_width_m": 2.1,
      "show_launch_height": true,
      "table_bounds_m": [
        -2.2,
        2.2,
        -0.6,
        0.6
      ],
      "grid_back_y_m": 0.22
    },
    "profile_type": "smooth_random",
    "candidate_policy": {
      "name": "close_physics_v1",
      "minimum_separation_m": 0.02,
      "maximum_separation_m": 0.08,
      "minimum_separation_pixels": 6.0,
      "same_motion_phase": true
    },
    "truth_profile_rank": 0,
    "maximum_candidate_separation_m": 0.06811455258244038
  },
  "actual": {
    "Engine": "CYCLES",
    "Render device": "CPU",
    "Samples": 96,
    "Denoising": true,
    "Resolution": [
      1920,
      1280
    ],
    "Scene FPS": 24.0,
    "Colour transform": "Standard",
    "Exposure": -0.4000000059604645,
    "Render seed": 7,
    "Actual camera": {
      "position_m": [
        0.0,
        -7.0,
        2.1600000858306885
      ],
      "rotation_euler_rad": [
        1.5707963705062866,
        -0.0,
        0.0
      ],
      "lens_mm": 50.0,
      "depth_of_field": false,
      "fstop": 2.799999952316284,
      "focus_distance_m": 10.0
    },
    "frame": "A",
    "geometry": {
      "objects": [
        {
          "specimen_id": "sample_A",
          "center_m": [
            -1.107345670716273,
            0.0,
            1.7668862043849893
          ],
          "center_pixels": [
            497.80351638793945,
            475.91758728027344
          ],
          "diameter_pixels": 25.04344940185547
        }
      ],
      "elapsed_s": 1.0
    }
  }
}
```
