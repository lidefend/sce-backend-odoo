#!/usr/bin/env bash
set -euo pipefail

# Derive the isolated contract-lifecycle profile's env file from the existing
# governed dev credentials. Only the profile identity (project, database,
# dbfilter, volumes, ports) and the fixed fixture password are new; no new
# credential authority is minted.

: "${ROOT_DIR:?ROOT_DIR is required}"
SOURCE_ENV_FILE="${SOURCE_ENV_FILE:-${ROOT_DIR}/.env.dev}"
TARGET_ENV_FILE="${TARGET_ENV_FILE:-${ROOT_DIR}/.env.local.contract-lifecycle}"

[[ "${TARGET_ENV_FILE}" = /* ]] || TARGET_ENV_FILE="${ROOT_DIR}/${TARGET_ENV_FILE}"
[[ "${SOURCE_ENV_FILE}" = /* ]] || SOURCE_ENV_FILE="${ROOT_DIR}/${SOURCE_ENV_FILE}"

# Deploy-time revision injection. The supply-chain attestation binds the *running*
# deployment SHA, so the revision this profile serves must be declared here (the
# compose file substitutes SC_SOURCE_REVISION) rather than left as the
# placeholder "unknown". Defaults to this worktree's HEAD; override with
# CONTRACT_LIFECYCLE_SOURCE_REVISION=<40-hex> when deploying another revision.
source_revision="${CONTRACT_LIFECYCLE_SOURCE_REVISION:-${SC_SOURCE_REVISION:-}}"
if [[ -z "${source_revision}" ]]; then
  source_revision="$(git -C "${ROOT_DIR}" rev-parse HEAD 2>/dev/null || true)"
fi
if [[ ! "${source_revision}" =~ ^[0-9a-f]{40}$ ]]; then
  echo "[local.contract-lifecycle.prepare] a 40-hex deployment source revision is required, got: ${source_revision:-<empty>}" >&2
  exit 2
fi

refresh_source_revision() {
  local current
  current="$(grep -E '^SC_SOURCE_REVISION=' "${TARGET_ENV_FILE}" 2>/dev/null | tail -1 | cut -d= -f2- || true)"
  if [[ "${current}" == "${source_revision}" ]]; then
    echo "[local.contract-lifecycle.prepare] deploy revision already ${source_revision}"
    return 0
  fi
  if grep -qE '^SC_SOURCE_REVISION=' "${TARGET_ENV_FILE}"; then
    sed -i "s/^SC_SOURCE_REVISION=.*/SC_SOURCE_REVISION=${source_revision}/" "${TARGET_ENV_FILE}"
  else
    printf 'SC_SOURCE_REVISION=%s\n' "${source_revision}" >>"${TARGET_ENV_FILE}"
  fi
  chmod 600 "${TARGET_ENV_FILE}"
  echo "[local.contract-lifecycle.prepare] deploy revision ${current:-<none>} -> ${source_revision} (re-run local.contract-lifecycle.up to apply)"
}

if [[ -f "${TARGET_ENV_FILE}" ]]; then
  chmod 600 "${TARGET_ENV_FILE}"
  echo "[local.contract-lifecycle.prepare] reuse ${TARGET_ENV_FILE}"
  refresh_source_revision
  exit 0
fi
if [[ ! -f "${SOURCE_ENV_FILE}" ]]; then
  echo "[local.contract-lifecycle.prepare] source env is missing: ${SOURCE_ENV_FILE}" >&2
  exit 2
fi

project_name="${LOCAL_CONTRACT_LIFECYCLE_PROJECT_NAME:-sc-contract-lifecycle-v1}"
db_name="${LOCAL_CONTRACT_LIFECYCLE_DB_NAME:-sc_contract_lifecycle}"
db_data="${LOCAL_CONTRACT_LIFECYCLE_DB_DATA:-sc_contract_lifecycle_db_data}"
redis_data="${LOCAL_CONTRACT_LIFECYCLE_REDIS_DATA:-sc_contract_lifecycle_redis_data}"
odoo_data="${LOCAL_CONTRACT_LIFECYCLE_ODOO_DATA:-sc_contract_lifecycle_odoo_data}"
nginx_port="${LOCAL_CONTRACT_LIFECYCLE_NGINX_PORT:-18090}"
odoo_port="${LOCAL_CONTRACT_LIFECYCLE_ODOO_PORT:-8079}"
db_user="${LOCAL_CONTRACT_LIFECYCLE_DB_USER:-odoo}"
fixture_password="${LOCAL_CONTRACT_LIFECYCLE_PASSWORD:-scdevpass}"

if [[ ! "${project_name}" =~ ^sc-[a-z0-9-]+$ ]]; then
  echo "[local.contract-lifecycle.prepare] invalid isolated project name: ${project_name}" >&2
  exit 2
fi
for value in "${db_name}" "${db_data}" "${redis_data}" "${odoo_data}"; do
  if [[ ! "${value}" =~ ^sc_[a-z0-9_]+$ ]]; then
    echo "[local.contract-lifecycle.prepare] invalid isolated identifier: ${value}" >&2
    exit 2
  fi
done
if [[ ! "${db_user}" =~ ^[a-z_][a-z0-9_]*$ ]]; then
  echo "[local.contract-lifecycle.prepare] invalid database user: ${db_user}" >&2
  exit 2
fi
if [[ -z "${fixture_password}" ]]; then
  echo "[local.contract-lifecycle.prepare] empty fixture password" >&2
  exit 2
fi
for value in "${nginx_port}" "${odoo_port}"; do
  if [[ ! "${value}" =~ ^[0-9]+$ ]] || (( value < 1024 || value > 65535 )); then
    echo "[local.contract-lifecycle.prepare] invalid isolated port: ${value}" >&2
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
  if [[ "${LOCAL_CONTRACT_LIFECYCLE_PREPARE_FOR_REBUILD:-0}" != "1" \
    || "${CONFIRM_LOCAL_CONTRACT_LIFECYCLE_REBUILD:-}" != "REBUILD_ISOLATED_CONTRACT_LIFECYCLE" ]]; then
    echo "[local.contract-lifecycle.prepare] DENY profile volumes already exist while the env file is absent: ${existing_volumes[*]}" >&2
    echo "[local.contract-lifecycle.prepare] use the governed local.contract-lifecycle.rebuild confirmation; do not re-mint credentials over old volumes" >&2
    exit 2
  fi
  echo "[local.contract-lifecycle.prepare] rebuild confirmed; the rebuild path will discard: ${existing_volumes[*]}"
fi

umask 077
cat >"${TARGET_ENV_FILE}" <<EOF
ENV=dev
ENV_FILE=${TARGET_ENV_FILE}
COMPOSE_PROJECT_NAME=${project_name}
DB_USER=${db_user}
DB_PASSWORD=${fixture_password}
DB_NAME=${db_name}
ADMIN_PASSWD=${fixture_password}
JWT_SECRET=local-contract-lifecycle-fixed-jwt-secret
SC_BOOTSTRAP_SECRET=local-contract-lifecycle-fixed-bootstrap-secret
SC_BOOTSTRAP_LOGIN=svc_project_ro
SCENE_CHANNEL=stable
SCENE_USE_PINNED=0
SCENE_ROLLBACK=0
ODOO_DBFILTER=^${db_name}\$
DB_DATA=${db_data}
REDIS_DATA=${redis_data}
ODOO_DATA=${odoo_data}
NGINX_PORT=${nginx_port}
ODOO_PORT=${odoo_port}
FRONTEND_DIST_DIR=./frontend/apps/web/dist-dev
ISOLATED_REHEARSAL_DATABASE=1
SC_SOURCE_REVISION=${source_revision}
VITE_ODOO_DB=${db_name}
VITE_ODOO_DB_LOCKED=1
EOF
chmod 600 "${TARGET_ENV_FILE}"
echo "[local.contract-lifecycle.prepare] created ${TARGET_ENV_FILE} mode=600 project=${project_name} db=${db_name}"
