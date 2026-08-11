#!/usr/bin/env bash
set -euo pipefail

: "${ROOT_DIR:?ROOT_DIR is required}"
source "${ROOT_DIR}/scripts/common/env.sh"
source "${ROOT_DIR}/scripts/common/compose.sh"

if [[ "${ENV}" != "dev" || "${ISOLATED_REHEARSAL_DATABASE:-0}" != "1" ]]; then
  echo "[local.clean.rebuild] refused: target is not marked as an isolated dev rehearsal" >&2
  exit 2
fi
if [[ ! "${COMPOSE_PROJECT_NAME}" =~ ^sc-[a-z0-9-]+$ || ! "${DB_NAME}" =~ ^sc_[a-z0-9_]+$ ]]; then
  echo "[local.clean.rebuild] refused: invalid isolated project/database identity" >&2
  exit 2
fi
if [[ "${ODOO_DBFILTER}" != "^${DB_NAME}$" ]]; then
  echo "[local.clean.rebuild] refused: dbfilter is not exact for ${DB_NAME}" >&2
  exit 2
fi
if [[ "${CONFIRM_LOCAL_CLEAN_REBUILD:-}" != "REBUILD_ISOLATED_REHEARSAL" ]]; then
  echo "[local.clean.rebuild] confirmation required: CONFIRM_LOCAL_CLEAN_REBUILD=REBUILD_ISOLATED_REHEARSAL" >&2
  exit 2
fi

echo "[local.clean.rebuild] remove only project=${COMPOSE_PROJECT_NAME} isolated volumes"
compose_dev down --volumes --remove-orphans
compose_dev up -d db redis
compose_dev run --rm -T --entrypoint /bin/sh odoo -c \
  'python3 /usr/local/bin/render_odoo_conf.py /etc/odoo/odoo.conf.template "${ODOO_CONF_OUT:-/var/lib/odoo/odoo.conf}"'
compose_dev run --rm -T --entrypoint /usr/bin/odoo odoo \
  --config=/var/lib/odoo/odoo.conf \
  -d "${DB_NAME}" \
  --db_host=db --db_port=5432 --db_user="${DB_USER}" --db_password="${DB_PASSWORD}" \
  --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/source-addons,/mnt/addons_external/oca_server_ux \
  -i "${LOCAL_CLEAN_MODULES:-sc_norm_engine}" --without-demo=all \
  --no-http --workers=0 --max-cron-threads=0 --stop-after-init
compose_dev up -d
echo "[local.clean.rebuild] PASS project=${COMPOSE_PROJECT_NAME} db=${DB_NAME}"
