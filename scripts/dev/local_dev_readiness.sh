#!/usr/bin/env bash
set -euo pipefail

: "${ROOT_DIR:?ROOT_DIR is required}"
source "${ROOT_DIR}/scripts/common/env.sh"

[[ "${ENV}" == "dev" \
  && "${COMPOSE_PROJECT_NAME}" == "sc-local-dev" \
  && "${DB_NAME}" == "sc_dev_demo" \
  && "${ODOO_DBFILTER}" == '^sc_dev_demo$' \
  && "${DB_DATA}" == "sc_local_dev_db_data" \
  && "${REDIS_DATA}" == "sc_local_dev_redis_data" \
  && "${ODOO_DATA}" == "sc_local_dev_odoo_data" ]] || {
    echo "[local.dev.ready] identity mismatch" >&2
    exit 2
  }

for volume in "${DB_DATA}" "${REDIS_DATA}" "${ODOO_DATA}"; do
  docker volume inspect "${volume}" >/dev/null 2>&1 || {
    echo "[local.dev.ready] missing feature-demo volume: ${volume}" >&2
    echo "[local.dev.ready] run governed local.dev.rebuild_demo" >&2
    exit 2
  }
done

echo "[local.dev.ready] PASS project=${COMPOSE_PROJECT_NAME} db=${DB_NAME}"
