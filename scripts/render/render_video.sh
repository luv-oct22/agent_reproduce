#!/bin/bash
set -e

CONFIG="${CONFIG:?Error: set CONFIG=/path/to/config.yaml}"
OUTPUT_DIR="${OUTPUT_DIR:-renders}"
VX="${VX:-5.0}"
VY="${VY:-0.0}"
VZ="${VZ:-5.0}"
FPS="${FPS:-60}"
SAMPLES="${SAMPLES:-64}"
FRAME_STEP="${FRAME_STEP:-10}"
RES_X="${RES_X:-1920}"
RES_Y="${RES_Y:-1080}"

cd "$(dirname "$0")/../.."

python -m src.simulation.render_scene \
    --config "$CONFIG" \
    --output-dir "$OUTPUT_DIR" \
    --format blender \
    --velocity "$VX" "$VY" "$VZ" \
    --fps "$FPS" \
    --samples "$SAMPLES" \
    --frame-step "$FRAME_STEP" \
    --res-x "$RES_X" \
    --res-y "$RES_Y"
