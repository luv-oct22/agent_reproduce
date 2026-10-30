#!/bin/bash
set -e

MODEL="${MODEL:-gpt-4o}"
TASKS="${TASKS:-shoot_ball}"
QUESTIONS="${QUESTIONS:?Error: set QUESTIONS=/path/to/questions.json}"
RECORD="${RECORD:-}"
OUTPUT_DIR="${OUTPUT_DIR:-results}"
NO_HISTORY="${NO_HISTORY:-false}"

cd "$(dirname "$0")/../.."

ARGS=(
    --tasks $TASKS
    --model "$MODEL"
    --mode evaluate
    --questions "$QUESTIONS"
    --output-dir "$OUTPUT_DIR"
)

if [ -n "$RECORD" ]; then
    ARGS+=(--record "$RECORD")
fi

if [ "$NO_HISTORY" = "true" ]; then
    ARGS+=(--no-history)
fi

python eval.py "${ARGS[@]}"
