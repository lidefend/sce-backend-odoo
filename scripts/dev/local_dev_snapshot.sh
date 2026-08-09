#!/usr/bin/env bash
set -euo pipefail

: "${ROOT_DIR:?ROOT_DIR is required}"
source "${ROOT_DIR}/scripts/common/env.sh"
source "${ROOT_DIR}/scripts/common/compose.sh"

expected_project="sc-backend-odoo-dev"
expected_db="sc_demo"
expected_filter='^sc_demo$'
if [[ "${COMPOSE_PROJECT_NAME}" != "${expected_project}" || "${DB_NAME}" != "${expected_db}" || "${ODOO_DBFILTER}" != "${expected_filter}" ]]; then
  echo "[local.dev.snapshot] refused: expected project=${expected_project} db=${expected_db} dbfilter=${expected_filter}" >&2
  exit 2
fi

db_cid="$(compose_dev ps -q db)"
odoo_cid="$(compose_dev ps -q odoo)"
if [[ -z "${db_cid}" || -z "${odoo_cid}" ]]; then
  echo "[local.dev.snapshot] db and odoo services must be running" >&2
  exit 2
fi

snapshot_id="$(date -u +%Y%m%dT%H%M%SZ)"
snapshot_dir="${ROOT_DIR}/artifacts/local-dev/snapshots/${snapshot_id}"
mkdir -p "${snapshot_dir}"

echo "[local.dev.snapshot] database -> ${snapshot_dir}/sc_demo.dump"
docker exec -e PGPASSWORD="${DB_PASSWORD}" "${db_cid}" \
  pg_dump -U "${DB_USER}" -d "${DB_NAME}" -Fc >"${snapshot_dir}/sc_demo.dump"

echo "[local.dev.snapshot] filestore -> ${snapshot_dir}/sc_demo-filestore.tar.gz"
docker exec "${odoo_cid}" sh -c \
  'if [ -d /var/lib/odoo/filestore/sc_demo ]; then tar -C /var/lib/odoo/filestore -czf - sc_demo; else tar -czf - --files-from /dev/null; fi' \
  >"${snapshot_dir}/sc_demo-filestore.tar.gz"

db_size="$(docker exec -e PGPASSWORD="${DB_PASSWORD}" "${db_cid}" psql -U "${DB_USER}" -d "${DB_NAME}" -Atc 'SELECT pg_database_size(current_database())')"
source_sha="$(git -C "${ROOT_DIR}" rev-parse HEAD)"
cat >"${snapshot_dir}/manifest.txt" <<EOF
schema_version=1
snapshot_id=${snapshot_id}
environment_id=local-persistent-development
tenant_id=platform-internal-demo
compose_project=${COMPOSE_PROJECT_NAME}
database=${DB_NAME}
dbfilter=${ODOO_DBFILTER}
filestore=odoo_data:/var/lib/odoo/filestore/${DB_NAME}
source_sha=${source_sha}
database_size_bytes=${db_size}
EOF
(cd "${snapshot_dir}" && sha256sum sc_demo.dump sc_demo-filestore.tar.gz >>manifest.txt)
chmod -R go-rwx "${snapshot_dir}"
echo "[local.dev.snapshot] PASS ${snapshot_dir}"
