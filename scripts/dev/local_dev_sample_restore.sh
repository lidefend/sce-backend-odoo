#!/usr/bin/env bash
set -euo pipefail

: "${ROOT_DIR:?ROOT_DIR is required}"
: "${LOCAL_DEV_SAMPLE_BACKUP_DIR:?LOCAL_DEV_SAMPLE_BACKUP_DIR is required}"
source "${ROOT_DIR}/scripts/common/env.sh"
source "${ROOT_DIR}/scripts/common/compose.sh"

expected_root="/home/lidefend/workspace/.secure/local-dev-refresh"
backup_dir="$(readlink -f -- "${LOCAL_DEV_SAMPLE_BACKUP_DIR}")"
expected_project="sc-local-sample"
expected_db="sc_dev_sample"
expected_filter='^sc_dev_sample$'
expected_db_volume="sc_local_sample_db_data"
expected_redis_volume="sc_local_sample_redis_data"
expected_odoo_volume="sc_local_sample_odoo_data"

[[ "${CONFIRM_LOCAL_DEV_SAMPLE_RESTORE:-}" == "RESTORE_VERIFIED_DAILY_SAMPLE" ]] || {
  echo "[local.dev.restore] exact confirmation is required" >&2
  exit 2
}
[[ "${backup_dir}" =~ ^${expected_root}/sc_demo-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$ ]] || {
  echo "[local.dev.restore] invalid governed backup directory: ${backup_dir}" >&2
  exit 2
}
[[ "${COMPOSE_PROJECT_NAME}" == "${expected_project}" \
  && "${DB_NAME}" == "${expected_db}" \
  && "${ODOO_DBFILTER}" == "${expected_filter}" \
  && "${DB_DATA}" == "${expected_db_volume}" \
  && "${REDIS_DATA}" == "${expected_redis_volume}" \
  && "${ODOO_DATA}" == "${expected_odoo_volume}" ]] || {
    echo "[local.dev.restore] local target identity mismatch" >&2
    exit 2
  }

for artifact in database.dump filestore.tar.gz manifest.json SHA256SUMS; do
  [[ -f "${backup_dir}/${artifact}" && ! -L "${backup_dir}/${artifact}" ]] || {
    echo "[local.dev.restore] artifact missing or unsafe: ${artifact}" >&2
    exit 2
  }
done
(cd "${backup_dir}" && sha256sum -c SHA256SUMS)
python3 - "${backup_dir}/manifest.json" "${backup_dir}/filestore.tar.gz" <<'PY'
import json
import sys
import tarfile
from pathlib import Path, PurePosixPath

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if manifest.get("database") != "sc_demo":
    raise SystemExit("[local.dev.restore] source manifest database mismatch")
if manifest.get("schema_version") != "daily_candidate_data_continuity.v1":
    raise SystemExit("[local.dev.restore] source manifest schema mismatch")
if manifest.get("backup_status") != "complete" or not manifest.get("pair_stable_during_capture"):
    raise SystemExit("[local.dev.restore] source pair is not complete and stable")
with tarfile.open(sys.argv[2], "r:gz") as archive:
    members = archive.getmembers()
    if not members:
        raise SystemExit("[local.dev.restore] source filestore is empty")
    for member in members:
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or path.parts[0] != "sc_demo":
            raise SystemExit("[local.dev.restore] unsafe filestore member")
        if not (member.isfile() or member.isdir()):
            raise SystemExit("[local.dev.restore] unsupported filestore member")
PY

if [[ -n "$(compose_dev ps -aq)" ]]; then
  echo "[local.dev.restore] local project containers must be down" >&2
  exit 2
fi
for volume in "${DB_DATA}" "${REDIS_DATA}" "${ODOO_DATA}"; do
  if docker volume inspect "${volume}" >/dev/null 2>&1; then
    echo "[local.dev.restore] target volume already exists: ${volume}" >&2
    exit 2
  fi
