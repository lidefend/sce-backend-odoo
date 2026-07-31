#!/bin/sh
set -eu

ACTION="${1:-}"
case "$ACTION" in
  probe|operator-grant|payload-plan|payload-import|payload-verify) ;;
  *) echo "usage: production-maintenance {probe|operator-grant|payload-plan|payload-import|payload-verify}" >&2; exit 64 ;;
esac

CONF="/opt/sce-runtime/config/odoo.conf"
DB="${TARGET_DB:-${ODOO_DB:-}}"
test "$DB" = "sc_production"
test "${SC_MAINTENANCE_HTTP_DISABLED:-}" = "1"

python3 /usr/local/bin/production_db_contract.py preflight
python3 /usr/local/bin/render_odoo_conf.py /etc/odoo/odoo.conf.template "$CONF"
python3 /usr/local/bin/production_maintenance_config.py "$CONF"

case "$ACTION" in
  probe)
    SCRIPT=/usr/local/share/sce/production_maintenance_probe.py
    ;;
  operator-grant)
    SCRIPT=/usr/local/share/sce/provision_tenant_payload_operator.py
    ;;
  payload-plan)
    SC_TENANT_PAYLOAD_MAINTENANCE_CAPABILITY="$(
      python3 -c 'import secrets; print(secrets.token_hex(32))'
    )"
    export SC_TENANT_PAYLOAD_MAINTENANCE_CAPABILITY
    export SC_TENANT_PAYLOAD_ACTION=plan
    SCRIPT=/usr/local/share/sce/tenant_payload_odoo_action.py
    ;;
  payload-import)
    SC_TENANT_PAYLOAD_MAINTENANCE_CAPABILITY="$(
      python3 -c 'import secrets; print(secrets.token_hex(32))'
    )"
    export SC_TENANT_PAYLOAD_MAINTENANCE_CAPABILITY
    export SC_TENANT_PAYLOAD_ACTION=import
    SCRIPT=/usr/local/share/sce/tenant_payload_odoo_action.py
    ;;
  payload-verify)
    SC_TENANT_PAYLOAD_MAINTENANCE_CAPABILITY="$(
      python3 -c 'import secrets; print(secrets.token_hex(32))'
    )"
    export SC_TENANT_PAYLOAD_MAINTENANCE_CAPABILITY
    export SC_TENANT_PAYLOAD_ACTION=verify
    SCRIPT=/usr/local/share/sce/tenant_payload_odoo_action.py
    ;;
esac

exec odoo shell -d "$DB" -c "$CONF" --no-http --log-level=error < "$SCRIPT"
