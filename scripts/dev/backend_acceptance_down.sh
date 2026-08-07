#!/usr/bin/env bash
set -euo pipefail
docker rm -f "${BACKEND_ACCEPTANCE_NAME:-sc-backend-odoo-acceptance}" >/dev/null 2>&1 || true
echo "[backend.acceptance.down] PASS"
