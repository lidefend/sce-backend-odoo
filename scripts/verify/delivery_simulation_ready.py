#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from python_http_smoke_utils import env_value, get_base_url, http_post_json, obtain_runtime_probe_token


ROOT = Path(__file__).resolve().parents[2]
PLAYBOOK = ROOT / "docs" / "product" / "delivery_playbook_v1.md"
REPORT_MD = ROOT / "docs" / "ops" / "audit" / "delivery_simulation_report.md"
REPORT_JSON = ROOT / "artifacts" / "backend" / "delivery_simulation_report.json"


def _intent(intent_url: str, token: str, intent: str, params: dict, context: dict | None = None) -> tuple[int, dict]:
    payload = {"intent": intent, "params": params}
    if isinstance(context, dict):
        payload["context"] = context
    return http_post_json(intent_url, payload, headers={"Authorization": f"Bearer {token}"})


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    if not PLAYBOOK.is_file():
        errors.append("missing docs/product/delivery_playbook_v1.md")

    base_url = get_base_url()
    intent_url = f"{base_url}/api/v1/intent"
    db_name = env_value("DB_NAME") or env_value("ODOO_DB") or "sc_dev"

    timeline: list[dict] = []
    auth_ok, token, auth_source = obtain_runtime_probe_token(intent_url, db_name)
    timeline.append({"step": "authenticate", "source": auth_source, "ok": auth_ok})
    if not auth_ok:
        errors.append("runtime probe authentication failed")

    if token:
        for step, intent, params, context in [
            ("system.init", "system.init", {"contract_mode": "user"}, {"sc.bundle": "construction"}),
            ("ui.contract", "ui.contract", {"op": "model", "model": "project.project", "view_type": "form"}, None),
            (
                "execute_button",
                "execute_button",
                {"model": "project.project", "button": {"name": "action_view_tasks", "type": "object"}, "res_id": 1, "dry_run": True},
                None,
            ),
            ("payment.submit", "payment.request.submit", {"request_id": "R8-SIM-001"}, None),
        ]:
            status, payload = _intent(intent_url, token, intent, params, context=context)
            ok = status < 500 and isinstance(payload, dict)
            timeline.append({"step": step, "intent": intent, "status": status, "ok": bool(ok)})
            if status >= 500:
                errors.append(f"{step} returned 5xx")
            elif status >= 400:
                warnings.append(f"{step} returned {status}")

    payload = {
        "ok": len(errors) == 0,
        "summary": {
            "steps": len(timeline),
            "error_count": len(errors),
            "warning_count": len(warnings),
        },
        "timeline": timeline,
        "errors": errors,
        "warnings": warnings,
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Delivery Simulation Report",
        "",
        f"- steps: {len(timeline)}",
        f"- error_count: {len(errors)}",
        f"- warning_count: {len(warnings)}",
        "",
        "## Timeline",
        "",
    ]
    for row in timeline:
        lines.append(f"- {row.get('step')}: status={row.get('status')} ok={row.get('ok')}")
    lines.extend(["", "## Errors", ""])
    if errors:
        for item in errors:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.extend(["", "## Warnings", ""])
    if warnings:
        for item in warnings:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(str(REPORT_MD))
    print(str(REPORT_JSON))
    if errors:
        print("[delivery_simulation_ready] FAIL")
        return 2
    print("[delivery_simulation_ready] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
