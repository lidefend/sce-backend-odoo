#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$root"

branch="$(git branch --show-current)"
[[ "$branch" =~ ^(feature|fix|refactor|audit|release|codex)/.+$ ]] || {
  echo "[contract-image] blocked: an allowlisted branch is required" >&2; exit 2;
}
[[ -z "$(git status --short)" ]] || {
  echo "[contract-image] blocked: a clean committed worktree is required" >&2; exit 2;
}

source_sha="$(git rev-parse HEAD)"
short_sha="${source_sha:0:12}"
stamp="$(date -u +%Y%m%d%H%M%S)-$$"
prefix="sc-contract-hardening-${stamp}"
db="sc_contract_hardening_test_${stamp//-/}"
image="sce-contract-hardening:${short_sha}"
builder="sce-contract-hardening-builder:${short_sha}"
network="${prefix}-network"
db_container="${prefix}-db"
redis_container="${prefix}-redis"
odoo_container="${prefix}-odoo"
database_volume="sce-${db}-postgres"
redis_volume="sce-${db}-redis"
filestore_volume="sce-${db}-filestore"
session_volume="sce-${db}-sessions"
tmp_volume="sce-${db}-tmp"
log_volume="sce-${db}-logs"
context_dir="$(mktemp -d -t sc-contract-hardening-context.XXXXXX)"
log_dir="$(mktemp -d -t sc-contract-hardening-logs.XXXXXX)"
password="contract-test-only"

