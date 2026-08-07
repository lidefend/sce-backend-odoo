#!/usr/bin/env bash
set -euo pipefail
NAME="${BACKEND_ACCEPTANCE_NAME:-sc-backend-odoo-acceptance}"
PORT="${BACKEND_ACCEPTANCE_PORT:-18082}"
DATABASE="${BACKEND_ACCEPTANCE_DB:-sc_frontend_acceptance}"
if [[ ! "$DATABASE" =~ ^[a-zA-Z0-9_]+$ ]]; then
  echo "[backend.acceptance.up] invalid database identifier" >&2
  exit 2
fi
if docker ps --format '{{.Names}}' | grep -qx "$NAME"; then
  if curl -fsS "http://127.0.0.1:${PORT}/web/login" >/dev/null 2>&1; then
    echo "[backend.acceptance.up] already healthy"
    exit 0
  fi
  echo "[backend.acceptance.up] replacing unhealthy container" >&2
fi
docker rm -f "$NAME" >/dev/null 2>&1 || true
PRODUCT_VERSION="$(tr -d '[:space:]' < VERSION)"
SOURCE_REVISION="$(git rev-parse HEAD)"
docker compose run -d --no-deps --name "$NAME" -p "127.0.0.1:${PORT}:8069" \
  -e ODOO_DB="$DATABASE" \
  -e DB_NAME="$DATABASE" \
  -e ODOO_DBFILTER="^${DATABASE}$" \
  -e LIST_DB=false \
  -e SC_PRODUCT_VERSION="$PRODUCT_VERSION" \
  -e SC_SOURCE_REVISION="$SOURCE_REVISION" \
  odoo >/dev/null
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:${PORT}/web/login" >/dev/null 2>&1; then echo "[backend.acceptance.up] PASS db=${DATABASE} port=${PORT}"; exit 0; fi
  sleep 2
done
docker logs --tail 100 "$NAME" >&2
exit 1
