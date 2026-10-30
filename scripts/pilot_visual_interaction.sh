#!/usr/bin/env bash
# Visual-interaction pilot: episodes, then the frozen exam under every evidence arm, then analysis.
# Usage: MODEL=gpt-6.1-sol MODE=frames_predict REGIMES=g1 RULES="rule_1 rule_2" EPISODES=6 \
#          ./scripts/pilot_visual_interaction.sh > logs/pilot_visual_interaction.log 2>&1 &
# Every stage resumes from its ledger, so rerunning continues where it stopped.
set -uo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=.
PY="${PY:-python}"; MODEL="${MODEL:-gpt-6.1-sol}"; MODE="${MODE:-frames_predict}"
REGIMES="${REGIMES:-g1}"; RULES="${RULES:-rule_1 rule_2}"; EPISODES="${EPISODES:-0}"
for g in $REGIMES; do
  for r in $RULES; do
    echo "=== episodes $g $r $(date +%H:%M:%S)"
    "$PY" -m src.visual_interaction --groups="$g" --rules="$r" episodes --model "$MODEL" --mode "$MODE" --limit "$EPISODES"
    echo "=== exam $g $r $(date +%H:%M:%S)"
    "$PY" -m src.visual_interaction --groups="$g" --rules="$r" exam --model "$MODEL" --mode "$MODE"
  done
done
"$PY" -m src.visual_interaction analyze --models "$MODEL" --modes "$MODE"
echo "=== done $(date +%H:%M:%S)"
