#!/usr/bin/env bash
set -euo pipefail

: "${ROOT_DIR:?ROOT_DIR is required}"
source "${ROOT_DIR}/scripts/common/env.sh"
source "${ROOT_DIR}/scripts/common/compose.sh"

[[ "${ENV}" == "dev" && "${COMPOSE_PROJECT_NAME}" == "sc-local-dev" && "${DB_NAME}" == "sc_dev_demo" ]] || {
  echo "[local.dev.realistic.authority] DENY dev identity mismatch" >&2
  exit 2
}

compose_dev run --rm -T \
  --entrypoint /usr/bin/odoo odoo shell \
  --config="${ODOO_CONF}" -d "${DB_NAME}" \
  --db_host=db --db_port=5432 --db_user="${DB_USER}" --db_password="${DB_PASSWORD}" \
  --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/source-addons,/mnt/demo-addons,/mnt/extra-addons,"${ADDONS_EXTERNAL_MOUNT}" \
  --no-http --workers=0 --max-cron-threads=0 \
  < "${ROOT_DIR}/scripts/dev/local_dev_realistic_authority_verify.py"
