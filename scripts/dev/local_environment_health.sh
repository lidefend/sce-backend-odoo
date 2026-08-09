#!/usr/bin/env bash
set -euo pipefail

: "${ROOT_DIR:?ROOT_DIR is required}"
profile="${1:-}"
source "${ROOT_DIR}/scripts/common/env.sh"
source "${ROOT_DIR}/scripts/common/compose.sh"

case "${profile}" in
  persistent)
    expected_project="sc-backend-odoo-dev"
    expected_db="sc_demo"
    expected_filter='^sc_demo$'
    expected_db_volume="sc_dev_db_data"
    expected_redis_volume="sc_dev_redis_data"
    expected_odoo_volume="sc_dev_odoo_data"
    ;;
  clean)
    expected_project="sc-local-clean"
    expected_db="sc_clean"
    expected_filter='^sc_clean$'
    expected_db_volume="sc_local_clean_db_data"
    expected_redis_volume="sc_local_clean_redis_data"
    expected_odoo_volume="sc_local_clean_odoo_data"
    expected_product_module="sc_norm_engine"
    ;;
  *)
    echo "usage: $0 persistent|clean" >&2
    exit 2
    ;;
esac

fail=0
check_equal() {
  local label="$1" actual="$2" expected="$3"
  if [[ "${actual}" != "${expected}" ]]; then
    echo "[local.env.health] FAIL ${label}: actual=${actual} expected=${expected}" >&2
    fail=1
  fi
}

check_equal project "${COMPOSE_PROJECT_NAME}" "${expected_project}"
check_equal database "${DB_NAME}" "${expected_db}"
check_equal dbfilter "${ODOO_DBFILTER}" "${expected_filter}"
check_equal db_volume "${DB_DATA:-}" "${expected_db_volume}"
check_equal redis_volume "${REDIS_DATA:-}" "${expected_redis_volume}"
check_equal odoo_volume "${ODOO_DATA:-}" "${expected_odoo_volume}"

db_cid="$(compose_dev ps -q db)"
redis_cid="$(compose_dev ps -q redis)"
odoo_cid="$(compose_dev ps -q odoo)"
if [[ -z "${db_cid}" || -z "${redis_cid}" || -z "${odoo_cid}" ]]; then
  echo "[local.env.health] FAIL profile=${profile}: db, redis and odoo services must be running" >&2
  exit 1
fi

actual_db_volume="$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}' "${db_cid}")"
actual_redis_volume="$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}' "${redis_cid}")"
actual_odoo_volume="$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/var/lib/odoo"}}{{.Name}}{{end}}{{end}}' "${odoo_cid}")"
check_equal mounted_db_volume "${actual_db_volume}" "${expected_db_volume}"
check_equal mounted_redis_volume "${actual_redis_volume}" "${expected_redis_volume}"
check_equal mounted_odoo_volume "${actual_odoo_volume}" "${expected_odoo_volume}"

db_state="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${db_cid}")"
odoo_state="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${odoo_cid}")"
db_name="$(docker exec -e PGPASSWORD="${DB_PASSWORD}" "${db_cid}" psql -U "${DB_USER}" -d "${DB_NAME}" -Atc 'SELECT current_database()')"
base_state="$(docker exec -e PGPASSWORD="${DB_PASSWORD}" "${db_cid}" psql -U "${DB_USER}" -d "${DB_NAME}" -Atc "SELECT state FROM ir_module_module WHERE name='base'")"
rendered_filter="$(docker exec "${odoo_cid}" sed -n 's/^[[:space:]]*dbfilter[[:space:]]*=[[:space:]]*//p' /var/lib/odoo/odoo.conf | tail -n 1)"

check_equal db_health "${db_state}" healthy
check_equal odoo_health "${odoo_state}" healthy
check_equal runtime_database "${db_name}" "${expected_db}"
check_equal base_module "${base_state}" installed
check_equal rendered_dbfilter "${rendered_filter}" "${expected_filter}"
if [[ -n "${expected_product_module:-}" ]]; then
  product_state="$(docker exec -e PGPASSWORD="${DB_PASSWORD}" "${db_cid}" psql -U "${DB_USER}" -d "${DB_NAME}" -Atc "SELECT state FROM ir_module_module WHERE name='${expected_product_module}'")"
  check_equal product_module "${product_state}" installed
  clean_counts="$(docker exec -e PGPASSWORD="${DB_PASSWORD}" "${db_cid}" psql -U "${DB_USER}" -d "${DB_NAME}" -Atc "SELECT (SELECT count(*) FROM project_project) || ',' || (SELECT count(*) FROM sc_norm_specialty) || ',' || (SELECT count(*) FROM sc_norm_chapter) || ',' || (SELECT count(*) FROM sc_norm_item)")"
  check_equal clean_business_counts "${clean_counts}" '0,0,0,0'
fi

http_code="$(curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:${NGINX_PORT}/" || true)"
check_equal frontend_http "${http_code}" 200

if [[ "${fail}" != "0" ]]; then
  exit 1
fi
echo "[local.env.health] PASS profile=${profile} project=${COMPOSE_PROJECT_NAME} db=${DB_NAME} dbfilter=${ODOO_DBFILTER}"
