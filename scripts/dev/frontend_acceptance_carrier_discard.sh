#!/usr/bin/env bash
set -euo pipefail

# Governed discard entry for the managed local acceptance carrier
# (project sc-fe-r2-p1-01 / database sc_frontend_acceptance). It removes only
# the three declared volumes and only this project's containers, and only when
# the exact declared identity and an explicit confirmation phrase are present.
# This is a P4 environment entry: it must never be invoked from CI.
# Its reciprocal entry is `make acceptance.runtime.carrier.provision`.

: "${ROOT_DIR:?ROOT_DIR is required}"
# shellcheck source=./frontend_acceptance_carrier_common.sh
source "$ROOT_DIR/scripts/dev/frontend_acceptance_carrier_common.sh"

readonly CONFIRM_PHRASE="DISCARD_MANAGED_ACCEPTANCE_CARRIER"

require_no_foreign_mounter() {
  local volume="$1" consumers cid project service oneoff
  docker volume inspect "$volume" >/dev/null 2>&1 || return 0
  consumers="$(docker ps -aq --filter "volume=$volume")"
  [[ -n "$consumers" ]] || return 0
  while IFS= read -r cid; do
    [[ -n "$cid" ]] || continue
    project="$(docker inspect "$cid" --format '{{index .Config.Labels "com.docker.compose.project"}}')"
    service="$(docker inspect "$cid" --format '{{index .Config.Labels "com.docker.compose.service"}}')"
    oneoff="$(docker inspect "$cid" --format '{{index .Config.Labels "com.docker.compose.oneoff"}}')"
    [[ "$project" == "$EXPECTED_PROJECT" ]] || carrier_deny "volume $volume has foreign mounter project=$project"
    [[ "$service" == "db" || "$service" == "redis" || "$service" == "odoo" ]] || carrier_deny "volume $volume has undeclared service=$service"
    [[ "$oneoff" != "True" && "$oneoff" != "true" ]] || carrier_deny "volume $volume has undeclared one-off mounter service=$service"
  done <<<"$consumers"
  return 0
}

carrier_absent() {
  carrier_all_volumes_present && return 1
  [[ -z "$(docker ps -aq --filter "label=com.docker.compose.project=$EXPECTED_PROJECT")" ]] || return 1
  return 0
}

main() {
  carrier_resolve_profile_identity
  carrier_require_exact_identity
  carrier_require_confirmation CONFIRM_ACCEPTANCE_CARRIER_DISCARD "$CONFIRM_PHRASE" || exit 2
  carrier_carriers_stopped

  if carrier_absent; then
    echo "$CARRIER_LOG_PREFIX discard PASS already_absent=true project=$EXPECTED_PROJECT"
    return 0
  fi

  local volume
  for volume in "$DB_DATA" "$REDIS_DATA" "$ODOO_DATA"; do
    require_no_foreign_mounter "$volume"
  done

  carrier_source_compose
  echo "$CARRIER_LOG_PREFIX discard remove only project=$EXPECTED_PROJECT db=$EXPECTED_DATABASE"
  compose_dev down --remove-orphans

  for volume in "$DB_DATA" "$REDIS_DATA" "$ODOO_DATA"; do
    if docker volume inspect "$volume" >/dev/null 2>&1; then
      docker volume rm "$volume" >/dev/null
    fi
    docker volume inspect "$volume" >/dev/null 2>&1 && carrier_fail "volume remains: $volume"
  done

  local remaining
  remaining="$(docker ps -aq --filter "label=com.docker.compose.project=$EXPECTED_PROJECT")"
  [[ -z "$remaining" ]] || carrier_fail "containers remain for project=$EXPECTED_PROJECT"

  echo "$CARRIER_LOG_PREFIX discard PASS project=$EXPECTED_PROJECT volumes_removed=3"
  echo "$CARRIER_LOG_PREFIX RECREATE via make acceptance.runtime.carrier.provision"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
