#!/usr/bin/env bash
set -euo pipefail

lock="${PRODUCTION_RELEASE_SET_LOCK:?PRODUCTION_RELEASE_SET_LOCK is required}"
[[ "${ENV:-}" == "prod" && "${PRODUCTION_COMPOSE_PROJECT:-}" == "sc_production" ]] || {
  echo "PRODUCTION_OPERATOR_TARGET_INVALID" >&2
  exit 2
}
[[ "${TARGET_DB:-}" == "sc_production" && "${TENANT_PAYLOAD_DB_ALLOWLIST:-}" == "sc_production" ]] || {
  echo "PRODUCTION_OPERATOR_DATABASE_INVALID" >&2
  exit 2
}
[[ -n "${APPROVED_BY:-}" ]] || { echo "APPROVED_BY is required" >&2; exit 2; }
python3 scripts/release/production_release_set.py validate --lock "$lock"

field() {
  python3 scripts/release/production_release_set.py operator-field --lock "$lock" --field "$1"
}

identity_type="$(field identity_type)"
identity_key="$(field identity_key)"
tenant_key="$(field tenant_key)"
customer_modules="$(python3 scripts/release/production_release_set.py modules --lock "$lock")"
direct_grant_targets="$(field direct_grant_targets)"
transitive_implied_closure="$(field importer_transitive_implied_closure)"
required_existing_groups="$(field required_existing_operator_groups)"
expected_direct_additions="$(field expected_direct_grant_additions)"
expected_effective_additions="$(field expected_effective_group_additions)"
expected_undeclared_additions="$(field expected_undeclared_group_additions)"
expected_company_scope="$(field expected_company_scope)"
scope_version="$(field grant_scope_version)"

docker compose -p sc_production \
  -f docker-compose.production-candidate.yml \
  -f docker-compose.production-customer.yml \
  run --rm --no-deps -T --user odoo \
  -e SC_MAINTENANCE_HTTP_DISABLED=1 \
  -e "SC_TENANT_PAYLOAD_OPERATOR_IDENTITY_TYPE=$identity_type" \
  -e "SC_TENANT_PAYLOAD_OPERATOR_IDENTITY_KEY=$identity_key" \
  -e "SC_TENANT_PAYLOAD_TENANT_KEY=$tenant_key" \
  -e "SC_PRODUCTION_CUSTOMER_MODULES=$customer_modules" \
  -e "SC_TENANT_PAYLOAD_DIRECT_GRANT_TARGETS=$direct_grant_targets" \
  -e "SC_TENANT_PAYLOAD_TRANSITIVE_IMPLIED_CLOSURE=$transitive_implied_closure" \
  -e "SC_TENANT_PAYLOAD_REQUIRED_EXISTING_GROUPS=$required_existing_groups" \
  -e "SC_TENANT_PAYLOAD_EXPECTED_DIRECT_ADDITIONS=$expected_direct_additions" \
  -e "SC_TENANT_PAYLOAD_EXPECTED_EFFECTIVE_ADDITIONS=$expected_effective_additions" \
  -e "SC_TENANT_PAYLOAD_EXPECTED_UNDECLARED_ADDITIONS=$expected_undeclared_additions" \
  -e "SC_TENANT_PAYLOAD_EXPECTED_COMPANY_SCOPE=$expected_company_scope" \
  -e "SC_TENANT_PAYLOAD_GRANT_SCOPE_VERSION=$scope_version" \
  -e SC_TENANT_PAYLOAD_DB_ALLOWLIST=sc_production \
  -e "SC_TENANT_PAYLOAD_APPROVED_BY=$APPROVED_BY" \
  --entrypoint /usr/local/bin/production-maintenance odoo operator-grant
