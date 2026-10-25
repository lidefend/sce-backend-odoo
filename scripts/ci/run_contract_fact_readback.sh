#!/usr/bin/env bash
set -euo pipefail

# Run the contract/fact readback probe in the CI backend-suite compose carrier.
# make test runs a one-off odoo container with --entrypoint bash and explicit
# CLI arguments (no -c config file), so the daily-runtime odoo_shell_exec.sh
# (compose exec + /var/lib/odoo/odoo.conf) does not apply here. This wrapper
# mirrors test.sh: a disposable odoo container, explicit DB/addons arguments,
# and the probe script is piped to odoo shell on stdin.

source "$(dirname "$0")/../_lib/common.sh"

: "${DB_NAME:?DB_NAME is required}"
: "${DB_USER:?DB_USER is required}"
: "${DB_PASSWORD:?DB_PASSWORD is required}"

compose ${COMPOSE_FILES} run --no-deps --rm -T --entrypoint odoo \
  -e CANDIDATE_DB_NAME="${CANDIDATE_DB_NAME:-}" \
  -e CANDIDATE_GIT_HEAD="${CANDIDATE_GIT_HEAD:-}" \
  -e CANDIDATE_GIT_TREE="${CANDIDATE_GIT_TREE:-}" \
  -e CANDIDATE_ROLE_XMLID="${CANDIDATE_ROLE_XMLID:-}" \
  -e CANDIDATE_ACTION_XMLID="${CANDIDATE_ACTION_XMLID:-}" \
  odoo shell \
  --db_host=db --db_port=5432 --db_user="${DB_USER}" --db_password="${DB_PASSWORD}" \
  -d "${DB_NAME}" \
  --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/source-addons,/mnt/demo-addons,"${ADDONS_EXTERNAL_MOUNT}" \
  --no-http --workers=0 --max-cron-threads=0
