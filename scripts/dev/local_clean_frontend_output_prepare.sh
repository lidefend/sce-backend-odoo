#!/usr/bin/env bash
set -euo pipefail
: "${ROOT_DIR:?ROOT_DIR required}"
: "${ENV_FILE:?ENV_FILE required}"
source "$ENV_FILE"
[[ "${COMPOSE_PROJECT_NAME:-}" == sc-local-clean && "${DB_NAME:-}" == sc_clean && "${ODOO_DBFILTER:-}" == '^sc_clean$' ]] || {
  echo '[local.clean.frontend.output] profile identity mismatch' >&2; exit 2;
}
expected="$ROOT_DIR/frontend/apps/web/dist-clean"
case "${FRONTEND_DIST_DIR:-}" in
  ./frontend/apps/web/dist-clean|frontend/apps/web/dist-clean|"$expected") ;;
  *) echo '[local.clean.frontend.output] unexpected output path' >&2; exit 2 ;;
esac
[[ ! -L "$expected" && "$(realpath -m "$expected")" == "$expected" ]] || {
  echo '[local.clean.frontend.output] symlink or noncanonical output path' >&2; exit 2;
}
if [[ -d "$expected" && ! -w "$expected" ]]; then
  # Compose can create a missing bind directory as root before the first build.
  # Repair only this exact generated directory, never recursively or a volume.
  [[ "$(stat -c %u "$expected")" == 0 ]] || { echo 'unexpected output owner' >&2; exit 2; }
  sudo -n chown -- "$(id -u):$(id -g)" "$expected"
fi
mkdir -p "$expected"
[[ -d "$expected" && -w "$expected" ]] || exit 2
echo '[local.clean.frontend.output] PASS exact output is writable'
