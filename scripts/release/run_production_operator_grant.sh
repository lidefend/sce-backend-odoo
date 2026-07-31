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
target_group="$(field target_group_xmlid)"
expected_before="$(field expected_membership_before)"
expected_after="$(field expected_membership_after)"
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
  -e "SC_TENANT_PAYLOAD_TARGET_GROUP_XMLID=$target_group" \
  -e "SC_TENANT_PAYLOAD_EXPECTED_MEMBERSHIP_BEFORE=$expected_before" \
  -e "SC_TENANT_PAYLOAD_EXPECTED_MEMBERSHIP_AFTER=$expected_after" \
  -e "SC_TENANT_PAYLOAD_EXPECTED_COMPANY_SCOPE=$expected_company_scope" \
  -e "SC_TENANT_PAYLOAD_GRANT_SCOPE_VERSION=$scope_version" \
  -e SC_TENANT_PAYLOAD_DB_ALLOWLIST=sc_production \
  -e "SC_TENANT_PAYLOAD_APPROVED_BY=$APPROVED_BY" \
  --entrypoint /usr/local/bin/production-maintenance odoo operator-grant
