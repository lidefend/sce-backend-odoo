#!/usr/bin/env bash
set -euo pipefail
: "${SC_GOVERNED_FRONTEND_DB_ENSURE_ENTRY:?DENY: use make db.frontend.acceptance.ensure; direct entry execution is forbidden}"

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
export ROOT_DIR
source "$ROOT_DIR/scripts/common/governed_make_entry.sh"
require_governed_make_ancestor "frontend_acceptance_db_ensure_entry.sh" "$ROOT_DIR" "db.frontend.acceptance.ensure"

if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
  source "$ROOT_DIR/scripts/common/frontend_release_ci_identity.sh"
  validate_frontend_release_ci_identity "$ROOT_DIR"
  # Identity validation must complete before this first CI side effect.
  source "$ROOT_DIR/scripts/common/compose.sh"
  compose_dev up -d --wait db redis odoo
  SC_GOVERNED_FRONTEND_DB_ENSURE_LOWER_ENTRY=1 bash "$ROOT_DIR/scripts/test/frontend_acceptance_db_ensure.sh"
else
  SC_GOVERNED_ACCEPTANCE_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="${SC_ACCEPTANCE_RUNTIME_PROFILE:-local}" bash "$ROOT_DIR/scripts/dev/frontend_acceptance_runtime.sh" db-ensure
fi
