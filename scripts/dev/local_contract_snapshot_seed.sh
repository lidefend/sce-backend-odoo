#!/usr/bin/env bash
set -euo pipefail

# Seed the isolated contract-snapshot profile from the registered demo dataset
# (project sc-local-dev / database sc_dev_demo). The seed is read-only on the
# source: it never writes to the source database, volumes, env file or
# containers. The target identity is matched exactly and the action needs an
# explicit confirmation.

: "${ROOT_DIR:?ROOT_DIR is required}"
source "${ROOT_DIR}/scripts/common/env.sh"
source "${ROOT_DIR}/scripts/common/compose.sh"

expected_project="sc-contract-snapshot-v1"
expected_db="sc_contract_snapshot"
expected_filter='^sc_contract_snapshot$'
expected_db_volume="sc_contract_snapshot_db_data"
expected_redis_volume="sc_contract_snapshot_redis_data"
expected_odoo_volume="sc_contract_snapshot_odoo_data"
seed_project="sc-local-dev"
seed_db="sc_dev_demo"
seed_filter='^sc_dev_demo$'

[[ "${ENV}" == "dev" \
  && "${ISOLATED_REHEARSAL_DATABASE:-0}" == "1" \
  && "${COMPOSE_PROJECT_NAME}" == "${expected_project}" \
  && "${DB_NAME}" == "${expected_db}" \
  && "${ODOO_DBFILTER}" == "${expected_filter}" \
  && "${DB_DATA}" == "${expected_db_volume}" \
  && "${REDIS_DATA}" == "${expected_redis_volume}" \
  && "${ODOO_DATA}" == "${expected_odoo_volume}" ]] || {
    echo "[local.contract-snapshot.seed] DENY target profile identity mismatch" >&2
    exit 2
  }

[[ "${LOCAL_CONTRACT_SNAPSHOT_SEED_PROJECT:-${seed_project}}" == "${seed_project}" \
  && "${LOCAL_CONTRACT_SNAPSHOT_SEED_DB:-${seed_db}}" == "${seed_db}" ]] || {
    echo "[local.contract-snapshot.seed] DENY seed identity drift: only ${seed_project}/${seed_db} is a registered seed" >&2
    exit 2
  }

[[ "${CONFIRM_LOCAL_CONTRACT_SNAPSHOT_SEED:-}" == "SEED_ISOLATED_CONTRACT_SNAPSHOT" ]] || {
  echo "[local.contract-snapshot.seed] confirmation required: CONFIRM_LOCAL_CONTRACT_SNAPSHOT_SEED=SEED_ISOLATED_CONTRACT_SNAPSHOT" >&2
  exit 2
}

