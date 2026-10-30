#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
exec python -m src.simulation.balance_batch render --output-dir renders/lab_5/drag_prediction --resolution 1920 1280 "$@"
