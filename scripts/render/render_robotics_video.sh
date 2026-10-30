#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."

scene="${VIDEO_SCENE:-renders/robotics_lab/scene.blend}"
history="${VIDEO_HISTORY:-renders/robotics_lab/sim_history.json}"
output="${VIDEO_OUTPUT:-renders/robotics_lab_video}"
fps="${VIDEO_FPS:-24}"
samples="${VIDEO_SAMPLES:-24}"
render_bin="${BLENDER_BIN:-.tools/blender-3.6.23-linux-x64/blender}"
if [[ ! -x "$render_bin" ]]; then render_bin=blender; fi
if [[ ! -f "$scene" || ! -f "$history" ]]; then
    echo 'Create the saved lab first: bash scripts/render/render_robotics_lab.sh' >&2
    exit 1
fi
frame_count=$(python -c 'import json, math, sys; d=json.load(open(sys.argv[1])); print(math.ceil(d.get("animation", {}).get("duration", d["history"][-1]["time"]) * int(sys.argv[2])) + 1)' "$history" "$fps")
common=(--history "$history" --output-dir "$output" --fps "$fps" --samples "$samples")
encoding=(--video-name "${VIDEO_NAME:-simulation.mp4}")
if [[ -n "${VIDEO_DURATION:-}" ]]; then encoding+=(--duration "$VIDEO_DURATION"); fi
for ((start=0; start<frame_count; start+=8)); do
    "$render_bin" --background "$scene" --python-exit-code 1 \
        --python src/simulation/render_saved_video.py -- \
        --mode frames "${common[@]}" --start "$start" --end "$((start+8))"
done
"$render_bin" --background "$scene" --python-exit-code 1 \
    --python src/simulation/render_saved_video.py -- --mode encode "${common[@]}" "${encoding[@]}"
