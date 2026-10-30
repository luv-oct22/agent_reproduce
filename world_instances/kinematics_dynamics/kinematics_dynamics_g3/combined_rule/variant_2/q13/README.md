# kinematics_dynamics_g1/combined_rule/variant_2/q13

Host-only resolved question record:

```json
{
  "question_id": "variant_2_q13",
  "group_id": "kinematics_dynamics_g1",
  "rule": "combined_rule",
  "variant_id": "variant_2",
  "target_object_id": "object_2",
  "scene_state": {
    "objects": [
      {
        "object_id": "object_1",
        "color": "red",
        "mass_kg": 0.3,
        "radius_m": 0.13,
        "initial_position_m": [
          -0.4,
          0.1,
          1.9
        ],
        "initial_velocity_m_s": [
          -0.8,
          0.9,
          -0.3
        ]
      },
      {
        "object_id": "object_2",
        "color": "blue",
        "mass_kg": 0.3,
        "radius_m": 0.12,
        "initial_position_m": [
          -0.4,
          -0.2,
          2.6
        ],
        "initial_velocity_m_s": [
          -0.7,
          -0.0,
          -0.1
        ]
      }
    ],
    "start_time_s": 1.5,
    "duration_s": 0.11,
    "target_object_id": "object_2"
  },
  "hidden_parameters": {
    "equation_parameters": {
      "kind": "power_position",
      "p": 1.3
    },
    "force_function": {
      "field_kind": "linear_time",
      "amplitude": 0.2,
      "time_scale": 4.0,
      "reference_time_s": 2.0
    }
  }
}
```
