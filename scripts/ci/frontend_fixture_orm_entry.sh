#!/usr/bin/env bash
set -euo pipefail
: "${SC_FRONTEND_RELEASE_CI_ENTRY:?DENY: use acceptance.frontend.fixture_orm}"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
export ROOT_DIR
if [[ "${GITHUB_ACTIONS:-}" != true ]]; then
  exec bash "$ROOT_DIR/scripts/dev/frontend_acceptance_operation_entry.sh" fixture-orm
fi
# ORM-only CI routing does not change the local preview or browser lifecycle.
source "$ROOT_DIR/config/acceptance/isolated_entry_identity.v1.env"
export SC_ENTRY_NAMESPACE SC_ENTRY_AUDIENCE SC_ENTRY_SHARED_SECRET SC_ENTRY_ROUTE_VERSION
source "$ROOT_DIR/scripts/common/frontend_release_ci_identity.sh"
verify_frozen_frontend_release_ci_identity "$ROOT_DIR"
validate_frozen_frontend_release_ci_resources "$ROOT_DIR" required
bash "$ROOT_DIR/scripts/test/frontend_acceptance_fixture_orm.sh"
validate_frozen_frontend_release_ci_resources "$ROOT_DIR" required
