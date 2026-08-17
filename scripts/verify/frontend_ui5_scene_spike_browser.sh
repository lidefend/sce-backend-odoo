#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PORT="${SC_UI5_SPIKE_PORT:-5186}"
BASE_URL="http://127.0.0.1:${PORT}"
ARTIFACT_DIR="${SC_UI5_SPIKE_ARTIFACT_DIR:-/tmp/sc-ui5-scene-spike}"
SERVER_LOG="${ARTIFACT_DIR}/preview.log"

mkdir -p "${ARTIFACT_DIR}"

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]] && kill -0 "${SERVER_PID}" 2>/dev/null; then
    kill "${SERVER_PID}" 2>/dev/null || true
    wait "${SERVER_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

cd "${ROOT_DIR}"
scripts/dev/pnpm_exec.sh -C frontend/apps/scene-ui5-spike preview \
  --host 127.0.0.1 --port "${PORT}" >"${SERVER_LOG}" 2>&1 &
SERVER_PID=$!

for _ in $(seq 1 80); do
  if curl --fail --silent --show-error "${BASE_URL}" >/dev/null; then
    break
  fi
  if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
    echo "[verify.frontend.ui5_scene_spike.browser] FAIL preview stopped" >&2
    cat "${SERVER_LOG}" >&2
    exit 1
  fi
  sleep 0.25
done

SC_UI5_SPIKE_URL="${BASE_URL}" \
SC_UI5_SPIKE_ARTIFACT_DIR="${ARTIFACT_DIR}" \
node scripts/verify/frontend_ui5_scene_spike_browser.mjs
