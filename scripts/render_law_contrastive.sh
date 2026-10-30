#!/usr/bin/env bash
# Render law-contrastive exam images with the existing attraction renderer (manual stage).
# Reads manifests written by `python -m src.law_contrastive export`. Skips complete items and keeps
# going on failures. Env: DEVICE (CUDA|OPTIX|CPU), SAMPLES (default 96), RENDERS_DIR, BLENDER_BIN.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BLENDER="${BLENDER_BIN:-$ROOT/.tools/blender-3.6.23-linux-x64/blender}"
RENDERS_DIR="${RENDERS_DIR:-$ROOT/renders/law_contrastive}"
DEVICE="${DEVICE:-CUDA}"; SAMPLES="${SAMPLES:-96}"
shopt -s nullglob
scenes=("$RENDERS_DIR"/*/*/*/*/scene.json)
[[ ${#scenes[@]} -gt 0 ]] || { echo "No manifests under $RENDERS_DIR; run: python -m src.law_contrastive prepare" >&2; exit 1; }
rendered=0; skipped=0; failed=()
for scene in "${scenes[@]}"; do
  dir="$(dirname "$scene")"; rel="${dir#$ROOT/}"
  complete=true
  for f in context choice_A choice_B choice_C choice_D; do [[ -f "$dir/$f.png" ]] || complete=false; done
  if [[ $complete == true ]]; then skipped=$((skipped+1)); continue; fi
  echo "[render] $rel"
  if "$BLENDER" --background --python-exit-code 1 --python "$ROOT/src/simulation/blender_attraction.py" -- \
       --manifest "$scene" --device "$DEVICE" --samples "$SAMPLES" --resolution 1920 1280 --no-text > "$dir/render.log" 2>&1; then
    rendered=$((rendered+1)); rm -f "$dir/scene.blend"
  else
    failed+=("$rel"); echo "[render] FAILED $rel (see $rel/render.log)" >&2
  fi
done
echo "Rendered $rendered, skipped $skipped complete, failed ${#failed[@]} of ${#scenes[@]}."
[[ ${#failed[@]} -eq 0 ]] || { printf '  %s\n' "${failed[@]}" >&2; exit 1; }
