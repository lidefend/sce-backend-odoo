#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
NAME="${BACKEND_ACCEPTANCE_NAME:-sc-backend-odoo-acceptance}"
PORT="${BACKEND_ACCEPTANCE_PORT:-18082}"
DATABASE="${BACKEND_ACCEPTANCE_DB:-sc_frontend_acceptance}"
if [[ ! "$DATABASE" =~ ^[a-zA-Z0-9_]+$ ]]; then
  echo "[backend.acceptance.up] invalid database identifier" >&2
  exit 2
fi
PRODUCT_VERSION="$(tr -d '[:space:]' < "$ROOT_DIR/VERSION")"
SOURCE_REVISION="${SC_ACCEPTANCE_SOURCE_SHA:-$(git -C "$ROOT_DIR" rev-parse HEAD)}"
[[ "$SOURCE_REVISION" =~ ^[0-9a-f]{40}$ ]] || { echo "DENY exact source SHA required" >&2; exit 2; }
SOURCE_FINGERPRINT="$(printf '%s\n' "$SOURCE_REVISION" | sha256sum | cut -d' ' -f1)"
# Local acceptance consumes a sealed source artifact. CI keeps its isolated
# checkout lifecycle; daily/product Compose entrypoints are unaffected.
compose_args=()
if [[ "${GITHUB_ACTIONS:-}" != true ]]; then
  artifact_override="$(python3 "$ROOT_DIR/scripts/dev/acceptance_artifact.py" compose --source-sha "$SOURCE_REVISION")"
  git -C "$ROOT_DIR" diff --quiet "$SOURCE_REVISION" -- addons demo_addons addons_external VERSION config/odoo.conf.template scripts/odoo-entrypoint.sh scripts/render_odoo_conf.py
  [[ -z "$(git -C "$ROOT_DIR" ls-files --others --exclude-standard -- addons demo_addons addons_external)" ]] || { echo "DENY untracked runtime source" >&2; exit 2; }
  [[ -z "${SC_CUSTOMER_ADDONS_ROOT:-}" ]] || { echo "DENY customer payload not declared for local acceptance" >&2; exit 2; }
  compose_args=(-f "$ROOT_DIR/docker-compose.yml" -f "$artifact_override")
fi
# Serialize service replacement with probes on both registered preview URLs.
# Locks use the same target-key function as frontend_acceptance_lease.mjs.
lock_root="${XDG_RUNTIME_DIR:-${TMPDIR:-/tmp}}/sce-frontend-acceptance/leases"
mkdir -p "$lock_root"
for frontend_port in "${FRONTEND_ACCEPTANCE_PORT:-5175}" "${SC_ACCEPTANCE_STANDARD_PREVIEW_PORT:-5180}"; do
  key="$(printf '%s' "http://127.0.0.1:$frontend_port|http://127.0.0.1:$PORT|$DATABASE" | sha256sum | cut -d' ' -f1)"
  exec {lease_fd}>"$lock_root/$key.lock"
  flock -n -x "$lease_fd" || { echo "DENY active acceptance lease" >&2; exit 2; }
done
backup=""
was_running=false
installed=false
rollback() {
  status=$?
  if [[ "$installed" != true && -n "$backup" ]]; then
    docker rm -f "$NAME" >/dev/null 2>&1 || true
    docker rename "$backup" "$NAME" || { echo "DENY rollback rename failed" >&2; exit 1; }
    if [[ "$was_running" == true ]]; then docker start "$NAME" >/dev/null || exit 1; fi
    echo "[backend.acceptance.up] restored prior carrier" >&2
  fi
  exit "$status"
}
trap rollback EXIT
if docker inspect "$NAME" >/dev/null 2>&1; then
  previous_id="$(docker inspect "$NAME" --format '{{.Id}}')"
  [[ "$previous_id" =~ ^[0-9a-f]{64}$ ]] || { echo "DENY invalid previous carrier identity" >&2; exit 2; }
  backup="$NAME-rollback-${previous_id:0:12}"
  if docker inspect "$backup" >/dev/null 2>&1; then backup=""; echo "DENY unresolved rollback carrier" >&2; exit 2; fi
  was_running="$(docker inspect "$NAME" --format '{{.State.Running}}')"
  if [[ "$was_running" == true ]]; then docker stop "$NAME" >/dev/null; fi
  # Set recovery authority only after the old carrier has actually moved.
  pending_backup="$backup"; backup=""
  docker rename "$NAME" "$pending_backup"
  backup="$pending_backup"
fi
docker compose "${compose_args[@]}" run -d --no-deps --name "$NAME" -p "127.0.0.1:${PORT}:8069" \
  -e ODOO_DB="$DATABASE" \
  -e DB_NAME="$DATABASE" \
  -e ODOO_DBFILTER="^${DATABASE}$" \
  -e LIST_DB=false \
  -e SC_PRODUCT_VERSION="$PRODUCT_VERSION" \
  -e SC_SOURCE_REVISION="$SOURCE_REVISION" \
  -e SC_SOURCE_FINGERPRINT="$SOURCE_FINGERPRINT" \
  odoo >/dev/null
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:${PORT}/web/login" >/dev/null 2>&1; then
    if [[ "${GITHUB_ACTIONS:-}" != true ]]; then
      writable="$(docker inspect "$NAME" --format '{{range .Mounts}}{{if or (eq .Destination "/mnt/source-addons") (eq .Destination "/mnt/demo-addons") (eq .Destination "/mnt/addons_external")}}{{println .RW}}{{end}}{{end}}')"
      [[ "$writable" == $'false\nfalse\nfalse' ]] || { echo "DENY artifact mount readback is not read-only" >&2; exit 2; }
    fi
    installed=true; echo "[backend.acceptance.up] PASS db=${DATABASE} port=${PORT} rollback=${backup:-none}"; exit 0; fi
  sleep 2
done
docker logs --tail 100 "$NAME" >&2
exit 1
