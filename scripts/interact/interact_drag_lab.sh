#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export OPENAI_MAX_RETRIES="${OPENAI_MAX_RETRIES:-5}"
export OPENAI_CONNECT_TIMEOUT="${OPENAI_CONNECT_TIMEOUT:-120}"
export OPENAI_TIMEOUT="${OPENAI_TIMEOUT:-900}"
printf 'API settings: retries=%s, connect timeout=%ss, read/write/pool timeout=%ss\n' \
  "$OPENAI_MAX_RETRIES" "$OPENAI_CONNECT_TIMEOUT" "$OPENAI_TIMEOUT"
exec python eval.py --tasks identify_drag --config configs/drag_lab.yaml \
  --mode interact --max-turns 32 --output-dir results/drag_lab "$@"
