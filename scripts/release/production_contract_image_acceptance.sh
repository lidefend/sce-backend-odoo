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
r11c_source_dump="${R11C_SOURCE_DUMP:-}"
r11c_source_dump_sha256="${R11C_SOURCE_DUMP_SHA256:-}"

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
  cd /opt/sce-product/contracts
  sha256sum -c formal_business_product_menu_policy_v1.json.sha256
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

image_id="$(docker image inspect "$image" --format '{{.Id}}')"
release_identity_dir="$log_dir/release-identity"
mkdir -p "$release_identity_dir"
SOURCE_SHA="$source_sha" IMAGE_DIGEST="$image_id" RELEASE_IDENTITY_DIR="$release_identity_dir" python3 - <<'PY'
import hashlib
import json
import os
from pathlib import Path

root = Path(os.environ["RELEASE_IDENTITY_DIR"])
manifest = root / "product-release-manifest.json"
manifest.write_text(
    json.dumps(
        {
            "schema_version": "product_release_manifest.v2",
            "repository": "lidefend/sce-backend-odoo",
            "branch": "main",
            "source_sha": os.environ["SOURCE_SHA"],
            "oci_revision": os.environ["SOURCE_SHA"],
            "container_source_revision": os.environ["SOURCE_SHA"],
            "image_digest": os.environ["IMAGE_DIGEST"],
            "archive_sha256": "a" * 64,
            "archive_reload_digest": os.environ["IMAGE_DIGEST"],
            "baseline_checksum": "b" * 64,
            "scan": {
                "status": "completed",
                "source_sha": os.environ["SOURCE_SHA"],
                "image_digest": os.environ["IMAGE_DIGEST"],
                "counts": {
                    "CRITICAL": 0,
                    "HIGH": 0,
                    "MEDIUM": 0,
                    "LOW": 0,
                    "SECRET": 0,
                },
                "policy": {"result": "pass"},
            },
        },
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)
(root / "product-release-manifest.sha256").write_text(
    f"{hashlib.sha256(manifest.read_bytes()).hexdigest()}  {manifest.name}\n",
    encoding="utf-8",
)
PY

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
  -e "EXPECTED_IMAGE_DIGEST=$image_id"
  -e RELEASE_MANIFEST_PATH=/opt/sce-release/product-release-manifest.json
  -e RELEASE_MANIFEST_CHECKSUM_PATH=/opt/sce-release/product-release-manifest.sha256
)
mounts=(
  -v "$filestore_volume:/opt/sce-runtime/filestore"
  -v "$session_volume:/opt/sce-runtime/sessions"
  -v "$tmp_volume:/opt/sce-runtime/tmp"
  -v "$log_volume:/opt/sce-runtime/logs"
  -v "$release_identity_dir/product-release-manifest.json:/opt/sce-release/product-release-manifest.json:ro"
  -v "$release_identity_dir/product-release-manifest.sha256:/opt/sce-release/product-release-manifest.sha256:ro"
)

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

