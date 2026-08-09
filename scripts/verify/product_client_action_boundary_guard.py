#!/usr/bin/env python3
"""Keep Odoo client actions outside the contract-driven product runtime."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
def main() -> int:
    violations: list[str] = []

    menu_service = (ROOT / "addons/smart_core/delivery/menu_service.py").read_text(encoding="utf-8")
    if 'if action_model == "ir.actions.client":\n            return False' not in menu_service:
        violations.append("menu_service.py: product route authority no longer explicitly rejects ir.actions.client")

    norm_views = (ROOT / "addons/sc_norm_engine/views/norm_views.xml").read_text(encoding="utf-8")
    if 'id="action_sc_norm_catalog_workbench" model="ir.actions.act_window"' not in norm_views:
        violations.append("sc_norm_engine: contract-driven workbench is not a model-backed act_window")
    if 'id="action_sc_norm_catalog_workbench" model="ir.actions.client"' in norm_views:
        violations.append("sc_norm_engine: product workbench regressed to ir.actions.client")

    preflight = (ROOT / "frontend/apps/web/src/app/action_runtime/useActionViewLoadPreflightRuntime.ts").read_text(encoding="utf-8")
    for forbidden in ("clientPresentation", "kind: 'client'", 'presentation === \'hierarchy_browser\''):
        if forbidden in preflight:
            violations.append(f"frontend action preflight promotes client action through {forbidden!r}")

    spec = (ROOT / "docs/architecture/native_view_reuse_frontend_spec_v1.md").read_text(encoding="utf-8")
    if "## 15. 客户端动作边界（强制）" not in spec:
        violations.append("native view frontend spec is missing the mandatory client-action boundary")

    if violations:
        for row in violations:
            print(f"[product-client-action-boundary] FAIL {row}", file=sys.stderr)
        return 1
    print("[product-client-action-boundary] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
