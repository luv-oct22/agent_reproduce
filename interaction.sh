#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
WORLD_SELECTOR=""; RULE_SELECTOR=""; VARIANT_SELECTOR=""; QUESTION_SELECTOR=""
MODEL="${MODEL:-gpt-5.6}"; AGENT_CONFIG=""; HARNESS_CONFIG=""
TEMPERATURE=""; SEED=""; MAX_COMPLETION_TOKENS=""; SKIP_COMPLETED=0; RESUME_PREFIX=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --w) WORLD_SELECTOR="${2:?--w requires a value}"; shift 2 ;;
    --r) RULE_SELECTOR="${2:?--r requires a value}"; shift 2 ;;
    --v) VARIANT_SELECTOR="${2:?--v requires a value}"; shift 2 ;;
    --q) QUESTION_SELECTOR="${2:?--q requires a value}"; shift 2 ;;
    --model) MODEL="${2:?--model requires a value}"; shift 2 ;;
    --agent-config) AGENT_CONFIG="${2:?--agent-config requires a value}"; shift 2 ;;
    --harness-config) HARNESS_CONFIG="${2:?--harness-config requires a value}"; shift 2 ;;
    --temperature) TEMPERATURE="${2:?--temperature requires a value}"; shift 2 ;;
    --seed) SEED="${2:?--seed requires a value}"; shift 2 ;;
    --max-completion-tokens) MAX_COMPLETION_TOKENS="${2:?--max-completion-tokens requires a value}"; shift 2 ;;
    --skip-completed) SKIP_COMPLETED=1; shift ;;
    --resume) SKIP_COMPLETED=1; RESUME_PREFIX="${2:?--resume requires a run-id prefix, e.g. qwen3.8-max_20261016}"; shift 2 ;;
    --help|-h) echo "Usage: ./interaction.sh [selectors] [--model MODEL] [--temperature T] [--seed N] [--max-completion-tokens N] [--skip-completed | --resume RUN_ID_PREFIX]"; exit 0 ;;
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
# A question counts as completed when an earlier run directory matching PREFIX*
# saved a record where the agent called finish or used every turn (skipped turns
# count as used). A run that crashed mid-question is not complete.
# --skip-completed matches every run of this model; --resume PREFIX matches only
# run ids starting with PREFIX (e.g. qwen3.8-max_20261016).
is_completed() {
  local question_root="$1" prefix="$2" run_dir
  for run_dir in "$question_root"/interaction/"$prefix"*/; do
    [[ -f "$run_dir/interaction.json" ]] || continue
    python - "$run_dir" <<'PY' && return 0
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
  return 1
}
EXTRA_ARGS=(--model "$MODEL")
[[ -z "$AGENT_CONFIG" ]] || EXTRA_ARGS+=(--agent-config "$AGENT_CONFIG")
[[ -z "$HARNESS_CONFIG" ]] || EXTRA_ARGS+=(--harness-config "$HARNESS_CONFIG")
[[ -z "$TEMPERATURE" ]] || EXTRA_ARGS+=(--temperature "$TEMPERATURE")
[[ -z "$SEED" ]] || EXTRA_ARGS+=(--seed "$SEED")
[[ -z "$MAX_COMPLETION_TOKENS" ]] || EXTRA_ARGS+=(--max-completion-tokens "$MAX_COMPLETION_TOKENS")
SAFE_MODEL="$(printf '%s' "$MODEL" | tr -c 'A-Za-z0-9_.-' '_')"
RUN_ID="${SAFE_MODEL}_$(date -u +%Y%m%d_%H%M%S_%N)"
count=0; skipped=0; failed=()
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
          echo "[interaction] $family/$group/$rule/$variant/$question"
          output="$ROOT/results/$family/$group/$rule/$variant/$question/interaction/$RUN_ID"
          world_instance="$group_dir/baseline/instance.json"
          [[ -f "$world_instance" ]] || { echo "Missing baseline world: $world_instance" >&2; exit 1; }
          if [[ "$SKIP_COMPLETED" == 1 ]] && is_completed "$ROOT/results/$family/$group/$rule/$variant/$question" "${RESUME_PREFIX:-${SAFE_MODEL}_}"; then
            echo "[interaction] SKIP (already completed): $family/$group/$rule/$variant/$question"
            skipped=$((skipped + 1)); continue
          fi
          if (cd "$question_dir" && "$ROOT/scripts/pipeline/interact_question.sh" \
            --question-file "$question_dir/question.json" --world-instance "$world_instance" \
            --output-dir "$output" "${EXTRA_ARGS[@]}"); then
            count=$((count + 1))
          else
            echo "[interaction] FAILED (exit $?): $family/$group/$rule/$variant/$question" >&2
            failed+=("$family/$group/$rule/$variant/$question")
          fi
        done
      done
    done
  done
done
if [[ $count -eq 0 && $skipped -eq 0 && ${#failed[@]} -eq 0 ]]; then
  echo "No matching question folders." >&2; exit 1
fi
echo "Completed $count interaction(s), skipped $skipped already-completed, failed ${#failed[@]}."
if [[ ${#failed[@]} -gt 0 ]]; then
  echo "Failed questions (rerun the same command with --skip-completed, or --resume <run-id prefix>, to retry only these):" >&2
  printf '  %s\n' "${failed[@]}" >&2
  exit 1
fi
