# Drag scene parameters (host-only)

Exact recorded objects, gravity and contact rules; do not include this file in model context. Heights in the public instructions are sphere-bottom clearances. All options depict the same elapsed time.

```json
{
  "scene": {
    "format": "drag_prediction_scene",
    "schema_version": 2,
    "visual_version": 2,
    "id": "drag_006",
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
        "release_height_m": 2.225,
        "position_m": [
          -1.5,
          0,
          3.115
        ],
        "velocity_m_s": [
          1.1,
          0,
          0
        ]
      }
    ],
    "elapsed_s": 3.08,
    "choices": {
      "A": {
        "hypothesis": "local_profile_3",
        "world": {
          "format": "height_drag_world",
          "schema_version": 1,
          "visibility": "host_only",
          "world_id": "sha256:86e582f68958fadc2d5260aef47e4bc53f94c5acab8fef455fef3d2ebfbb3e90",
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
            0.20153481502774384,
            0.017806991389292058,
            0.09276377031559614,
            0.07699637417015176,
            0.22933181453449814,
            0.20995497384215525,
            0.27376385396067704,
            0.03572531500966708,
            0.1366244264734476,
            0.018914004917275566,
            0.07496312162447528,
            0.15879999254621602,
            0.018146372793606844
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
              -0.4316020516064447,
              0.0,
              1.0036404830665386
            ],
            "velocity_m_s": [
              0.05212487357340696,
              0.0,
              -0.331663472289406
            ],
            "impacts": 2
          }
        ]
      },
      "B": {
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
              -0.41178484706814783,
              0.0,
              1.0129876450448296
            ],
            "velocity_m_s": [
              0.05714799153763329,
              0.0,
              -0.3076497784476267
            ],
            "impacts": 2
          }
        ]
      },
      "C": {
        "hypothesis": "local_profile_0",
        "world": {
          "format": "height_drag_world",
          "schema_version": 1,
          "visibility": "host_only",
          "world_id": "sha256:dbb8249999cfb07965714ddaebe81df13adbef64d21596bffa7eac78ea0b2b31",
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
            0.18323168460287123,
            0.016145374265136115,
            0.08374796634994144,
            0.07020059384917225,
            0.21206632725369443,
            0.1988186063736224,
            0.25866851598186147,
            0.03418615436825789,
            0.12382313017929002,
            0.018095571076570064,
            0.0702887948301843,
            0.1520591155574933,
            0.016793548037747665
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
              -0.3698551565243933,
              0.0,
              1.0324356277119136
            ],
            "velocity_m_s": [
              0.06818098808407275,
              0.0,
              -0.2520375445147798
            ],
            "impacts": 2
          }
        ]
      },
      "D": {
        "hypothesis": "local_profile_1",
        "world": {
          "format": "height_drag_world",
          "schema_version": 1,
          "visibility": "host_only",
          "world_id": "sha256:2a5b6d1c7686796f77b7f6b7cb7b21b2b57b60d9b3b531488d43a14d63c602db",
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
            0.18933272807782875,
            0.01669924663985476,
            0.08675323433849301,
            0.07246585395616542,
            0.21782148968062903,
            0.20253072886313334,
            0.2637002953081333,
            0.03469920791539429,
            0.1280902289440092,
            0.018368382356805234,
            0.07184690376161462,
            0.1543060745537342,
            0.017244489623034057
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
              -0.3912245757544815,
              0.0,
              1.0225973499194887
            ],
            "velocity_m_s": [
              0.062491199356653655,
              0.0,
              -0.2811210815479254
            ],
            "impacts": 2
          }
        ]
      }
    },
    "answer": "B",
    "images": {
      "context": "context.png",
      "A": "choice_A.png",
      "B": "choice_B.png",
      "C": "choice_C.png",
      "D": "choice_D.png"
    },
    "minimum_candidate_separation_m": 0.021910979730744663,
    "truth_impacts": 2,
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
    "truth_profile_rank": 2,
    "maximum_candidate_separation_m": 0.06813104584124571
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
    "frame": "context",
    "geometry": {
      "objects": [
        {
          "specimen_id": "sample_A",
          "center_m": [
            -1.5,
            0,
            3.115
          ],
          "center_pixels": [
            333.9130210876465,
            1038.6085510253906
          ],
          "diameter_pixels": 25.04344940185547
        }
      ],
      "elapsed_s": 0
    }
  }
}
```
