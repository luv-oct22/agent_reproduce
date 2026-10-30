#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export VIDEO_SCENE="${VIDEO_SCENE:-renders/lab_1/original_distance/scene.blend}"
export VIDEO_HISTORY="${VIDEO_HISTORY:-renders/lab_1/original_distance/sim_history.json}"
export VIDEO_OUTPUT="${VIDEO_OUTPUT:-renders/lab_1/original_distance}"
bash scripts/render/render_robotics_video.sh
