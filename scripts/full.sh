#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"$ROOT/scripts/interaction.sh" "$@"
"$ROOT/scripts/eval.sh" "$@"
