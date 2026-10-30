# kinematics_dynamics_g1/combined_rule/variant_1/q14

Host-only resolved question record:

```json
{
  "question_id": "variant_1_q14",
  "group_id": "kinematics_dynamics_g1",
  "rule": "combined_rule",
  "variant_id": "variant_1",
  "target_object_id": "object_3",
  "scene_state": {
    "objects": [
      {
        "object_id": "object_1",
        "color": "red",
        "mass_kg": 0.5,
        "radius_m": 0.12,
        "initial_position_m": [
          0.4,
          0.1,
          1.6
        ],
        "initial_velocity_m_s": [
          -0.1,
          -0.3,
          -1.1
        ]
      },
      {
        "object_id": "object_2",
        "color": "blue",
        "mass_kg": 0.4,
        "radius_m": 0.1,
        "initial_position_m": [
          -0.7,
          -0.5,
          1.9
        ],
        "initial_velocity_m_s": [
          -0.2,
          -0.9,
          0.4
        ]
      },
      {
        "object_id": "object_3",
        "color": "green",
        "mass_kg": 1.2,
        "radius_m": 0.14,
        "initial_position_m": [
          -1.0,
          -0.6,
          2.5
        ],
        "initial_velocity_m_s": [
          -0.4,
          -0.8,
          0.2
        ]
      }
    ],
    "start_time_s": 3.6,
    "duration_s": 0.16,
    "target_object_id": "object_3"
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
