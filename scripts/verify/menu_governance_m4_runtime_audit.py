# -*- coding: utf-8 -*-
"""Read-only runtime evidence for the frozen menu-governance M4 scope.

Executed inside ``odoo shell``.  The script never writes business records and
only exports menu metadata and fixture-role visibility facts.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


SCOPE_PATH = Path(
    os.getenv(
        "PRODUCT_MENU_M4_SCOPE_PATH",
        "/mnt/artifacts/menu-governance/menu_m4_governance.json",
    )
)
OUTPUT_PATH = Path(
    os.getenv(
        "PRODUCT_MENU_M4_RUNTIME_PATH",
        "/mnt/artifacts/menu-governance/menu-m4-runtime-resource-probe.json",
    )
)
ROLES = (
    "fixture_role_finance",
    "fixture_role_project_a_member",
    "fixture_role_pm",
    "fixture_role_contract_operator",
    "fixture_role_config_admin",
    "fixture_role_config_admin_peer",
    "fixture_role_owner",
    "fixture_role_executive",
)


def _text(value) -> str:
    return str(value or "").strip()


def _xmlid(record) -> str:
    if not record:
        return ""
    return record.get_external_id().get(record.id, "") or ""


def _path(menu) -> list[str]:
    parts = []
    current = menu
    visited = set()
    while current and int(current.id) not in visited:
        visited.add(int(current.id))
        parts.append(_text(current.name))
        current = current.parent_id
    return list(reversed([part for part in parts if part]))


def _visible_ids(user, company) -> set[int]:
    menu_model = env["ir.ui.menu"].with_user(user).with_company(company)  # noqa: F821
    try:
        return {int(menu_id) for menu_id in menu_model._visible_menu_ids(debug=False)}
    except TypeError:
        return {int(menu_id) for menu_id in menu_model._visible_menu_ids()}


def _action(menu) -> dict[str, object]:
    action = menu.action
    if not action:
        return {"exists": False, "type": "", "xmlid": "", "res_model": ""}
    action = action.sudo().exists()
    return {
        "exists": bool(action),
        "type": _text(getattr(action, "type", action._name if action else "")),
        "xmlid": _xmlid(action),
        "res_model": _text(getattr(action, "res_model", "")),
    }


scope = json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
expected_sha = _text(scope.get("source_commit_sha"))
if len(expected_sha) != 40:
    raise AssertionError("M4 scope does not bind a full source commit SHA")

companies = env["res.company"].sudo().search([], order="id")  # noqa: F821
company_aliases = {int(company.id): f"company_{index + 1}" for index, company in enumerate(companies)}
users = {
    login: env["res.users"].sudo().search([("login", "=", login)], limit=1)  # noqa: F821
    for login in ROLES
}
missing_users = sorted(login for login, user in users.items() if not user)
if missing_users:
    raise AssertionError("missing fixture roles: %s" % ", ".join(missing_users))

rows = []
for decision in scope.get("decisions", []):
    xmlid = _text(decision.get("menu_xmlid"))
    menu = env.ref(xmlid, raise_if_not_found=False)  # noqa: F821
    if not menu or menu._name != "ir.ui.menu":
        rows.append({"menu_xmlid": xmlid, "exists": False, "visibility": []})
        continue
    visibility = []
    for login, user in users.items():
        allowed_companies = user.company_ids & companies
        for company in allowed_companies:
            visibility.append(
                {
                    "role": login,
                    "company": company_aliases[int(company.id)],
                    "visible": int(menu.id) in _visible_ids(user, company),
                }
            )
    rows.append(
        {
            "menu_xmlid": xmlid,
            "exists": True,
            "name": _text(menu.name),
            "path": _path(menu),
            "parent_xmlid": _xmlid(menu.parent_id),
            "sequence": int(menu.sequence or 0),
            "groups": sorted(_xmlid(group) for group in menu.groups_id if _xmlid(group)),
            "action": _action(menu),
            "visibility": visibility,
        }
    )

report = {
    "schema": "sce.menu_governance_m4_runtime_resource_probe.v1",
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "evidence_status": "RESOURCE_PROBE_ONLY_RUNTIME_SHA_UNVERIFIED",
    "database_role": "isolated_acceptance_rehearsal",
    "database": "sc_frontend_acceptance",
    "static_scope_source_sha": expected_sha,
    "served_runtime_source_sha": None,
    "read_only": True,
    "scope_count": len(scope.get("decisions", [])),
    "resolved_count": sum(1 for row in rows if row["exists"]),
    "role_count": len(ROLES),
    "company_count": len(companies),
    "rows": rows,
}
if report["scope_count"] != 22 or report["resolved_count"] != 22:
    raise AssertionError("M4 runtime scope is incomplete: %s" % report)

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: report[key] for key in ("schema", "scope_count", "resolved_count", "role_count", "company_count")}, ensure_ascii=False))
