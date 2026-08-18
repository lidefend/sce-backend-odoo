#!/usr/bin/env bash
set -euo pipefail

: "${ROOT_DIR:?ROOT_DIR is required}"
SOURCE_ENV_FILE="${SOURCE_ENV_FILE:-${ROOT_DIR}/.env.dev}"
TARGET_ENV_FILE="${TARGET_ENV_FILE:-${ROOT_DIR}/.env.local.clean}"

[[ "${TARGET_ENV_FILE}" = /* ]] || TARGET_ENV_FILE="${ROOT_DIR}/${TARGET_ENV_FILE}"
[[ "${SOURCE_ENV_FILE}" = /* ]] || SOURCE_ENV_FILE="${ROOT_DIR}/${SOURCE_ENV_FILE}"

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

project_name="${LOCAL_CLEAN_PROJECT_NAME:-sc-local-clean}"
db_user="${LOCAL_CLEAN_DB_USER:-sc_clean_odoo}"
db_name="${LOCAL_CLEAN_DB_NAME:-sc_clean}"
db_data="${LOCAL_CLEAN_DB_DATA:-sc_local_clean_db_data}"
redis_data="${LOCAL_CLEAN_REDIS_DATA:-sc_local_clean_redis_data}"
odoo_data="${LOCAL_CLEAN_ODOO_DATA:-sc_local_clean_odoo_data}"
nginx_port="${LOCAL_CLEAN_NGINX_PORT:-18083}"
odoo_port="${LOCAL_CLEAN_ODOO_PORT:-8072}"

if [[ ! "${project_name}" =~ ^sc-[a-z0-9-]+$ ]]; then
  echo "[local.clean.prepare] invalid isolated project name: ${project_name}" >&2
  exit 2
fi
for value in "${db_user}" "${db_name}" "${db_data}" "${redis_data}" "${odoo_data}"; do
  if [[ ! "${value}" =~ ^sc_[a-z0-9_]+$ ]]; then
    echo "[local.clean.prepare] invalid isolated identifier: ${value}" >&2
    exit 2
  fi
done
for value in "${nginx_port}" "${odoo_port}"; do
  if [[ ! "${value}" =~ ^[0-9]+$ ]] || (( value < 1024 || value > 65535 )); then
    echo "[local.clean.prepare] invalid isolated port: ${value}" >&2
    exit 2
  fi
done

existing_volumes=()
for volume in "${db_data}" "${redis_data}" "${odoo_data}"; do
  if docker volume inspect "${volume}" >/dev/null 2>&1; then
    existing_volumes+=("${volume}")
  fi
done
if (( ${#existing_volumes[@]} > 0 )); then
  if [[ "${LOCAL_CLEAN_PREPARE_FOR_REBUILD:-0}" != "1" \
    || "${CONFIRM_LOCAL_CLEAN_REBUILD:-}" != "REBUILD_ISOLATED_REHEARSAL" ]]; then
    echo "[local.clean.prepare] DENY credential authority is missing while isolated volumes exist: ${existing_volumes[*]}" >&2
    echo "[local.clean.prepare] use the governed local.clean.rebuild confirmation; do not generate new credentials over old volumes" >&2
    exit 2
  fi
fi

frontend_dist="${ROOT_DIR}/frontend/apps/web/dist-clean"
mkdir -p "${frontend_dist}"
chmod 755 "${frontend_dist}"

umask 077
db_password="$(random_secret 24)"
admin_password="$(random_secret 24)"
jwt_secret="$(random_secret 32)"
bootstrap_secret="$(random_secret 32)"

{
  printf '%s\n' \
    'ENV=dev' \
    "ENV_FILE=${TARGET_ENV_FILE}" \
    "COMPOSE_PROJECT_NAME=${project_name}" \
    "DB_USER=${db_user}" \
    "DB_PASSWORD=${db_password}" \
    "DB_NAME=${db_name}" \
    "ADMIN_PASSWD=${admin_password}" \
    "JWT_SECRET=${jwt_secret}" \
    "ODOO_DBFILTER=^${db_name}$" \
    "DB_DATA=${db_data}" \
    "REDIS_DATA=${redis_data}" \
    "ODOO_DATA=${odoo_data}" \
    "NGINX_PORT=${nginx_port}" \
    "ODOO_PORT=${odoo_port}" \
    'FRONTEND_DIST_DIR=./frontend/apps/web/dist-clean' \
    "VITE_ODOO_DB=${db_name}" \
    'VITE_ODOO_DB_LOCKED=1' \
    'VITE_APP_ENV=development' \
    'VITE_BUILD_MODE=development' \
    'VITE_BUILD_OUT_DIR=dist-clean' \
    'VITE_PLATFORM_ADMIN_DB=sc_platform_control' \
    "SC_BOOTSTRAP_SECRET=${bootstrap_secret}" \
    'SC_BOOTSTRAP_LOGIN=admin' \
    'SCENE_CHANNEL=stable' \
    'SCENE_USE_PINNED=0' \
    'SCENE_ROLLBACK=0' \
    'SC_ENVIRONMENT=dev' \
    'SC_ALLOW_DEMO_DATA=0' \
    'SC_SEED_ENABLED=0'
  printf '%s\n' 'ISOLATED_REHEARSAL_DATABASE=1'
} >"${TARGET_ENV_FILE}"
chmod 600 "${TARGET_ENV_FILE}"

echo "[local.clean.prepare] created ${TARGET_ENV_FILE} mode=600"
echo "[local.clean.prepare] project=${project_name} db=${db_name} dbfilter=^${db_name}$"
