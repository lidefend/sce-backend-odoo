#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

: "${DB_NAME:?DB_NAME must be supplied by the governed runtime entry}"
: "${ENV_FILE:?ENV_FILE must be supplied by the governed runtime entry}"
: "${COMPOSE_PROJECT_NAME:?COMPOSE_PROJECT_NAME must be supplied by the governed runtime entry}"
: "${COMPOSE_FILES:?COMPOSE_FILES must be supplied by the governed runtime entry}"
if [[ "${ODOO_SHELL_RUN_ISOLATED:-0}" != "0" ]]; then
  echo "form contract audit requires the same persistent service for copy and execution" >&2
  exit 2
fi
source scripts/_lib/common.sh
OUT_DIR="${OUT_DIR:-artifacts/backend/form_structure_contract_runtime}"
TMP_SCRIPT="/tmp/form_structure_contract_runtime_audit.py"
TMP_OUT="/tmp/form_structure_contract_runtime"
LIMIT="${LIMIT:-0}"
[[ "$LIMIT" =~ ^[0-9]+$ ]] || { echo "LIMIT must be a nonnegative integer" >&2; exit 2; }

# Copy and execution share the existing governed Compose authority.
# shellcheck disable=SC2086
compose ${COMPOSE_FILES} cp scripts/verify/form_structure_contract_runtime_audit.py "odoo:$TMP_SCRIPT"

status=0
bash scripts/ops/odoo_shell_exec.sh <<PY || status=$?
import runpy
import sys
sys.argv = ["$TMP_SCRIPT", "--out-dir", "$TMP_OUT", "--limit", "$LIMIT"]
runpy.run_path("$TMP_SCRIPT", run_name="__main__", init_globals={"env": env})
PY

mkdir -p "$OUT_DIR"
# shellcheck disable=SC2086
compose ${COMPOSE_FILES} cp "odoo:$TMP_OUT/." "$OUT_DIR/"
exit "$status"
