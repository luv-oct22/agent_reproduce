#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export OPENAI_MAX_RETRIES="${OPENAI_MAX_RETRIES:-5}"
export OPENAI_CONNECT_TIMEOUT="${OPENAI_CONNECT_TIMEOUT:-120}"
export OPENAI_TIMEOUT="${OPENAI_TIMEOUT:-900}"
printf 'API settings: retries=%s connect_timeout=%ss timeout=%ss\n' "$OPENAI_MAX_RETRIES" "$OPENAI_CONNECT_TIMEOUT" "$OPENAI_TIMEOUT"
exec python -m src.drag_evaluate "$@"
