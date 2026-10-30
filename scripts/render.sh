#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORLD_SELECTOR=""; RULE_SELECTOR=""; VARIANT_SELECTOR=""; QUESTION_SELECTOR=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --w) WORLD_SELECTOR="${2:?--w requires a value}"; shift 2 ;;
    --r) RULE_SELECTOR="${2:?--r requires a value}"; shift 2 ;;
    --v) VARIANT_SELECTOR="${2:?--v requires a value}"; shift 2 ;;
    --q) QUESTION_SELECTOR="${2:?--q requires a value}"; shift 2 ;;
    --help|-h) echo "Usage: ./scripts/render.sh [--w WORLD|GROUP] [--r RULE] [--v VARIANT] [--q QUESTION]"; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done
matches() { [[ -z "$1" || "$2" == "$1" ]]; }
count=0
for family_dir in "$ROOT"/world_instances/*; do
  [[ -d "$family_dir" ]] || continue; family="$(basename "$family_dir")"
  if [[ -n "$WORLD_SELECTOR" && "$WORLD_SELECTOR" != "$family" && ! -d "$family_dir/$WORLD_SELECTOR" ]]; then continue; fi
  for group_dir in "$family_dir"/*; do
    [[ -d "$group_dir" ]] || continue; group="$(basename "$group_dir")"
    if [[ -n "$WORLD_SELECTOR" && "$WORLD_SELECTOR" != "$family" && "$WORLD_SELECTOR" != "$group" ]]; then continue; fi
    for rule_dir in "$group_dir"/rule_* "$group_dir"/combined_rule; do
      [[ -d "$rule_dir" ]] || continue; rule="$(basename "$rule_dir")"; matches "$RULE_SELECTOR" "$rule" || continue
      for variant_dir in "$rule_dir"/variant_*; do
        [[ -d "$variant_dir" ]] || continue; variant="$(basename "$variant_dir")"; matches "$VARIANT_SELECTOR" "$variant" || continue
        for question_dir in "$variant_dir"/q??; do
          [[ -d "$question_dir" ]] || continue; question="$(basename "$question_dir")"; matches "$QUESTION_SELECTOR" "$question" || continue
          question_file="$question_dir/question.json"; output="$ROOT/renders/$family/$group/$rule/$variant/$question"
          world_instance="$group_dir/baseline/instance.json"
          [[ -f "$world_instance" ]] || { echo "Missing baseline world: $world_instance" >&2; exit 1; }
          echo "[render] $family/$group/$rule/$variant/$question"
          (cd "$ROOT" && python -m scripts.pipeline.render_question \
            --world-instance "$world_instance" --question-file "$question_file" \
            --output-dir "$output" --device "${DEVICE:-CUDA}" \
            --samples "${SAMPLES:-96}" --resolution "${RESOLUTION_X:-1920}" "${RESOLUTION_Y:-1280}")
          count=$((count + 1))
        done
      done
    done
  done
done
[[ $count -gt 0 ]] || { echo "No matching question folders." >&2; exit 1; }
echo "Completed $count render(s)."
