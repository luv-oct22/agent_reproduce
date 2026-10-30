# Drag scene parameters (host-only)

Exact recorded objects, gravity and contact rules; do not include this file in model context. Heights in the public instructions are sphere-bottom clearances. All options depict the same elapsed time.

```json
{
  "scene": {
    "format": "drag_prediction_scene",
    "schema_version": 2,
    "visual_version": 2,
    "id": "drag_007",
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
        "release_height_m": 2.425,
        "position_m": [
          -1.5,
          0,
          3.315
        ],
        "velocity_m_s": [
          0.75,
          0,
          0
        ]
      }
    ],
    "elapsed_s": 1.46,
    "choices": {
      "A": {
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
              -0.8621910527070447,
              0.0,
              1.4002219948864987
            ],
            "velocity_m_s": [
              0.1362350868953356,
              0.0,
              -1.8455763697726173
            ],
            "impacts": 0
          }
        ]
      },
      "B": {
        "hypothesis": "local_profile_0",
        "world": {
          "format": "height_drag_world",
          "schema_version": 1,
          "visibility": "host_only",
          "world_id": "sha256:be2108995cef94e75ac8d841f8bf07bbd8eba809b9b609497a15cc36f7c83b3e",
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
            0.19218720215537966,
            0.016732712755938586,
            0.08749610470102377,
            0.07191909178645535,
            0.2151242525052784,
            0.2034768953924668,
            0.2607985474970604,
            0.03422665376518075,
            0.13026627409514935,
            0.01813186560311318,
            0.07146075682640075,
            0.15394584946580375,
            0.017299834326305087
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
              -0.8555332116501695,
              0.0,
              1.3783420972668479
            ],
            "velocity_m_s": [
              0.14361606062687218,
              0.0,
              -1.8939285628363582
            ],
            "impacts": 0
          }
        ]
      },
      "C": {
        "hypothesis": "local_profile_3",
        "world": {
          "format": "height_drag_world",
          "schema_version": 1,
          "visibility": "host_only",
          "world_id": "sha256:8fb4e71a86308caa3534fda75b11f55a2be6c883b0e3638a83d3a81f4a79e2da",
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
            0.20192691034759958,
            0.018293931531843055,
            0.09428329757908618,
            0.08035515861656507,
            0.24048145131213397,
            0.2117747632729992,
            0.2845991289090948,
            0.03718347685723056,
            0.13653943493588655,
            0.01965984970489484,
            0.07729352442633337,
            0.1617674017183178,
            0.018486624972351182
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
              -0.875007915038659,
              0.0,
              1.4424683503204563
            ],
            "velocity_m_s": [
              0.12227523313139306,
              0.0,
              -1.7497733412808978
            ],
            "impacts": 0
          }
        ]
      },
      "D": {
        "hypothesis": "local_profile_2",
        "world": {
          "format": "height_drag_world",
          "schema_version": 1,
          "visibility": "host_only",
          "world_id": "sha256:e2a538ab1a3f53f43f434d429a12b947680dc4e9dccfa43c11f12275975e9cd9",
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
            0.19868034095019294,
            0.017773525273208232,
            0.09202089995306537,
            0.07754313633986183,
            0.2320290517098488,
            0.20900880731282173,
            0.27666560177175004,
            0.036197869159880616,
            0.13444838132230746,
            0.019150521670967622,
            0.07534926855968918,
            0.15916021763414648,
            0.018091028090335814
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
              -0.8686812157036818,
              0.0,
              1.4215983871815339
            ],
            "velocity_m_s": [
              0.12912449502714798,
              0.0,
              -1.797549075785623
            ],
            "impacts": 0
          }
        ]
      }
    },
    "answer": "A",
    "images": {
      "context": "context.png",
      "A": "choice_A.png",
      "B": "choice_B.png",
      "C": "choice_C.png",
      "D": "choice_D.png"
    },
    "minimum_candidate_separation_m": 0.02180785376636549,
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
    "truth_profile_rank": 1,
    "maximum_candidate_separation_m": 0.06701820948641547
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
    "scene_digest": "067d87863a7a9c28279963bb325d3d162182b3ee48c1f75d7a8d7bff82c13c52",
    "frames": {
      "context": {
        "objects": [
          {
            "specimen_id": "sample_A",
            "center_m": [
              -1.5,
              0,
              3.315
            ],
            "center_pixels": [
              333.9130210876465,
              1122.0868682861328
            ],
            "diameter_pixels": 25.04344940185547
          }
        ],
        "elapsed_s": 0
      },
      "A": {
        "objects": [
          {
            "specimen_id": "sample_A",
            "center_m": [
              -0.8621910527070447,
              0.0,
              1.4002219948864987
            ],
            "center_pixels": [
              600.1289176940918,
              322.8750991821289
            ],
            "diameter_pixels": 25.04344940185547
          }
        ],
        "elapsed_s": 1.46
      },
      "B": {
        "objects": [
          {
            "specimen_id": "sample_A",
            "center_m": [
              -0.8555332116501695,
              0.0,
              1.3783420972668479
            ],
            "center_pixels": [
              602.907886505127,
              313.74267578125
            ],
            "diameter_pixels": 25.04344940185547
          }
        ],
        "elapsed_s": 1.46
      },
      "C": {
        "objects": [
          {
            "specimen_id": "sample_A",
            "center_m": [
              -0.875007915038659,
              0.0,
              1.4424683503204563
            ],
            "center_pixels": [
              594.7793197631836,
              340.5084228515625
            ],
            "diameter_pixels": 25.043506622314453
          }
        ],
        "elapsed_s": 1.46
      },
      "D": {
        "objects": [
          {
            "specimen_id": "sample_A",
            "center_m": [
              -0.8686812157036818,
              0.0,
              1.4215983871815339
            ],
            "center_pixels": [
              597.4200439453125,
              331.79744720458984
            ],
            "diameter_pixels": 25.043506622314453
          }
        ],
        "elapsed_s": 1.46
      }
    },
    "images_rendered": true,
    "blender_version": "3.6.23",
    "requested_backend": "CPU"
  }
}
```