done

compose_dev up -d db redis
db_cid="$(compose_dev ps -q db)"
for _ in $(seq 1 30); do
  state="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${db_cid}")"
  [[ "${state}" == "healthy" ]] && break
  sleep 2
done
[[ "${state:-}" == "healthy" ]] || {
  echo "[local.dev.restore] fresh database did not become healthy" >&2
  exit 1
}

docker exec -i "${db_cid}" \
  pg_restore -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists --no-owner --no-privileges \
  <"${backup_dir}/database.dump"

local_uuid="$(python3 -c 'import uuid; print(uuid.uuid4())')"
docker exec -i "${db_cid}" \
  psql -X -v ON_ERROR_STOP=1 -U "${DB_USER}" -d "${DB_NAME}" \
  -v local_uuid="${local_uuid}" <<'SQL'
UPDATE ir_config_parameter SET value = :'local_uuid' WHERE key = 'database.uuid';
UPDATE ir_config_parameter SET value = 'http://127.0.0.1:18084' WHERE key = 'web.base.url';
UPDATE ir_cron SET active = false;
UPDATE ir_mail_server SET active = false;
SQL

while read -r table_name minimum maximum; do
  [[ "${table_name}" =~ ^[a-z][a-z0-9_]*$ \
    && "${minimum}" =~ ^[0-9]+$ \
    && "${maximum}" =~ ^[0-9]+$ ]] || {
      echo "[local.dev.restore] unsafe recovery expectation" >&2
      exit 2
    }
  actual="$(docker exec "${db_cid}" \
    psql -X -Aqt -v ON_ERROR_STOP=1 -U "${DB_USER}" -d "${DB_NAME}" \
    -c "SELECT count(*) FROM ${table_name}")"
  if (( actual < minimum || actual > maximum )); then
    echo "[local.dev.restore] restored count mismatch table=${table_name} actual=${actual} expected=${minimum}..${maximum}" >&2
    exit 1
  fi
  echo "[local.dev.restore] verified table=${table_name} rows=${actual}"
done < <(python3 - "${backup_dir}/manifest.json" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
ranges = manifest.get("recovery_expectations", {}).get("table_count_ranges", {})
if not ranges:
    raise SystemExit("[local.dev.restore] table count expectations are missing")
for table_name in sorted(ranges):
    bounds = ranges[table_name]
    print(table_name, int(bounds["minimum"]), int(bounds["maximum"]))
PY
)

compose_dev create odoo
docker run --rm \
  -v "${backup_dir}:/backup:ro" \
  -v "${ODOO_DATA}:/target" \
  alpine:3.20 sh -ceu '
    mkdir -p /target/filestore
    tar -xzf /backup/filestore.tar.gz -C /target/filestore
    mv /target/filestore/sc_demo /target/filestore/sc_dev_sample
    chown -R 101:101 /target
  '

compose_dev up -d odoo nginx
odoo_cid="$(compose_dev ps -q odoo)"
for _ in $(seq 1 90); do
  state="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${odoo_cid}")"
  [[ "${state}" == "healthy" ]] && break
  sleep 2
done
[[ "${state:-}" == "healthy" ]] || {
  echo "[local.dev.restore] Odoo did not become healthy" >&2
  exit 1
}

manifest_sha="$(sha256sum "${backup_dir}/manifest.json" | awk '{print $1}')"
docker run --rm -v "${ODOO_DATA}:/target" alpine:3.20 sh -ceu \
  'printf "%s %s\n" "$1" "$2" > /target/.sc_local_sample_restored; chown 101:101 /target/.sc_local_sample_restored; chmod 600 /target/.sc_local_sample_restored' \
  _ "$(basename "${backup_dir}")" "${manifest_sha}"

echo "[local.dev.restore] PASS project=${COMPOSE_PROJECT_NAME} db=${DB_NAME} source=$(basename "${backup_dir}")"
