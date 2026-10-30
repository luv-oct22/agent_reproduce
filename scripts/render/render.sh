#!/bin/bash
set -e

CONFIG="${CONFIG:?Error: set CONFIG=/path/to/config.yaml}"
OUTPUT_DIR="${OUTPUT_DIR:-renders}"
STEP="${STEP:-500}"
TRAIL="${TRAIL:-50}"
VX="${VX:-5.0}"
VY="${VY:-0.0}"
VZ="${VZ:-5.0}"

cd "$(dirname "$0")/../.."

python -m src.simulation.render_scene \
    --config "$CONFIG" \
    --output-dir "$OUTPUT_DIR" \
    --step "$STEP" \
    --trail "$TRAIL" \
    --velocity "$VX" "$VY" "$VZ"
