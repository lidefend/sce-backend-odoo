#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
export ROOT_DIR

# shellcheck source=../common/guard_prod.sh
source "$ROOT_DIR/scripts/common/guard_prod.sh"
guard_prod_forbid

if [[ "$#" -ne 0 ]]; then
  echo "[admin-vis-p3-orm][FATAL] this entrypoint accepts no database override or positional argument" >&2
  exit 2
fi

authorization_test_tags="${SC_AUTHORIZATION_ORM_TEST_TAGS:-admin_vis_p3_project_record_rule_orm}"
case "$authorization_test_tags" in
  admin_vis_p3_project_record_rule_orm|chatter_timeline_authorization_orm) ;;
  *)
    echo "[admin-vis-p3-orm][FATAL] unsupported fixed authorization test tag" >&2
    exit 2
    ;;
esac

case "${ENV:-dev}" in
  dev|test) ;;
  *)
    echo "[admin-vis-p3-orm][FATAL] ENV must be dev or test" >&2
    exit 2
    ;;
esac

read -r -a compose_binary <<<"${COMPOSE_BIN:-docker compose}"
if ! command -v "${compose_binary[0]}" >/dev/null 2>&1; then
  echo "[admin-vis-p3-orm][FATAL] docker compose is unavailable" >&2
  exit 127
fi

timestamp="$(date -u +%Y%m%d%H%M%S)"
random_suffix="$(od -An -N4 -tx1 /dev/urandom | tr -d ' \\n')"
owner_id="admin-vis-p3-${timestamp}-${random_suffix}"
temp_database="sc_test_admin_vis_p3_${timestamp}_${random_suffix}"
compose_project="sc-${owner_id}"

validate_database_name() {
  local candidate="$1"
  [[ "$candidate" =~ ^sc_test_admin_vis_p3_[0-9]{14}_[0-9a-f]{8}$ ]] || return 1
  case "${candidate,,}" in
    postgres|template0|template1|sc_demo|sc_demo_*|sc_frontend_acceptance|sc_frontend_acceptance_*|\
    sc_prod|sc_prod_*|sc_production|sc_production_*|sc_platform_control|scbs|legacy_source_b|*daily*|*uat*|*acceptance*)
      return 1
      ;;
  esac
}

for denied_name in \
  postgres template0 template1 sc_demo sc_demo_copy sc_frontend_acceptance \
  sc_prod sc_production sc_platform_control LEGACY_SOURCE_A LEGACY_SOURCE_B sc_daily sc_tenant_uat; do
  if validate_database_name "$denied_name"; then
    echo "[admin-vis-p3-orm][FATAL] denylist self-check accepted ${denied_name}" >&2
    exit 2
  fi
done
validate_database_name "$temp_database" || {
  echo "[admin-vis-p3-orm][FATAL] generated database name failed the fixed-prefix guard" >&2
  exit 2
}

export ENV=test
export ENV_FILE="$ROOT_DIR/.env.test.example"
export COMPOSE_PROJECT_NAME="$compose_project"
export PROJECT="$compose_project"
export DB_NAME="$temp_database"
export ODOO_DBFILTER="^${temp_database}$"
export DB_DATA="${compose_project}-db-data"
export REDIS_DATA="${compose_project}-redis-data"
export ODOO_DATA="${compose_project}-odoo-data"

compose=(
  "${compose_binary[@]}"
  --project-directory "$ROOT_DIR"
  -p "$compose_project"
  -f "$ROOT_DIR/docker-compose.yml"
  -f "$ROOT_DIR/docker-compose.admin-vis-p3-orm.yml"
)

container_inventory() {
  docker ps -a --format '{{.ID}}|{{.Names}}|{{.Image}}' | LC_ALL=C sort
}

network_inventory() {
  docker network ls --format '{{.ID}}|{{.Name}}|{{.Driver}}' | LC_ALL=C sort
}

volume_inventory() {
  docker volume ls --format '{{.Name}}|{{.Driver}}' | LC_ALL=C sort
}

database_inventory() {
  local container_id container_name postgres_user database_name
  while IFS= read -r container_id; do
    [[ -n "$container_id" ]] || continue
    container_name="$(docker inspect --format '{{.Name}}' "$container_id" | sed 's#^/##')"
    postgres_user="$(
      docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$container_id" |
        sed -n 's/^POSTGRES_USER=//p' |
        head -n 1
    )"
    [[ -n "$postgres_user" ]] || postgres_user=postgres
    while IFS= read -r database_name; do
      [[ -n "$database_name" ]] || continue
      printf '%s|%s\n' "$container_name" "$database_name"
    done < <(
      docker exec "$container_id" \
        psql -X -A -t -U "$postgres_user" -d postgres \
        -c "SELECT datname FROM pg_database ORDER BY datname"
    )
  done < <(docker ps --filter label=com.docker.compose.service=db --format '{{.ID}}' | LC_ALL=C sort)
}

