#!/usr/bin/env bash
# Expanded pilot: one model, every regime x condition cell, ~10 new questions per cell and arm.
# Usage: MODEL=gpt-6.1-sol LIMIT=10 ./scripts/pilot_law_contrastive_all_cells.sh > logs/pilot_all_cells.log 2>&1 &
# Ledgers resume, so questions answered by the first pilot (g1/rule_1) are skipped.
set -uo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=.
MODEL="${MODEL:-gpt-6.1-sol}"; LIMIT="${LIMIT:-10}"
PY="${PY:-python}"
for g in g1 g2 g3; do
  for r in rule_1 rule_2 combined_rule; do
    echo "=== $g $r $(date +%H:%M:%S)"
    "$PY" -m src.law_contrastive --groups="$g" --rules="$r" exam --model "$MODEL" --limit "$LIMIT"
  done
done
"$PY" -m src.law_contrastive analyze --models "$MODEL"
echo "=== done $(date +%H:%M:%S)"
