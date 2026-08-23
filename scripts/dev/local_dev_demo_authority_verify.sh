#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
export ROOT_DIR

source "$ROOT_DIR/scripts/common/env.sh"
source "$ROOT_DIR/scripts/common/guard_prod.sh"
source "$ROOT_DIR/scripts/common/compose.sh"
source "$ROOT_DIR/scripts/common/demo_data_guard.sh"

: "${DB_NAME:?DB_NAME required}"
: "${DB_USER:?DB_USER required}"
: "${DB_PASSWORD:?DB_PASSWORD required}"

guard_prod_forbid
guard_demo_data_scope

printf '[local.dev.demo.authority] verify db=%s\n' "$DB_NAME"

compose_dev run --rm -T \
  -e DB_NAME \
  -e SC_ENVIRONMENT \
  -e SC_ALLOW_DEMO_DATA \
  --entrypoint /usr/bin/odoo odoo \
  shell --config="$ODOO_CONF" \
  -d "$DB_NAME" \
  --db_host=db --db_port=5432 --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/source-addons,/mnt/demo-addons,/mnt/extra-addons,"$ADDONS_EXTERNAL_MOUNT" \
  --no-http --workers=0 --max-cron-threads=0 \
  < "$ROOT_DIR/scripts/dev/local_dev_demo_authority_preflight.py"
