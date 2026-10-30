#!/bin/bash
set -e

MODEL="${MODEL:-gpt-4o}"
TASKS="${TASKS:-shoot_ball}"
MAX_TURNS="${MAX_TURNS:-10}"
CONFIG="${CONFIG:-configs/shoot_ball.yaml}"
QUESTIONS="${QUESTIONS:?Error: set QUESTIONS=/path/to/questions.json}"
OUTPUT_DIR="${OUTPUT_DIR:-results}"
RENDER_EVERY="${RENDER_EVERY:-100}"

cd "$(dirname "$0")/../.."

echo "============================================"
echo "  Full Pipeline: render + interact + eval"
echo "============================================"

echo ""
echo "[1/3] Rendering simulation snapshots..."
python -m src.simulation.render_scene \
    --config "$CONFIG" \
    --output-dir "$OUTPUT_DIR/snapshots" \
    --every "$RENDER_EVERY"

echo ""
echo "[2/3] Running interaction..."
python eval.py \
    --tasks $TASKS \
    --model "$MODEL" \
    --max-turns "$MAX_TURNS" \
    --mode interact \
    --config "$CONFIG" \
    --output-dir "$OUTPUT_DIR"

echo ""
echo "[3/3] Running evaluation..."
python eval.py \
    --tasks $TASKS \
    --model "$MODEL" \
    --mode evaluate \
    --questions "$QUESTIONS" \
    --output-dir "$OUTPUT_DIR"

echo ""
echo "Done. Results saved to $OUTPUT_DIR"
