#!/usr/bin/env bash
set -euo pipefail

: "${ROOT_DIR:?ROOT_DIR is required}"
source "${ROOT_DIR}/scripts/common/env.sh"
source "${ROOT_DIR}/scripts/common/compose.sh"

[[ "${ENV}" == "dev" && "${COMPOSE_PROJECT_NAME}" == "sc-local-dev" && "${DB_NAME}" == "sc_dev_demo" && "${ODOO_DBFILTER}" == '^sc_dev_demo$' ]] || {
  echo "[local.dev.rebuild_realistic] DENY dev identity mismatch" >&2
  exit 2
}
[[ "${CONFIRM_LOCAL_DEV_REALISTIC_REBUILD:-}" == "REBUILD_CURRENT_FEATURE_DEV" ]] || {
  echo "[local.dev.rebuild_realistic] confirmation required: CONFIRM_LOCAL_DEV_REALISTIC_REBUILD=REBUILD_CURRENT_FEATURE_DEV" >&2
  exit 2
}

echo "[local.dev.rebuild_realistic] reset project=${COMPOSE_PROJECT_NAME} db=${DB_NAME} odoo_demo=0"
compose_dev up -d db redis
compose_dev stop nginx odoo >/dev/null 2>&1 || true
bash "${ROOT_DIR}/scripts/db/reset.sh"
compose_dev run --rm -T --entrypoint /usr/bin/odoo odoo \
  --config="${ODOO_CONF}" -d "${DB_NAME}" \
  --db_host=db --db_port=5432 --db_user="${DB_USER}" --db_password="${DB_PASSWORD}" \
  --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/source-addons,/mnt/demo-addons,/mnt/extra-addons,"${ADDONS_EXTERNAL_MOUNT}" \
  -i smart_construction_core,smart_construction_seed,smart_construction_portal \
  --without-demo=all --no-http --workers=0 --max-cron-threads=0 --stop-after-init
compose_dev up -d
bash "${ROOT_DIR}/scripts/dev/local_dev_realistic_authority_verify.sh"
bash "${ROOT_DIR}/scripts/dev/local_environment_health.sh" persistent
echo "[local.dev.rebuild_realistic] PASS project=${COMPOSE_PROJECT_NAME} db=${DB_NAME} odoo_demo=0"
