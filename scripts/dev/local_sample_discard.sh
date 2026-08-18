#!/usr/bin/env bash
set -euo pipefail

: "${ROOT_DIR:?ROOT_DIR is required}"
source "${ROOT_DIR}/scripts/common/env.sh"
source "${ROOT_DIR}/scripts/common/compose.sh"

[[ "${ENV}" == "dev" \
  && "${TECHNICAL_SAMPLE_DATABASE:-0}" == "1" \
  && "${COMPOSE_PROJECT_NAME}" == "sc-local-sample" \
  && "${DB_NAME}" == "sc_dev_sample" \
  && "${ODOO_DBFILTER}" == '^sc_dev_sample$' \
  && "${DB_DATA}" == "sc_local_sample_db_data" \
  && "${REDIS_DATA}" == "sc_local_sample_redis_data" \
  && "${ODOO_DATA}" == "sc_local_sample_odoo_data" ]] || {
    echo "[local.sample.discard] DENY technical-sample identity mismatch" >&2
    exit 2
  }

[[ "${CONFIRM_LOCAL_DEV_SAMPLE_DISCARD:-}" == "DISCARD_LOCAL_TECHNICAL_SAMPLE" ]] || {
  echo "[local.sample.discard] confirmation required: CONFIRM_LOCAL_DEV_SAMPLE_DISCARD=DISCARD_LOCAL_TECHNICAL_SAMPLE" >&2
  exit 2
}

echo "[local.sample.discard] remove only project=${COMPOSE_PROJECT_NAME} db=${DB_NAME}"
compose_dev down --volumes --remove-orphans
for volume in "${DB_DATA}" "${REDIS_DATA}" "${ODOO_DATA}"; do
  if docker volume inspect "${volume}" >/dev/null 2>&1; then
    docker volume rm "${volume}"
  fi
  if docker volume inspect "${volume}" >/dev/null 2>&1; then
    echo "[local.sample.discard] volume remains: ${volume}" >&2
    exit 1
  fi
done

echo "[local.sample.discard] PASS project=${COMPOSE_PROJECT_NAME}"
