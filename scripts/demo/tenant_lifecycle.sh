#!/usr/bin/env bash
set -euo pipefail

: "${ROOT_DIR:?ROOT_DIR is required}"
source "${ROOT_DIR}/scripts/common/env.sh"
source "${ROOT_DIR}/scripts/common/compose.sh"
source "${ROOT_DIR}/scripts/common/demo_data_guard.sh"

action="${1:-reset}"
[[ "${action}" == "reset" || "${action}" == "verify" ]] || {
  echo "usage: tenant_lifecycle.sh {reset|verify}" >&2
  exit 64
}

guard_demo_data_scope
[[ "${SC_DEMO_TENANT_LIFECYCLE:-}" == "1" ]] || { echo "DEMO_TENANT_LIFECYCLE_MARKER_REQUIRED" >&2; exit 40; }
[[ "${ISOLATED_DEMO_TENANT:-}" == "1" ]] || { echo "ISOLATED_DEMO_TENANT_REQUIRED" >&2; exit 41; }
[[ "${ODOO_DBFILTER}" == "^${DB_NAME}$" ]] || { echo "DEMO_TENANT_EXACT_DBFILTER_REQUIRED" >&2; exit 42; }
[[ "${COMPOSE_PROJECT_NAME}" == sc-demo-* ]] || { echo "DEMO_TENANT_PROJECT_IDENTITY_INVALID" >&2; exit 43; }
[[ -z "${SC_CUSTOMER_ADDONS_ROOT:-}" ]] || { echo "DEMO_TENANT_CUSTOMER_ADDONS_FORBIDDEN" >&2; exit 44; }
for identity in "${DB_DATA:-}" "${REDIS_DATA:-}" "${ODOO_DATA:-}"; do
  [[ "${identity}" == sc_demo_* ]] || { echo "DEMO_TENANT_STORAGE_IDENTITY_INVALID" >&2; exit 45; }
done

lock_file="${SC_DEMO_TENANT_LOCK_FILE:-/tmp/${COMPOSE_PROJECT_NAME}.lifecycle.lock}"
exec 9>"${lock_file}"
flock -n 9 || { echo "DEMO_TENANT_LIFECYCLE_ALREADY_RUNNING" >&2; exit 46; }

verify_runtime() {
  local metrics
  metrics="$(compose_dev exec -T db psql -U "${DB_USER}" -d "${DB_NAME}" -AtF '|' -c "
SELECT
  (SELECT count(*) FROM ir_module_module WHERE state IN ('to install','to upgrade','to remove')),
  (SELECT count(*) FROM ir_module_module WHERE name='smart_construction_demo' AND state='installed'),
  (SELECT count(*) FROM ir_module_module WHERE name LIKE 'sce_customer_%' AND state='installed');")"
  IFS='|' read -r pending demo_installed customer_installed <<<"${metrics}"
  [[ "${pending}" == "0" && "${demo_installed}" == "1" && "${customer_installed}" == "0" ]]
  demo_xmlids="$(compose_dev exec -T db psql -U "${DB_USER}" -d "${DB_NAME}" -Atc \
    "SELECT count(*) FROM ir_model_data WHERE module='smart_construction_demo';")"
  [[ "${demo_xmlids}" -gt 0 ]]
  local ready=0
  local attempt
  for attempt in $(seq 1 "${SC_DEMO_TENANT_READY_ATTEMPTS:-30}"); do
    if compose_dev exec -T odoo python3 -c \
      "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8069/web/login', timeout=3)" \
      >/dev/null 2>&1; then
      ready=1
      break
    fi
    sleep 2
  done
  [[ "${ready}" == "1" ]] || {
    echo "DEMO_TENANT_ODOO_READY_TIMEOUT" >&2
    compose_dev logs --tail=120 odoo >&2 || true
    return 47
  }
  printf '[demo.tenant] PASS db=%s demo_xmlids=%s customer_modules=0 pending=0\n' "${DB_NAME}" "${demo_xmlids}"
}

if [[ "${action}" == "verify" ]]; then
  verify_runtime
  exit 0
fi

export DEMO_LOGFILE="${SC_DEMO_TENANT_LOGFILE:-/var/lib/odoo/demo-lifecycle-logs/install.log}"

# Compose creates a missing bind-mount source as root.  Pre-create the exact
# evidence directory as the invoking user so runtime audits remain writable on
# both the first reset and every replay.
install -d -m 0777 "${ROOT_DIR}/artifacts" "${ROOT_DIR}/artifacts/demo"
chmod 0777 "${ROOT_DIR}/artifacts/demo"

compose_dev stop nginx odoo >/dev/null 2>&1 || true
restore_failure_state() {
  status=$?
  if [[ "${status}" -ne 0 ]]; then
    echo "[demo.tenant] reset failed; public proxy remains stopped" >&2
  fi
  exit "${status}"
}
trap restore_failure_state EXIT

compose_dev up -d db redis
# The Odoo data volume belongs exclusively to this demo tenant. Remove only
# this exact database's filestore and the isolated volume's sessions.
compose_dev run --rm -T --no-deps --entrypoint python3 odoo \
  /mnt/scripts/demo/purge_demo_runtime.py \
  --data-root /var/lib/odoo --database "${DB_NAME}"

SC_ENVIRONMENT=demo SC_ALLOW_DEMO_DATA=1 CODEX_MODE=gate \
  make --no-print-directory -C "${ROOT_DIR}" ENV="${ENV}" ENV_FILE="${ENV_FILE}" \
  demo.reset DB_NAME="${DB_NAME}"

# A tenant reset must produce the release-grade product walkthrough, not only
# the module's minimal bootstrap records. Keep failure-drill scenarios out.
SC_ENVIRONMENT=demo SC_ALLOW_DEMO_DATA=1 DEMO_RESTART_AFTER_LOAD=0 \
  make --no-print-directory -C "${ROOT_DIR}" ENV="${ENV}" ENV_FILE="${ENV_FILE}" \
  demo.load.release DB_NAME="${DB_NAME}"

compose_dev up -d odoo
verify_runtime
SC_ENVIRONMENT=demo SC_ALLOW_DEMO_DATA=1 \
  make --no-print-directory -C "${ROOT_DIR}" ENV="${ENV}" ENV_FILE="${ENV_FILE}" \
  verify.demo.release.seed DB_NAME="${DB_NAME}"
SC_ENVIRONMENT=demo SC_ALLOW_DEMO_DATA=1 \
  make --no-print-directory -C "${ROOT_DIR}" ENV="${ENV}" ENV_FILE="${ENV_FILE}" \
  verify.demo.formal_product_coverage DB_NAME="${DB_NAME}"
compose_dev up -d nginx
trap - EXIT
printf '[demo.tenant] reset complete db=%s\n' "${DB_NAME}"
