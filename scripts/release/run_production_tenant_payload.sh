#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../_lib/common.sh"

action="${SC_TENANT_PAYLOAD_ACTION:-}"
[[ "$action" =~ ^(plan|import|verify)$ ]] || { echo "PRODUCTION_TPV1_ACTION_INVALID" >&2; exit 2; }
[[ "${ENV:-}" == "prod" && "${PRODUCTION_COMPOSE_PROJECT:-}" == "sc_production" ]] || {
  echo "PRODUCTION_TPV1_TARGET_INVALID" >&2; exit 2;
}
[[ "${TARGET_DB:-}" == "sc_production" && "${DB_NAME:-}" == "sc_production" ]] || {
  echo "PRODUCTION_TPV1_DATABASE_INVALID" >&2; exit 2;
}
[[ -n "${PRODUCTION_RELEASE_SET_LOCK:-}" ]] || { echo "PRODUCTION_RELEASE_SET_LOCK_REQUIRED" >&2; exit 2; }
python3 scripts/release/production_release_set.py validate --lock "$PRODUCTION_RELEASE_SET_LOCK"

payload_root="$(realpath "${TENANT_PAYLOAD:?TENANT_PAYLOAD is required}")"
customer_root="$(realpath "${SC_CUSTOMER_ADDONS_ROOT:?SC_CUSTOMER_ADDONS_ROOT is required}")"
public_key="$(realpath "${SC_TENANT_PAYLOAD_PUBLIC_KEY:?SC_TENANT_PAYLOAD_PUBLIC_KEY is required}")"
for path in "$payload_root" "$customer_root" "$public_key"; do
  [[ ! -L "$path" ]] || { echo "PRODUCTION_TPV1_SYMLINK_FORBIDDEN" >&2; exit 2; }
done
case "$payload_root:$customer_root" in
  *"/data/odoo/legacy_attachments"*) echo "PRODUCTION_TPV1_LEGACY_ATTACHMENTS_FORBIDDEN" >&2; exit 2;;
esac
locked_tenant="$(python3 scripts/release/production_release_set.py tenant --lock "$PRODUCTION_RELEASE_SET_LOCK")"
[[ "${TENANT_KEY:-}" == "$locked_tenant" ]] || { echo "PRODUCTION_TPV1_TENANT_INVALID" >&2; exit 2; }
[[ "${TENANT_PAYLOAD_DB_ALLOWLIST:-}" == "sc_production" ]] || { echo "PRODUCTION_TPV1_ALLOWLIST_INVALID" >&2; exit 2; }
if [[ "$action" == "import" ]]; then
  [[ "${CONFIRM_PRODUCTION_TENANT_PAYLOAD_IMPORT:-}" == "YES_IMPORT_LOCKED_V4_INTO_SC_PRODUCTION" ]] || {
    echo "PRODUCTION_TPV1_IMPORT_CONFIRMATION_REQUIRED" >&2; exit 2;
  }
  [[ "${PROD_DANGER:-}" == "1" ]] || { echo "PRODUCTION_TPV1_DANGER_GUARD_REQUIRED" >&2; exit 2; }
fi

payload_gid="$(stat -c %g "$payload_root")"
export SC_TENANT_PAYLOAD_HOST_GID="$payload_gid"
compose_files=(-f docker-compose.production-candidate.yml -f docker-compose.production-customer.yml -f docker-compose.tenant-payload.yml)
docker compose -p sc_production "${compose_files[@]}" run --rm --no-deps -T \
  --user odoo \
  --volume "$payload_root:/mnt/tenant-payload:ro" \
  --volume "$public_key:/mnt/tenant-payload-public-key:ro" \
  -e "SC_TENANT_PAYLOAD_ACTION=$action" \
  -e "SC_TENANT_PAYLOAD_TENANT_KEY=$locked_tenant" \
  -e "SC_TENANT_PAYLOAD_OPERATOR_LOGIN=${TENANT_PAYLOAD_OPERATOR_LOGIN:?operator login required}" \
  -e SC_TENANT_PAYLOAD_DB_ALLOWLIST=sc_production \
  -e "SC_TENANT_PAYLOAD_APPROVED_CHECKSUM=${APPROVE_PAYLOAD_CHECKSUM:?approved checksum required}" \
  -e "SC_TENANT_PAYLOAD_CHUNK_SIZE=${TENANT_PAYLOAD_CHUNK_SIZE:-100}" \
  -e SC_TENANT_PAYLOAD_PUBLIC_KEY=/mnt/tenant-payload-public-key \
  --entrypoint odoo odoo shell -d sc_production -c /var/lib/odoo/odoo.conf --log-level=error \
  < scripts/tenant_payload/odoo_action.py
