#!/usr/bin/env bash
set -euo pipefail

umask 077
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy

: "${REGISTRY_AUDIT_RUN_ID:?REGISTRY_AUDIT_RUN_ID required}"
: "${REGISTRY_AUDIT_DATABASE_NAME:?REGISTRY_AUDIT_DATABASE_NAME required}"
: "${REGISTRY_AUDIT_DATABASE_USER:?REGISTRY_AUDIT_DATABASE_USER required}"
: "${REGISTRY_AUDIT_DATABASE_PASSWORD:?REGISTRY_AUDIT_DATABASE_PASSWORD required}"
: "${REGISTRY_AUDIT_MODULES:?REGISTRY_AUDIT_MODULES required}"
: "${REGISTRY_AUDIT_OUTPUT_FILE:?REGISTRY_AUDIT_OUTPUT_FILE required}"

case "${REGISTRY_AUDIT_DATABASE_NAME}" in
  sc_admin_vis_p3_registry_audit_*) ;;
  *)
    echo "refusing unexpected registry audit database name" >&2
    exit 2
    ;;
esac

mkdir -p "${HOME}" /var/lib/odoo

ODOO_COMMON_ARGS=(
  --db_host=db
  --db_port=5432
  --db_user="${REGISTRY_AUDIT_DATABASE_USER}"
  --db_password="${REGISTRY_AUDIT_DATABASE_PASSWORD}"
  --database="${REGISTRY_AUDIT_DATABASE_NAME}"
  --db-filter="^${REGISTRY_AUDIT_DATABASE_NAME}$"
  --data-dir=/var/lib/odoo
  --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/source-addons,/mnt/addons_external/oca_server_ux
  --no-http
  --workers=0
  --max-cron-threads=0
  --without-demo=all
)

echo "[registry-audit] initialize registry modules=${REGISTRY_AUDIT_MODULES}"
/usr/bin/odoo \
  "${ODOO_COMMON_ARGS[@]}" \
  --init="${REGISTRY_AUDIT_MODULES}" \
  --stop-after-init \
  --log-level=warn

echo "[registry-audit] export registry metadata"
/usr/bin/odoo shell \
  "${ODOO_COMMON_ARGS[@]}" \
  --stop-after-init \
  < /mnt/registry-audit/registry_export.py

test -s "${REGISTRY_AUDIT_OUTPUT_FILE}"
chmod 0644 "${REGISTRY_AUDIT_OUTPUT_FILE}"
echo "[registry-audit] export complete"
