# Drag scene parameters (host-only)

Exact recorded objects, gravity and contact rules; do not include this file in model context. Heights in the public instructions are sphere-bottom clearances. All options depict the same elapsed time.

```json
{
  "scene": {
    "format": "drag_prediction_scene",
    "schema_version": 2,
    "visual_version": 2,
    "id": "drag_016",
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
        "release_height_m": 2.325,
        "position_m": [
          -1.5,
          0,
          3.2150000000000003
        ],
        "velocity_m_s": [
          0.7,
          0,
          0
        ]
      }
    ],
    "elapsed_s": 1.38,
    "choices": {
      "A": {
        "hypothesis": "local_profile_3",
        "world": {
          "format": "height_drag_world",
          "schema_version": 1,
          "visibility": "host_only",
          "world_id": "sha256:36b7262e002d6b0daa4456482e87cf42c587a0b0c3a4ef294c970240c9fef417",
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
            0.19989021945918986,
            0.017701109298878158,
            0.09167400441212045,
            0.0772284640042462,
            0.22915488095229233,
            0.2124808054791309,
            0.27524201452108743,
            0.036725295404972054,
            0.13634884319728435,
            0.01909708000144776,
            0.07541502165400314,
            0.16017856741139241,
            0.018066576424898492
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
              -0.9110494733224889,
              0.0,
              1.5129411980349485
            ],
            "velocity_m_s": [
              0.12774659494305085,
              0.0,
              -1.689760808498014
            ],
            "impacts": 0
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
              -0.9049625151889661,
              0.0,
              1.491890995190622
            ],
            "velocity_m_s": [
              0.135215485020131,
              0.0,
              -1.73910536003945
            ],
            "impacts": 0
          }
        ]
      },
      "C": {
        "hypothesis": "local_profile_0",
        "world": {
          "format": "height_drag_world",
          "schema_version": 1,
          "visibility": "host_only",
          "world_id": "sha256:cdcc3e5e5b8e9ba32b424d457bd644fac23ba741e7bdff5f5a49a9210275869e",
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
            0.1865208757399792,
            0.016357138445963912,
            0.0859274981568928,
            0.06973641418098335,
            0.21242019441810614,
            0.193766943099671,
            0.25571219486104074,
            0.03218619357764794,
            0.12437429673161648,
            0.017729420908225678,
            0.06938499477112861,
            0.14930196582714045,
            0.016953140775164372
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
              -0.8922588473013412,
              0.0,
              1.4481579234448225
            ],
            "velocity_m_s": [
              0.15100334576710117,
              0.0,
              -1.8380538547728944
            ],
            "impacts": 0
          }
        ]
      },
      "D": {
        "hypothesis": "local_profile_1",
        "world": {
          "format": "height_drag_world",
          "schema_version": 1,
          "visibility": "host_only",
          "world_id": "sha256:d19b0283110ecfab9606f1eb7ff1995b078c7609b2d75901134c14eb4b17029d",
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
            0.19097732364638273,
            0.01680512873026866,
            0.0878430002419687,
            0.07223376412207098,
            0.21799842326283486,
            0.20000489722615766,
            0.26222213474772293,
            0.03369922752008931,
            0.12836581222017246,
            0.01818530727263304,
            0.07139500373208678,
            0.1529274996885578,
            0.017324285991742412
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
              -0.8987004423450821,
              0.0,
              1.4702944144330305
            ],
            "velocity_m_s": [
              0.142967956120789,
              0.0,
              -1.7885477321517653
            ],
            "impacts": 0
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
    "minimum_candidate_separation_m": 0.02191260137698281,
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
    "truth_profile_rank": 2,
    "maximum_candidate_separation_m": 0.06745339348680908
  },
  "actual": {
    "Engine": "CYCLES",
    "Render device": "GPU",
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
    "frame": "B",
    "geometry": {
      "objects": [
        {
          "specimen_id": "sample_A",
          "center_m": [
            -0.9049625151889661,
            0.0,
            1.491890995190622
          ],
          "center_pixels": [
            582.2764778137207,
            361.13697052001953
          ],
          "diameter_pixels": 25.04344940185547
        }
      ],
      "elapsed_s": 1.38
    }
  }
}
```
