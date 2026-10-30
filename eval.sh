#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
WORLD_SELECTOR=""; RULE_SELECTOR=""; VARIANT_SELECTOR=""; QUESTION_SELECTOR=""
MODEL="${MODEL:-gpt-5.6}"
TEMPERATURE=""; SEED=""; MAX_COMPLETION_TOKENS=""; SKIP_EVALUATED=0
# Interaction records are matched by model. INTERACTION_MODEL=<name> scores another
# model's interactions with $MODEL (default: same model as --model).
INTERACTION_MODEL="${INTERACTION_MODEL:-}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --w) WORLD_SELECTOR="${2:?--w requires a value}"; shift 2 ;;
    --r) RULE_SELECTOR="${2:?--r requires a value}"; shift 2 ;;
    --v) VARIANT_SELECTOR="${2:?--v requires a value}"; shift 2 ;;
    --q) QUESTION_SELECTOR="${2:?--q requires a value}"; shift 2 ;;
    --model) MODEL="${2:?--model requires a value}"; shift 2 ;;
    --temperature) TEMPERATURE="${2:?--temperature requires a value}"; shift 2 ;;
    --seed) SEED="${2:?--seed requires a value}"; shift 2 ;;
    --max-completion-tokens) MAX_COMPLETION_TOKENS="${2:?--max-completion-tokens requires a value}"; shift 2 ;;
    --skip-evaluated) SKIP_EVALUATED=1; shift ;;
    --help|-h) echo "Usage: ./eval.sh [selectors] [--model MODEL] [--temperature T] [--seed N] [--max-completion-tokens N] [--skip-evaluated]"; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done
matches() {
  [[ -z "$1" ]] && return 0
  local wanted="${2#q011}"; [[ "$2" == q011 ]] && wanted=q11
  local item
  IFS=',' read -ra items <<< "$1"
  for item in "${items[@]}"; do
    [[ "$item" == "$2" || "$item" == "$wanted" ]] && return 0
  done
  return 1
}
EVAL_ARGS=()
[[ -z "$TEMPERATURE" ]] || EVAL_ARGS+=(--temperature "$TEMPERATURE")
[[ -z "$SEED" ]] || EVAL_ARGS+=(--seed "$SEED")
[[ -z "$MAX_COMPLETION_TOKENS" ]] || EVAL_ARGS+=(--max-completion-tokens "$MAX_COMPLETION_TOKENS")
count=0; skipped=0; already=0; failed=()
SAFE_MODEL="$(printf '%s' "$MODEL" | tr -c 'A-Za-z0-9_.-' '_')"
SAFE_INTERACTION_MODEL="$(printf '%s' "${INTERACTION_MODEL:-$MODEL}" | tr -c 'A-Za-z0-9_.-' '_')"
# Latest COMPLETED interaction record of the interaction model for one question
# (agent called finish, or used every turn; skipped turns count as used).
latest_completed_record() {
  local root="$1" prefix="$2" run_dir best=""
  for run_dir in "$root"/"$prefix"_*/; do
    [[ -f "$run_dir/interaction.json" ]] || continue
    python - "$run_dir" <<'PY' && best="${run_dir%/}/interaction.json"
import json, sys
from pathlib import Path
d = Path(sys.argv[1])
rec = json.loads((d / 'interaction.json').read_text())
try:
    max_turns = int(json.loads((d / 'model_parameters.json').read_text()).get('max_turns') or 8)
except (OSError, ValueError):
    max_turns = 8
turns = sum(m.get('role') == 'assistant' for m in rec.get('messages', [])) + len(rec.get('skipped_turns', []))
sys.exit(0 if rec.get('finished') or turns >= max_turns else 1)
PY
  done
  [[ -n "$best" ]] && printf '%s' "$best"
}
already_evaluated() {
  local root="$1" prefix="$2" d
  for d in "$root"/"$prefix"_*/; do [[ -f "$d/summary.json" ]] && return 0; done
  return 1
}
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
          interaction_root="$ROOT/results/$family/$group/$rule/$variant/$question/interaction"
          record=""
          [[ -d "$interaction_root" ]] && record="$(latest_completed_record "$interaction_root" "$SAFE_INTERACTION_MODEL")"
          if [[ -z "$record" ]]; then echo "[evaluation] skip $family/$group/$rule/$variant/$question (no completed $SAFE_INTERACTION_MODEL interaction record)" >&2; skipped=$((skipped + 1)); continue; fi
          if [[ "$SKIP_EVALUATED" == 1 ]] && already_evaluated "$ROOT/results/$family/$group/$rule/$variant/$question/evaluation" "$SAFE_MODEL"; then
            echo "[evaluation] SKIP (already evaluated): $family/$group/$rule/$variant/$question"; already=$((already + 1)); continue
          fi
          echo "[evaluation] $family/$group/$rule/$variant/$question"
          eval_id="${SAFE_MODEL}_$(date -u +%Y%m%d_%H%M%S_%N)"
          output_dir="$ROOT/results/$family/$group/$rule/$variant/$question/evaluation/$eval_id"
          # The question schema names its family (e.g. "attraction"); the folder is the world family.
          qfamily="$(grep -oE '"family": *"[A-Za-z_]+"' "$question_dir/question.json" | head -1 | sed -E 's/.*"([A-Za-z_]+)"$/\1/')"
          ok=1
          if [[ "$family" == "attraction" || "$qfamily" == "attraction" ]]; then
            render_dir="$ROOT/renders/$family/$group/$rule/$variant/$question"
            if [[ ! -f "$render_dir/scene.json" ]]; then
              echo "[evaluation] skip $family/$group/$rule/$variant/$question (missing rendered scene; run render.sh first)" >&2
              skipped=$((skipped + 1)); continue
            fi
            (cd "$ROOT" && python -m scripts.eval.evaluate_attraction_visual \
              --model "$MODEL" --interaction-record "$record" \
              --render-dir "$render_dir" --output-dir "$output_dir" "${EVAL_ARGS[@]}") || ok=0
          else
            (cd "$question_dir" && INTERACTION_RECORD="$record" "$ROOT/scripts/pipeline/evaluate_question.sh" \
              --question-file "$question_dir/question.json" --output-dir "$output_dir") || ok=0
          fi
          if [[ $ok == 1 ]]; then count=$((count + 1)); else
            echo "[evaluation] FAILED: $family/$group/$rule/$variant/$question" >&2
            failed+=("$family/$group/$rule/$variant/$question")
          fi
        done
      done
    done
  done
done
if [[ $count -eq 0 && $already -eq 0 && ${#failed[@]} -eq 0 ]]; then echo "No matching interaction records were found." >&2; exit 1; fi
echo "Completed $count evaluation(s); skipped $skipped (no record), $already already evaluated, failed ${#failed[@]}."
if [[ ${#failed[@]} -gt 0 ]]; then
  echo "Failed questions (rerun the same command with --skip-evaluated to retry only these):" >&2
  printf '  %s\n' "${failed[@]}" >&2; exit 1
fi
