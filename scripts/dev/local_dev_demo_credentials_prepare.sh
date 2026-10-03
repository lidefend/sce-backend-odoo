#!/usr/bin/env bash
set -euo pipefail

# sc-local-dev is an isolated local demo database used for repeated developer
# verification. Owner decision (2026-10-03): that profile uses one fixed,
# intentionally simple demo credential so a developer can log in without
# reading a per-install secret. The per-install random path stays available
# with SC_DEV_DEMO_PASSWORD_MODE=random. This script never reads the database
# password, the JWT secret or any tenant credential; the fixed value below is
# valid only inside sc-local-dev.
FIXED_DEV_DEMO_PASSWORD="scdevpass"
MODE="${SC_DEV_DEMO_PASSWORD_MODE:-fixed}"
case "${MODE}" in
  fixed|random) ;;
  *)
    echo "[local.dev.credentials] DENY unknown SC_DEV_DEMO_PASSWORD_MODE=${MODE}" >&2
    exit 2
    ;;
esac

: "${ROOT_DIR:?ROOT_DIR is required}"
target="${TARGET_ENV_FILE:-${ROOT_DIR}/.env.dev}"
expected="/home/lidefend/workspace/sce-backend-odoo/.env.dev"
resolved="$(readlink -f -- "${target}")"

[[ "${resolved}" == "${expected}" && -f "${target}" && ! -L "${target}" ]] || {
  echo "[local.dev.credentials] DENY non-canonical env file" >&2
  exit 2
}
[[ "$(stat -c '%u' "${target}")" == "$(id -u)" ]] || {
    echo "[local.dev.credentials] DENY env ownership mismatch" >&2
    exit 2
  }
if [[ "$(stat -c '%a' "${target}")" != "600" ]]; then
  chmod 600 "${target}"
  echo "[local.dev.credentials] restricted canonical env mode to 600"
fi

for exact in \
  'COMPOSE_PROJECT_NAME=sc-local-dev' \
  'DB_NAME=sc_dev_demo' \
  'ODOO_DBFILTER=^sc_dev_demo$' \
  'DB_DATA=sc_local_dev_db_data' \
  'REDIS_DATA=sc_local_dev_redis_data' \
  'ODOO_DATA=sc_local_dev_odoo_data'; do
  [[ "$(grep -Fxc -- "${exact}" "${target}")" == "1" ]] || {
    echo "[local.dev.credentials] DENY feature-demo identity mismatch" >&2
    exit 2
  }
done

count="$(grep -c '^SC_DEMO_USER_PASSWORD=' "${target}" || true)"
if [[ "${count}" == "1" ]]; then
  value="$(sed -n 's/^SC_DEMO_USER_PASSWORD=//p' "${target}")"
  [[ "${value}" =~ ^[0-9a-f]{64}$ || "${value}" == "${FIXED_DEV_DEMO_PASSWORD}" ]] || {
    echo "[local.dev.credentials] DENY invalid existing demo credential" >&2
    exit 2
  }
  if [[ "${MODE}" == "fixed" && "${value}" != "${FIXED_DEV_DEMO_PASSWORD}" ]]; then
    sed -i "s|^SC_DEMO_USER_PASSWORD=.*|SC_DEMO_USER_PASSWORD=${FIXED_DEV_DEMO_PASSWORD}|" "${target}"
    chmod 600 "${target}"
    echo "[local.dev.credentials] switched canonical demo credential to the fixed dev value"
    exit 0
  fi
  if [[ "${MODE}" == "random" && "${value}" == "${FIXED_DEV_DEMO_PASSWORD}" ]]; then
    value="$(openssl rand -hex 32)"
    sed -i "s|^SC_DEMO_USER_PASSWORD=.*|SC_DEMO_USER_PASSWORD=${value}|" "${target}"
    chmod 600 "${target}"
    echo "[local.dev.credentials] created canonical demo credential; value not printed"
    exit 0
  fi
  echo "[local.dev.credentials] reuse canonical demo credential"
  exit 0
fi
[[ "${count}" == "0" ]] || {
  echo "[local.dev.credentials] DENY duplicate demo credential" >&2
  exit 2
}

if [[ "${MODE}" == "fixed" ]]; then
  value="${FIXED_DEV_DEMO_PASSWORD}"
  note="created canonical demo credential; fixed dev value"
else
  value="$(openssl rand -hex 32)"
  note="created canonical demo credential; value not printed"
fi
printf '\nSC_DEMO_USER_PASSWORD=%s\n' "${value}" >>"${target}"
chmod 600 "${target}"
echo "[local.dev.credentials] ${note}"
