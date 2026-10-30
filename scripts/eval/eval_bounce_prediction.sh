#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
exec python -m src.bounce_evaluate "$@"
