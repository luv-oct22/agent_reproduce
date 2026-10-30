#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."

# Additional arguments can override settings, e.g. --step 260 or --samples 256.
python -m src.simulation.render_scene \
    --config configs/robotics_lab.yaml \
    --format blender --still --save-blend \
    --samples 64 --res-x 1920 --res-y 1280 \
    --output-dir renders/robotics_lab "$@"
