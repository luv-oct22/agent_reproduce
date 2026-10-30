#!/usr/bin/env bash
set -euo pipefail

QUESTION_FILE=""
WORLD_INSTANCE=""
INTERACTION_RECORD=""
AGENT_CONFIG=""
HARNESS_CONFIG=""
RENDERER_CONFIG=""
OUTPUT_DIR=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --question-file) QUESTION_FILE="$2"; shift 2 ;;
    --world-instance) WORLD_INSTANCE="$2"; shift 2 ;;
    --interaction-record) INTERACTION_RECORD="$2"; shift 2 ;;
    --agent-config) AGENT_CONFIG="$2"; shift 2 ;;
    --harness-config) HARNESS_CONFIG="$2"; shift 2 ;;
    --renderer-config) RENDERER_CONFIG="$2"; shift 2 ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    *) break ;;
  esac
done
: "${QUESTION_FILE:?--question-file is required}"
: "${INTERACTION_RECORD:?--interaction-record is required}"
: "${OUTPUT_DIR:?--output-dir is required}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUNNER="${EVALUATION_RUNNER:-$ROOT/scripts/eval/evaluate.sh}"
export QUESTION_FILE WORLD_INSTANCE INTERACTION_RECORD AGENT_CONFIG HARNESS_CONFIG RENDERER_CONFIG OUTPUT_DIR
exec bash "$RUNNER" --question-file "$QUESTION_FILE" --world-instance "$WORLD_INSTANCE" \
  --interaction-record "$INTERACTION_RECORD" --agent-config "$AGENT_CONFIG" \
  --harness-config "$HARNESS_CONFIG" --renderer-config "$RENDERER_CONFIG" \
  --output-dir "$OUTPUT_DIR" "$@"
