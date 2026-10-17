#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$root"

project="sc-production-blocker-matrix"
compose_file="docker-compose.migration-safety.yml"
database="${BLOCKER_ASSET_DATABASE:-sc_blocker_formal_empty}"
image="${BLOCKER_RUNTIME_IMAGE:-sce-blocker-runtime:test}"
frontend_image="${BLOCKER_FRONTEND_IMAGE:-}"
container="sc-production-blocker-assets"
port="${BLOCKER_ASSET_PORT:-18092}"
artifacts="${BLOCKER_ASSET_ARTIFACTS:-artifacts/production-blocker/runtime-assets}"
compose=(docker compose -p "$project" -f "$compose_file")
export BLOCKER_RUNTIME_IMAGE="$image"
mkdir -p "$artifacts"
scratch="$(mktemp -d)"
cleanup() {
  docker rm -f "$container" >/dev/null 2>&1 || true
  rm -rf "$scratch"
}
trap cleanup EXIT

asset_before="$("${compose[@]}" exec -T db psql -U odoo -d "$database" -At -c \
  "SELECT count(*) FROM ir_attachment WHERE url LIKE '/web/assets/%' OR name LIKE 'web.assets%'")"
"${compose[@]}" exec -T db psql -U odoo -d "$database" -v ON_ERROR_STOP=1 -At -c \
  "DELETE FROM ir_attachment WHERE url LIKE '/web/assets/%' OR name LIKE 'web.assets%'" \
  > "$artifacts/asset-cache-delete.txt"

docker rm -f "$container" >/dev/null 2>&1 || true
"${compose[@]}" run -d --no-deps --name "$container" -p "$port:8069" --entrypoint odoo odoo \
  --db_host=db --db_port=5432 --db_user=odoo --db_password=odoo \
  --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons,/mnt/addons_external/oca_server_ux \
  --data-dir=/var/lib/odoo -d "$database" --db-filter="^${database}$" \
  --workers=0 --max-cron-threads=0 > "$artifacts/runtime-container-id.txt"

ready=0
for _ in $(seq 1 90); do
  if curl -fsS "http://127.0.0.1:$port/web/login?db=$database" > "$scratch/login.html"; then
    ready=1
    break
  fi
  sleep 1
done
[[ "$ready" -eq 1 ]]

curl -fsS -c "$scratch/cookies.txt" -H 'Content-Type: application/json' \
  -d "{\"jsonrpc\":\"2.0\",\"params\":{\"db\":\"$database\",\"login\":\"admin\",\"password\":\"admin\"}}" \
  "http://127.0.0.1:$port/web/session/authenticate" > "$scratch/session.json"
jq -e '.result.uid > 0' "$scratch/session.json" >/dev/null
curl -fsS -b "$scratch/cookies.txt" "http://127.0.0.1:$port/web" > "$scratch/web.html"

python3 - "$scratch/web.html" "$scratch/asset-urls.txt" <<'PY'
import html
import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text()
urls = sorted(set(html.unescape(value) for value in re.findall(r'(?:src|href)=["\']([^"\']*/web/assets/[^"\']+)', text)))
Path(sys.argv[2]).write_text("\n".join(urls) + "\n")
if not urls:
    raise SystemExit("authenticated backend page did not expose web asset URLs")
PY

asset_requests=0
while IFS= read -r url; do
  [[ -n "$url" ]] || continue
  curl -fsS -b "$scratch/cookies.txt" "http://127.0.0.1:$port$url" >/dev/null
  asset_requests=$((asset_requests + 1))
done < "$scratch/asset-urls.txt"
[[ "$asset_requests" -gt 0 ]]

asset_after="$("${compose[@]}" exec -T db psql -U odoo -d "$database" -At -c \
  "SELECT count(*) FROM ir_attachment WHERE url LIKE '/web/assets/%' OR name LIKE 'web.assets%'")"
[[ "$asset_after" -gt 0 ]]

report_result="$("${compose[@]}" run --rm --no-deps --entrypoint odoo odoo shell \
  --db_host=db --db_port=5432 --db_user=odoo --db_password=odoo \
  --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons,/mnt/addons_external/oca_server_ux \
  --data-dir=/var/lib/odoo -d "$database" --no-http <<'PY' | grep '^REPORT_OK|'
import hashlib
record = env['ir.module.module'].search([('name', '=', 'base')], limit=1)
pdf, kind = env['ir.actions.report']._render_qweb_pdf('base.ir_module_reference_print', res_ids=record.ids)
print('REPORT_OK|%s|%s|%s' % (kind, len(pdf), hashlib.sha256(pdf).hexdigest()))
PY
)"
[[ "$report_result" == REPORT_OK\|pdf\|* ]]

docker run --rm --entrypoint sh "$image" -eu -c '
  test ! -e /opt/sce/frontend
  test ! -e /usr/share/nginx/html/index.html
  ! command -v nginx
  ! command -v node
  ! command -v npm
'

# The static frontend is a separate carrier. Assert it only when its image is
# supplied; the Odoo runtime image above must never carry it.
if [[ -n "$frontend_image" ]]; then
  docker run --rm --entrypoint sh "$frontend_image" -eu -c '
    test -s /usr/share/nginx/html/index.html
    test -s /usr/share/nginx/html/.build-sha256
    command -v nginx
  '
fi

ASSET_BEFORE="$asset_before" ASSET_AFTER="$asset_after" ASSET_REQUESTS="$asset_requests" \
REPORT_RESULT="$report_result" IMAGE="$image" FRONTEND_IMAGE="$frontend_image" \
ARTIFACTS="$artifacts" python3 - <<'PY'
import json
import os
from pathlib import Path

kind, size, digest = os.environ["REPORT_RESULT"].split("|")[1:]
frontend_image = os.environ["FRONTEND_IMAGE"]
payload = {
    "schema_version": 1,
    "production_startup": True,
    "backend_login": True,
    "admin_authentication": True,
    "asset_cache": {
        "before_clear": int(os.environ["ASSET_BEFORE"]),
        "after_rebuild": int(os.environ["ASSET_AFTER"]),
        "requested_assets": int(os.environ["ASSET_REQUESTS"]),
    },
    "report": {"kind": kind, "bytes": int(size), "sha256": digest},
    "custom_frontend": {
        "present": False,
        "carrier": "separate_frontend_image",
        "frontend_image_checked": bool(frontend_image),
    },
    "node_runtime_present": False,
    "rtl_boundary": "unsupported_ltr_only",
}
root = Path(os.environ["ARTIFACTS"])
(root / "summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
print("[production-blocker-runtime-assets] " + json.dumps(payload, sort_keys=True))
PY
