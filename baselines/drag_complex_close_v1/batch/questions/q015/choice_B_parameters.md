# Drag scene parameters (host-only)

Exact recorded objects, gravity and contact rules; do not include this file in model context. Heights in the public instructions are sphere-bottom clearances. All options depict the same elapsed time.

```json
{
  "scene": {
    "format": "drag_prediction_scene",
    "schema_version": 2,
    "visual_version": 2,
    "id": "drag_015",
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
        "release_height_m": 2.075,
        "position_m": [
          -1.5,
          0,
          2.9650000000000003
        ],
        "velocity_m_s": [
          1.0,
          0,
          0
        ]
      }
    ],
    "elapsed_s": 3.05,
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
              -0.6993604862485844,
              0.0,
              1.0044059963954732
            ],
            "velocity_m_s": [
              0.04145173060371252,
              0.0,
              -0.3527932098087441
            ],
            "impacts": 2
          }
        ]
      },
      "B": {
        "hypothesis": "local_profile_2",
        "world": {
          "format": "height_drag_world",
          "schema_version": 1,
          "visibility": "host_only",
          "world_id": "sha256:84b4becc855a205075de8335e61a3d803048e104279907ab669548735142103d",
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
            0.20049105418950525,
            0.017866557925312183,
            0.09238837101918639,
            0.07637920540850691,
            0.2280467639936171,
            0.21417815345752794,
            0.27434596686079177,
            0.03611016796383178,
            0.13679617863880034,
            0.019176057893281747,
            0.07570478979285342,
            0.16006476152999363,
            0.018167307917090477
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
              -0.7207793548999039,
              0.0,
              0.9971089859091644
            ],
            "velocity_m_s": [
              0.037315798493970244,
              0.0,
              -0.363770298382464
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
          "world_id": "sha256:07ae3d69e9c7c07f5ab63d4e016976ad742d3435549a9d1494376c75e6db07cc",
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
            0.19037648891606734,
            0.016639680103834636,
            0.08712863363490277,
            0.07308302271781027,
            0.21910654022151005,
            0.19830754924776064,
            0.2631181824080186,
            0.03431435496122959,
            0.12791847677865648,
            0.01810632938079905,
            0.0711052355932365,
            0.15304130556995657,
            0.01722355449955043
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
              -0.6769859869237969,
              0.0,
              1.0121440313854657
            ],
            "velocity_m_s": [
              0.04594080505750039,
              0.0,
              -0.33964385486864407
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
          "world_id": "sha256:38246130a38de9795d6f706b180486733d4684d3f4a8d396bc28777bbd567024",
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
            0.2055483368262242,
            0.01847999683605096,
            0.09501823971132818,
            0.07802729675385525,
            0.23251687587967065,
            0.22211345556241155,
            0.2799598590871784,
            0.03700807446513287,
            0.14123502956887227,
            0.0197109221495231,
            0.07800456689266187,
            0.16357648951001216,
            0.0186391846258605
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
              -0.741286735918306,
              0.0,
              0.9902589280842353
            ],
            "velocity_m_s": [
              0.03351214175972396,
              0.0,
              -0.37268979546932895
            ],
            "impacts": 2
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
    "minimum_candidate_separation_m": 0.021621192576701018,
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
    "truth_profile_rank": 1,
    "maximum_candidate_separation_m": 0.06792307463418001
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
            -0.7207793548999039,
            0.0,
            0.9971089859091644
          ],
          "center_pixels": [
            659.1529655456543,
            154.61923599243164
          ],
          "diameter_pixels": 25.04344940185547
        }
      ],
      "elapsed_s": 3.05
    }
  }
}
```
