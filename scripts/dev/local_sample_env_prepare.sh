#!/usr/bin/env bash
set -euo pipefail

: "${ROOT_DIR:?ROOT_DIR is required}"
SOURCE_ENV_FILE="${SOURCE_ENV_FILE:-${ROOT_DIR}/.env.dev}"
TARGET_ENV_FILE="${TARGET_ENV_FILE:-${ROOT_DIR}/.env.local.sample}"

if [[ -f "${TARGET_ENV_FILE}" ]]; then
  chmod 600 "${TARGET_ENV_FILE}"
  echo "[local.sample.prepare] reuse ${TARGET_ENV_FILE}"
  exit 0
fi
[[ -f "${SOURCE_ENV_FILE}" ]] || {
  echo "[local.sample.prepare] source env is missing" >&2
  exit 2
}
for volume in sc_local_sample_db_data sc_local_sample_redis_data sc_local_sample_odoo_data; do
  if docker volume inspect "${volume}" >/dev/null 2>&1; then
    echo "[local.sample.prepare] DENY credentials missing while sample volume exists: ${volume}" >&2
    exit 2
  fi
done

umask 077
db_password="$(openssl rand -hex 24)"
admin_password="$(openssl rand -hex 24)"
jwt_secret="$(openssl rand -hex 32)"
bootstrap_secret="$(openssl rand -hex 32)"
cat >"${TARGET_ENV_FILE}" <<EOF
ENV=dev
ENV_FILE=${TARGET_ENV_FILE}
COMPOSE_PROJECT_NAME=sc-local-sample
DB_USER=odoo
DB_PASSWORD=${db_password}
DB_NAME=sc_dev_sample
ADMIN_PASSWD=${admin_password}
JWT_SECRET=${jwt_secret}
SC_BOOTSTRAP_SECRET=${bootstrap_secret}
SC_BOOTSTRAP_LOGIN=svc_project_ro
SCENE_CHANNEL=stable
SCENE_USE_PINNED=0
SCENE_ROLLBACK=0
ODOO_DBFILTER=^sc_dev_sample\$
DB_DATA=sc_local_sample_db_data
REDIS_DATA=sc_local_sample_redis_data
ODOO_DATA=sc_local_sample_odoo_data
NGINX_PORT=18084
ODOO_PORT=8073
VITE_PLATFORM_ADMIN_DB=sc_platform_core
FRONTEND_DIST_DIR=./frontend/apps/web/dist-dev
VITE_ODOO_DB=sc_dev_sample
VITE_ODOO_DB_LOCKED=1
TECHNICAL_SAMPLE_DATABASE=1
EOF
chmod 600 "${TARGET_ENV_FILE}"
echo "[local.sample.prepare] created ${TARGET_ENV_FILE} mode=600"