mapfile -t seed_db_ids < <(
  docker ps --filter "label=com.docker.compose.project=${seed_project}" \
    --filter "label=com.docker.compose.service=db" --format '{{.ID}}'
)
mapfile -t seed_odoo_ids < <(
  docker ps --filter "label=com.docker.compose.project=${seed_project}" \
    --filter "label=com.docker.compose.service=odoo" --format '{{.ID}}'
)
(( ${#seed_db_ids[@]} == 1 )) || {
  echo "[local.contract-snapshot.seed] DENY expected exactly one ${seed_project} db container, found ${#seed_db_ids[@]}" >&2
  exit 2
}
(( ${#seed_odoo_ids[@]} == 1 )) || {
  echo "[local.contract-snapshot.seed] DENY expected exactly one ${seed_project} odoo container, found ${#seed_odoo_ids[@]}" >&2
  exit 2
}
seed_db_id="${seed_db_ids[0]}"
seed_odoo_id="${seed_odoo_ids[0]}"
seed_user="$(docker inspect "${seed_db_id}" --format '{{range .Config.Env}}{{println .}}{{end}}' | sed -n 's/^POSTGRES_USER=//p')"
seed_database="$(docker inspect "${seed_db_id}" --format '{{range .Config.Env}}{{println .}}{{end}}' | sed -n 's/^POSTGRES_DB=//p')"
[[ "${seed_user}" =~ ^[a-z_][a-z0-9_]*$ && "${seed_database}" == "${seed_db}" ]] || {
  echo "[local.contract-snapshot.seed] DENY seed container identity mismatch user=${seed_user} db=${seed_database}" >&2
  exit 2
}

compose_dev up -d db redis >/dev/null
target_db_id="$(compose_dev ps -q db)"
[[ -n "${target_db_id}" ]] || {
  echo "[local.contract-snapshot.seed] target db service is not running" >&2
  exit 1
}
state=""
for _ in $(seq 1 30); do
  state="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${target_db_id}")"
  [[ "${state}" == "healthy" ]] && break
  sleep 2
done
[[ "${state}" == "healthy" ]] || {
  echo "[local.contract-snapshot.seed] target database did not become healthy" >&2
  exit 1
}

# The restore replaces the whole database (pg_restore --clean). A running Odoo
# keeps objects open, so the DROP can fail and leave the target half-restored:
# observed as "duplicate key ... res_company_pkey" plus "multiple primary keys".
# Refuse instead of doing that; the governed reset is local.contract-snapshot.rebuild,
# which takes the whole profile down before seeding.
mapfile -t target_odoo_ids < <(
  docker ps --filter "label=com.docker.compose.project=${COMPOSE_PROJECT_NAME}" \
    --filter "label=com.docker.compose.service=odoo" --format '{{.ID}}'
)
(( ${#target_odoo_ids[@]} == 0 )) || {
  echo "[local.contract-snapshot.seed] DENY target odoo is running (${#target_odoo_ids[@]} container(s)); seeding a live profile can half-restore ${DB_NAME}. Use local.contract-snapshot.rebuild." >&2
  exit 2
}

dump_file="$(mktemp -p "${TMPDIR:-/tmp}" contract-snapshot-seed.XXXXXX.dump)"
cleanup() { rm -f "${dump_file}"; }
trap cleanup EXIT

echo "[local.contract-snapshot.seed] dump ${seed_project}/${seed_db} (read-only)"
docker exec "${seed_db_id}" pg_dump -U "${seed_user}" -d "${seed_database}" -Fc >"${dump_file}"
dump_sha="$(sha256sum "${dump_file}" | awk '{print $1}')"
dump_bytes="$(stat -c '%s' "${dump_file}")"
echo "[local.contract-snapshot.seed] seed_dump_sha256=${dump_sha} bytes=${dump_bytes}"

echo "[local.contract-snapshot.seed] restore into ${COMPOSE_PROJECT_NAME}/${DB_NAME}"
docker exec -i "${target_db_id}" \
  pg_restore -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists --no-owner --no-privileges \
  <"${dump_file}"

local_uuid="$(python3 -c 'import uuid; print(uuid.uuid4())')"
docker exec -i "${target_db_id}" \
  psql -X -v ON_ERROR_STOP=1 -U "${DB_USER}" -d "${DB_NAME}" \
  -v local_uuid="${local_uuid}" -v base_url="http://127.0.0.1:${NGINX_PORT}" <<'SQL'
UPDATE ir_config_parameter SET value = :'local_uuid' WHERE key = 'database.uuid';
UPDATE ir_config_parameter SET value = :'base_url' WHERE key = 'web.base.url';
UPDATE ir_cron SET active = false;
UPDATE ir_mail_server SET active = false;
SQL

# Transient run-state hygiene. The registered seed source is a live demo dataset,
# so the dump can carry committed operation state. The contract matrix replays
# fixed request ids (my_work_complete_batch_pm -> snapshot_my_work_batch_1) and
# the idempotency store commits independently of the request transaction, so an
# inherited record turns that case's first-call baseline into a 409
# IDEMPOTENCY_CONFLICT. A baseline dataset must be operation-free; purge the
# transient run-state tables and prove every one of them is empty afterwards.
echo "[local.contract-snapshot.seed] purge transient run-state"
docker exec -i "${target_db_id}" \
  psql -X -v ON_ERROR_STOP=1 -U "${DB_USER}" -d "${DB_NAME}" <<'SQL'
TRUNCATE TABLE sc_idempotency_record;
SQL

while read -r transient_table; do
  [[ "${transient_table}" =~ ^[a-z][a-z0-9_]*$ ]] || {
    echo "[local.contract-snapshot.seed] unsafe transient-state expectation" >&2
    exit 2
  }
  remaining="$(docker exec "${target_db_id}" \
    psql -X -Aqt -v ON_ERROR_STOP=1 -U "${DB_USER}" -d "${DB_NAME}" \
    -c "SELECT count(*) FROM ${transient_table}")"
  [[ "${remaining}" == "0" ]] || {
    echo "[local.contract-snapshot.seed] transient run-state survived the purge table=${transient_table} rows=${remaining}" >&2
    exit 1
  }
  echo "[local.contract-snapshot.seed] cleared transient table=${transient_table} rows=0"
done <<'TRANSIENT'
sc_idempotency_record
TRANSIENT

echo "[local.contract-snapshot.seed] copy filestore ${seed_db} -> ${DB_NAME}"
docker exec "${seed_odoo_id}" tar -C /var/lib/odoo/filestore -czf - "${seed_db}" \
  | docker run --rm -i -e SEED_NAME="${seed_db}" -e TARGET_NAME="${DB_NAME}" \
      -v "${ODOO_DATA}:/target" alpine:3.20 sh -ceu '
        mkdir -p /target/filestore
        rm -rf "/target/filestore/${TARGET_NAME}"
        tar -xzf - -C /target/filestore
        [ -d "/target/filestore/${SEED_NAME}" ] || { echo "seed filestore missing" >&2; exit 2; }
        mv "/target/filestore/${SEED_NAME}" "/target/filestore/${TARGET_NAME}"
        chown -R 101:101 /target
      '

while read -r table_name minimum; do
  [[ "${table_name}" =~ ^[a-z][a-z0-9_]*$ && "${minimum}" =~ ^[0-9]+$ ]] || {
    echo "[local.contract-snapshot.seed] unsafe verification expectation" >&2
    exit 2
  }
  actual="$(docker exec "${target_db_id}" \
    psql -X -Aqt -v ON_ERROR_STOP=1 -U "${DB_USER}" -d "${DB_NAME}" \
    -c "SELECT count(*) FROM ${table_name}")"
  if (( actual < minimum )); then
    echo "[local.contract-snapshot.seed] restored count below minimum table=${table_name} actual=${actual} minimum=${minimum}" >&2
    exit 1
  fi
  echo "[local.contract-snapshot.seed] verified table=${table_name} rows=${actual} minimum=${minimum}"
done <<'EXPECT'
project_project 50
payment_request 100
res_users 50
ir_module_module 1
EXPECT

docker run --rm -e DUMP_SHA="${dump_sha}" -e SEED_REF="${seed_project}/${seed_db}" \
  -v "${ODOO_DATA}:/target" alpine:3.20 sh -ceu \
  'printf "%s %s\n" "${SEED_REF}" "${DUMP_SHA}" > /target/.sc_contract_snapshot_seed; chown 101:101 /target/.sc_contract_snapshot_seed; chmod 600 /target/.sc_contract_snapshot_seed'

echo "[local.contract-snapshot.seed] PASS project=${COMPOSE_PROJECT_NAME} db=${DB_NAME} seed=${seed_project}/${seed_db} seed_dump_sha256=${dump_sha}"