inventory_digest() {
  printf '%s' "$1" | sha256sum | awk '{print $1}'
}

containers_before="$(container_inventory)"
networks_before="$(network_inventory)"
volumes_before="$(volume_inventory)"
databases_before="$(database_inventory)"
containers_before_digest="$(inventory_digest "$containers_before")"
networks_before_digest="$(inventory_digest "$networks_before")"
volumes_before_digest="$(inventory_digest "$volumes_before")"
databases_before_digest="$(inventory_digest "$databases_before")"

cleanup_complete=false
cleanup_result=0
database_removed=false
resources_removed=false
test_log="$(mktemp)"
frontend_artifact_dir=""

cleanup() {
  local original_status="$1"
  local database_container residue_count project_resource_count
  set +e

  database_container="$("${compose[@]}" ps -q db 2>/dev/null)"
  if [[ -n "$database_container" ]]; then
    docker exec "$database_container" \
      psql -X -v ON_ERROR_STOP=1 -U "$DB_USER" -d postgres \
      -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${temp_database}' AND pid <> pg_backend_pid();" \
      >/dev/null 2>&1
    docker exec "$database_container" \
      dropdb -U "$DB_USER" --if-exists "$temp_database" \
      >/dev/null 2>&1
    residue_count="$(
      docker exec "$database_container" \
        psql -X -A -t -U "$DB_USER" -d postgres \
        -c "SELECT count(*) FROM pg_database WHERE datname = '${temp_database}';" 2>/dev/null |
        tr -d '[:space:]'
    )"
    if [[ "$residue_count" == "0" ]]; then
      database_removed=true
    else
      cleanup_result=86
    fi
  else
    cleanup_result=86
  fi

  "${compose[@]}" down --volumes --remove-orphans --timeout 20 >/dev/null 2>&1
  if [[ "$?" -ne 0 ]]; then
    cleanup_result=86
  fi

  project_resource_count="$(
    {
      docker ps -aq --filter "label=com.docker.compose.project=${compose_project}"
      docker network ls -q --filter "label=com.docker.compose.project=${compose_project}"
      docker volume ls -q --filter "label=com.docker.compose.project=${compose_project}"
    } | sed '/^$/d' | wc -l | tr -d '[:space:]'
  )"
  if [[ "$project_resource_count" == "0" ]]; then
    resources_removed=true
  else
    cleanup_result=86
  fi
  if [[ -f "$test_log" ]]; then
    find "$test_log" -delete
  fi
  if [[ -n "$frontend_artifact_dir" && -d "$frontend_artifact_dir" ]]; then
    find "$frontend_artifact_dir" -depth -delete
  fi

  containers_after="$(container_inventory)"
  networks_after="$(network_inventory)"
  volumes_after="$(volume_inventory)"
  databases_after="$(database_inventory)"
  containers_after_digest="$(inventory_digest "$containers_after")"
  networks_after_digest="$(inventory_digest "$networks_after")"
  volumes_after_digest="$(inventory_digest "$volumes_after")"
  databases_after_digest="$(inventory_digest "$databases_after")"

  [[ "$containers_before" == "$containers_after" ]] || cleanup_result=86
  [[ "$networks_before" == "$networks_after" ]] || cleanup_result=86
  [[ "$volumes_before" == "$volumes_after" ]] || cleanup_result=86
  [[ "$databases_before" == "$databases_after" ]] || cleanup_result=86

  cleanup_complete=true
  printf 'ADMIN_VIS_P3_TEMP_OWNER=%s\n' "$owner_id"
  printf 'ADMIN_VIS_P3_TEMP_DATABASE=%s\n' "$temp_database"
  printf 'ADMIN_VIS_P3_DATABASES_BEFORE_SHA256=%s\n' "$databases_before_digest"
  printf 'ADMIN_VIS_P3_DATABASES_AFTER_SHA256=%s\n' "$databases_after_digest"
  printf 'ADMIN_VIS_P3_CONTAINERS_BEFORE_SHA256=%s\n' "$containers_before_digest"
  printf 'ADMIN_VIS_P3_CONTAINERS_AFTER_SHA256=%s\n' "$containers_after_digest"
  printf 'ADMIN_VIS_P3_NETWORKS_BEFORE_SHA256=%s\n' "$networks_before_digest"
  printf 'ADMIN_VIS_P3_NETWORKS_AFTER_SHA256=%s\n' "$networks_after_digest"
  printf 'ADMIN_VIS_P3_VOLUMES_BEFORE_SHA256=%s\n' "$volumes_before_digest"
  printf 'ADMIN_VIS_P3_VOLUMES_AFTER_SHA256=%s\n' "$volumes_after_digest"
  printf 'ADMIN_VIS_P3_TEMP_DATABASE_REMOVED=%s\n' "$database_removed"
  printf 'ADMIN_VIS_P3_TEMP_RESOURCES_REMOVED=%s\n' "$resources_removed"

  if [[ "$cleanup_result" -ne 0 ]]; then
    echo "[admin-vis-p3-orm][FATAL] exact cleanup or baseline restoration failed" >&2
    exit "$cleanup_result"
  fi
  exit "$original_status"
}

