#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
python scripts/assets/fetch_lab_assets.py --verify
python -m src.simulation.render_scene \
    --config configs/robotics_lab_panda.yaml --format blender --still --save-blend \
    --output-dir renders/lab_1/original_distance --samples 64 --res-x 1920 --res-y 1280 "$@"
