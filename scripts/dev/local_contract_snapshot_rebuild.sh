#!/usr/bin/env bash
set -euo pipefail

# Rebuild the isolated contract-snapshot profile from scratch: reset only its
# own volumes, seed from the registered demo dataset, then upgrade this
# worktree's smart_core so the profile runs the candidate source. Mirrors the
# isolated rehearsal pattern: exact identity, exact dbfilter, explicit
# confirmation.

: "${ROOT_DIR:?ROOT_DIR is required}"
source "${ROOT_DIR}/scripts/common/env.sh"
source "${ROOT_DIR}/scripts/common/compose.sh"

if [[ "${ENV}" != "dev" || "${ISOLATED_REHEARSAL_DATABASE:-0}" != "1" ]]; then
  echo "[local.contract-snapshot.rebuild] refused: target is not marked as an isolated dev rehearsal" >&2
  exit 2
fi
if [[ "${COMPOSE_PROJECT_NAME}" != "sc-contract-snapshot-v1" || "${DB_NAME}" != "sc_contract_snapshot" ]]; then
  echo "[local.contract-snapshot.rebuild] refused: invalid isolated project/database identity" >&2
  exit 2
fi
if [[ "${ODOO_DBFILTER}" != "^${DB_NAME}$" ]]; then
  echo "[local.contract-snapshot.rebuild] refused: dbfilter is not exact for ${DB_NAME}" >&2
  exit 2
fi
if [[ "${CONFIRM_LOCAL_CONTRACT_SNAPSHOT_REBUILD:-}" != "REBUILD_ISOLATED_CONTRACT_SNAPSHOT" ]]; then
  echo "[local.contract-snapshot.rebuild] confirmation required: CONFIRM_LOCAL_CONTRACT_SNAPSHOT_REBUILD=REBUILD_ISOLATED_CONTRACT_SNAPSHOT" >&2
  exit 2
fi

modules="${LOCAL_CONTRACT_SNAPSHOT_MODULES:-smart_core}"

echo "[local.contract-snapshot.rebuild] reset project=${COMPOSE_PROJECT_NAME} isolated volumes"
compose_dev down --volumes --remove-orphans >/dev/null 2>&1 || true
for volume in "${DB_DATA}" "${REDIS_DATA}" "${ODOO_DATA}"; do
  if docker volume inspect "${volume}" >/dev/null 2>&1; then
    docker volume rm "${volume}" >/dev/null
  fi
  if docker volume inspect "${volume}" >/dev/null 2>&1; then
    echo "[local.contract-snapshot.rebuild] volume survived reset: ${volume}" >&2
    exit 1
  fi
done

ENV="${ENV}" ENV_FILE="${ENV_FILE}" ROOT_DIR="${ROOT_DIR}" \
  CONFIRM_LOCAL_CONTRACT_SNAPSHOT_SEED=SEED_ISOLATED_CONTRACT_SNAPSHOT \
  bash "${ROOT_DIR}/scripts/dev/local_contract_snapshot_seed.sh"

compose_dev run --rm -T --entrypoint /bin/sh odoo -c \
  'python3 /usr/local/bin/render_odoo_conf.py /etc/odoo/odoo.conf.template "${ODOO_CONF_OUT:-/var/lib/odoo/odoo.conf}"'
echo "[local.contract-snapshot.rebuild] upgrade modules=${modules} onto the seeded database"
compose_dev run --rm -T --entrypoint /usr/bin/odoo odoo \
  --config=/var/lib/odoo/odoo.conf \
  -d "${DB_NAME}" \
  --db_host=db --db_port=5432 --db_user="${DB_USER}" --db_password="${DB_PASSWORD}" \
  --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/source-addons,/mnt/demo-addons,/mnt/addons_external/oca_server_ux \
  -u "${modules}" \
  --no-http --workers=0 --max-cron-threads=0 --stop-after-init

compose_dev up -d

target_db_id="$(compose_dev ps -q db)"
state=""
for _ in $(seq 1 60); do
  state="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${target_db_id}")"
  [[ "${state}" == "healthy" ]] && break
  sleep 2
done
[[ "${state}" == "healthy" ]] || {
  echo "[local.contract-snapshot.rebuild] target database did not become healthy" >&2
  exit 1
}

module_state="$(docker exec "${target_db_id}" psql -X -Aqt -U "${DB_USER}" -d "${DB_NAME}" \
  -c "SELECT state || ':' || latest_version FROM ir_module_module WHERE name = 'smart_core'")"
[[ "${module_state}" == installed:* ]] || {
  echo "[local.contract-snapshot.rebuild] smart_core is not installed: ${module_state}" >&2
  exit 1
}
slo_table="$(docker exec "${target_db_id}" psql -X -Aqt -U "${DB_USER}" -d "${DB_NAME}" \
  -c "SELECT coalesce(to_regclass('public.sc_contract_slo_observation')::text, '')")"
[[ -n "${slo_table}" ]] || {
  echo "[local.contract-snapshot.rebuild] candidate model table sc_contract_slo_observation is missing; the profile does not run this worktree's smart_core" >&2
  exit 1
}

echo "[local.contract-snapshot.rebuild] PASS project=${COMPOSE_PROJECT_NAME} db=${DB_NAME} modules=${modules} smart_core=${module_state#installed:}"
