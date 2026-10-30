# kinematics_dynamics_g1/combined_rule/variant_3

Shared constants:

```json
{
  "acceleration_m_s2": [
    1.2,
    -0.7,
    0.4
  ],
  "time_scale_s": 1.0,
  "clock_range_s": [
    0.0,
    30.0
  ],
  "minimum_separation_m": 0.05
}
```

Hidden parameters used by this variant (host-only):

```json
{
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
```

The same q01–q15 initial scenes are used across the three rule branches.
