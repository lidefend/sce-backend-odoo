#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
source "$ROOT_DIR/scripts/common/frontend_acceptance_guard.sh"

guard_frontend_acceptance_scope

if [[ -z "${SC_ACCEPTANCE_FIXTURE_PASSWORD:-}" ]]; then
  echo "[DENY] delivery business success requires SC_ACCEPTANCE_FIXTURE_PASSWORD" >&2
  exit 24
fi

if [[ "${ROLE_FINANCE_LOGIN:-}" != "fixture_role_finance" ]]; then
  echo "[DENY] delivery business success requires ROLE_FINANCE_LOGIN=fixture_role_finance" >&2
  exit 25
fi

if [[ "${ROLE_EXECUTIVE_LOGIN:-}" != "fixture_role_executive" ]]; then
  echo "[DENY] delivery business success requires ROLE_EXECUTIVE_LOGIN=fixture_role_executive" >&2
  exit 26
fi

echo "[delivery.acceptance.scope] PASS db=${DB_NAME} fixture=P4"
