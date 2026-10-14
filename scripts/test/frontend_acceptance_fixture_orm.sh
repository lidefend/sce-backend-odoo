#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
export ROOT_DIR

source "$ROOT_DIR/scripts/common/frontend_acceptance_guard.sh"
guard_frontend_acceptance_scope
acquire_frontend_acceptance_lock lifecycle

source "$ROOT_DIR/scripts/common/env.sh"
source "$ROOT_DIR/scripts/common/guard_prod.sh"
guard_prod_forbid
source "$ROOT_DIR/scripts/_lib/common.sh"

# The acceptance fixture module is listed in forbidden_implicit_modules, so no
# product/demo profile ever installs it. Selecting its tag on a profile that does
# not carry the module runs zero tests and still exits zero - a green receipt for
# nothing. This entry runs the same tag on the governed acceptance carrier, where
# the module is installed and the freeze it pins is actually exercised.
MODULE=smart_construction_acceptance_fixture
TEST_TAGS=acceptance_fixture_execution_freeze
TEST_TAGS_FINAL="$(normalize_test_tags "${MODULE}" "${TEST_TAGS}")"
export DB_NAME SC_ENVIRONMENT SC_ALLOW_DEMO_DATA

echo "[acceptance.frontend.fixture_orm] db=${DB_NAME} module=${MODULE} tags=${TEST_TAGS_FINAL}"

LOG_DIR="${ROOT_DIR}/.runtime/acceptance"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/fixture_orm_$(date -u +%Y%m%dT%H%M%SZ).log"

# The rendered acceptance /var/lib/odoo/odoo.conf pins `logfile`, which sends the
# whole test receipt to a file inside the carrier and leaves this entry's stdout
# empty - a receipt nobody can read proves nothing. The carrier config stays the
# identity source (credentials, dbfilter, data_dir, addons_path); only the log
# destination is overridden on the command line.
set +e
# shellcheck disable=SC2086
compose ${COMPOSE_FILES} run --rm -T \
  -v "${DOCS_MOUNT_HOST}:${DOCS_MOUNT_CONT}:ro" \
  -v "${CONFIG_MOUNT_HOST}:${CONFIG_MOUNT_CONT}:ro" \
  --entrypoint bash odoo -lc "
    pip3 install -q -r ${CONFIG_MOUNT_CONT}/requirements-test.txt
    exec /usr/bin/odoo -c /var/lib/odoo/odoo.conf \
      -d ${DB_NAME} \
      --no-http --workers=0 --max-cron-threads=0 \
      --test-enable \
      --test-tags \"${TEST_TAGS_FINAL}\" \
      --stop-after-init \
      --logfile=/dev/stdout \
      --log-level=test
  " 2>&1 | tee "$LOG_FILE"
run_rc="${PIPESTATUS[0]}"
set -e
[[ "$run_rc" -eq 0 ]] || {
  echo "[acceptance.frontend.fixture_orm] FAIL odoo exit=${run_rc} log=${LOG_FILE}" >&2
  exit "$run_rc"
}

# A green exit code is not a test result: selecting a tag that matches nothing
# exits zero with no summary at all. Bind the receipt to the summary line the
# test runner actually prints.
summary="$(grep -E 'error\(s\) of [0-9]+ tests' "$LOG_FILE" | tail -n 1 || true)"
[[ -n "$summary" ]] || {
  echo "[acceptance.frontend.fixture_orm] DENY no test summary for tags=${TEST_TAGS_FINAL} log=${LOG_FILE}" >&2
  exit 2
}
tests="$(sed -E 's/.*error\(s\) of ([0-9]+) tests.*/\1/' <<<"$summary")"
failed="$(sed -E 's/^.* ([0-9]+) failed.*/\1/' <<<"$summary")"
[[ "$tests" =~ ^[0-9]+$ && "$failed" =~ ^[0-9]+$ ]] || {
  echo "[acceptance.frontend.fixture_orm] DENY unreadable test summary: ${summary}" >&2
  exit 2
}
(( tests > 0 )) || {
  echo "[acceptance.frontend.fixture_orm] DENY zero tests matched tags=${TEST_TAGS_FINAL} log=${LOG_FILE}" >&2
  exit 2
}
(( failed == 0 )) || {
  echo "[acceptance.frontend.fixture_orm] FAIL tests=${tests} failed=${failed} log=${LOG_FILE}" >&2
  exit 1
}
echo "[acceptance.frontend.fixture_orm] PASS tests=${tests} failed=${failed} log=${LOG_FILE}"
