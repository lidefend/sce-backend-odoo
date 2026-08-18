#!/usr/bin/env bash
set -euo pipefail

: "${ROOT_DIR:?ROOT_DIR is required}"
source "${ROOT_DIR}/scripts/common/env.sh"

[[ "${TECHNICAL_SAMPLE_DATABASE:-0}" == "1" \
  && "${COMPOSE_PROJECT_NAME}" == "sc-local-sample" \
  && "${DB_NAME}" == "sc_dev_sample" \
  && "${DB_DATA}" == "sc_local_sample_db_data" \
  && "${REDIS_DATA}" == "sc_local_sample_redis_data" \
  && "${ODOO_DATA}" == "sc_local_sample_odoo_data" ]] || {
    echo "[local.sample.ready] identity mismatch" >&2
    exit 2
  }
for volume in "${DB_DATA}" "${REDIS_DATA}" "${ODOO_DATA}"; do
  docker volume inspect "${volume}" >/dev/null 2>&1 || {
    echo "[local.sample.ready] missing restored volume: ${volume}" >&2
    exit 2
  }
done
marker="$(docker run --rm -v "${ODOO_DATA}:/target:ro" alpine:3.20 cat /target/.sc_local_sample_restored 2>/dev/null || true)"
[[ "${marker}" =~ ^sc_demo-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}[[:space:]][0-9a-f]{64}$ ]] || {
  echo "[local.sample.ready] governed restore marker is missing or invalid" >&2
  exit 2
}
echo "[local.sample.ready] PASS ${marker}"
