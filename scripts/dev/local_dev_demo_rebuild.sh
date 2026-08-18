#!/usr/bin/env bash
set -euo pipefail

: "${ROOT_DIR:?ROOT_DIR is required}"
source "${ROOT_DIR}/scripts/common/env.sh"
source "${ROOT_DIR}/scripts/common/compose.sh"

[[ "${ENV}" == "dev" \
  && "${COMPOSE_PROJECT_NAME}" == "sc-local-dev" \
  && "${DB_NAME}" == "sc_dev_demo" \
  && "${ODOO_DBFILTER}" == '^sc_dev_demo$' \
  && "${DB_DATA}" == "sc_local_dev_db_data" \
  && "${REDIS_DATA}" == "sc_local_dev_redis_data" \
  && "${ODOO_DATA}" == "sc_local_dev_odoo_data" ]] || {
    echo "[local.dev.rebuild] DENY feature-demo identity mismatch" >&2
    exit 2
  }

[[ "${CONFIRM_LOCAL_DEV_DEMO_REBUILD:-}" == "REBUILD_CURRENT_FEATURE_DEMO" ]] || {
  echo "[local.dev.rebuild] confirmation required: CONFIRM_LOCAL_DEV_DEMO_REBUILD=REBUILD_CURRENT_FEATURE_DEMO" >&2
  exit 2
}

echo "[local.dev.rebuild] initialize infrastructure project=${COMPOSE_PROJECT_NAME} db=${DB_NAME}"
compose_dev up -d db redis
db_cid="$(compose_dev ps -q db)"
for _ in $(seq 1 60); do
  state="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${db_cid}")"
  [[ "${state}" == "healthy" ]] && break
  sleep 2
done
[[ "${state:-}" == "healthy" ]] || {
  echo "[local.dev.rebuild] database did not become healthy" >&2
  exit 1
}

# Rebuild is also safe when repeated against a running feature-demo lifecycle.
compose_dev stop nginx odoo >/dev/null 2>&1 || true
export SC_ENVIRONMENT=demo
export SC_ALLOW_DEMO_DATA=1
if ! bash "${ROOT_DIR}/scripts/demo/reset.sh"; then
  echo "[local.dev.rebuild] demo installation failed; inspect with make local.dev.logs" >&2
  exit 1
fi
if ! DEMO_RESTART_AFTER_LOAD=0 bash "${ROOT_DIR}/scripts/demo/load_full.sh"; then
  echo "[local.dev.rebuild] full demo load failed; inspect with make local.dev.logs" >&2
  exit 1
fi
compose_dev up -d
bash "${ROOT_DIR}/scripts/dev/local_environment_health.sh" persistent
echo "[local.dev.rebuild] PASS project=${COMPOSE_PROJECT_NAME} db=${DB_NAME}"
