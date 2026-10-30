# Global interaction, rendering, and evaluation commands

The root launchers discover the canonical
`world_instances/<family>/<group>/<rule>/<variant>/<question>` tree.

```bash
./interaction.sh --w central_force_dynamics --r rule_1 --v variant_1 --q q01
./interaction.sh --w central_force_dynamics --r rule_1 --v variant_1
./interaction.sh --w central_force_dynamics

./eval.sh --w central_force_dynamics --r rule_1 --v variant_1 --q q01
./eval.sh --w central_force_dynamics --r rule_1
./eval.sh

./scripts/render.sh --w central_force_dynamics --r rule_1 --v variant_1 --q q01
./full.sh --w central_force_dynamics --r rule_1 --v variant_1 --q q01
```

The four selectors are `--w` (family or group), `--r` (rule), `--v` (variant),
and `--q` (question). Leaving a selector unset expands it to all entries at
that level. `eval.sh` uses the matching interaction record and skips questions
that have not been interacted with yet. Rendering and evaluation scripts live
under `scripts/`; each question folder contains a public `question.json` index
and a host-only `instance.json` with the resolved scene, equation parameters,
intrinsic values, and matched baseline constants.
