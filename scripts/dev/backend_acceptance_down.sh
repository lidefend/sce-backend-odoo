#!/usr/bin/env bash
set -euo pipefail
: "${SC_GOVERNED_ACCEPTANCE_LOWER_ENTRY:?DENY: use make backend.acceptance.down; direct backend acceptance shutdown is forbidden}"
ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
source "$ROOT_DIR/scripts/common/governed_make_entry.sh"
require_governed_make_ancestor "backend_acceptance_down.sh" "$ROOT_DIR" "backend.acceptance.down"
NAME="${BACKEND_ACCEPTANCE_NAME:-sc-backend-odoo-acceptance}"
[[ "$NAME" == "sc-backend-odoo-acceptance" ]] || { echo "[backend.acceptance.down] DENY non-canonical container=$NAME" >&2; exit 2; }
if docker inspect "$NAME" >/dev/null 2>&1; then
  source_mount="$(docker inspect "$NAME" --format '{{range .Mounts}}{{if eq .Destination "/mnt/source-addons"}}{{.Source}}{{end}}{{end}}')"
  [[ "$source_mount" == "$(readlink -f "$ROOT_DIR/addons")" ]] || { echo "[backend.acceptance.down] DENY source identity mismatch" >&2; exit 2; }
  container_env="$(docker inspect "$NAME" --format '{{range .Config.Env}}{{println .}}{{end}}')"
  grep -Fqx 'DB_NAME=sc_frontend_acceptance' <<<"$container_env" || { echo "[backend.acceptance.down] DENY database identity mismatch" >&2; exit 2; }
  grep -Fqx 'ODOO_DBFILTER=^sc_frontend_acceptance$' <<<"$container_env" || { echo "[backend.acceptance.down] DENY database filter mismatch" >&2; exit 2; }
  expected_revision="$(git -C "$ROOT_DIR" rev-parse HEAD)"
  expected_fingerprint="$(ROOT_DIR="$ROOT_DIR" bash "$ROOT_DIR/scripts/dev/acceptance_source_fingerprint.sh")"
  expected_version="$(tr -d '[:space:]' < "$ROOT_DIR/VERSION")"
  grep -Fqx "SC_SOURCE_REVISION=$expected_revision" <<<"$container_env" || { echo "[backend.acceptance.down] DENY source revision mismatch" >&2; exit 2; }
  grep -Fqx "SC_SOURCE_FINGERPRINT=$expected_fingerprint" <<<"$container_env" || { echo "[backend.acceptance.down] DENY source fingerprint mismatch" >&2; exit 2; }
  grep -Fqx "SC_PRODUCT_VERSION=$expected_version" <<<"$container_env" || { echo "[backend.acceptance.down] DENY product version mismatch" >&2; exit 2; }
  odoo_volume="$(docker inspect "$NAME" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/odoo"}}{{.Name}}{{end}}{{end}}')"
  [[ "$odoo_volume" == "sc_fe_r2_p1_01_odoo" ]] || { echo "[backend.acceptance.down] DENY filestore identity mismatch" >&2; exit 2; }
  [[ "$(docker port "$NAME" 8069/tcp 2>/dev/null || true)" == "127.0.0.1:18082" ]] || { echo "[backend.acceptance.down] DENY port identity mismatch" >&2; exit 2; }
  docker rm -f "$NAME" >/dev/null
fi
echo "[backend.acceptance.down] PASS"
