# Drag scene parameters (host-only)

Exact recorded objects, gravity and contact rules; do not include this file in model context. Heights in the public instructions are sphere-bottom clearances. All options depict the same elapsed time.

```json
{
  "scene": {
    "format": "drag_prediction_scene",
    "schema_version": 2,
    "visual_version": 2,
    "id": "drag_003",
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
        "release_height_m": 1.475,
        "position_m": [
          -1.5,
          0,
          2.365
        ],
        "velocity_m_s": [
          1.0,
          0,
          0
        ]
      }
    ],
    "elapsed_s": 2.55,
    "choices": {
      "A": {
        "hypothesis": "local_profile_1",
        "world": {
          "format": "height_drag_world",
          "schema_version": 1,
          "visibility": "host_only",
          "world_id": "sha256:1b002fb74068e964efa2e33ef8ae4bc184165aab6609d545bb461d8ce58275a7",
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
            0.18492694929857234,
            0.016395110889259424,
            0.08808069888270596,
            0.07139720212839552,
            0.2139211813073202,
            0.1984269117494894,
            0.26120108871376896,
            0.033744008176260484,
            0.12939919629016505,
            0.018004380173049204,
            0.07084651955908812,
            0.1482352642665502,
            0.016805678893970947
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
              -0.9921202480047363,
              0.0,
              1.0165957993881
            ],
            "velocity_m_s": [
              0.04531111188422559,
              0.0,
              0.2206613618936805
            ],
            "impacts": 2
          }
        ]
      },
      "B": {
        "hypothesis": "local_profile_0",
        "world": {
          "format": "height_drag_world",
          "schema_version": 1,
          "visibility": "host_only",
          "world_id": "sha256:a688ad65e079ba7462f24ab71d9b0e0a029414264c5296112d90441d9a01cfed",
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
            0.17442012704435836,
            0.015537102763945439,
            0.08640289543836736,
            0.06806329019363246,
            0.20426571050707684,
            0.19061097214633452,
            0.25367010279313273,
            0.03227575488999029,
            0.12644106487160167,
            0.01736756670905801,
            0.06828802642513129,
            0.1399174949831253,
            0.015915926579621445
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
              -0.9686230382670402,
              0.0,
              1.0225199019171898
            ],
            "velocity_m_s": [
              0.051321630902865296,
              0.0,
              0.2643566164801782
            ],
            "impacts": 2
          }
        ]
      },
      "C": {
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
              -1.0142451631509077,
              0.0,
              1.0104749761491676
            ],
            "velocity_m_s": [
              0.039743982916021166,
              0.0,
              0.1793350852287496
            ],
            "impacts": 2
          }
        ]
      },
      "D": {
        "hypothesis": "local_profile_3",
        "world": {
          "format": "height_drag_world",
          "schema_version": 1,
          "visibility": "host_only",
          "world_id": "sha256:ba8c7c4c7bd67bba3e25f0ae84992f3e0eb2c56cd3fb3dc1bbe736a8907b297e",
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
            0.20594059380700025,
            0.018111127139887395,
            0.09143630577138318,
            0.07806502599792164,
            0.23323212290780693,
            0.21405879095579916,
            0.2762630605550414,
            0.03668051474880088,
            0.13531545912729176,
            0.019278007101031596,
            0.0759635058270018,
            0.1648708028334,
            0.018585183522669954
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
              -1.035053749478246,
              0.0,
              1.0042289221453387
            ],
            "velocity_m_s": [
              0.03461926826572978,
              0.0,
              0.1405373746788648
            ],
            "impacts": 2
          }
        ]
      }
    },
    "answer": "C",
    "images": {
      "context": "context.png",
      "A": "choice_A.png",
      "B": "choice_B.png",
      "C": "choice_C.png",
      "D": "choice_D.png"
    },
    "minimum_candidate_separation_m": 0.021725801609170436,
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
    "maximum_candidate_separation_m": 0.06890282529070109
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
    "frame": "D",
    "geometry": {
      "objects": [
        {
          "specimen_id": "sample_A",
          "center_m": [
            -1.035053749478246,
            0.0,
            1.0042289221453387
          ],
          "center_pixels": [
            527.9775810241699,
            157.59106636047363
          ],
          "diameter_pixels": 25.04344940185547
        }
      ],
      "elapsed_s": 2.55
    }
  }
}
```
