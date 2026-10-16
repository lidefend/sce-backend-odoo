#!/usr/bin/env bash
# Bounded performance-baseline capture for the registered local.dev profile.
#
# P4 collection wrapper. It reuses the registered sc-local-dev / sc_dev_demo
# runtime and the existing governed entries; it starts no environment, creates no
# database, port, volume or credential, and never writes product code. Every
# capture is written under one ignored evidence directory and normalized once by
# scripts/verify/system_performance_baseline.py.
set -euo pipefail
: "${ROOT_DIR:?ROOT_DIR required}"
source "${ROOT_DIR}/scripts/common/env.sh"
[[ "${ENV}" == dev && "${COMPOSE_PROJECT_NAME}" == sc-local-dev && "${DB_NAME}" == sc_dev_demo && "${ODOO_DBFILTER}" == '^sc_dev_demo$' ]]

OUT_DIR="${ROOT_DIR}/artifacts/backend/system-performance-baseline"
SOURCES="${PRODUCT_PERFORMANCE_BASELINE_SOURCES:-sla,observe}"
STRICT="${PRODUCT_PERFORMANCE_BASELINE_STRICT:-0}"
mkdir -p "${OUT_DIR}"

captured=()
failed=()

want() { [[ ",${SOURCES}," == *",$1,"* ]]; }

run_capture() {
  local name="$1"; shift
  local log="${OUT_DIR}/${name}.log"
  echo "[baseline] capturing ${name}"
  if "$@" >"${log}" 2>&1; then
    captured+=("${log}")
  else
    echo "[baseline] capture ${name} FAILED; see ${log}" >&2
    failed+=("${name}")
  fi
}

echo "[baseline] collecting registered deployment identity"
python3 "${ROOT_DIR}/scripts/ops/local_dev_performance_identity.py" \
  --env-file "${ENV_FILE}" --out "${OUT_DIR}/identity.json"

if want sla; then
  # The collector writes its own structured JSON report; only that JSON is a
  # baseline input. Its stdout log stays as a diagnostic trace.
  echo "[baseline] capturing sla-guard"
  if python3 "${ROOT_DIR}/scripts/verify/platform_sla_guard.py" >"${OUT_DIR}/sla-guard.log" 2>&1; then
    cp "${ROOT_DIR}/artifacts/backend/platform_sla_report.json" "${OUT_DIR}/sla-guard.json"
    captured+=("${OUT_DIR}/sla-guard.json")
  else
    echo "[baseline] capture sla-guard FAILED; see ${OUT_DIR}/sla-guard.log" >&2
    failed+=("sla")
  fi
fi

if want observe; then
  run_capture observe env \
    PRODUCT_PERFORMANCE_MODE=observe PRODUCT_PERFORMANCE_REQUEST_CASE=web_startup \
    "${MAKE:-make}" --no-print-directory -C "${ROOT_DIR}" \
    ENV=dev ENV_FILE="${ENV_FILE}" local.dev.runtime.performance.observe
fi

if want contract_profile; then
  run_capture contract-profile env \
    PRODUCT_PERFORMANCE_MODE=contract_profile PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID="${PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID:-878}" \
    "${MAKE:-make}" --no-print-directory -C "${ROOT_DIR}" \
    ENV=dev ENV_FILE="${ENV_FILE}" local.dev.runtime.performance.observe
fi

if want permission; then
  run_capture permission env \
    PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID="${PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID:-878}" \
    "${MAKE:-make}" --no-print-directory -C "${ROOT_DIR}" \
    ENV=dev ENV_FILE="${ENV_FILE}" local.dev.runtime.permission.probe
fi

if want cache_identity; then
  run_capture cache-identity env \
    PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID="${PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID:-878}" \
    "${MAKE:-make}" --no-print-directory -C "${ROOT_DIR}" \
    ENV=dev ENV_FILE="${ENV_FILE}" local.dev.runtime.cache_identity.probe
fi

if [[ ${#captured[@]} -eq 0 ]]; then
  echo "[baseline] no capture succeeded; nothing to normalize" >&2
  exit 2
fi

strict_flag=()
if [[ "${STRICT}" == "1" ]]; then
  strict_flag=(--strict)
fi

echo "[baseline] normalizing ${#captured[@]} capture(s)"
python3 "${ROOT_DIR}/scripts/verify/system_performance_baseline.py" \
  "${strict_flag[@]}" \
  --identity-file "${OUT_DIR}/identity.json" \
  --inputs "${captured[@]}" \
  --out "${ROOT_DIR}/artifacts/backend/system_performance_baseline.json" \
  --report "${ROOT_DIR}/docs/ops/audit/system_performance_baseline.md"

if [[ ${#failed[@]} -gt 0 ]]; then
  echo "[baseline] failed captures: ${failed[*]}" >&2
  exit 2
fi
