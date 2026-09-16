#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="${ROOT_DIR:?ROOT_DIR is required}"
ENV_FILE="${ENV_FILE:?ENV_FILE is required}"
set -a
source "$ENV_FILE"
set +a
[[ "${COMPOSE_PROJECT_NAME:-}" == sc-local-dev && "${DB_NAME:-}" == sc_dev_demo ]] || exit 2
[[ -n "${SC_DEMO_USER_PASSWORD:-}" ]] || exit 2
resolve_scope() {
  bash "$ROOT_DIR/scripts/ops/odoo_shell_exec.sh" < "$ROOT_DIR/scripts/verify/local_dev_form_lowcode_scope.py" |
    sed -n 's/^FORM_LOWCODE_SCOPE=//p' | tail -1
}
before="$(resolve_scope)"
[[ -n "$before" ]] || exit 2
FORM_SCOPE="$before" python3 - "$ROOT_DIR" <<'PY'
import hashlib, json, os, pathlib, sys
scope = json.loads(os.environ["FORM_SCOPE"])
source = pathlib.Path(sys.argv[1]) / "addons/smart_core/core/form_configuration_compiler.py"
if scope["compiler_sha256"] != hashlib.sha256(source.read_bytes()).hexdigest():
    raise SystemExit("runtime compiler differs from current candidate")
PY
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
BEFORE="$before" AFTER="$after" python3 - <<'PY'
import json, os
a, b = [json.loads(os.environ[key]) for key in ("BEFORE", "AFTER")]
if a != b:
    raise SystemExit("form lowcode journey changed runtime identity or material business data")
print("[local.dev.form_lowcode.browser] business fingerprints unchanged")
PY
exit "$status"
