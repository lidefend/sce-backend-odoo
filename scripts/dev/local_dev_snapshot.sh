#!/usr/bin/env bash
set -euo pipefail

: "${ROOT_DIR:?ROOT_DIR is required}"
source "${ROOT_DIR}/scripts/common/env.sh"
source "${ROOT_DIR}/scripts/common/compose.sh"

profile="${1:-persistent}"
case "${profile}" in
  persistent)
    expected_project="sc-local-dev"
    expected_db="sc_dev_demo"
    expected_filter='^sc_dev_demo$'
    tenant_id="platform-local-feature-demo"
    ;;
  sample)
    expected_project="sc-local-sample"
    expected_db="sc_dev_sample"
    expected_filter='^sc_dev_sample$'
    tenant_id="platform-local-business-sample"
    ;;
  *)
    echo "usage: $0 persistent|sample" >&2
    exit 2
    ;;
esac
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

echo "[local.dev.snapshot] database -> ${snapshot_dir}/${DB_NAME}.dump"
docker exec "${db_cid}" \
  pg_dump -U "${DB_USER}" -d "${DB_NAME}" -Fc >"${snapshot_dir}/${DB_NAME}.dump"

echo "[local.dev.snapshot] filestore -> ${snapshot_dir}/${DB_NAME}-filestore.tar.gz"
docker exec "${odoo_cid}" sh -c \
  'if [ -d "/var/lib/odoo/filestore/${DB_NAME}" ]; then tar -C /var/lib/odoo/filestore -czf - "${DB_NAME}"; else tar -czf - --files-from /dev/null; fi' \
  >"${snapshot_dir}/${DB_NAME}-filestore.tar.gz"

db_size="$(docker exec "${db_cid}" psql -U "${DB_USER}" -d "${DB_NAME}" -Atc 'SELECT pg_database_size(current_database())')"
source_sha="$(git -C "${ROOT_DIR}" rev-parse HEAD)"
cat >"${snapshot_dir}/manifest.txt" <<EOF
schema_version=1
snapshot_id=${snapshot_id}
environment_id=local-persistent-development
tenant_id=${tenant_id}
compose_project=${COMPOSE_PROJECT_NAME}
database=${DB_NAME}
dbfilter=${ODOO_DBFILTER}
filestore=odoo_data:/var/lib/odoo/filestore/${DB_NAME}
source_sha=${source_sha}
database_size_bytes=${db_size}
EOF
(cd "${snapshot_dir}" && sha256sum "${DB_NAME}.dump" "${DB_NAME}-filestore.tar.gz" >>manifest.txt)
chmod -R go-rwx "${snapshot_dir}"
echo "[local.dev.snapshot] PASS ${snapshot_dir}"
