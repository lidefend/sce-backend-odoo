#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from python_http_smoke_utils import env_value, get_base_url, http_post_json, obtain_runtime_probe_token


ROOT = Path(__file__).resolve().parents[2]
UI_GUIDE = ROOT / "docs" / "product" / "ui_guideline_v1.md"
REPORT_MD = ROOT / "docs" / "ops" / "audit" / "ui_surface_stability_report.md"
REPORT_JSON = ROOT / "artifacts" / "backend" / "ui_surface_stability_report.json"


def _intent(
    intent_url: str,
    token: str,
    intent: str,
    params: dict,
    context: dict | None = None,
    db_name: str = "",
) -> tuple[int, dict]:
    payload = {"intent": intent, "params": params}
    if isinstance(context, dict):
        payload["context"] = context
    headers = {"Authorization": f"Bearer {token}"}
    if db_name:
        headers["X-Odoo-DB"] = db_name
    return http_post_json(payload=payload, url=intent_url, headers=headers)


def _shape(data: dict) -> list[str]:
    if isinstance(data.get("data"), dict):
        data = data.get("data")
    if not isinstance(data, dict):
        return []
    return sorted(data.keys())


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    if not UI_GUIDE.is_file():
        errors.append("missing docs/product/ui_guideline_v1.md")

    base_url = get_base_url()
    intent_url = f"{base_url}/api/v1/intent"
    db_name = env_value("DB_NAME") or env_value("ODOO_DB") or "sc_dev"
    ok, token, _auth_source = obtain_runtime_probe_token(intent_url, db_name)
    if not ok:
        errors.append("runtime probe authentication failed for ui surface stability")
        token = ""

    required = [
        "user",
        "navigation",
        "intents",
        "default_route",
        "role_surface",
        "scene_ready_contract",
        "page_contracts",
    ]
    modes = {
        "default": {},
        "bundle_construction": {"sc.bundle": "construction"},
        "bundle_owner": {"sc.bundle": "owner", "sc.industry": "owner"},
    }
    shapes = {}

    if token:
        for mode, context in modes.items():
            status, payload = _intent(
                intent_url,
                token,
                "system.init",
                {"contract_mode": "user"},
                context=context,
                db_name=db_name,
            )
            if status >= 400 or not isinstance(payload, dict) or payload.get("ok") is not True:
                errors.append(f"system.init failed in mode={mode}")
                continue
            data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
            keys = _shape(data)
            shapes[mode] = keys
            for k in required:
                if k not in keys:
                    errors.append(f"mode={mode} missing required surface key: {k}")

    if shapes.get("default") and shapes.get("bundle_owner"):
        if shapes["default"] != shapes["bundle_owner"]:
            warnings.append("bundle_owner differs from default shape (allowed if additive)")

    payload = {
        "ok": len(errors) == 0,
        "summary": {
            "mode_count": len(shapes),
            "error_count": len(errors),
            "warning_count": len(warnings),
        },
        "shapes": shapes,
        "errors": errors,
        "warnings": warnings,
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# UI Surface Stability Report",
        "",
        f"- mode_count: {len(shapes)}",
        f"- error_count: {len(errors)}",
        f"- warning_count: {len(warnings)}",
        "",
        "## Errors",
        "",
    ]
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
        print("[ui_surface_stability_ready] FAIL")
        return 2
    print("[ui_surface_stability_ready] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
