#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

git -C "$ROOT_DIR" rev-parse --verify HEAD >/dev/null
{
  git -C "$ROOT_DIR" rev-parse HEAD
  git -C "$ROOT_DIR" diff --binary HEAD -- addons
  while IFS= read -r -d '' path; do
    printf '%s\0' "$path"
    if [[ -L "$ROOT_DIR/$path" ]]; then
      readlink "$ROOT_DIR/$path"
    else
      sha256sum "$ROOT_DIR/$path" | awk '{print $1}'
    fi
  done < <(git -C "$ROOT_DIR" ls-files --others --exclude-standard -z -- addons | LC_ALL=C sort -z)
} | sha256sum | awk '{print $1}'
