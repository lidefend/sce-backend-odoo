#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
lockfile="$ROOT_DIR/frontend/pnpm-lock.yaml"
workspace="$ROOT_DIR/frontend/pnpm-workspace.yaml"
[[ -f "$lockfile" && -f "$workspace" && ! -L "$lockfile" && ! -L "$workspace" ]] || {
  echo "[frontend.dependencies.cached] DENY invalid lockfile/workspace identity" >&2
  exit 2
}
lock_sha="$(sha256sum "$lockfile" | awk '{print $1}')"
[[ "$lock_sha" =~ ^[0-9a-f]{64}$ ]] || {
  echo "[frontend.dependencies.cached] DENY invalid lockfile fingerprint" >&2
  exit 2
}

"$ROOT_DIR/scripts/dev/pnpm_exec.sh" -C "$ROOT_DIR/frontend" install \
  --offline --frozen-lockfile --ignore-scripts

for required in \
  "$ROOT_DIR/frontend/node_modules/.pnpm" \
  "$ROOT_DIR/frontend/apps/web/node_modules/.bin/eslint" \
  "$ROOT_DIR/frontend/apps/web/node_modules/.bin/vite" \
  "$ROOT_DIR/frontend/apps/web/node_modules/.bin/vue-tsc"; do
  [[ -e "$required" ]] || {
    echo "[frontend.dependencies.cached] DENY incomplete cached dependency projection: $required" >&2
    exit 2
  }
done
echo "[frontend.dependencies.cached] PASS lock_sha256=$lock_sha mode=offline,frozen,ignore-scripts"
