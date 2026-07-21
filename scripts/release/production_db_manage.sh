#!/bin/sh
set -eu

ACTION="${1:-}"
case "$ACTION" in
  preflight|health|init|install|upgrade) ;;
  *) echo "usage: production-db-manage {preflight|health|init|install|upgrade}" >&2; exit 64 ;;
esac

python3 /usr/local/bin/production_db_contract.py "$ACTION"
DB="${TARGET_DB:-${ODOO_DB:-${DB_NAME:-}}}"
CONF="${ODOO_CONF_OUT:-/opt/sce-runtime/config/odoo.conf}"
python3 /usr/local/bin/render_odoo_conf.py /etc/odoo/odoo.conf.template "$CONF"

readonly_probe() {
  python3 - "$DB" <<'PY'
import os, sys, psycopg2
db = sys.argv[1]
conn = psycopg2.connect(host=os.environ.get("DB_HOST", "db"), port=int(os.environ.get("DB_PORT", "5432")), user=os.environ.get("DB_USER"), password=os.environ.get("DB_PASSWORD"), dbname=db, options="-c default_transaction_read_only=on")
try:
    conn.set_session(readonly=True)
    with conn.cursor() as cr:
        cr.execute("SELECT to_regclass('public.ir_module_module')")
        initialized = bool(cr.fetchone()[0])
        if not initialized:
            raise SystemExit("database exists but is not initialized")
        cr.execute("SELECT state FROM ir_module_module WHERE name='base' LIMIT 1")
        row = cr.fetchone()
        if not row or row[0] != "installed":
            raise SystemExit("database exists but base is not installed")
finally:
    conn.rollback(); conn.close()
PY
}

case "$ACTION" in
  preflight|health) readonly_probe ;;
  init)
    python3 - "$DB" <<'PY'
import os, sys, psycopg2
from psycopg2 import sql
db = sys.argv[1]
conn = psycopg2.connect(host=os.environ.get("DB_HOST", "db"), port=int(os.environ.get("DB_PORT", "5432")), user=os.environ.get("DB_USER"), password=os.environ.get("DB_PASSWORD"), dbname="postgres")
conn.autocommit = True
try:
    with conn.cursor() as cr:
        cr.execute("SELECT 1 FROM pg_database WHERE datname=%s", (db,))
        if cr.fetchone(): raise SystemExit("target database already exists; refusing initialization")
        cr.execute(sql.SQL("CREATE DATABASE {} WITH TEMPLATE template0 ENCODING 'UTF8'").format(sql.Identifier(db)))
finally: conn.close()
PY
    exec odoo -c "$CONF" -d "$DB" --no-http --workers=0 --max-cron-threads=0 -i base --without-demo=all --stop-after-init ;;
  install) readonly_probe; exec odoo -c "$CONF" -d "$DB" --no-http --workers=0 --max-cron-threads=0 -i "$TARGET_MODULE" --without-demo=all --stop-after-init ;;
  upgrade) readonly_probe; exec odoo -c "$CONF" -d "$DB" --no-http --workers=0 --max-cron-threads=0 -u "$TARGET_MODULE" --without-demo=all --stop-after-init ;;
esac
