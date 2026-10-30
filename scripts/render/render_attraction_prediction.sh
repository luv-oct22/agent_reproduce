#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
exec python -m src.simulation.attraction_scene render \
  --output-dir renders/attraction/paired_close_v1 --resolution 1920 1280 "$@"
