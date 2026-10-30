#!/usr/bin/env bash
set -euo pipefail

DEST="${1:-/data/tos/chenliang1/docker_images}"
TMP="${TMPDIR:-/tmp}/docker_image_archive"
mkdir -p "$DEST" "$TMP"

mapfile -t IMAGES < <(docker image ls --format '{{.Repository}}:{{.Tag}}' \
  | rg -i 'qwen|deepseek|glm|bench' | sort -u)

for image in "${IMAGES[@]}"; do
  name="${image//:/__}"
  archive="$DEST/$name.tar"
  if [[ -s "$archive" ]]; then
    echo "[skip-existing] $image"
    docker rmi "$image"
    continue
  fi
  local_archive="$TMP/$name.tar"
  echo "[save] $image"
  docker save "$image" -o "$local_archive"
  test -s "$local_archive"
  echo "[copy] $archive"
  cp "$local_archive" "$archive"
  test -s "$archive"
  rm -f "$local_archive"
  docker rmi "$image"
  echo "[done] $image"
done

echo "Archived ${#IMAGES[@]} Docker image reference(s) to $DEST and removed successfully archived local images."
