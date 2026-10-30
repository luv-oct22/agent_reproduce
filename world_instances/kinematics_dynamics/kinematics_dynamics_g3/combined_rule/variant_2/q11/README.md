# kinematics_dynamics_g1/combined_rule/variant_2/q11

Host-only resolved question record:

```json
{
  "question_id": "variant_2_q11",
  "group_id": "kinematics_dynamics_g1",
  "rule": "combined_rule",
  "variant_id": "variant_2",
  "target_object_id": "object_1",
  "scene_state": {
    "objects": [
      {
        "object_id": "object_1",
        "color": "red",
        "mass_kg": 1.7,
        "radius_m": 0.13,
        "initial_position_m": [
          -0.1,
          0.4,
          2.7
        ],
        "initial_velocity_m_s": [
          0.6,
          -0.6,
          -0.1
        ]
      },
      {
        "object_id": "object_2",
        "color": "blue",
        "mass_kg": 1.7,
        "radius_m": 0.15,
        "initial_position_m": [
          -0.4,
          0.5,
          1.4
        ],
        "initial_velocity_m_s": [
          1.0,
          0.7,
          -0.6
        ]
      },
      {
        "object_id": "object_3",
        "color": "green",
        "mass_kg": 0.7,
        "radius_m": 0.12,
        "initial_position_m": [
          -1.1,
          0.6,
          2.6
        ],
        "initial_velocity_m_s": [
          0.7,
          -0.8,
          -0.0
        ]
      }
    ],
    "start_time_s": 4.0,
    "duration_s": 0.26,
    "target_object_id": "object_1"
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
