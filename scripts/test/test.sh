#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
export ROOT_DIR

# shellcheck source=../common/env.sh
source "$ROOT_DIR/scripts/common/env.sh"
source "$ROOT_DIR/scripts/common/guard_prod.sh"
source "$(dirname "$0")/../_lib/common.sh"
guard_prod_forbid
log "dev test (upgrade + tests) DB=${DB_NAME} tags=${TEST_TAGS}"
TEST_TAGS_FINAL="$(normalize_test_tags "${MODULE}" "${TEST_TAGS}")"

# Opt-in evidence capture in the existing test container after dependency install.
# No extra database or test execution, and no environment/credential dump.
RECEIPT_ARGS=()
if [[ "${SC_BACKEND_RECEIPT_CAPTURE:-0}" == "1" ]]; then
  RECEIPT_ARGS=(-e SC_BACKEND_RECEIPT_CAPTURE=1
    -v "${ROOT_DIR}/scripts/ci/backend_test_receipt.py:/tmp/sc-test-tools/scripts/ci/backend_test_receipt.py:ro")
fi

# Optional runner-owned download/wheel cache. This never contains a database
# or a test verdict: pip still resolves and installs the requested dependencies.
PIP_CACHE_ARGS=()
if [[ -n "${SC_TEST_PIP_CACHE_HOST:-}" ]]; then
  case "${SC_TEST_PIP_CACHE_HOST}" in
    /*) ;;
    *) echo "SC_TEST_PIP_CACHE_HOST must be absolute" >&2; exit 2 ;;
  esac
  if [[ "${SC_TEST_PIP_CACHE_HOST}" == / || "${SC_TEST_PIP_CACHE_HOST}" == *:* ||
        "${SC_TEST_PIP_CACHE_HOST}" == *$'\n'* || ! -d "${SC_TEST_PIP_CACHE_HOST}" ]]; then
    echo "invalid or absent runner pip cache directory" >&2
    exit 2
  fi
  PIP_CACHE_ARGS=(-v "${SC_TEST_PIP_CACHE_HOST}:/tmp/sc-test-pip-cache"
    -e PIP_CACHE_DIR=/tmp/sc-test-pip-cache)
fi

# Explicit CI-only opt-in; ordinary local.test and clean-install lanes stay fresh.
PREPARATION_ARGS=()
PREPARATION_COMMAND=""
PREPARATION_ODOO_ARGS=""
# Explicit workflow tag overrides may select dependency at_install tests.
# They must retain the original fresh-install behavior.
if [[ "${SC_TEST_DEPENDENCY_PREPARATION:-0}" == "1" && -z "${TEST_TAGS_INPUT:-}" ]]; then
  PREPARATION_ARGS=(-v "${ROOT_DIR}/scripts/test/dependency_baseline.py:/tmp/sc-dependency-baseline.py:ro"
    -e "SC_TEST_TARGET_MODULE=${MODULE}" -e "SC_TEST_TARGET_DB=${DB_NAME}"
    -e "GITHUB_RUN_ID=${GITHUB_RUN_ID:-}" -e "GITHUB_RUN_ATTEMPT=${GITHUB_RUN_ATTEMPT:-}"
    -e "SHARD_INDEX=${SHARD_INDEX:-}" -e "SOURCE_SHA=${SOURCE_SHA:-}"
    -e "COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}" -e "ADDONS_EXTERNAL_MOUNT=${ADDONS_EXTERNAL_MOUNT}")
  PREPARATION_ODOO_ARGS="--db-filter=^${DB_NAME}$ --data-dir=/var/lib/odoo"
  PREPARATION_COMMAND="python3 /tmp/sc-dependency-baseline.py || exit \$?"
fi

RUN_RM="${RUN_RM:---rm}"
RUN_NAME=()
if [[ "${KEEP_TEST_CONTAINER:-0}" == "1" ]]; then
  RUN_RM=""
  RUN_NAME=(--name "sc-test-odoo-${DB_NAME}")
  if docker ps -a --format '{{.Names}}' | grep -q "^sc-test-odoo-${DB_NAME}$"; then
    docker rm -f "sc-test-odoo-${DB_NAME}" >/dev/null
  fi
fi

# shellcheck disable=SC2086
compose ${COMPOSE_FILES} run --no-deps ${RUN_RM} -T "${RUN_NAME[@]}" \
  "${RECEIPT_ARGS[@]}" "${PIP_CACHE_ARGS[@]}" "${PREPARATION_ARGS[@]}" \
  -v "${DOCS_MOUNT_HOST}:${DOCS_MOUNT_CONT}:ro" \
  -v "${CONFIG_MOUNT_HOST}:${CONFIG_MOUNT_CONT}:ro" \
  --entrypoint bash odoo -lc "
    pip3 install -q -r ${CONFIG_MOUNT_CONT}/requirements-test.txt
    if [ \"\${SC_BACKEND_RECEIPT_CAPTURE:-0}\" = 1 ]; then
      python3 /tmp/sc-test-tools/scripts/ci/backend_test_receipt.py environment || exit \$?
    fi
    ${PREPARATION_COMMAND}
    exec /usr/bin/odoo \
      --db_host=db --db_port=5432 --db_user=${DB_USER} --db_password=${DB_PASSWORD} \
      -d ${DB_NAME} ${PREPARATION_ODOO_ARGS} \
      --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/source-addons,/mnt/demo-addons,${ADDONS_EXTERNAL_MOUNT} \
      -i ${MODULE} \
      --without-demo=all \
      --no-http --workers=0 --max-cron-threads=0 \
      --test-enable \
      --test-tags \"${TEST_TAGS_FINAL}\" \
      --stop-after-init \
      --log-level=test
  "
