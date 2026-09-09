#!/usr/bin/env bash
set -euo pipefail

: "${ROOT_DIR:?ROOT_DIR is required}"
: "${COMPOSE_PROJECT_NAME:?COMPOSE_PROJECT_NAME is required}"
: "${DB_NAME:?DB_NAME is required}"
: "${ODOO_DBFILTER:?ODOO_DBFILTER is required}"
: "${DB_DATA:?DB_DATA is required}"
: "${REDIS_DATA:?REDIS_DATA is required}"
: "${ODOO_DATA:?ODOO_DATA is required}"
: "${DB_USER:?DB_USER is required}"

# shellcheck source=../common/compose.sh
source "$ROOT_DIR/scripts/common/compose.sh"
# shellcheck source=../common/frontend_acceptance_guard.sh
source "$ROOT_DIR/scripts/common/frontend_acceptance_guard.sh"

readonly EXPECTED_PROJECT="sc-fe-r2-p1-01"
readonly EXPECTED_DATABASE="sc_frontend_acceptance"
readonly EXPECTED_FILTER='^sc_frontend_acceptance$'
readonly EXPECTED_DB_VOLUME="sc_fe_r2_p1_01_db"
readonly EXPECTED_REDIS_VOLUME="sc_fe_r2_p1_01_redis"
readonly EXPECTED_ODOO_VOLUME="sc_fe_r2_p1_01_odoo"
readonly RECOVERY_ROOT="/home/lidefend/workspace/sce-offrepo/artifacts/frontend-acceptance/recovery"

require_exact_identity() {
  [[ "$COMPOSE_PROJECT_NAME" == "$EXPECTED_PROJECT" \
    && "$DB_NAME" == "$EXPECTED_DATABASE" \
    && "$ODOO_DBFILTER" == "$EXPECTED_FILTER" \
    && "$DB_DATA" == "$EXPECTED_DB_VOLUME" \
    && "$REDIS_DATA" == "$EXPECTED_REDIS_VOLUME" \
    && "$ODOO_DATA" == "$EXPECTED_ODOO_VOLUME" \
    && "${SC_ENVIRONMENT:-}" == "acceptance" \
    && "${SC_ALLOW_DEMO_DATA:-}" == "1" ]] || {
      echo "[acceptance.baseline.rebuild] DENY managed acceptance identity mismatch" >&2
      exit 2
    }
}

require_expected_head() {
  local actual_head="${1:?actual head is required}"
  [[ "${EXPECTED_HEAD:-}" =~ ^[0-9a-f]{40}$ && "$EXPECTED_HEAD" == "$actual_head" ]] || {
    echo "[acceptance.baseline.rebuild] DENY EXPECTED_HEAD must equal current 40-character HEAD=$actual_head" >&2
    exit 2
  }
}

database_scalar() {
  local sql="$1"
  local db_cid
  db_cid="$(compose_dev ps -q db)"
  [[ -n "$db_cid" ]] || { echo "[acceptance.baseline.rebuild] DENY database carrier is absent" >&2; exit 2; }
  docker exec "$db_cid" psql -X -Aqt -v ON_ERROR_STOP=1 -U "$DB_USER" -d "$DB_NAME" -c "$sql"
}

