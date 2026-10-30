#!/usr/bin/env bash
set -euo pipefail

QUESTION_FILE=""
WORLD_INSTANCE=""
AGENT_CONFIG=""
HARNESS_CONFIG=""
OUTPUT_DIR=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --question-file) QUESTION_FILE="$2"; shift 2 ;;
    --world-instance) WORLD_INSTANCE="$2"; shift 2 ;;
    --agent-config) AGENT_CONFIG="$2"; shift 2 ;;
    --harness-config) HARNESS_CONFIG="$2"; shift 2 ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    *) break ;;
  esac
done
: "${QUESTION_FILE:?--question-file is required}"
: "${OUTPUT_DIR:?--output-dir is required}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export QUESTION_FILE WORLD_INSTANCE AGENT_CONFIG HARNESS_CONFIG OUTPUT_DIR
if [[ -n "${INTERACTION_RUNNER:-}" ]]; then
  exec bash "$INTERACTION_RUNNER" --question-file "$QUESTION_FILE" --world-instance "$WORLD_INSTANCE" \
    --agent-config "$AGENT_CONFIG" --harness-config "$HARNESS_CONFIG" \
    --output-dir "$OUTPUT_DIR" "$@"
fi
cd "$ROOT"
exec python -m scripts.pipeline.run_interaction \
  --question-file "$QUESTION_FILE" --world-instance "$WORLD_INSTANCE" \
  --agent-config "$AGENT_CONFIG" --harness-config "$HARNESS_CONFIG" \
  --output-dir "$OUTPUT_DIR" "$@"
