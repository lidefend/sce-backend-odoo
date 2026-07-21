#!/bin/sh
set -e

TPL="/etc/odoo/odoo.conf.template"
OUT="${ODOO_CONF_OUT:-/opt/sce-runtime/config/odoo.conf}"
DB="${ODOO_DB:-${DB_NAME:-}}"

if [ -z "${DB:-}" ]; then
  echo "[entrypoint] ODOO_DB or DB_NAME is required; refusing implicit database selection" >&2
  exit 64
fi

python3 /usr/local/bin/production_db_contract.py runtime
echo "[entrypoint] render odoo.conf: ${TPL} -> ${OUT}"
mkdir -p "$(dirname "$OUT")"
python3 /usr/local/bin/render_odoo_conf.py "$TPL" "$OUT"

echo "[entrypoint] verify existing initialized database (read only)"
python3 - <<'PY'
import os
import psycopg2

db = os.environ.get("ODOO_DB") or os.environ.get("DB_NAME")
conn = psycopg2.connect(
    host=os.environ.get("DB_HOST", "db"),
    port=int(os.environ.get("DB_PORT", "5432")),
    user=os.environ.get("DB_USER"),
    password=os.environ.get("DB_PASSWORD"),
    dbname=db,
    options="-c default_transaction_read_only=on",
)
try:
    conn.set_session(readonly=True, autocommit=False)
    with conn.cursor() as cr:
        cr.execute("SELECT to_regclass('public.ir_module_module')")
        if not cr.fetchone()[0]:
            raise SystemExit("[entrypoint] target database is not initialized; use the explicit management entry")
        cr.execute("SELECT state FROM ir_module_module WHERE name='base' LIMIT 1")
        row = cr.fetchone()
        if not row or row[0] != "installed":
            raise SystemExit("[entrypoint] base is not installed; use the explicit management entry")
finally:
    conn.rollback()
    conn.close()
PY

echo "[entrypoint] start odoo"
exec odoo -c "$OUT"
