#!/usr/bin/env bash
set -euo pipefail
NAME=sc-backend-odoo-acceptance
if docker ps --format '{{.Names}}' | grep -qx "$NAME"; then
  if curl -fsS http://127.0.0.1:18082/web/login >/dev/null 2>&1; then
    echo "[backend.acceptance.up] already healthy"
    exit 0
  fi
  echo "[backend.acceptance.up] replacing unhealthy container" >&2
fi
docker rm -f "$NAME" >/dev/null 2>&1 || true
PRODUCT_VERSION="$(tr -d '[:space:]' < VERSION)"
SOURCE_REVISION="$(git rev-parse HEAD)"
docker compose run -d --no-deps --name "$NAME" -p 127.0.0.1:18082:8069 \
  -e ODOO_DB=sc_frontend_acceptance \
  -e DB_NAME=sc_frontend_acceptance \
  -e ODOO_DBFILTER='^sc_frontend_acceptance$' \
  -e LIST_DB=false \
  -e SC_PRODUCT_VERSION="$PRODUCT_VERSION" \
  -e SC_SOURCE_REVISION="$SOURCE_REVISION" \
  odoo >/dev/null
for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:18082/web/login >/dev/null 2>&1; then echo "[backend.acceptance.up] PASS db=sc_frontend_acceptance port=18082"; exit 0; fi
  sleep 2
done
docker logs --tail 100 "$NAME" >&2
exit 1
