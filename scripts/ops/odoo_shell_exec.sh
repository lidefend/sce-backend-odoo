#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../_lib/common.sh"

DB_NAME="${DB_NAME:-}"
if [[ -z "$DB_NAME" ]]; then
  echo "❌ DB_NAME is required" >&2
  exit 2
fi

ENV_FORWARD_ARGS=()
while IFS='=' read -r env_name _; do
  case "$env_name" in
    APPLY|ARCHIVE_*|MIGRATION_*|DIRECT_ACCEPTANCE_*|FRESH_DB_*|LEGACY_USER_*|LEGACY_ATTACHMENT_*|PROJECT_ANCHOR_*|PROJECT_MASTER_*|BUSINESS_FACT_*|BUSINESS_CONFIG_*|PRODUCT_*|CONTRACT_*|CONSTRUCTION_CONTRACT_*|SUPPLIER_CONTRACT_*|LOWCODE_*|NAV_PRO_*|PLATFORM_RELEASE_*|SC_COLOCATED_PLATFORM_SNAPSHOT_APPLY|SC_RUNTIME_*|SC_CONFIRM_*|SC_ACCEPTANCE_*|SC_TENANT_PAYLOAD_*|LEGACY_55_*|ROLE_*|USER_DATA_*|DEMO_OWNERSHIP_*|SC_DEMO_OWNERSHIP_CLEANUP_APPROVED|SOURCE_DATABASE_FINGERPRINT|APPROVED_BY|SC_ENVIRONMENT|SC_ALLOW_DEMO_DATA|PARTNER_ASSET_XML|PARTNER_BUSINESS_ALIGNED_GATE_CSV|PARTNER_FACT_ALIGNMENT_*|PARTNER_PROFILE_BACKFILL_*|PARTNER_SOURCE_CREATOR_*)
      if [[ -n "${!env_name:-}" ]]; then
        ENV_FORWARD_ARGS+=("-e" "${env_name}=${!env_name}")
      fi
      ;;
  esac
done < <(env)

if [[ "${ODOO_SHELL_RUN_ISOLATED:-0}" == "1" ]]; then
  # The acceptance fixture must not depend on the lifecycle or stale mounts of
  # the daily Odoo service. Compose run creates a disposable shell carrier with
  # the currently declared volumes and removes it after the transaction.
  # shellcheck disable=SC2086
  compose ${COMPOSE_FILES} run --rm --no-deps -T --entrypoint odoo "${ENV_FORWARD_ARGS[@]}" \
    -e ODOO_DB="$DB_NAME" -e DB_NAME="$DB_NAME" \
    -e ODOO_DBFILTER="^${DB_NAME//./\\.}\$" \
    -e DB_HOST="${DB_HOST:-db}" -e DB_PORT="${DB_PORT:-5432}" \
    -e DB_USER="$DB_USER" -e DB_PASSWORD="$DB_PASSWORD" \
    -e ADMIN_PASSWD="$ADMIN_PASSWD" -e JWT_SECRET="$JWT_SECRET" \
    odoo shell -d "$DB_NAME" -c /var/lib/odoo/odoo.conf
else
  # shellcheck disable=SC2086
  compose ${COMPOSE_FILES} exec -T "${ENV_FORWARD_ARGS[@]}" odoo odoo shell -d "$DB_NAME" -c /var/lib/odoo/odoo.conf
fi
