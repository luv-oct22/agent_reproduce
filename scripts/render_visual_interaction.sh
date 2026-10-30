#!/usr/bin/env bash
# Render visual-interaction outcome frames: one Blender process per world, skipping rendered frames.
# Reads frames.json written by `python -m src.visual_interaction prepare`.
# Env: DEVICE (CUDA|OPTIX|CPU, default CUDA), SAMPLES (default 32), FRAMES_DIR, BLENDER_BIN,
#      ONLY (glob over worlds, e.g. 'central_force_dynamics_g1/rule_2/*').
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BLENDER="${BLENDER_BIN:-$ROOT/.tools/blender-3.6.23-linux-x64/blender}"
FRAMES_DIR="${FRAMES_DIR:-$ROOT/renders/visual_interaction}"
DEVICE="${DEVICE:-CUDA}"; SAMPLES="${SAMPLES:-32}"; ONLY="${ONLY:-*/*/*}"
shopt -s nullglob
manifests=("$FRAMES_DIR"/*/$ONLY/frames.json)
[[ ${#manifests[@]} -gt 0 ]] || { echo "No frames.json under $FRAMES_DIR; run: python -m src.visual_interaction prepare" >&2; exit 1; }
failed=()
for m in "${manifests[@]}"; do
  dir="$(dirname "$m")"; rel="${dir#$ROOT/}"
  echo "[render] $rel $(date +%H:%M:%S)"
  if ! "$BLENDER" --background --python-exit-code 1 --python "$ROOT/src/simulation/blender_visual_interaction.py" -- \
       --manifest "$m" --device "$DEVICE" --samples "$SAMPLES" > "$dir/render.log" 2>&1; then
    failed+=("$rel"); echo "[render] FAILED $rel (see $rel/render.log)" >&2
  fi
done
echo "Worlds: ${#manifests[@]}, failed: ${#failed[@]}."
[[ ${#failed[@]} -eq 0 ]] || { printf '  %s\n' "${failed[@]}" >&2; exit 1; }