if [[ -n "$r11c_source_dump" ]]; then
  [[ -f "$r11c_source_dump" && -r "$r11c_source_dump" ]] || {
    echo "[contract-image] R11C_SOURCE_DUMP must be a readable file" >&2; exit 2;
  }
  if [[ -n "$r11c_source_dump_sha256" ]]; then
    [[ "$(sha256sum "$r11c_source_dump" | awk '{print $1}')" == "$r11c_source_dump_sha256" ]] || {
      echo "[contract-image] R11C source dump checksum mismatch" >&2; exit 2;
    }
  fi
  docker rm -f "$odoo_container" >/dev/null
  odoo_container=""
  docker exec "$db_container" psql -U odoo -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS \"$db\"" >/dev/null
  docker exec "$db_container" psql -U odoo -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE \"$db\" OWNER odoo" >/dev/null
  docker cp "$r11c_source_dump" "$db_container:/tmp/r11c-source.dump"
  docker exec "$db_container" pg_restore -U odoo -d "$db" --no-owner --no-privileges --exit-on-error /tmp/r11c-source.dump
  docker exec "$db_container" rm -f /tmp/r11c-source.dump

  docker run --rm --network "$network" "${common_env[@]}" "${mounts[@]}" \
    -e SC_COLOCATED_PLATFORM_CONFIG_APPLY=I_ACKNOWLEDGE_COLOCATED_PLATFORM_CONFIGURATION \
    --entrypoint /usr/local/bin/production-db-manage "$image" configure-platform >"$log_dir/r11c-configure.log" 2>&1

  policy_snapshot_state() {
    docker exec "$db_container" psql -U odoo -d "$db" -At -F '|' -c \
      "SELECT product_key, (SELECT count(*) FROM jsonb_array_elements(menu_groups) g, jsonb_array_elements(g->'menus') m WHERE (m->>'enabled')::boolean AND m->>'release_state'='released'), note FROM sc_product_policy WHERE product_key IN ('construction.standard','construction.preview') ORDER BY product_key; SELECT count(*) FROM sc_edition_release_snapshot;"
  }
  initial_state="$(policy_snapshot_state)"
  grep -q 'construction.standard|214|' <<<"$initial_state"
  grep -q 'construction.preview|214|' <<<"$initial_state"
  [[ "$(tail -1 <<<"$initial_state")" == "0" ]]

  snapshot_env=(
    -e SC_COLOCATED_PLATFORM_SNAPSHOT_APPLY=I_ACKNOWLEDGE_COLOCATED_PLATFORM_SNAPSHOT_INITIALIZATION
    -e "PLATFORM_RELEASE_VERSION=$product_version"
  )
  missing_contracts="$log_dir/missing-contracts"
  mkdir -p "$missing_contracts"
  if docker run --rm --network "$network" "${common_env[@]}" "${mounts[@]}" "${snapshot_env[@]}" \
      -e PLATFORM_RELEASE_PRODUCT_KEY=construction.standard \
      -v "$missing_contracts:/opt/sce-product/contracts:ro" \
      --entrypoint /usr/local/bin/production-db-manage "$image" initialize-platform-snapshot \
      >"$log_dir/r11c-missing-baseline.log" 2>&1; then
    echo "[contract-image] missing locked baseline unexpectedly initialized" >&2; exit 1
  fi
  grep -q 'LOCKED_MENU_BASELINE_MISSING' "$log_dir/r11c-missing-baseline.log"
  [[ "$(policy_snapshot_state)" == "$initial_state" ]]

  invalid_contracts="$log_dir/invalid-contracts"
  mkdir -p "$invalid_contracts"
  printf '%s\n' '{"schema":"corrupt"}' >"$invalid_contracts/formal_business_product_menu_policy_v1.json"
  cp scripts/verify/baselines/formal_business_product_menu_policy_v1.json.sha256 "$invalid_contracts/"
  if docker run --rm --network "$network" "${common_env[@]}" "${mounts[@]}" "${snapshot_env[@]}" \
      -e PLATFORM_RELEASE_PRODUCT_KEY=construction.standard \
      -v "$invalid_contracts:/opt/sce-product/contracts:ro" \
      --entrypoint /usr/local/bin/production-db-manage "$image" initialize-platform-snapshot \
      >"$log_dir/r11c-invalid-baseline.log" 2>&1; then
    echo "[contract-image] invalid locked baseline unexpectedly initialized" >&2; exit 1
  fi
  grep -q 'LOCKED_MENU_BASELINE_INVALID' "$log_dir/r11c-invalid-baseline.log"
  [[ "$(policy_snapshot_state)" == "$initial_state" ]]

  tax_certificate_artifact_state() {
    docker exec "$db_container" psql -U odoo -d "$db" -At -F '|' -c \
      "SELECT count(*) FROM ir_model_data WHERE module='smart_construction_core' AND name='action_sc_tax_certificate_registration_user'; SELECT count(*) FROM ir_model WHERE model='sc.legacy.payment.residual.fact'; SELECT COALESCE((SELECT res_model FROM ir_act_window a JOIN ir_model_data d ON d.model='ir.actions.act_window' AND d.res_id=a.id WHERE d.module='smart_construction_core' AND d.name='action_sc_tax_certificate_registration_user' LIMIT 1),''); SELECT count(*) FROM ir_model_data WHERE module='smart_construction_core' AND name='menu_sc_tax_certificate_registration_user';"
  }
  run_snapshot_init() {
    product_key="$1"
    output="$2"
    docker run --rm --network "$network" "${common_env[@]}" "${mounts[@]}" "${snapshot_env[@]}" \
        -e "PLATFORM_RELEASE_PRODUCT_KEY=$product_key" \
        --entrypoint /usr/local/bin/production-db-manage "$image" initialize-platform-snapshot >"$output" 2>&1
  }
  run_snapshot_init construction.standard "$log_dir/r11f2-standard.log"
  run_snapshot_init construction.preview "$log_dir/r11f2-preview.log"
  run_snapshot_init construction.standard "$log_dir/r11f2-standard-repeat.log"
  [[ "$(tax_certificate_artifact_state)" == $'1\n0\nsc.tax.certificate.registration\n1' ]]
  echo "[contract-image] R11F2 TAX_CERTIFICATE_INITIALIZATION PASS database=$db formal_action=true formal_menu=true legacy_model=false"
fi

image_size="$(docker image inspect "$image" --format '{{.Size}}')"
echo "[contract-image] PASS image=$image id=${image_id:7:12} size=$image_size user=$runtime_user database=$db"
