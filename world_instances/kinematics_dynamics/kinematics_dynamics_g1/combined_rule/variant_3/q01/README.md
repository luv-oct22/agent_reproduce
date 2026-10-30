# kinematics_dynamics_g1/combined_rule/variant_3/q01

Host-only resolved question record:

```json
{
  "question_id": "variant_3_q01",
  "group_id": "kinematics_dynamics_g1",
  "rule": "combined_rule",
  "variant_id": "variant_3",
  "target_object_id": "object_1",
  "scene_state": {
    "objects": [
      {
        "object_id": "object_1",
        "color": "red",
        "mass_kg": 2.0,
        "radius_m": 0.12,
        "initial_position_m": [
          1.0,
          -0.3,
          1.1
        ],
        "initial_velocity_m_s": [
          0.8,
          0.9,
          -0.4
        ]
      },
      {
        "object_id": "object_2",
        "color": "blue",
        "mass_kg": 0.4,
        "radius_m": 0.11,
        "initial_position_m": [
          0.4,
          -0.1,
          2.6
        ],
        "initial_velocity_m_s": [
          0.3,
          -1.0,
          0.1
        ]
      }
    ],
    "start_time_s": 1.1,
    "duration_s": 0.12,
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
