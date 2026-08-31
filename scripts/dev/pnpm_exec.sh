#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
REAL_HOME="${SNAP_REAL_HOME:-$HOME}"
NVM_ROOT="${NVM_DIR:-${REAL_HOME}/.nvm}"

ensure_node_runtime() {
  if command -v node >/dev/null 2>&1; then
    return 0
  fi

  if [[ -s "${NVM_ROOT}/nvm.sh" ]]; then
    # shellcheck disable=SC1090
    . "${NVM_ROOT}/nvm.sh"
  fi

  if command -v node >/dev/null 2>&1; then
    return 0
  fi

  if [[ -d "${NVM_ROOT}/versions/node" ]]; then
    local latest_node_bin
    latest_node_bin="$(find "${NVM_ROOT}/versions/node" -maxdepth 2 -type d -name bin | sort | tail -n 1)"
    if [[ -n "${latest_node_bin:-}" ]]; then
      export PATH="${latest_node_bin}:$PATH"
    fi
  fi

  command -v node >/dev/null 2>&1
}

ensure_node_runtime || {
  echo "node runtime is required but was not found (searched NVM_ROOT=${NVM_ROOT})" >&2
  exit 2
}

if [[ -n "${PNPM_BIN:-}" ]]; then
  exec "${PNPM_BIN}" "$@"
fi

PNPM_VERSION="$(
  ROOT_DIR="${ROOT_DIR}" node - <<'NODE'
const pkg = require(`${process.env.ROOT_DIR}/frontend/package.json`);
const spec = String(pkg.packageManager || 'pnpm@').trim();
const match = spec.match(/^pnpm@(.+)$/);
if (!match) {
  process.exit(2);
}
process.stdout.write(match[1]);
NODE
)"

candidate_paths=()
if [[ -n "${COREPACK_HOME:-}" ]]; then
  candidate_paths+=("${COREPACK_HOME}/v1/pnpm/${PNPM_VERSION}/bin/pnpm.cjs")
fi
candidate_paths+=(
  "${ROOT_DIR}/../.corepack/v1/pnpm/${PNPM_VERSION}/bin/pnpm.cjs"
  "${REAL_HOME}/.cache/node/corepack/v1/pnpm/${PNPM_VERSION}/bin/pnpm.cjs"
  "${REAL_HOME}/.local/share/node/corepack/v1/pnpm/${PNPM_VERSION}/bin/pnpm.cjs"
)

for candidate in "${candidate_paths[@]}"; do
  if [[ -f "${candidate}" ]]; then
    exec node "${candidate}" "$@"
  fi
done

if command -v pnpm >/dev/null 2>&1; then
  current_version="$(pnpm --version 2>/dev/null || true)"
  if [[ "${current_version}" == "${PNPM_VERSION}" ]]; then
    exec pnpm "$@"
  fi
fi

if command -v corepack >/dev/null 2>&1; then
  export COREPACK_ENABLE_DOWNLOAD_PROMPT=0
  exec corepack pnpm "$@"
fi

echo "pnpm ${PNPM_VERSION} is required but was not found" >&2
exit 2
