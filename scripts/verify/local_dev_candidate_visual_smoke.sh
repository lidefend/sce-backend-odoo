#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:?ROOT_DIR is required}"
ENV_FILE="${ENV_FILE:?ENV_FILE is required}"
[[ -f "${ENV_FILE}" ]] || { echo "local.dev env authority is missing" >&2; exit 2; }

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

[[ "${COMPOSE_PROJECT_NAME:-}" == "sc-local-dev" ]] || { echo "expected sc-local-dev" >&2; exit 2; }
[[ "${DB_NAME:-}" == "sc_dev_demo" ]] || { echo "expected sc_dev_demo" >&2; exit 2; }
[[ -n "${SC_DEMO_USER_PASSWORD:-}" ]] || { echo "SC_DEMO_USER_PASSWORD is required" >&2; exit 2; }

FRONTEND_URL="${FRONTEND_URL:?FRONTEND_URL is required}" \
DB_NAME="${DB_NAME}" \
E2E_LOGIN="${CANDIDATE_VISUAL_LOGIN:-sc_test_admin}" \
E2E_PASSWORD="${SC_DEMO_USER_PASSWORD}" \
CANDIDATE_GIT_HEAD="${CANDIDATE_GIT_HEAD:?CANDIDATE_GIT_HEAD is required}" \
CANDIDATE_VISUAL_ROUTES_JSON="${CANDIDATE_VISUAL_ROUTES_JSON:?CANDIDATE_VISUAL_ROUTES_JSON is required}" \
node "${ROOT_DIR}/scripts/verify/local_dev_candidate_visual_smoke.mjs"
