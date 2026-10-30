#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export OPENAI_MAX_RETRIES="${OPENAI_MAX_RETRIES:-5}"
export OPENAI_CONNECT_TIMEOUT="${OPENAI_CONNECT_TIMEOUT:-120}"
export OPENAI_TIMEOUT="${OPENAI_TIMEOUT:-900}"
exec python eval.py --tasks characterize_objects --config configs/object_attributes_attraction_g1.yaml \
  --mode interact --max-turns 8 --output-dir results/object_attributes "$@"
