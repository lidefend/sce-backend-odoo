#!/usr/bin/env bash
set -euo pipefail

outdir=""
case_name=""
args=("$@")
for ((i=0; i<${#args[@]}; i++)); do
  if [ "${args[$i]}" = "--outdir" ]; then
    outdir="${args[$((i+1))]}"
  fi
  if [ "${args[$i]}" = "--case" ]; then
    case_name="${args[$((i+1))]}"
  fi
done

stable_args=()
if [ "${SC_CONTRACT_STABLE:-}" = "1" ]; then
  stable_args+=(--stable)
fi

if [ "${SC_FORCE_DOCKER:-}" != "1" ] && python3 - <<'PY' >/dev/null 2>&1
import odoo  # noqa: F401
PY
then
  exec python3 scripts/contract/snapshot_export.py "${stable_args[@]}" "$@"
fi

if [ -z "$outdir" ]; then
  outdir="docs/contract/snapshots"
fi
if [ -z "$case_name" ]; then
  echo "missing --case" >&2
  exit 2
fi
mkdir -p "$outdir"

publish_docker_snapshot() {
  local compose_command="$1"
  shift
  local target="${outdir}/${case_name}.json"
  local temporary
  temporary="$(mktemp "${outdir}/.${case_name}.json.tmp.XXXXXX")"
  trap 'rm -f "$temporary"' RETURN

  if [ "$compose_command" = "docker compose" ]; then
    if ! docker compose exec -T odoo python3 - --stdout "${stable_args[@]}" "$@" < scripts/contract/snapshot_export.py > "$temporary"; then
      echo "snapshot export failed; preserved existing target: ${target}" >&2
      return 1
    fi
  else
    if ! docker-compose exec -T odoo python3 - --stdout "${stable_args[@]}" "$@" < scripts/contract/snapshot_export.py > "$temporary"; then
      echo "snapshot export failed; preserved existing target: ${target}" >&2
      return 1
    fi
  fi

  if [ ! -s "$temporary" ]; then
    echo "snapshot export produced empty output; preserved existing target: ${target}" >&2
    return 1
  fi
  if ! python3 - "$temporary" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    payload = json.load(handle)
if not isinstance(payload, dict):
    raise SystemExit("snapshot root must be a JSON object")
PY
  then
    echo "snapshot export produced invalid JSON; preserved existing target: ${target}" >&2
    return 1
  fi

  mv "$temporary" "$target"
  trap - RETURN
  echo "$target"
}

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  publish_docker_snapshot "docker compose" "$@"
  exit $?
fi

if command -v docker-compose >/dev/null 2>&1 && docker-compose version >/dev/null 2>&1; then
  publish_docker_snapshot "docker-compose" "$@"
  exit $?
fi

echo "No local odoo module and no docker compose available" >&2
exit 2
