#!/usr/bin/env bash
set -euo pipefail
: "${ROOT_DIR:?ROOT_DIR required}"
source "${ROOT_DIR}/scripts/common/env.sh"
[[ "${ENV}" == dev && "${COMPOSE_PROJECT_NAME}" == sc-local-dev && "${DB_NAME}" == sc_dev_demo && "${ODOO_DBFILTER}" == '^sc_dev_demo$' && "${NGINX_PORT}" == 18081 ]]
export SC_DEMO_USER_PASSWORD DB_NAME COMPOSE_PROJECT_NAME FRONTEND_DIST_DIR
if [[ "${PRODUCT_PERFORMANCE_BROWSER_SCOPE:-}" == "dev-acceptance-remediation" ]]; then
  if [[ "${DEV_ACCEPTANCE_ONLY:-}" == "record" ]]; then
    [[ -z "$(git -C "${ROOT_DIR}" status --porcelain=v1 --untracked-files=all)" ]] || {
      echo "record identity evidence requires a clean worktree" >&2
      exit 1
    }
    export DEV_ACCEPTANCE_EXPECTED_BUILD_SHA="${DEV_ACCEPTANCE_EXPECTED_BUILD_SHA:-$(git -C "${ROOT_DIR}" rev-parse HEAD)}"
  fi
  exec node scripts/verify/local_dev_dev_acceptance_remediation_browser.mjs
fi
exec node scripts/verify/local_dev_runtime_performance_browser.mjs
