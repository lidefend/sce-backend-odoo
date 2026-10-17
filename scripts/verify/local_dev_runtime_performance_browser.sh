#!/usr/bin/env bash
set -euo pipefail
: "${ROOT_DIR:?ROOT_DIR required}"
source "${ROOT_DIR}/scripts/common/env.sh"
[[ "${ENV}" == dev && "${COMPOSE_PROJECT_NAME}" == sc-local-dev && "${DB_NAME}" == sc_dev_demo && "${ODOO_DBFILTER}" == '^sc_dev_demo$' && "${NGINX_PORT}" == 18081 ]]
export SC_DEMO_USER_PASSWORD DB_NAME COMPOSE_PROJECT_NAME FRONTEND_DIST_DIR
exec node scripts/verify/local_dev_runtime_performance_browser.mjs
