# kinematics_dynamics_g1/rule_2/variant_2/q01

Host-only resolved question record:

```json
{
  "question_id": "variant_2_q01",
  "group_id": "kinematics_dynamics_g1",
  "rule": "rule_2",
  "variant_id": "variant_2",
  "target_object_id": "object_1",
  "scene_state": {
    "objects": [
      {
        "object_id": "object_1",
        "color": "red",
        "mass_kg": 0.4,
        "radius_m": 0.12,
        "initial_position_m": [
          -1.0,
          0.6,
          2.6
        ],
        "initial_velocity_m_s": [
          -0.5,
          -0.1,
          -0.5
        ]
      },
      {
        "object_id": "object_2",
        "color": "blue",
        "mass_kg": 0.7,
        "radius_m": 0.11,
        "initial_position_m": [
          0.1,
          -0.0,
          1.0
        ],
        "initial_velocity_m_s": [
          -0.9,
          -0.4,
          -0.9
        ]
      }
    ],
    "start_time_s": 1.3,
    "duration_s": 0.12,
    "target_object_id": "object_1"
  },
  "hidden_parameters": {
    "force_function": {
      "field_kind": "linear_time",
      "amplitude": 0.2,
      "time_scale": 4.0,
      "reference_time_s": 2.0
    }
  }
}
```
