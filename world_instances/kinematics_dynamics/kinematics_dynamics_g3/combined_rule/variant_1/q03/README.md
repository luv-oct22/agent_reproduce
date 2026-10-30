# kinematics_dynamics_g1/combined_rule/variant_1/q03

Host-only resolved question record:

```json
{
  "question_id": "variant_1_q03",
  "group_id": "kinematics_dynamics_g1",
  "rule": "combined_rule",
  "variant_id": "variant_1",
  "target_object_id": "object_2",
  "scene_state": {
    "objects": [
      {
        "object_id": "object_1",
        "color": "red",
        "mass_kg": 1.5,
        "radius_m": 0.08,
        "initial_position_m": [
          1.0,
          0.5,
          2.3
        ],
        "initial_velocity_m_s": [
          0.1,
          0.7,
          -0.6
        ]
      },
      {
        "object_id": "object_2",
        "color": "blue",
        "mass_kg": 1.1,
        "radius_m": 0.09,
        "initial_position_m": [
          0.9,
          -0.1,
          1.1
        ],
        "initial_velocity_m_s": [
          0.8,
          0.2,
          0.2
        ]
      },
      {
        "object_id": "object_3",
        "color": "green",
        "mass_kg": 0.9,
        "radius_m": 0.09,
        "initial_position_m": [
          -0.9,
          -0.6,
          1.9
        ],
        "initial_velocity_m_s": [
          1.0,
          0.1,
          0.5
        ]
      },
      {
        "object_id": "object_4",
        "color": "yellow",
        "mass_kg": 0.6,
        "radius_m": 0.16,
        "initial_position_m": [
          0.5,
          -0.4,
          1.9
        ],
        "initial_velocity_m_s": [
          0.9,
          0.5,
          0.7
        ]
      }
    ],
    "start_time_s": 1.9,
    "duration_s": 0.21,
    "target_object_id": "object_2"
  },
  "hidden_parameters": {
    "equation_parameters": {
      "kind": "power_velocity",
      "p": 0.8
    },
    "force_function": {
      "field_kind": "linear_space",
      "amplitude": 0.3,
      "time_scale": 4.0,
      "reference_time_s": 2.0
    }
  }
}
```
