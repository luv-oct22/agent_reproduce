#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
exec python -m src.simulation.balance_batch render \
  --output-dir renders/lab_4/bounce_prediction "$@"
