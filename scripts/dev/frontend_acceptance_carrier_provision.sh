#!/usr/bin/env bash
set -euo pipefail

# Governed provision entry for the managed local acceptance carrier
# (project sc-fe-r2-p1-01 / database sc_frontend_acceptance). It is the
# reciprocal of `make acceptance.runtime.carrier.discard`: it rebuilds the
# declared empty infrastructure and then delegates the database creation,
# module install and baseline upgrade to the existing governed provisioning
# script `scripts/test/frontend_acceptance_db_ensure.sh`.
#
# The existing `db.frontend.acceptance.ensure` operation cannot be used from a
# removed carrier because its runtime wrapper requires a passing preflight,
# which in turn requires the carrier and the database to already exist.
#
# This is a P4 environment entry: it must never be invoked from CI.

: "${ROOT_DIR:?ROOT_DIR is required}"
# shellcheck source=./frontend_acceptance_carrier_common.sh
source "$ROOT_DIR/scripts/dev/frontend_acceptance_carrier_common.sh"

readonly CONFIRM_PHRASE="PROVISION_MANAGED_ACCEPTANCE_CARRIER"

carrier_operational() {
  carrier_all_volumes_present || return 1
  carrier_all_containers_present || return 1
  docker exec "${COMPOSE_PROJECT_NAME}-db-1" psql -U "$DB_USER" -d postgres -Atc \
    "SELECT 1 FROM pg_database WHERE datname = '$EXPECTED_DATABASE'" 2>/dev/null | grep -qx 1
}

render_odoo_conf() {
  compose_dev run --rm -T --no-deps --entrypoint /bin/sh odoo -eu -c \
    'python3 /usr/local/bin/render_odoo_conf.py /etc/odoo/odoo.conf.template "${ODOO_CONF_OUT:-/var/lib/odoo/odoo.conf}"'
}

main() {
  carrier_resolve_profile_identity
  carrier_require_exact_identity
  carrier_require_confirmation CONFIRM_ACCEPTANCE_CARRIER_PROVISION "$CONFIRM_PHRASE" || exit 2
  carrier_carriers_stopped
  carrier_source_compose

  if carrier_operational; then
    echo "$CARRIER_LOG_PREFIX provision PASS already_operational=true project=$EXPECTED_PROJECT"
    return 0
  fi

  echo "$CARRIER_LOG_PREFIX provision rebuild declared empty infrastructure project=$EXPECTED_PROJECT db=$EXPECTED_DATABASE"
  compose_dev up -d --wait db redis
  compose_dev create odoo
  render_odoo_conf

  bash "$ROOT_DIR/scripts/test/frontend_acceptance_db_ensure.sh"

  compose_dev up -d --wait odoo

  carrier_all_volumes_present || carrier_fail "declared volume set is incomplete"
  carrier_all_containers_present || carrier_fail "declared container set is incomplete"
  docker exec "${COMPOSE_PROJECT_NAME}-db-1" psql -U "$DB_USER" -d postgres -Atc \
    "SELECT 1 FROM pg_database WHERE datname = '$EXPECTED_DATABASE'" | grep -qx 1 \
    || carrier_fail "managed database is absent"

  echo "$CARRIER_LOG_PREFIX provision PASS project=$EXPECTED_PROJECT database=$EXPECTED_DATABASE source_sha=$(git -C "$ROOT_DIR" rev-parse HEAD)"
  echo "$CARRIER_LOG_PREFIX NEXT seed fixtures with make acceptance.frontend.fixture"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
