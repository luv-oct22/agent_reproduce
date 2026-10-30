# kinematics_dynamics_g1/combined_rule/variant_3/q14

Host-only resolved question record:

```json
{
  "question_id": "variant_3_q14",
  "group_id": "kinematics_dynamics_g1",
  "rule": "combined_rule",
  "variant_id": "variant_3",
  "target_object_id": "object_1",
  "scene_state": {
    "objects": [
      {
        "object_id": "object_1",
        "color": "red",
        "mass_kg": 1.6,
        "radius_m": 0.1,
        "initial_position_m": [
          1.2,
          -0.5,
          1.3
        ],
        "initial_velocity_m_s": [
          -0.1,
          0.1,
          0.0
        ]
      },
      {
        "object_id": "object_2",
        "color": "blue",
        "mass_kg": 1.5,
        "radius_m": 0.12,
        "initial_position_m": [
          -0.4,
          0.3,
          1.4
        ],
        "initial_velocity_m_s": [
          0.8,
          -0.6,
          0.1
        ]
      },
      {
        "object_id": "object_3",
        "color": "green",
        "mass_kg": 1.0,
        "radius_m": 0.08,
        "initial_position_m": [
          0.2,
          -0.5,
          2.5
        ],
        "initial_velocity_m_s": [
          -0.2,
          -0.7,
          -1.1
        ]
      }
    ],
    "start_time_s": 1.4,
    "duration_s": 0.19,
    "target_object_id": "object_1"
  },
  "hidden_parameters": {
    "equation_parameters": {
      "kind": "log_velocity",
      "scale": 1.0
    },
    "force_function": {
      "field_kind": "quadratic_space",
      "amplitude": 0.4,
      "time_scale": 4.0,
      "reference_time_s": 2.0
    }
  }
}
```
