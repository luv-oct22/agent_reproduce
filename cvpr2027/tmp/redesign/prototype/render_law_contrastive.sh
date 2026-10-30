#!/usr/bin/env bash
# Render law-contrastive exam items with the existing attraction renderer.
# Skips items whose five images exist; keeps going on failures. Env: DEVICE (CUDA|OPTIX|CPU), SAMPLES.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BLENDER="${BLENDER_BIN:-$ROOT/.tools/blender-3.6.23-linux-x64/blender}"
DEVICE="${DEVICE:-CUDA}"; SAMPLES="${SAMPLES:-96}"
done_n=0; skip_n=0; fail=()
for scene in "$ROOT"/renders/law_contrastive/central_force_dynamics/*/*/*/scene.json; do
  dir="$(dirname "$scene")"
  if [[ -f "$dir/context.png" && -f "$dir/choice_D.png" ]]; then skip_n=$((skip_n+1)); continue; fi
  echo "[render] ${dir#$ROOT/}"
  if "$BLENDER" --background --python-exit-code 1 --python "$ROOT/src/simulation/blender_attraction.py" -- \
       --manifest "$scene" --device "$DEVICE" --samples "$SAMPLES" --resolution 1920 1280 --no-text > "$dir/render.log" 2>&1; then
    done_n=$((done_n+1)); rm -f "$dir/scene.blend"
  else
    fail+=("${dir#$ROOT/}"); echo "[render] FAILED ${dir#$ROOT/} (see render.log)" >&2
  fi
done
echo "Rendered $done_n, skipped $skip_n complete, failed ${#fail[@]}."
[[ ${#fail[@]} -eq 0 ]] || { printf '  %s\n' "${fail[@]}" >&2; exit 1; }
