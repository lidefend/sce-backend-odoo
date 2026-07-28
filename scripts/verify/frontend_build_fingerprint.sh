#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
DIST_DIR="${1:-${ROOT_DIR}/frontend/apps/web/dist}"

if [[ ! -d "${DIST_DIR}" ]] || [[ ! -s "${DIST_DIR}/index.html" ]]; then
  echo "[frontend_build_fingerprint] missing production frontend build: ${DIST_DIR}" >&2
  exit 2
fi

fingerprint="$(
  cd "${DIST_DIR}"
  LC_ALL=C find . -type f ! -name .build-sha256 -print0 \
    | LC_ALL=C sort -z \
    | xargs -0 sha256sum \
    | sha256sum \
    | awk '{print $1}'
)"

if [[ ! "${fingerprint}" =~ ^[0-9a-f]{64}$ ]]; then
  echo "[frontend_build_fingerprint] invalid calculated fingerprint" >&2
  exit 2
fi

printf '%s\n' "${fingerprint}" >"${DIST_DIR}/.build-sha256"
echo "[frontend_build_fingerprint] PASS sha256=${fingerprint}"
