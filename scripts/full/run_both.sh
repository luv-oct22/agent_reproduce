#!/bin/bash
set -e

MODEL="${MODEL:-gpt-4o}"
TASKS="${TASKS:-shoot_ball}"
MAX_TURNS="${MAX_TURNS:-10}"
QUESTIONS="${QUESTIONS:?Error: set QUESTIONS=/path/to/questions.json}"
OUTPUT_DIR="${OUTPUT_DIR:-results}"

cd "$(dirname "$0")/../.."

python eval.py \
    --tasks $TASKS \
    --model "$MODEL" \
    --max-turns "$MAX_TURNS" \
    --mode both \
    --questions "$QUESTIONS" \
    --output-dir "$OUTPUT_DIR"