audit() {
  local module_version db_size attachment_count user_count fixture_xmlids redis_keys filestore_bytes filestore_files compatible_backup
  module_version="$(database_scalar "SELECT COALESCE(latest_version, '') FROM ir_module_module WHERE name = 'smart_construction_core'")"
  db_size="$(database_scalar 'SELECT pg_database_size(current_database())')"
  attachment_count="$(database_scalar 'SELECT count(*) FROM ir_attachment')"
  user_count="$(database_scalar 'SELECT count(*) FROM res_users')"
  fixture_xmlids="$(database_scalar "SELECT count(*) FROM ir_model_data WHERE module = 'smart_construction_acceptance_fixture'")"
  redis_keys="$(docker exec "${COMPOSE_PROJECT_NAME}-redis-1" redis-cli DBSIZE | tr -dc '0-9')"
  filestore_bytes="$(docker run --rm -v "${ODOO_DATA}:/source:ro" alpine:3.20 sh -ceu 'du -sb /source | cut -f1')"
  filestore_files="$(docker run --rm -v "${ODOO_DATA}:/source:ro" alpine:3.20 sh -ceu 'find /source -type f | wc -l')"
  compatible_backup="not_found"
  if [[ -d "$RECOVERY_ROOT" ]] && grep -RFlx 'source_module_version=17.0.0.162' "$RECOVERY_ROOT"/*/manifest.txt >/dev/null 2>&1; then
    compatible_backup="available"
  fi
  printf '%s\n' \
    "[acceptance.baseline.audit] PASS profile=local project=$COMPOSE_PROJECT_NAME database=$DB_NAME dbfilter=$ODOO_DBFILTER" \
    "[acceptance.baseline.audit] lifecycle database_volume=$DB_DATA filestore_volume=$ODOO_DATA session_volume=$REDIS_DATA" \
    "[acceptance.baseline.audit] current smart_construction_core=$module_version database_bytes=$db_size users=$user_count attachments=$attachment_count fixture_xmlids=$fixture_xmlids" \
    "[acceptance.baseline.audit] filestore_bytes=$filestore_bytes filestore_files=$filestore_files redis_keys=$redis_keys" \
    "[acceptance.baseline.audit] classification=platform_internal_acceptance fixture_allowed=true customer_business_data_allowed=false" \
    "[acceptance.baseline.audit] compatible_162_backup=$compatible_backup recovery_root=$RECOVERY_ROOT"
}

archive_volume() {
  local volume="$1" output="$2"
  docker run --rm -v "${volume}:/source:ro" alpine:3.20 sh -ceu 'tar -C /source -czf - .' >"$output"
}

restore_volume() {
  local volume="$1" archive="$2"
  docker volume create "$volume" >/dev/null
  docker run --rm -v "${volume}:/target" -v "${archive}:/backup.tar.gz:ro" alpine:3.20 \
    sh -ceu 'tar -C /target -xzf /backup.tar.gz'
}

restore_recovery_bundle() {
  local bundle="$1"
  echo "[acceptance.baseline.rebuild] restoring recovery bundle=$bundle" >&2
  compose_dev down --remove-orphans >/dev/null 2>&1 || true
  for volume in "$DB_DATA" "$REDIS_DATA" "$ODOO_DATA"; do
    docker volume rm "$volume" >/dev/null 2>&1 || true
  done
  restore_volume "$REDIS_DATA" "$bundle/redis-volume.tar.gz"
  restore_volume "$ODOO_DATA" "$bundle/odoo-volume.tar.gz"
  compose_dev up -d --wait db
  docker exec -i "$(compose_dev ps -q db)" pg_restore \
    -U "$DB_USER" -d "$DB_NAME" --clean --if-exists --no-owner --no-privileges \
    <"$bundle/database.dump"
  compose_dev up -d --wait redis
  compose_dev create odoo >/dev/null
  echo "[acceptance.baseline.rebuild] RECOVERED bundle=$bundle" >&2
}

rebuild() {
  local actual_head backend_present frontend_present snapshot_id bundle db_cid module_version destructive_started
  actual_head="$(git -C "$ROOT_DIR" rev-parse HEAD)"
  require_expected_head "$actual_head"
  printf '%s\n' \
    "[acceptance.baseline.rebuild.plan] project=$COMPOSE_PROJECT_NAME database=$DB_NAME dbfilter=$ODOO_DBFILTER" \
    "[acceptance.baseline.rebuild.plan] exact_volumes=$DB_DATA,$REDIS_DATA,$ODOO_DATA" \
    "[acceptance.baseline.rebuild.plan] safeguard=cold_database_filestore_session_bundle root=$RECOVERY_ROOT" \
    "[acceptance.baseline.rebuild.plan] action=stop_carriers,backup,verify,remove_exact_volumes,recreate_empty_managed_infrastructure" \
    "[acceptance.baseline.rebuild.plan] post_action=make_db_ensure_then_fixture_snapshot_and_release_gate"
  if [[ "${APPLY:-0}" != "1" ]]; then
    echo "[acceptance.baseline.rebuild.plan] DRY_RUN PASS expected_head=$EXPECTED_HEAD"
    exit 0
  fi
  [[ "${CONFIRM_ACCEPTANCE_BASELINE_REBUILD:-}" == "REBUILD_DISPOSABLE_FRONTEND_ACCEPTANCE" ]] || {
    echo "[acceptance.baseline.rebuild] DENY exact destructive confirmation is required" >&2
    exit 2
  }
  [[ -z "$(git -C "$ROOT_DIR" status --porcelain=v2 --untracked-files=all)" ]] || {
    echo "[acceptance.baseline.rebuild] DENY worktree must be clean" >&2
    exit 2
  }
  frontend_present=0
  [[ ! -e "${FRONTEND_ACCEPTANCE_PIDFILE:-/tmp/sc-frontend-acceptance.pid}" ]] || frontend_present=1
  backend_present="$(docker inspect "${BACKEND_ACCEPTANCE_NAME:-sc-backend-odoo-acceptance}" --format '{{.Id}}' 2>/dev/null || true)"
  [[ "$frontend_present" == "0" && -z "$backend_present" ]] || {
    echo "[acceptance.baseline.rebuild] DENY frontend and standalone backend carriers must be stopped first" >&2
    exit 2
  }

  acquire_frontend_acceptance_lock baseline-rebuild
  snapshot_id="$(date -u +%Y%m%dT%H%M%SZ)-${actual_head:0:12}"
  bundle="$RECOVERY_ROOT/$snapshot_id"
  mkdir -p "$bundle"
  chmod 700 "$RECOVERY_ROOT" "$bundle"
  compose_dev stop odoo nginx >/dev/null 2>&1 || true
  db_cid="$(compose_dev ps -q db)"
  module_version="$(database_scalar "SELECT COALESCE(latest_version, '') FROM ir_module_module WHERE name = 'smart_construction_core'")"
  docker exec "$db_cid" pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc >"$bundle/database.dump"
  archive_volume "$ODOO_DATA" "$bundle/odoo-volume.tar.gz"
  docker exec "${COMPOSE_PROJECT_NAME}-redis-1" redis-cli SAVE >/dev/null
  compose_dev stop redis >/dev/null
  archive_volume "$REDIS_DATA" "$bundle/redis-volume.tar.gz"
  cat >"$bundle/manifest.txt" <<EOF
schema=frontend_acceptance_recovery_bundle.v1
status=complete
source_head=$actual_head
source_module_version=$module_version
compose_project=$COMPOSE_PROJECT_NAME
database=$DB_NAME
database_filter=$ODOO_DBFILTER
database_volume=$DB_DATA
session_volume=$REDIS_DATA
filestore_volume=$ODOO_DATA
EOF
  (cd "$bundle" && sha256sum database.dump odoo-volume.tar.gz redis-volume.tar.gz >SHA256SUMS)
  (cd "$bundle" && sha256sum -c SHA256SUMS)
  docker run --rm -v "$bundle:/backup:ro" postgres:15-alpine pg_restore --list /backup/database.dump >/dev/null

  destructive_started=0
  rollback_on_failure() {
    local status=$?
    if [[ "$status" != "0" && "$destructive_started" == "1" ]]; then
      restore_recovery_bundle "$bundle" || echo "[acceptance.baseline.rebuild] FATAL automatic recovery failed bundle=$bundle" >&2
    fi
    exit "$status"
  }
  trap rollback_on_failure EXIT
  destructive_started=1
  compose_dev down --remove-orphans
  for volume in "$DB_DATA" "$REDIS_DATA" "$ODOO_DATA"; do
    docker volume rm "$volume" >/dev/null
  done
  compose_dev up -d --wait db redis
  compose_dev create odoo >/dev/null
  destructive_started=0
  trap - EXIT
  echo "[acceptance.baseline.rebuild] PASS empty_infrastructure_ready=true recovery_bundle=$bundle"
}

require_exact_identity
case "${1:-audit}" in
  audit) audit ;;
  rebuild) rebuild ;;
  *) echo "usage: $0 audit|rebuild" >&2; exit 2 ;;
esac