cleanup() {
  status=$?
  if [[ "$status" -ne 0 ]]; then
    for log in "$log_dir"/*.log; do
      [[ -f "$log" ]] || continue
      echo "[contract-image] failure log: $(basename "$log")" >&2
      tail -80 "$log" >&2
    done
  fi
  docker rm -f "$odoo_container" "$redis_container" "$db_container" >/dev/null 2>&1 || true
  docker network rm "$network" >/dev/null 2>&1 || true
  for volume in "$database_volume" "$redis_volume" "$filestore_volume" "$session_volume" "$tmp_volume" "$log_volume"; do
    docker volume rm "$volume" >/dev/null 2>&1 || true
  done
  docker image rm "$image" "$builder" >/dev/null 2>&1 || true
  rm -rf -- "$context_dir" "$log_dir"
  return "$status"
}
trap cleanup EXIT

git archive HEAD | tar -x -C "$context_dir"
while IFS= read -r -d '' file; do
  [[ -e "$root/$file" || -L "$root/$file" ]] || continue
  touch -h -r "$root/$file" "$context_dir/$file"
done < <(git ls-files -z)
while IFS= read -r -d '' dir; do
  rel="${dir#"$context_dir"/}"
  [[ "$dir" == "$context_dir" ]] && continue
  [[ -d "$root/$rel" ]] || continue
  touch -h -r "$root/$rel" "$dir"
done < <(find "$context_dir" -type d -print0)
find "$context_dir/frontend" -exec touch -h -d '@0' {} +
docker build --file "$context_dir/Dockerfile.production-frontend-builder" --tag "$builder" "$context_dir"
builder_container="$(docker create "$builder")"
mkdir -p "$context_dir/frontend/apps/web/dist-production-candidate"
docker cp "$builder_container:/build/frontend/apps/web/dist/." "$context_dir/frontend/apps/web/dist-production-candidate/"
docker rm "$builder_container" >/dev/null

frontend_hash="$(find "$context_dir/frontend/apps/web/dist-production-candidate" -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')"
product_version="$(python3 scripts/release/product_release.py --version)"
docker build --file "$context_dir/Dockerfile.production-candidate" --tag "$image" \
  --build-arg "SOURCE_SHA=$source_sha" --build-arg "PRODUCT_VERSION=$product_version" \
  --build-arg "FRONTEND_BUILD_SHA256=$frontend_hash" --build-arg "BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --build-arg "PYTHON_VERSION=registry-pinned" --build-arg "NODE_VERSION=22.17.0-build-only" \
  --build-arg "PNPM_VERSION=9.12.3-build-only" "$context_dir"

runtime_user="$(docker image inspect "$image" --format '{{.Config.User}}')"
[[ -n "$runtime_user" && "$runtime_user" != "0" && "$runtime_user" != "root" ]]
docker run --rm --entrypoint sh "$image" -eu -c '
  for path in /mnt/product-addons /mnt/customer-addons /mnt/test-addons /mnt/source-addons /mnt/addons_external/oca_server_ux; do
    test -d "$path" && test -r "$path" && test -x "$path"
  done
  for path in /opt/sce-runtime/filestore /opt/sce-runtime/sessions /opt/sce-runtime/tmp /opt/sce-runtime/logs /opt/sce-runtime/config; do
    test -d "$path" && test -r "$path" && test -w "$path" && test -x "$path"
  done
'

docker network create "$network" >/dev/null
for volume in "$database_volume" "$redis_volume" "$filestore_volume" "$session_volume" "$tmp_volume" "$log_volume"; do
  docker volume create "$volume" >/dev/null
done
docker run -d --name "$db_container" --network "$network" -e POSTGRES_DB=postgres -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD="$password" -v "$database_volume:/var/lib/postgresql/data" \
  postgres:15@sha256:386166d1a81e5ed9dfbbbbd8d4abe439d35ced9cc845eb3d09bc43b0b3860117 >/dev/null
docker run -d --name "$redis_container" --network "$network" -v "$redis_volume:/data" \
  redis:7-alpine@sha256:b1addbe72465a718643cff9e60a58e6df1841e29d6d7d60c9a85d8d72f08d1a7 redis-server --appendonly yes >/dev/null
for _ in $(seq 1 40); do docker exec "$db_container" pg_isready -U odoo -d postgres >/dev/null 2>&1 && break; sleep 1; done
docker exec "$db_container" pg_isready -U odoo -d postgres >/dev/null

common_env=(
  -e "TARGET_DB=$db" -e "DB_NAME=$db" -e "ODOO_DB=$db" -e "ODOO_DBFILTER=^${db}$"
  -e DB_HOST="$db_container" -e DB_PORT=5432 -e DB_USER=odoo -e DB_PASSWORD="$password"
  -e ADMIN_PASSWD=contract-test-only -e JWT_SECRET=contract-test-only -e REDIS_HOST="$redis_container"
  -e ODOO_CONF_OUT=/opt/sce-runtime/config/odoo.conf -e TMPDIR=/opt/sce-runtime/tmp
  -e SC_ENVIRONMENT=contract_test -e SC_CONTRACT_TEST_MODE=1 -e SC_ALLOW_DEMO_DATA=0
  -e "PLATFORM_RELEASE_DB=$db"
  -e "SC_FILESTORE_SCOPE=$db" -e "SC_DATABASE_VOLUME=$database_volume" -e "SC_REDIS_VOLUME=$redis_volume"
  -e "SC_FILESTORE_VOLUME=$filestore_volume" -e "SC_SESSION_VOLUME=$session_volume"
  -e "SC_TMP_VOLUME=$tmp_volume" -e "SC_LOG_VOLUME=$log_volume" -e "EXPECTED_RELEASE_SHA=$source_sha"
)
mounts=(-v "$filestore_volume:/opt/sce-runtime/filestore" -v "$session_volume:/opt/sce-runtime/sessions" -v "$tmp_volume:/opt/sce-runtime/tmp" -v "$log_volume:/opt/sce-runtime/logs")

if docker run --rm --network "$network" "${common_env[@]}" "${mounts[@]}" "$image" >"$log_dir/missing-database.log" 2>&1; then
  echo "[contract-image] missing database unexpectedly started" >&2; exit 1
fi
[[ "$(docker exec "$db_container" psql -U odoo -d postgres -Atc "SELECT count(*) FROM pg_database WHERE datname='$db'")" == "0" ]]

failure_bin="$log_dir/failure-bin"
mkdir -p "$failure_bin"
printf '%s\n' '#!/bin/sh' 'exit 42' >"$failure_bin/odoo"
chmod 0755 "$failure_bin" "$failure_bin/odoo"
set +e
docker run --rm --network "$network" "${common_env[@]}" "${mounts[@]}" \
  -e PATH=/contract-failure-bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  -v "$failure_bin:/contract-failure-bin:ro" --entrypoint /usr/local/bin/production-db-manage "$image" init \
  >"$log_dir/init-injected-failure.log" 2>&1
injected_failure_status=$?
set -e
[[ "$injected_failure_status" == "42" ]] || {
  echo "[contract-image] expected injected initialization status 42, got $injected_failure_status" >&2; exit 1;
}
grep -q "removed the database created by this invocation" "$log_dir/init-injected-failure.log"
[[ "$(docker exec "$db_container" psql -U odoo -d postgres -Atc "SELECT count(*) FROM pg_database WHERE datname='$db'")" == "0" ]]

docker run --rm --network "$network" "${common_env[@]}" "${mounts[@]}" --entrypoint /usr/local/bin/production-db-manage "$image" init >"$log_dir/init.log" 2>&1
[[ "$(docker exec "$db_container" psql -U odoo -d postgres -Atc "SELECT count(*) FROM pg_database WHERE datname='$db'")" == "1" ]]
docker run --rm --network "$network" "${common_env[@]}" "${mounts[@]}" \
  -e SC_COLOCATED_PLATFORM_CONFIG_APPLY=I_ACKNOWLEDGE_COLOCATED_PLATFORM_CONFIGURATION \
  --entrypoint /usr/local/bin/production-db-manage "$image" configure-platform >"$log_dir/configure-platform.log" 2>&1
if docker run --rm --network "$network" "${common_env[@]}" "${mounts[@]}" --entrypoint /usr/local/bin/production-db-manage "$image" init \
    >"$log_dir/init-preexisting.log" 2>&1; then
  echo "[contract-image] pre-existing database initialization unexpectedly succeeded" >&2; exit 1
fi
grep -q "already exists; refusing initialization and cleanup" "$log_dir/init-preexisting.log"
[[ "$(docker exec "$db_container" psql -U odoo -d postgres -Atc "SELECT count(*) FROM pg_database WHERE datname='$db'")" == "1" ]]
docker run -d --name "$odoo_container" --network "$network" "${common_env[@]}" "${mounts[@]}" "$image" >/dev/null
wait_for_odoo() {
  for _ in $(seq 1 90); do
    if docker exec "$odoo_container" python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8069/web/login', timeout=3)" >/dev/null 2>&1; then return 0; fi
    sleep 2
  done
  docker logs --tail 80 "$odoo_container" >&2
  return 1
}
wait_for_odoo
docker restart "$odoo_container" >/dev/null
wait_for_odoo
demo_count="$(docker exec "$db_container" psql -U odoo -d "$db" -Atc "SELECT count(*) FROM ir_module_module WHERE state='installed' AND (name LIKE '%demo%' OR name LIKE '%fixture%')")"
[[ "$demo_count" == "0" ]]

image_id="$(docker image inspect "$image" --format '{{.Id}}')"
image_size="$(docker image inspect "$image" --format '{{.Size}}')"
echo "[contract-image] PASS image=$image id=${image_id:7:12} size=$image_size user=$runtime_user database=$db"
