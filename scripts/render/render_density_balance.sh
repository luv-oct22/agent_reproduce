#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
scene_path="${1:-renders/lab_2/density_balance/questions/q001_blue_orange/scene.json}"
if [[ $# -gt 0 ]]; then shift; fi
blender_bin="${BLENDER_BIN:-$PWD/.tools/blender-3.6.23-linux-x64/blender}"
exec "$blender_bin" --background --python-exit-code 1 \
  --python src/simulation/blender_balance.py -- \
  --manifest "$scene_path" --device "${RENDER_DEVICE:-CUDA}" "$@"
