#!/usr/bin/env bash
set -euo pipefail

# Discard only the isolated contract-lifecycle profile's own volumes so the
# profile can be rebuilt from a clean, credential-bound env file. The identity
# is matched exactly and the action needs an explicit confirmation.

: "${ROOT_DIR:?ROOT_DIR is required}"
source "${ROOT_DIR}/scripts/common/env.sh"
source "${ROOT_DIR}/scripts/common/compose.sh"

[[ "${ENV}" == "dev" \
  && "${ISOLATED_REHEARSAL_DATABASE:-0}" == "1" \
  && "${COMPOSE_PROJECT_NAME}" == "sc-contract-lifecycle-v1" \
  && "${DB_NAME}" == "sc_contract_lifecycle" \
  && "${ODOO_DBFILTER}" == '^sc_contract_lifecycle$' \
  && "${DB_DATA}" == "sc_contract_lifecycle_db_data" \
  && "${REDIS_DATA}" == "sc_contract_lifecycle_redis_data" \
  && "${ODOO_DATA}" == "sc_contract_lifecycle_odoo_data" ]] || {
    echo "[local.contract-lifecycle.discard] DENY isolated profile identity mismatch" >&2
    exit 2
  }

[[ "${CONFIRM_LOCAL_CONTRACT_LIFECYCLE_DISCARD:-}" == "DISCARD_ISOLATED_CONTRACT_LIFECYCLE" ]] || {
  echo "[local.contract-lifecycle.discard] confirmation required: CONFIRM_LOCAL_CONTRACT_LIFECYCLE_DISCARD=DISCARD_ISOLATED_CONTRACT_LIFECYCLE" >&2
  exit 2
}

echo "[local.contract-lifecycle.discard] remove only project=${COMPOSE_PROJECT_NAME} db=${DB_NAME}"
compose_dev down --volumes --remove-orphans
for volume in "${DB_DATA}" "${REDIS_DATA}" "${ODOO_DATA}"; do
  if docker volume inspect "${volume}" >/dev/null 2>&1; then
    docker volume rm "${volume}"
  fi
  if docker volume inspect "${volume}" >/dev/null 2>&1; then
    echo "[local.contract-lifecycle.discard] volume remains: ${volume}" >&2
    exit 1
  fi
done

echo "[local.contract-lifecycle.discard] PASS project=${COMPOSE_PROJECT_NAME}"
