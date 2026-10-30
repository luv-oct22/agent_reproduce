#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEVICE_NAME="${DEVICE:-CUDA}"; SAMPLES_VALUE="${SAMPLES:-96}"
RES_X="${RESOLUTION_X:-1920}"; RES_Y="${RESOLUTION_Y:-1280}"
WORLD_SELECTOR="${WORLD_SELECTOR:-}"; RULE_SELECTOR="${RULE_SELECTOR:-}"
VARIANT_SELECTOR="${VARIANT_SELECTOR:-}"; QUESTION_SELECTOR="${QUESTION_SELECTOR:-}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --w) WORLD_SELECTOR="${2:?--w requires a value}"; shift 2;;
    --r) RULE_SELECTOR="${2:?--r requires a value}"; shift 2;;
    --v) VARIANT_SELECTOR="${2:?--v requires a value}"; shift 2;;
    --q) QUESTION_SELECTOR="${2:?--q requires a value}"; shift 2;;
    --help|-h) echo "Usage: ./scripts/render_missing.sh [--w WORLD|GROUP] [--r RULE] [--v VARIANT] [--q QUESTION]"; exit 0;;
    *) echo "Unknown argument: $1" >&2; exit 2;;
  esac
done
matches(){ [[ -z "$1" || "$2" == "$1" ]]; }
rendered=0; skipped=0; failed=0
for family_dir in "$ROOT"/world_instances/*; do
  [[ -d "$family_dir" ]] || continue; family="$(basename "$family_dir")"
  [[ -z "$WORLD_SELECTOR" || "$WORLD_SELECTOR" == "$family" || -d "$family_dir/$WORLD_SELECTOR" ]] || continue
  for group_dir in "$family_dir"/*; do
    [[ -d "$group_dir" ]] || continue; group="$(basename "$group_dir")"
    [[ -z "$WORLD_SELECTOR" || "$WORLD_SELECTOR" == "$family" || "$WORLD_SELECTOR" == "$group" ]] || continue
    baseline="$group_dir/baseline/instance.json"; [[ -f "$baseline" ]] || continue
    for rule_dir in "$group_dir"/rule_* "$group_dir"/combined_rule; do
      [[ -d "$rule_dir" ]] || continue; rule="$(basename "$rule_dir")"; matches "$RULE_SELECTOR" "$rule" || continue
      for variant_dir in "$rule_dir"/variant_*; do
        [[ -d "$variant_dir" ]] || continue; variant="$(basename "$variant_dir")"; matches "$VARIANT_SELECTOR" "$variant" || continue
        for question_dir in "$variant_dir"/q??; do
          [[ -d "$question_dir" ]] || continue; question="$(basename "$question_dir")"; matches "$QUESTION_SELECTOR" "$question" || continue
          output="$ROOT/renders/$family/$group/$rule/$variant/$question"; complete=true
          [[ -f "$output/scene.json" ]] || complete=false
          for label in A B C D; do [[ -f "$output/choice_${label}.png" ]] || complete=false; done
          if [[ "$complete" == true ]]; then skipped=$((skipped+1)); continue; fi
          echo "[render-missing] $family/$group/$rule/$variant/$question"
          if (cd "$ROOT" && python -m scripts.pipeline.render_question --world-instance "$baseline" --question-file "$question_dir/question.json" --output-dir "$output" --device "$DEVICE_NAME" --samples "$SAMPLES_VALUE" --resolution "$RES_X" "$RES_Y"); then
            rendered=$((rendered+1))
          else
            failed=$((failed+1)); echo "[render-missing] failed: $family/$group/$rule/$variant/$question" >&2
          fi
        done
      done
    done
  done
done
echo "Completed $rendered missing render(s); skipped $skipped complete set(s); failed $failed."
