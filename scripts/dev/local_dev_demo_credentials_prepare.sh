#!/usr/bin/env bash
set -euo pipefail

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
  [[ "${value}" =~ ^[0-9a-f]{64}$ ]] || {
    echo "[local.dev.credentials] DENY invalid existing demo credential" >&2
    exit 2
  }
  echo "[local.dev.credentials] reuse canonical demo credential"
  exit 0
fi
[[ "${count}" == "0" ]] || {
  echo "[local.dev.credentials] DENY duplicate demo credential" >&2
  exit 2
}

value="$(openssl rand -hex 32)"
printf '\nSC_DEMO_USER_PASSWORD=%s\n' "${value}" >>"${target}"
chmod 600 "${target}"
echo "[local.dev.credentials] created canonical demo credential; value not printed"
