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
readonly EXPECTED_DATABASE_IMAGE="postgres:15"
readonly RECOVERY_ROOT="/home/lidefend/workspace/sce-offrepo/artifacts/frontend-acceptance/recovery"
readonly RECOVERY_PARENT="/home/lidefend/workspace/sce-offrepo/artifacts"

deny() {
  echo "[acceptance.baseline.rebuild] DENY $*" >&2
  return 2
}

require_exact_identity() {
  [[ "$COMPOSE_PROJECT_NAME" == "$EXPECTED_PROJECT" \
    && "$DB_NAME" == "$EXPECTED_DATABASE" \
    && "$ODOO_DBFILTER" == "$EXPECTED_FILTER" \
    && "$DB_DATA" == "$EXPECTED_DB_VOLUME" \
    && "$REDIS_DATA" == "$EXPECTED_REDIS_VOLUME" \
    && "$ODOO_DATA" == "$EXPECTED_ODOO_VOLUME" \
    && "${SC_ENVIRONMENT:-}" == "acceptance" \
    && "${SC_ALLOW_DEMO_DATA:-}" == "1" ]] \
    || deny "managed acceptance identity mismatch"
}

require_expected_head() {
  local actual_head="${1:?actual head is required}"
  [[ "${EXPECTED_HEAD:-}" =~ ^[0-9a-f]{40}$ && "$EXPECTED_HEAD" == "$actual_head" ]] \
    || deny "EXPECTED_HEAD must equal current 40-character HEAD=$actual_head"
}

database_scalar() {
  local sql="$1" db_cid
  db_cid="$(compose_dev ps -q db)"
  [[ -n "$db_cid" ]] || { deny "database carrier is absent"; return; }
  docker exec "$db_cid" psql -X -Aqt -v ON_ERROR_STOP=1 -U "$DB_USER" -d "$DB_NAME" -c "$sql"
}

database_scalar_in() {
  local database="$1" sql="$2" db_cid
  [[ "$database" =~ ^[a-z0-9_]+$ ]] || { deny "unsafe database identifier=$database"; return; }
  db_cid="$(compose_dev ps -q db)"
  [[ -n "$db_cid" ]] || { deny "database carrier is absent"; return; }
  docker exec "$db_cid" psql -X -Aqt -v ON_ERROR_STOP=1 -U "$DB_USER" -d "$database" -c "$sql"
}

database_names() {
  database_scalar "SELECT datname FROM pg_database WHERE datallowconn OR datname = 'template0' ORDER BY datname"
}

user_database_csv() {
  database_scalar "SELECT string_agg(datname, ',' ORDER BY datname) FROM pg_database WHERE datname NOT IN ('postgres', 'template0', 'template1')"
}

volume_metric() {
  local volume="$1" expression="$2"
  docker run --rm -v "${volume}:/source:ro" alpine:3.20 sh -ceu "$expression"
}

require_database_volume_scope() {
  local actual expected item
  local -a expected_items=()
  actual="$(user_database_csv)" || { deny "unable to inventory PostgreSQL databases"; return; }
  expected="${1:-${EXPECTED_DATABASES:-$EXPECTED_DATABASE}}"
  [[ "$expected" =~ ^[a-z0-9_]+(,[a-z0-9_]+)*$ ]] || {
    deny "EXPECTED_DATABASES must be a sorted comma-separated database list"
    return
  }
  IFS=',' read -r -a expected_items <<<"$expected"
  for item in "${expected_items[@]}"; do
    [[ "$item" != postgres && "$item" != template0 && "$item" != template1 ]] || {
      deny "EXPECTED_DATABASES must not include PostgreSQL system databases"
      return
    }
  done
  [[ ",${expected}," == *",${EXPECTED_DATABASE},"* ]] || {
    deny "EXPECTED_DATABASES must include $EXPECTED_DATABASE"
    return
  }
  [[ "$actual" == "$expected" ]] || {
    echo "[acceptance.baseline.rebuild] DENY PostgreSQL volume database scope mismatch expected=$expected actual=$actual" >&2
    return 2
  }
  echo "[acceptance.baseline.precheck] user_database_scope=$actual system_databases=postgres,template0,template1"
}

