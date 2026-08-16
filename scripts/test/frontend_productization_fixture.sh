#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
export ROOT_DIR

if [[ -z "${SC_ACCEPTANCE_FIXTURE_PASSWORD:-}" ]]; then
  echo "[DENY] frontend acceptance fixture requires SC_ACCEPTANCE_FIXTURE_PASSWORD" >&2
  exit 24
fi

source "$ROOT_DIR/scripts/common/frontend_acceptance_guard.sh"
guard_frontend_acceptance_scope
acquire_frontend_acceptance_lock lifecycle

source "$ROOT_DIR/scripts/common/env.sh"
source "$ROOT_DIR/scripts/common/guard_prod.sh"
guard_prod_forbid

export DB_NAME SC_ENVIRONMENT SC_ALLOW_DEMO_DATA SC_ACCEPTANCE_FIXTURE_PASSWORD SC_ACCEPTANCE_COMPONENT_DRIVER_PROBE_MODE

DB_NAME="$DB_NAME" bash scripts/ops/odoo_shell_exec.sh <<'PY'
import json
import os
from odoo.addons.smart_construction_acceptance_fixture.tools.component_driver_probe import apply_component_driver_probe
from odoo.addons.smart_construction_acceptance_fixture.tools.frontend_productization_fixture import ensure_fixture

summary = ensure_fixture(env)
probe_mode = str(os.environ.get("SC_ACCEPTANCE_COMPONENT_DRIVER_PROBE_MODE") or "").strip()
if probe_mode:
    probe_target = apply_component_driver_probe(env, probe_mode)
    if probe_target:
        print("SCENE_COMPONENT_DRIVER_TARGETS_JSON=" + json.dumps(probe_target, ensure_ascii=True, separators=(",", ":")))
env.cr.commit()
finance = env.ref("smart_construction_acceptance_fixture.fe_user_finance")
authenticated_uid = env["res.users"].sudo().authenticate(
    env.cr.dbname,
    finance.login,
    os.environ["SC_ACCEPTANCE_FIXTURE_PASSWORD"],
    {"interactive": True},
)
if int(authenticated_uid or 0) != finance.id:
    raise RuntimeError("frontend acceptance fixture credential verification failed")
print("[acceptance.frontend.fixture] PASS")
print("[acceptance.frontend.fixture.auth] PASS login=fixture_role_finance")
print(json.dumps(summary, ensure_ascii=False, indent=2))
PY
