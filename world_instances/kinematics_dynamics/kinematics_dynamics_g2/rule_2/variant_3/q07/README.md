# kinematics_dynamics_g1/rule_2/variant_3/q07

Host-only resolved question record:

```json
{
  "question_id": "variant_3_q07",
  "group_id": "kinematics_dynamics_g1",
  "rule": "rule_2",
  "variant_id": "variant_3",
  "target_object_id": "object_2",
  "scene_state": {
    "objects": [
      {
        "object_id": "object_1",
        "color": "red",
        "mass_kg": 0.3,
        "radius_m": 0.09,
        "initial_position_m": [
          -0.3,
          -0.5,
          0.9
        ],
        "initial_velocity_m_s": [
          0.2,
          0.8,
          1.0
        ]
      },
      {
        "object_id": "object_2",
        "color": "blue",
        "mass_kg": 0.7,
        "radius_m": 0.09,
        "initial_position_m": [
          0.7,
          -0.7,
          1.8
        ],
        "initial_velocity_m_s": [
          -0.7,
          -0.1,
          0.3
        ]
      }
    ],
    "start_time_s": 2.2,
    "duration_s": 0.11,
    "target_object_id": "object_2"
  },
  "hidden_parameters": {
    "force_function": {
      "field_kind": "quadratic_space",
      "amplitude": 0.4,
      "time_scale": 4.0,
      "reference_time_s": 2.0
    }
  }
}
```