require_no_database_clients() {
  local active_clients
  active_clients="$(database_scalar "SELECT count(*) FROM pg_stat_activity WHERE pid <> pg_backend_pid() AND backend_type = 'client backend' AND datname IN (SELECT datname FROM pg_database WHERE datname NOT IN ('postgres', 'template0', 'template1'))")" || {
    deny "unable to inspect PostgreSQL client activity"
    return
  }
  [[ "$active_clients" == "0" ]] || {
    deny "PostgreSQL user databases still have active clients count=$active_clients"
    return
  }
  echo "[acceptance.baseline.backup] database_clients_stopped=true"
}

require_volume_mount_scope() {
  local volume="$1" expected_service="$2" container_id project service
  local -a consumers=()
  mapfile -t consumers < <(docker ps -aq --filter "volume=$volume")
  [[ "${#consumers[@]}" -eq 1 ]] || {
    deny "volume=$volume expected one mount consumer service=$expected_service actual=${#consumers[@]}"
    return
  }
  container_id="${consumers[0]}"
  project="$(docker inspect "$container_id" --format '{{index .Config.Labels "com.docker.compose.project"}}')" || return 1
  service="$(docker inspect "$container_id" --format '{{index .Config.Labels "com.docker.compose.service"}}')" || return 1
  [[ "$project" == "$EXPECTED_PROJECT" && "$service" == "$expected_service" ]] || {
    deny "volume=$volume mount owner mismatch project=$project service=$service"
    return
  }
  echo "[acceptance.baseline.precheck] volume=$volume owner_project=$project owner_service=$service"
}

require_carrier_scope() {
  local backend_present frontend_pidfile
  frontend_pidfile="${FRONTEND_ACCEPTANCE_PIDFILE:-/tmp/sc-frontend-acceptance.pid}"
  [[ ! -e "$frontend_pidfile" && ! -L "$frontend_pidfile" ]] || {
    deny "managed frontend carrier must be stopped before rebuild"
    return
  }
  backend_present="$(docker inspect "${BACKEND_ACCEPTANCE_NAME:-sc-backend-odoo-acceptance}" --format '{{.Id}}' 2>/dev/null || true)"
  [[ -z "$backend_present" ]] || {
    deny "standalone acceptance backend carrier must be removed before rebuild"
    return
  }
  require_volume_mount_scope "$DB_DATA" db
  require_volume_mount_scope "$REDIS_DATA" redis
  require_volume_mount_scope "$ODOO_DATA" odoo
}

require_recovery_tools() {
  [[ -d "$RECOVERY_PARENT" && -w "$RECOVERY_PARENT" ]] || {
    deny "recovery artifact parent is absent or not writable: $RECOVERY_PARENT"
    return
  }
  docker image inspect alpine:3.20 >/dev/null 2>&1 || {
    deny "required preloaded image is absent: alpine:3.20"
    return
  }
  docker image inspect "$EXPECTED_DATABASE_IMAGE" >/dev/null 2>&1 || {
    deny "required managed database image is absent: $EXPECTED_DATABASE_IMAGE"
    return
  }
}

pre_execution_checks() {
  local actual_head
  actual_head="$(git -C "$ROOT_DIR" rev-parse HEAD)"
  require_expected_head "$actual_head"
  [[ -z "$(git -C "$ROOT_DIR" status --porcelain=v2 --untracked-files=all)" ]] || {
    deny "worktree must be clean"
    return
  }
  require_carrier_scope
  require_database_volume_scope
  require_recovery_tools
  echo "[acceptance.baseline.precheck] EXECUTABLE_CHECKS PASS expected_head=$EXPECTED_HEAD"
}

