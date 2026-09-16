#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="${ROOT_DIR:?ROOT_DIR is required}"
ENV_FILE="${ENV_FILE:?ENV_FILE is required}"
set -a
source "$ENV_FILE"
set +a
[[ "${COMPOSE_PROJECT_NAME:-}" == sc-local-dev && "${DB_NAME:-}" == sc_dev_demo ]] || exit 2
[[ -n "${SC_DEMO_USER_PASSWORD:-}" ]] || exit 2
if [[ "${FORM_LOWCODE_CONFIG_INVENTORY:-0}" == 1 && "${FORM_LOWCODE_SCOPE_ONLY:-0}" != 1 ]]; then
  echo "configuration inventory requires read-only scope mode" >&2
  exit 2
fi
resolve_scope() {
  LOWCODE_CONFIG_BATCH="${FORM_LOWCODE_CONFIG_BATCH:-0}" LOWCODE_CONFIG_INVENTORY="${FORM_LOWCODE_CONFIG_INVENTORY:-0}" LOWCODE_CONFIG_ENTRY="${FORM_LOWCODE_CONFIG_ENTRY:-0}" LOWCODE_FORM_TOPIC="${FORM_LOWCODE_TOPIC:-material}" bash "$ROOT_DIR/scripts/ops/odoo_shell_exec.sh" < "$ROOT_DIR/scripts/verify/local_dev_form_lowcode_scope.py" |
    sed -n 's/^FORM_LOWCODE_SCOPE=//p' | tail -1
}
before="$(resolve_scope)"
[[ -n "$before" ]] || exit 2
python3 -c '
import hashlib, json, pathlib, sys
scope = json.load(sys.stdin)
source = pathlib.Path(sys.argv[1]) / "addons/smart_core/core/form_configuration_compiler.py"
if scope["compiler_sha256"] != hashlib.sha256(source.read_bytes()).hexdigest():
    raise SystemExit("runtime compiler differs from current candidate")
' "$ROOT_DIR" <<<"$before"
if [[ "${FORM_LOWCODE_SCOPE_ONLY:-0}" == 1 ]]; then
  printf '%s\n' "$before"
  exit 0
fi
set +e
(
  cd "$ROOT_DIR/frontend/apps/web"
  FORM_LOWCODE_SCOPE="$before" CHANGE_SET_FORM_LOOP=1 BASE_URL=http://127.0.0.1:5174 \
    E2E_LOGIN=sc_test_admin E2E_PASSWORD="$SC_DEMO_USER_PASSWORD" DB_NAME=sc_dev_demo \
    CANDIDATE_GIT_HEAD="$(git -C "$ROOT_DIR" rev-parse HEAD)" \
    node scripts/low_code_change_set_acceptance.mjs
)
status=$?
set -e
after="$(resolve_scope)"
CONFIG_BATCH="${FORM_LOWCODE_CONFIG_BATCH:-0}" BEFORE="$before" AFTER="$after" python3 - <<'PY'
import json, os
a, b = [json.loads(os.environ[key]) for key in ("BEFORE", "AFTER")]
if os.environ.get("CONFIG_BATCH") == "1":
    old = a["configuration_entry"].pop("owner_change_sets")
    new = b["configuration_entry"].pop("owner_change_sets")
    by_id = {row["id"]: row for row in new}
    if any(by_id.get(row["id"]) != row for row in old):
        raise SystemExit("pre-existing designer draft was changed")
    ids = {row["id"] for row in old}
    added = [row for row in new if row["id"] not in ids]
    managed_ids = {row["id"] for row in added if row["name"] == "受管配置中心闭环" and row["state"] in {"discarded", "superseded"}}
    for row in added:
        if row["id"] in managed_ids:
            continue
        if row["name"] == "回滚：受管配置中心闭环" and row["state"] == "published" and row["rollback_of"] in managed_ids and row["rollback_verified"]:
            continue
        raise SystemExit("unexpected or unrestored configuration draft")
if a != b:
    raise SystemExit("form lowcode journey changed runtime identity or scoped business data")
print("[local.dev.form_lowcode.browser] business fingerprints unchanged")
PY
exit "$status"
