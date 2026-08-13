#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
export ROOT_DIR
ENV_FILE="$(mktemp)"
trap 'rm -f "$ENV_FILE"' EXIT
printf '%s\n' \
  'COMPOSE_PROJECT_NAME=sc_dev_from_file' \
  'PROJECT=sc_dev_from_file' \
  'DB_NAME=sc_demo' \
  'DB_USER=dev_from_file' \
  'DB_PASSWORD=dev_from_file_password' \
  'DB_DATA=sc_dev_db_data' \
  'REDIS_DATA=sc_dev_redis_data' \
  'ODOO_DATA=sc_dev_odoo_data' \
  'ODOO_DB=sc_demo' \
  'ODOO_DBFILTER=^sc_demo$$' \
  'ODOO_PORT=8069' \
  'LIST_DB=true' \
  'ADMIN_PASSWD=dev_from_file_admin' \
  'JWT_SECRET=dev_from_file_jwt' > "$ENV_FILE"
COMPOSE_PROJECT_NAME=sc_acceptance_probe
PROJECT=sc_acceptance_probe
DB_NAME=sc_frontend_acceptance
DB_USER=acceptance_probe
DB_PASSWORD=acceptance_probe_password
DB_DATA=sc_acceptance_probe_db
REDIS_DATA=sc_acceptance_probe_redis
ODOO_DATA=sc_acceptance_probe_odoo
ODOO_DB=sc_frontend_acceptance
ODOO_DBFILTER='^sc_frontend_acceptance$'
ODOO_PORT=19083
LIST_DB=false
ADMIN_PASSWD=acceptance_probe_admin
JWT_SECRET=acceptance_probe_jwt
export ENV_FILE COMPOSE_PROJECT_NAME PROJECT DB_NAME DB_USER DB_PASSWORD DB_DATA REDIS_DATA ODOO_DATA
export ODOO_DB ODOO_DBFILTER ODOO_PORT LIST_DB ADMIN_PASSWD JWT_SECRET

# shellcheck source=../common/env.sh
source "$ROOT_DIR/scripts/common/env.sh"

[[ "$COMPOSE_PROJECT_NAME" == sc_acceptance_probe ]]
[[ "$DB_DATA" == sc_acceptance_probe_db ]]
[[ "$REDIS_DATA" == sc_acceptance_probe_redis ]]
[[ "$ODOO_DATA" == sc_acceptance_probe_odoo ]]
[[ "$ODOO_DB" == sc_frontend_acceptance ]]
[[ "$ODOO_DBFILTER" == '^sc_frontend_acceptance$' ]]
[[ "$ODOO_PORT" == 19083 ]]
[[ "$LIST_DB" == false ]]
echo "[env_external_topology_precedence] PASS"
