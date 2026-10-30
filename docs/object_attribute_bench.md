# Intrinsic object-attribute baseline

This is a separate experiment stage for measuring properties belonging to one
object. It does not expose force, acceleration, distance dependence, or the
active world equation.

| Tool | Returned property | Cost |
|---|---|---:|
| `inspect_object` | Appearance and available intrinsic instruments | 0 |
| `measure_mass` | Inertial mass, kg | 1 |
| `measure_volume` | Geometric volume, m³ | 1 |
| `measure_geometry` | Sphere radius and diameter, m | 1 |
| `measure_density` | Mass divided by volume, kg/m³ | 1 |
| `measure_inertia` | Solid-sphere centre-axis moment, kg·m² | 1 |

The default budget is 12 measurement units and eight turns. Readings are
quantized, range-checked, and marked when saturated. Invalid requests and
exhausted budgets do not change state or spend units.

These tools deliberately exclude `measure_force`, `track_motion`, and
`apply_impulse`. Those belong to world-law experiments. A force depends on both
objects, their separation, and the world law, so it is not intrinsic to one
object alone.

Run the baseline with:

```bash
bash scripts/interact/interact_object_attributes.sh \
  --model YOUR_MODEL \
  --config configs/object_attributes_p2.yaml \
  --output-dir results/object_attributes/p2
```

Use `configs/object_attributes_p3.yaml` for the matched p=3 world. The catalog
and public prompt are identical across both worlds. The current pair has the
same object properties in both worlds, so this stage measures the same values;
only the hidden attraction law differs.

Private records contain the complete world and measurement journal. The model
conversation contains only public tool requests and results.