on_exit() {
  local status="$?"
  trap - EXIT INT TERM
  cleanup "$status"
}
trap on_exit EXIT INT TERM

echo "[admin-vis-p3-orm] owner=${owner_id}"
echo "[admin-vis-p3-orm] database=${temp_database}"
echo "[admin-vis-p3-orm] database_role=isolated_test_rehearsal"
echo "[admin-vis-p3-orm] tenant_id=synthetic_admin_vis_p3"
echo "[admin-vis-p3-orm] environment_id=${owner_id}"
echo "[admin-vis-p3-orm] exact_db_filter=${ODOO_DBFILTER}"

"${compose[@]}" up -d db
database_container="$("${compose[@]}" ps -q db)"
for attempt in $(seq 1 60); do
  if docker exec "$database_container" pg_isready -U "$DB_USER" -d "$temp_database" >/dev/null 2>&1; then
    break
  fi
  if [[ "$attempt" -eq 60 ]]; then
    echo "[admin-vis-p3-orm][FATAL] isolated PostgreSQL did not become ready" >&2
    exit 3
  fi
  sleep 1
done

frontend_artifact_dir="$(mktemp -d)"
provided_frontend_sha="${FRONTEND_BUILD_SHA256:-}"
docker build \
  --target frontend-artifact \
  --output "type=local,dest=${frontend_artifact_dir}" \
  --build-arg "APT_MIRROR=${APT_MIRROR:-default}" \
  "$ROOT_DIR"
frontend_build_sha="$(tr -d '[:space:]' <"${frontend_artifact_dir}/.build-sha256")"
if ! [[ "$frontend_build_sha" =~ ^[0-9a-f]{64}$ ]]; then
  echo "[admin-vis-p3-orm][FATAL] isolated frontend artifact digest is invalid" >&2
  exit 5
fi
if [[ -n "$provided_frontend_sha" && "$provided_frontend_sha" != "$frontend_build_sha" ]]; then
  echo "[admin-vis-p3-orm][FATAL] provided frontend artifact digest does not match the isolated build" >&2
  exit 5
fi
export FRONTEND_BUILD_SHA256="$frontend_build_sha"

odoo_common=(
  /usr/bin/odoo
  --db_host=db
  --db_port=5432
  "--db_user=${DB_USER}"
  "--db_password=${DB_PASSWORD}"
  -d "$temp_database"
  "--db-filter=${ODOO_DBFILTER}"
  --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/source-addons,/mnt/addons_external/oca_server_ux
  --without-demo=all
  --no-http
  --workers=0
  --max-cron-threads=0
  --stop-after-init
)

"${compose[@]}" run --rm --no-deps -T --entrypoint /usr/bin/odoo odoo \
  "${odoo_common[@]:1}" \
  -i smart_construction_core \
  --log-level=info

set +e
"${compose[@]}" run --rm --no-deps -T --entrypoint /usr/bin/odoo odoo \
  "${odoo_common[@]:1}" \
  -u smart_core \
  --test-enable \
  --test-tags "$authorization_test_tags" \
  --log-level=test 2>&1 | tee "$test_log"
test_status="${PIPESTATUS[0]}"
set -e
if [[ "$test_status" -ne 0 ]]; then
  echo "[admin-vis-p3-orm][FATAL] real ORM test process failed with ${test_status}" >&2
  exit "$test_status"
fi
if ! grep -Eq "0 failed, 0 error\\(s\\) of [1-9][0-9]* tests" "$test_log"; then
  echo "[admin-vis-p3-orm][FATAL] Odoo did not report any executed ORM test" >&2
  exit 4
fi

echo "[admin-vis-p3-orm] REAL_ORM_TEST_RESULT=PASS"