compatible_backup_status() {
  if [[ -d "$RECOVERY_ROOT" ]] && grep -RFlx 'source_module_version=17.0.0.162' "$RECOVERY_ROOT"/*/manifest.txt >/dev/null 2>&1; then
    echo available
  else
    echo not_found
  fi
}

audit() {
  local module_version db_size attachment_count user_count fixture_xmlids redis_keys filestore_bytes filestore_files user_databases database_inventory database public_tables odoo_registry
  local -a user_database_items=()
  module_version="$(database_scalar "SELECT COALESCE(latest_version, '') FROM ir_module_module WHERE name = 'smart_construction_core'")"
  db_size="$(database_scalar 'SELECT pg_database_size(current_database())')"
  attachment_count="$(database_scalar 'SELECT count(*) FROM ir_attachment')"
  user_count="$(database_scalar 'SELECT count(*) FROM res_users')"
  fixture_xmlids="$(database_scalar "SELECT count(*) FROM ir_model_data WHERE module = 'smart_construction_acceptance_fixture'")"
  redis_keys="$(docker exec "${COMPOSE_PROJECT_NAME}-redis-1" redis-cli DBSIZE | tr -dc '0-9')"
  filestore_bytes="$(volume_metric "$ODOO_DATA" 'du -sb /source | cut -f1')"
  filestore_files="$(volume_metric "$ODOO_DATA" 'find /source -type f | wc -l')"
  user_databases="$(user_database_csv)"
  database_inventory="$(database_scalar "SELECT string_agg(datname || ':' || pg_database_size(datname), ',' ORDER BY datname) FROM pg_database WHERE datname NOT IN ('template0', 'template1')")"
  require_volume_mount_scope "$DB_DATA" db
  require_volume_mount_scope "$REDIS_DATA" redis
  require_volume_mount_scope "$ODOO_DATA" odoo
  printf '%s\n' \
    "[acceptance.baseline.audit] PASS profile=local project=$COMPOSE_PROJECT_NAME database=$DB_NAME dbfilter=$ODOO_DBFILTER" \
    "[acceptance.baseline.audit] lifecycle database_volume=$DB_DATA filestore_volume=$ODOO_DATA session_volume=$REDIS_DATA" \
    "[acceptance.baseline.audit] user_databases=$user_databases database_inventory=$database_inventory" \
    "[acceptance.baseline.audit] current smart_construction_core=$module_version database_bytes=$db_size users=$user_count attachments=$attachment_count fixture_xmlids=$fixture_xmlids" \
    "[acceptance.baseline.audit] filestore_bytes=$filestore_bytes filestore_files=$filestore_files redis_keys=$redis_keys" \
    "[acceptance.baseline.audit] classification=platform_internal_acceptance fixture_allowed=true customer_business_data_allowed=false" \
    "[acceptance.baseline.audit] compatible_162_backup=$(compatible_backup_status) recovery_root=$RECOVERY_ROOT"
  IFS=',' read -r -a user_database_items <<<"$user_databases"
  for database in "${user_database_items[@]}"; do
    [[ "$database" != "$EXPECTED_DATABASE" ]] || continue
    public_tables="$(database_scalar_in "$database" "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'")"
    odoo_registry="$(database_scalar_in "$database" "SELECT CASE WHEN to_regclass('public.ir_module_module') IS NULL THEN 'false' ELSE 'true' END")"
    echo "[acceptance.baseline.audit] secondary_database=$database public_tables=$public_tables odoo_registry=$odoo_registry"
  done
}

archive_volume() {
  local volume="$1" output="$2"
  docker run --rm -v "${volume}:/source:ro" alpine:3.20 sh -ceu 'tar -C /source -czf - .' >"$output"
}

restore_volume() {
  local volume="$1" archive="$2"
  docker volume create "$volume" >/dev/null || return 1
  docker run --rm -v "${volume}:/target" -v "${archive}:/backup.tar.gz:ro" alpine:3.20 \
    sh -ceu 'tar -C /target -xzf /backup.tar.gz' || return 1
}

remove_volume_exact() {
  local volume="$1"
  if docker volume inspect "$volume" >/dev/null 2>&1; then
    docker volume rm "$volume" >/dev/null || return 1
  fi
  ! docker volume inspect "$volume" >/dev/null 2>&1
}

verify_bundle() {
  local bundle="$1" artifact
  for artifact in database.dump db-volume.tar.gz odoo-volume.tar.gz redis-volume.tar.gz SHA256SUMS manifest.txt MANIFEST_SHA256; do
    [[ -s "$bundle/$artifact" && ! -L "$bundle/$artifact" ]] || {
      echo "[acceptance.baseline.backup] FAIL missing or empty artifact=$artifact" >&2
      return 1
    }
  done
  grep -Fxq 'status=complete' "$bundle/manifest.txt" || return 1
  (cd "$bundle" && sha256sum -c SHA256SUMS) || return 1
  (cd "$bundle" && sha256sum -c MANIFEST_SHA256) || return 1
  docker run --rm -v "$bundle:/backup:ro" "$EXPECTED_DATABASE_IMAGE" pg_restore --list /backup/database.dump >/dev/null || return 1
  docker run --rm -v "$bundle:/backup:ro" alpine:3.20 sh -ceu \
    'tar -tzf /backup/db-volume.tar.gz >/dev/null && tar -tzf /backup/odoo-volume.tar.gz >/dev/null && tar -tzf /backup/redis-volume.tar.gz >/dev/null' || return 1
}

freeze_writers() {
  local odoo_cid nginx_cid
  compose_dev stop odoo nginx >/dev/null || {
    echo "[acceptance.baseline.backup] FAIL unable to stop managed writers" >&2
    return 1
  }
  odoo_cid="$(compose_dev ps -aq odoo)"
  nginx_cid="$(compose_dev ps -aq nginx)"
  [[ -n "$odoo_cid" && "$(docker inspect "$odoo_cid" --format '{{.State.Running}}')" == "false" ]] || {
    echo "[acceptance.baseline.backup] FAIL Odoo writer is not confirmed stopped" >&2
    return 1
  }
  if [[ -n "$nginx_cid" && "$(docker inspect "$nginx_cid" --format '{{.State.Running}}')" != "false" ]]; then
    echo "[acceptance.baseline.backup] FAIL nginx carrier is not confirmed stopped" >&2
    return 1
  fi
  [[ -z "$(docker ps -q --filter "volume=$ODOO_DATA")" ]] || {
    echo "[acceptance.baseline.backup] FAIL a running container still mounts the Odoo volume" >&2
    return 1
  }
  echo "[acceptance.baseline.backup] writers_stopped=true"
}

create_recovery_bundle() {
  local bundle="$1" actual_head="$2" db_cid module_version attachment_count filestore_files redis_keys database_scope
  mkdir -p "$bundle" || return 1
  chmod 700 "$RECOVERY_ROOT" "$bundle" || return 1
  freeze_writers || return 1
  require_no_database_clients || return 1
  db_cid="$(compose_dev ps -q db)"
  [[ -n "$db_cid" ]] || return 1
  module_version="$(database_scalar "SELECT COALESCE(latest_version, '') FROM ir_module_module WHERE name = 'smart_construction_core'")" || return 1
  attachment_count="$(database_scalar 'SELECT count(*) FROM ir_attachment')" || return 1
  filestore_files="$(volume_metric "$ODOO_DATA" 'find /source -type f | wc -l')" || return 1
  redis_keys="$(docker exec "${COMPOSE_PROJECT_NAME}-redis-1" redis-cli DBSIZE | tr -dc '0-9')" || return 1
  database_scope="$(user_database_csv)" || return 1
  docker exec "$db_cid" pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc >"$bundle/database.dump" || return 1
  archive_volume "$ODOO_DATA" "$bundle/odoo-volume.tar.gz" || return 1
  docker exec "${COMPOSE_PROJECT_NAME}-redis-1" redis-cli SAVE >/dev/null || return 1
  compose_dev stop redis >/dev/null || return 1
  [[ -z "$(docker ps -q --filter "volume=$REDIS_DATA")" ]] || return 1
  archive_volume "$REDIS_DATA" "$bundle/redis-volume.tar.gz" || return 1
  compose_dev stop db >/dev/null || return 1
  [[ -z "$(docker ps -q --filter "volume=$DB_DATA")" ]] || return 1
  archive_volume "$DB_DATA" "$bundle/db-volume.tar.gz" || return 1
  cat >"$bundle/manifest.txt" <<EOF
schema=frontend_acceptance_recovery_bundle.v1
status=staging
source_head=$actual_head
source_module_version=$module_version
compose_project=$COMPOSE_PROJECT_NAME
database=$DB_NAME
database_filter=$ODOO_DBFILTER
user_database_scope=$database_scope
database_volume=$DB_DATA
session_volume=$REDIS_DATA
filestore_volume=$ODOO_DATA
expected_attachment_count=$attachment_count
expected_filestore_file_count=$filestore_files
expected_redis_key_count=$redis_keys
EOF
  (cd "$bundle" && sha256sum database.dump db-volume.tar.gz odoo-volume.tar.gz redis-volume.tar.gz >SHA256SUMS) || return 1
  (cd "$bundle" && sha256sum -c SHA256SUMS) || return 1
  docker run --rm -v "$bundle:/backup:ro" "$EXPECTED_DATABASE_IMAGE" pg_restore --list /backup/database.dump >/dev/null || return 1
  docker run --rm -v "$bundle:/backup:ro" alpine:3.20 sh -ceu \
    'tar -tzf /backup/db-volume.tar.gz >/dev/null && tar -tzf /backup/odoo-volume.tar.gz >/dev/null && tar -tzf /backup/redis-volume.tar.gz >/dev/null' || return 1
  sed -i 's/^status=staging$/status=complete/' "$bundle/manifest.txt" || return 1
  (cd "$bundle" && sha256sum manifest.txt >MANIFEST_SHA256) || return 1
  verify_bundle "$bundle" || return 1
  echo "[acceptance.baseline.backup] PASS complete=true bundle=$bundle"
}

manifest_value() {
  local bundle="$1" key="$2"
  sed -n "s/^${key}=//p" "$bundle/manifest.txt" | tail -n 1
}

verify_restored_state() {
  local bundle="$1" expected_version expected_attachments expected_files expected_keys actual
  expected_version="$(manifest_value "$bundle" source_module_version)"
  expected_attachments="$(manifest_value "$bundle" expected_attachment_count)"
  expected_files="$(manifest_value "$bundle" expected_filestore_file_count)"
  expected_keys="$(manifest_value "$bundle" expected_redis_key_count)"
  require_database_volume_scope "$(manifest_value "$bundle" user_database_scope)" || return 1
  actual="$(database_scalar "SELECT COALESCE(latest_version, '') FROM ir_module_module WHERE name = 'smart_construction_core'")" || return 1
  [[ "$actual" == "$expected_version" ]] || return 1
  actual="$(database_scalar 'SELECT count(*) FROM ir_attachment')" || return 1
  [[ "$actual" == "$expected_attachments" ]] || return 1
  actual="$(volume_metric "$ODOO_DATA" 'find /source -type f | wc -l')" || return 1
  [[ "$actual" == "$expected_files" ]] || return 1
  actual="$(docker exec "${COMPOSE_PROJECT_NAME}-redis-1" redis-cli DBSIZE | tr -dc '0-9')" || return 1
  [[ "$actual" == "$expected_keys" ]] || return 1
  require_volume_mount_scope "$DB_DATA" db || return 1
  require_volume_mount_scope "$REDIS_DATA" redis || return 1
  require_volume_mount_scope "$ODOO_DATA" odoo || return 1
}

restore_recovery_bundle() {
  local bundle="$1"
  echo "[acceptance.baseline.rebuild] recovery_started bundle=$bundle" >&2
  verify_bundle "$bundle" || { echo "[acceptance.baseline.rebuild] RECOVERY_FAILED bundle_validation" >&2; return 1; }
  compose_dev down --remove-orphans >/dev/null || { echo "[acceptance.baseline.rebuild] RECOVERY_FAILED compose_down" >&2; return 1; }
  remove_volume_exact "$DB_DATA" || { echo "[acceptance.baseline.rebuild] RECOVERY_FAILED database_volume_remove" >&2; return 1; }
  remove_volume_exact "$REDIS_DATA" || { echo "[acceptance.baseline.rebuild] RECOVERY_FAILED session_volume_remove" >&2; return 1; }
  remove_volume_exact "$ODOO_DATA" || { echo "[acceptance.baseline.rebuild] RECOVERY_FAILED filestore_volume_remove" >&2; return 1; }
  compose_dev create db redis odoo >/dev/null || { echo "[acceptance.baseline.rebuild] RECOVERY_FAILED volume_carrier_create" >&2; return 1; }
  restore_volume "$REDIS_DATA" "$bundle/redis-volume.tar.gz" || { echo "[acceptance.baseline.rebuild] RECOVERY_FAILED session_unpack" >&2; return 1; }
  restore_volume "$ODOO_DATA" "$bundle/odoo-volume.tar.gz" || { echo "[acceptance.baseline.rebuild] RECOVERY_FAILED filestore_unpack" >&2; return 1; }
  restore_volume "$DB_DATA" "$bundle/db-volume.tar.gz" || { echo "[acceptance.baseline.rebuild] RECOVERY_FAILED database_unpack" >&2; return 1; }
  compose_dev up -d --wait db >/dev/null || { echo "[acceptance.baseline.rebuild] RECOVERY_FAILED database_start" >&2; return 1; }
  compose_dev up -d --wait redis >/dev/null || { echo "[acceptance.baseline.rebuild] RECOVERY_FAILED session_start" >&2; return 1; }
  verify_restored_state "$bundle" || { echo "[acceptance.baseline.rebuild] RECOVERY_FAILED post_restore_verification" >&2; return 1; }
  echo "[acceptance.baseline.rebuild] RECOVERED verified=true bundle=$bundle" >&2
}

print_plan() {
  printf '%s\n' \
    "[acceptance.baseline.rebuild.plan] GENERATED project=$COMPOSE_PROJECT_NAME database=$DB_NAME dbfilter=$ODOO_DBFILTER" \
    "[acceptance.baseline.rebuild.plan] exact_volumes=$DB_DATA,$REDIS_DATA,$ODOO_DATA" \
    "[acceptance.baseline.rebuild.plan] expected_user_databases=${EXPECTED_DATABASES:-$EXPECTED_DATABASE}" \
    "[acceptance.baseline.rebuild.plan] safeguard=cold_database_filestore_session_bundle root=$RECOVERY_ROOT" \
    "[acceptance.baseline.rebuild.plan] action=verify_scope,freeze_writers,backup,verify,remove_exact_volumes,recreate_empty_managed_infrastructure" \
    "[acceptance.baseline.rebuild.plan] automatic_recovery_scope=volume_removal_and_empty_infrastructure_recreation_only" \
    "[acceptance.baseline.rebuild.plan] post_action=make_db_ensure_then_fixture_snapshot_and_release_gate;failures_preserve_bundle_and_diagnostics"
}

rebuild() {
  local actual_head snapshot_id bundle destructive_started
  actual_head="$(git -C "$ROOT_DIR" rev-parse HEAD)"
  print_plan
  pre_execution_checks
  if [[ "${APPLY:-0}" != "1" ]]; then
    echo "[acceptance.baseline.rebuild.plan] DRY_RUN EXECUTABLE PASS expected_head=$EXPECTED_HEAD"
    return 0
  fi
  [[ "${CONFIRM_ACCEPTANCE_BASELINE_REBUILD:-}" == "REBUILD_DISPOSABLE_FRONTEND_ACCEPTANCE" ]] \
    || { deny "exact destructive confirmation is required"; return; }
  acquire_frontend_acceptance_lock baseline-rebuild
  snapshot_id="$(date -u +%Y%m%dT%H%M%SZ)-${actual_head:0:12}"
  bundle="$RECOVERY_ROOT/$snapshot_id"
  create_recovery_bundle "$bundle" "$actual_head" || {
    echo "[acceptance.baseline.rebuild] FAIL backup_not_complete deletion_started=false bundle=$bundle" >&2
    return 1
  }

  destructive_started=0
  rollback_on_failure() {
    local original_status=$?
    trap - EXIT
    if [[ "$original_status" != "0" && "$destructive_started" == "1" ]]; then
      if restore_recovery_bundle "$bundle"; then
        echo "[acceptance.baseline.rebuild] FAIL original_status=$original_status automatic_recovery=verified" >&2
        exit "$original_status"
      fi
      echo "[acceptance.baseline.rebuild] FATAL original_status=$original_status automatic_recovery=failed bundle=$bundle" >&2
      exit 70
    fi
    exit "$original_status"
  }
  trap rollback_on_failure EXIT
  destructive_started=1
  compose_dev down --remove-orphans
  remove_volume_exact "$DB_DATA"
  remove_volume_exact "$REDIS_DATA"
  remove_volume_exact "$ODOO_DATA"
  compose_dev up -d --wait db redis
  compose_dev create odoo >/dev/null
  require_database_volume_scope "$EXPECTED_DATABASE"
  require_volume_mount_scope "$DB_DATA" db
  require_volume_mount_scope "$REDIS_DATA" redis
  require_volume_mount_scope "$ODOO_DATA" odoo
  destructive_started=0
  trap - EXIT
  echo "[acceptance.baseline.rebuild] PASS empty_infrastructure_ready=true recovery_bundle=$bundle automatic_recovery_scope=environment_recreation"
}

main() {
  require_exact_identity
  case "${1:-audit}" in
    audit) audit ;;
    rebuild) rebuild ;;
    *) echo "usage: $0 audit|rebuild" >&2; return 2 ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
