#!/usr/bin/env bash
set -euo pipefail

: "${ROOT_DIR:?ROOT_DIR is required}"
SOURCE_ENV_FILE="${SOURCE_ENV_FILE:-${ROOT_DIR}/.env.dev}"
TARGET_ENV_FILE="${TARGET_ENV_FILE:-${ROOT_DIR}/.env.local.clean}"

[[ "${TARGET_ENV_FILE}" = /* ]] || TARGET_ENV_FILE="${ROOT_DIR}/${TARGET_ENV_FILE}"
[[ "${SOURCE_ENV_FILE}" = /* ]] || SOURCE_ENV_FILE="${ROOT_DIR}/${SOURCE_ENV_FILE}"

frontend_dist="${ROOT_DIR}/frontend/apps/web/dist-clean"
mkdir -p "${frontend_dist}"
chmod 755 "${frontend_dist}"

if [[ -f "${TARGET_ENV_FILE}" ]]; then
  chmod 600 "${TARGET_ENV_FILE}"
  echo "[local.clean.prepare] reuse ${TARGET_ENV_FILE}"
  exit 0
fi
if [[ ! -f "${SOURCE_ENV_FILE}" ]]; then
  echo "[local.clean.prepare] source env is missing: ${SOURCE_ENV_FILE}" >&2
  exit 2
fi

random_secret() {
  openssl rand -hex "$1"
}

umask 077
db_password="$(random_secret 24)"
admin_password="$(random_secret 24)"
jwt_secret="$(random_secret 32)"
bootstrap_secret="$(random_secret 32)"

{
  printf '%s\n' \
    'ENV=dev' \
    'ENV_FILE=.env.local.clean' \
    'COMPOSE_PROJECT_NAME=sc-local-clean' \
    'DB_USER=sc_clean_odoo' \
    "DB_PASSWORD=${db_password}" \
    'DB_NAME=sc_clean' \
    "ADMIN_PASSWD=${admin_password}" \
    "JWT_SECRET=${jwt_secret}" \
    'ODOO_DBFILTER=^sc_clean$' \
    'DB_DATA=sc_local_clean_db_data' \
    'REDIS_DATA=sc_local_clean_redis_data' \
    'ODOO_DATA=sc_local_clean_odoo_data' \
    'NGINX_PORT=18083' \
    'ODOO_PORT=8072' \
    'FRONTEND_DIST_DIR=./frontend/apps/web/dist-clean' \
    'VITE_ODOO_DB=sc_clean' \
    'VITE_ODOO_DB_LOCKED=1' \
    'VITE_APP_ENV=development' \
    'VITE_BUILD_MODE=development' \
    'VITE_BUILD_OUT_DIR=dist-clean' \
    'VITE_PLATFORM_ADMIN_DB=sc_platform_control' \
    "SC_BOOTSTRAP_SECRET=${bootstrap_secret}" \
    'SC_BOOTSTRAP_LOGIN=local_clean_bootstrap' \
    'SCENE_CHANNEL=stable' \
    'SCENE_USE_PINNED=0' \
    'SCENE_ROLLBACK=0' \
    'SC_ENVIRONMENT=dev' \
    'SC_ALLOW_DEMO_DATA=0' \
    'SC_SEED_ENABLED=0'
} >"${TARGET_ENV_FILE}"
chmod 600 "${TARGET_ENV_FILE}"

echo "[local.clean.prepare] created ${TARGET_ENV_FILE} mode=600"
echo "[local.clean.prepare] project=sc-local-clean db=sc_clean dbfilter=^sc_clean$"
