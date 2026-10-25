#!/usr/bin/env bash
set -euo pipefail
: "${ENV_FILE:?governed environment is required}"
set -a
source "$ENV_FILE"
set +a
[[ "${COMPOSE_PROJECT_NAME:-}" == sc-local-dev && "${DB_NAME:-}" == sc_dev_demo && "${NGINX_PORT:-}" == 18081 ]]
: "${SC_DEMO_USER_PASSWORD:?canonical demo credential required}"
E2E_PASSWORD="$SC_DEMO_USER_PASSWORD" node scripts/verify/local_dev_workspace_feedback.mjs
