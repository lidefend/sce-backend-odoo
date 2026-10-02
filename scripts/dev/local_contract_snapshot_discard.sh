#!/usr/bin/env bash
set -euo pipefail

# Discard only the isolated contract-snapshot profile's own volumes so the
# profile can be rebuilt from a clean, credential-bound env file. The identity
# is matched exactly and the action needs an explicit confirmation.

: "${ROOT_DIR:?ROOT_DIR is required}"
source "${ROOT_DIR}/scripts/common/env.sh"
source "${ROOT_DIR}/scripts/common/compose.sh"

[[ "${ENV}" == "dev" \
  && "${ISOLATED_REHEARSAL_DATABASE:-0}" == "1" \
  && "${COMPOSE_PROJECT_NAME}" == "sc-contract-snapshot-v1" \
  && "${DB_NAME}" == "sc_contract_snapshot" \
  && "${ODOO_DBFILTER}" == '^sc_contract_snapshot$' \
  && "${DB_DATA}" == "sc_contract_snapshot_db_data" \
  && "${REDIS_DATA}" == "sc_contract_snapshot_redis_data" \
  && "${ODOO_DATA}" == "sc_contract_snapshot_odoo_data" ]] || {
    echo "[local.contract-snapshot.discard] DENY isolated profile identity mismatch" >&2
    exit 2
  }

[[ "${CONFIRM_LOCAL_CONTRACT_SNAPSHOT_DISCARD:-}" == "DISCARD_ISOLATED_CONTRACT_SNAPSHOT" ]] || {
  echo "[local.contract-snapshot.discard] confirmation required: CONFIRM_LOCAL_CONTRACT_SNAPSHOT_DISCARD=DISCARD_ISOLATED_CONTRACT_SNAPSHOT" >&2
  exit 2
}

echo "[local.contract-snapshot.discard] remove only project=${COMPOSE_PROJECT_NAME} db=${DB_NAME}"
compose_dev down --volumes --remove-orphans
for volume in "${DB_DATA}" "${REDIS_DATA}" "${ODOO_DATA}"; do
  if docker volume inspect "${volume}" >/dev/null 2>&1; then
    docker volume rm "${volume}"
  fi
  if docker volume inspect "${volume}" >/dev/null 2>&1; then
    echo "[local.contract-snapshot.discard] volume remains: ${volume}" >&2
    exit 1
  fi
done

echo "[local.contract-snapshot.discard] PASS project=${COMPOSE_PROJECT_NAME}"
