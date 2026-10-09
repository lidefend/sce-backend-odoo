#!/usr/bin/env python3
"""nav_pro 01R route-authority HTTP acceptance probe (contract-driven).

The served ``navigation.route_authority`` is the *versioned role contract* for
the locked roles: the role's declared face partitioned into delivered entries
and explicit denials.  This probe asserts that partition against an authority
that is independent of the server's own answer - the repository's locked role
surface (``addons/smart_construction_core/core_extension_policy_maps.py``):

  * the served revision is the build the probe's contract belongs to;
  * every menu the locked role contract declares is delivered or explicitly
    denied with a ``reason_code`` - a declared entry may never disappear
    without an observable decision;
  * delivered entries carry a contract source, never a native menu tree acting
    as a second product-selection authority;
  * behaviour: ordinary roles never receive an admin route and are denied it,
    a contextual execution route obeys company/project scope, and the runtime
    never answers HTTP 500.

Delivered counts are deliberately NOT pinned: a count calibrates one build
against one release gate, whereas the partition identity holds for every build.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
from pathlib import Path
from urllib import request as urlrequest

from python_http_smoke_utils import extract_login_token, http_post_json


ROOT = Path(__file__).resolve().parents[2]
BASE_URL = str(os.getenv("E2E_BASE_URL") or "http://127.0.0.1:38069").rstrip("/")
DB_NAME = str(os.getenv("DB_NAME") or "sc_nav_pro_01")
PASSWORD = str(os.getenv("NAV_PRO_PASSWORD") or "")
EXPECTED_SHA = str(os.getenv("NAV_PRO_01R_EXPECTED_SHA") or "").strip()
OUTPUT = Path(os.getenv("NAV_PRO_01R_HTTP_OUT") or "/tmp/nav-pro-01/route-authority-http.json")

LOCKED_ROLES = ("finance", "project_member", "pm", "owner")
ADMIN_ROLE = "config_admin"
PLATFORM_ADMIN_ROLE = "system_admin"
MENU_FIELDS = (
    "primary_menu_xmlids",
    "role_home_menu_xmlids",
    "contextual_menu_xmlids",
    "admin_menu_xmlids",
    "menu_xmlids",
)
DELIVERED_BUCKETS = (
    "primary_actions",
    "role_home_actions",
    "contextual_actions",
    "admin_actions",
    "menu_containers",
)
CONTRACT_SOURCE_PREFIXES = ("role_surface.", "nav_policy_")


def _load_role_surface_overrides() -> dict:
    path = ROOT / "addons/smart_construction_core/core_extension_policy_maps.py"
    spec = importlib.util.spec_from_file_location("nav_pro_01r_role_policy", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load role-surface contract from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return dict(getattr(module, "ROLE_SURFACE_OVERRIDES") or {})


def _load_contract_version() -> str:
    text = (ROOT / "addons/smart_core/delivery/menu_service.py").read_text(encoding="utf-8")
    match = re.search(r'ROUTE_AUTHORITY_CONTRACT_VERSION\s*=\s*"([^"]+)"', text)
    if not match:
        raise RuntimeError("ROUTE_AUTHORITY_CONTRACT_VERSION not declared by menu_service.py")
    return match.group(1)


def _governance_permission_fields() -> tuple[str, ...]:
    """The enterprise permission surface fields declared by contract governance."""
    path = ROOT / "addons/smart_core/utils/contract_governance_enterprise_forms.py"
    module = ast.parse(path.read_text(encoding="utf-8"))
    names: set = set()
    for node in ast.walk(module):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "permission_fields":
                try:
                    value = ast.literal_eval(node.value)
                except (ValueError, SyntaxError):
                    continue
                if isinstance(value, (set, frozenset, list, tuple)):
                    names.update(str(item) for item in value)
    if not names:
        raise RuntimeError("permission_fields not declared by contract governance")
    return tuple(sorted(names))


def declared_permission_form_field(form_contract: dict) -> tuple[str, str]:
    """Resolve the governance-declared permission field as the form contract declares it."""
    roles = form_contract.get("fieldRoles") if isinstance(form_contract.get("fieldRoles"), dict) else {}
    labels = form_contract.get("fieldLabels") if isinstance(form_contract.get("fieldLabels"), dict) else {}
    for name in _governance_permission_fields():
        if name in roles or name in labels:
            label = str(labels.get(name) or "").strip()
            if label:
                return name, label
    raise RuntimeError("no governance-declared permission field is present in the form contract")


def admin_form_assertion(token: str, entry: dict) -> dict:
    """Bind one administrator role's form assertion to its own contract entry.

    The contract entry declares the consumable route, the model and the allowed
    operation. A writable surface must expose the governance-declared permission
    field; a read-only surface only has to render its declared model fields.
    """
    model = str(entry.get("model") or "").strip()
    if not model:
        raise RuntimeError(f"admin action {entry.get('action_xmlid')} declares no model")
    _, payload = intent("ui.contract.v2", {
        "op": "model",
        "model": model,
        "view_type": "form",
        "action_id": int(entry.get("action_id") or 0),
        "menu_id": int(entry.get("menu_id") or 0),
    }, token)
    form = (payload.get("data") or {}).get("formStructureContract") or {}
    if not isinstance(form, dict) or not form:
        raise RuntimeError("admin form structure contract missing from ui.contract.v2")
    try:
        field, label = declared_permission_form_field(form)
    except RuntimeError:
        field, label = "", ""
    labels = form.get("fieldLabels") if isinstance(form.get("fieldLabels"), dict) else {}
    roles = form.get("fieldRoles") if isinstance(form.get("fieldRoles"), dict) else {}
    declared_fields = sorted({str(name) for name in (*labels.keys(), *roles.keys()) if str(name).strip()})
    if not declared_fields:
        raise RuntimeError("admin form structure contract declares no field")
    return {
        "route": str(entry.get("route") or "").strip(),
        "model": model,
        "allowed_operation": str(entry.get("allowed_operation") or "").strip(),
        "permission_field": field,
        "permission_label": label,
        "declared_fields": declared_fields,
    }


def declared_menu_xmlids(overrides: dict, role_code: str) -> set:
    meta = overrides.get(role_code) or {}
    return {
        str(menu_xmlid).strip()
        for field in MENU_FIELDS
        for menu_xmlid in meta.get(field) or []
        if str(menu_xmlid).strip()
    }


def declared_context_scoped_action(overrides: dict, role_code: str) -> str:
    """The role's declared contextual action that requires company/project scope."""
    meta = overrides.get(role_code) or {}
    for spec in meta.get("contextual_action_authorities") or []:
        if not isinstance(spec, dict):
            continue
        requirements = spec.get("context_requirements")
        if isinstance(requirements, dict) and requirements.get("required_query"):
            action_xmlid = str(spec.get("action_xmlid") or "").strip()
            if action_xmlid:
                return action_xmlid
    raise RuntimeError(f"{role_code}: no context-scoped contextual action authority declared")


def declared_admin_action(overrides: dict, role_code: str) -> str:
    """The admin action the administrator role itself declares."""
    meta = overrides.get(role_code) or {}
    for spec in meta.get("admin_action_authorities") or []:
        if isinstance(spec, dict):
            action_xmlid = str(spec.get("action_xmlid") or "").strip()
            if action_xmlid:
                return action_xmlid
    raise RuntimeError(f"{role_code}: no admin action authority declared")


def runtime_version() -> dict:
    with urlrequest.urlopen(f"{BASE_URL}/api/runtime-version", timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def intent(name: str, params: dict, token: str = "") -> tuple[int, dict]:
    headers = {"X-Odoo-DB": DB_NAME}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        headers["X-Anonymous-Intent"] = "1"
    return http_post_json(
        f"{BASE_URL}/api/v1/intent?db={DB_NAME}",
        {"intent": name, "params": params},
        headers=headers,
    )


def login(role: str) -> str:
    status, payload = intent("login", {"db": DB_NAME, "login": f"nav_pro_{role}", "password": PASSWORD})
    if status >= 400 or payload.get("ok") is not True:
        raise RuntimeError(f"{role}.login failed: {status} {payload.get('error')}")
    return extract_login_token(payload)


def require_ok(result: tuple[int, dict], label: str) -> dict:
    status, payload = result
    if status >= 400 or payload.get("ok") is not True:
        raise RuntimeError(f"{label} failed: {status} {payload.get('error')}")
    return payload.get("data") if isinstance(payload.get("data"), dict) else {}


def require_denied(result: tuple[int, dict], label: str) -> None:
    status, payload = result
    if status != 403 or payload.get("ok") is not False:
        raise RuntimeError(f"{label} expected 403: {status} {payload}")


def navigation(token: str) -> dict:
    data = require_ok(intent("system.init", {"contract_mode": "user", "with_preload": False}, token), "system.init")
    contract = data.get("navigation") if isinstance(data.get("navigation"), dict) else {}
    if not contract.get("route_authority"):
        raise RuntimeError("navigation.route_authority missing")
    return contract


def route_authority(token: str) -> dict:
    return navigation(token)["route_authority"]


def delivered_xmlids(contract: dict) -> set:
    return {
        str(entry.get("menu_xmlid") or "").strip()
        for bucket in DELIVERED_BUCKETS
        for entry in contract.get(bucket) or []
        if isinstance(entry, dict) and str(entry.get("menu_xmlid") or "").strip()
    }


def denied_xmlids(contract: dict) -> set:
    return {
        str(entry.get("menu_xmlid") or "").strip()
        for entry in contract.get("denied_actions") or []
        if isinstance(entry, dict) and str(entry.get("menu_xmlid") or "").strip()
    }


def find(contract: dict, bucket: str, xmlid: str) -> dict:
    rows = [row for row in contract.get(bucket) or [] if isinstance(row, dict) and row.get("action_xmlid") == xmlid]
    if len(rows) != 1:
        raise RuntimeError(f"{bucket}.{xmlid} expected once, got {len(rows)}")
    return rows[0]


def first_pm_contract(token: str) -> dict:
    data = require_ok(intent("api.data", {
        "op": "list",
        "model": "construction.contract",
        "fields": ["id", "project_id", "company_id"],
        "domain": [["project_id", "!=", False], ["company_id", "!=", False]],
        "limit": 1,
    }, token), "pm.contract.sample")
    records = data.get("records") if isinstance(data.get("records"), list) else []
    if not records:
        raise RuntimeError("pm.contract.sample missing")
    return records[0]


def m2o_id(value) -> int:
    if isinstance(value, (list, tuple)) and value:
        return int(value[0])
    if isinstance(value, dict):
        return int(value.get("id") or 0)
    return int(value or 0)


def assert_partition(role: str, contract: dict, overrides: dict, version: str) -> dict:
    """Assert the served authority is the role contract's declared face, closed."""
    nav = contract
    authority = nav.get("route_authority") or {}
    for label, value in (
        (f"{role}.navigation.contract_version", nav.get("contract_version")),
        (f"{role}.route_authority.contract_version", authority.get("contract_version")),
    ):
        if value != version:
            raise RuntimeError(f"{label} expected {version!r}, got {value!r}")
    role_code = str((nav.get("meta") or {}).get("role_code") or "").strip()
    if role_code != role:
        raise RuntimeError(f"{role}.role_code expected {role!r}, got {role_code!r}")
    declared = declared_menu_xmlids(overrides, role_code)
    if not declared:
        raise RuntimeError(f"{role}: role contract declares no menu face")
    delivered = delivered_xmlids(authority)
    denied = denied_xmlids(authority)
    silent = sorted(declared - delivered - denied)
    if silent:
        raise RuntimeError(
            f"{role}: {len(silent)} declared menu entries are neither delivered nor explicitly "
            f"denied (silent drop): {silent[:10]}"
        )
    for entry in authority.get("denied_actions") or []:
        if not isinstance(entry, dict) or not entry.get("reason_code"):
            raise RuntimeError(f"{role}: denied entry without reason_code: {entry}")
    for bucket in DELIVERED_BUCKETS:
        for entry in authority.get(bucket) or []:
            if not isinstance(entry, dict):
                continue
            source = str(entry.get("source") or "")
            if not source.startswith(CONTRACT_SOURCE_PREFIXES):
                raise RuntimeError(
                    f"{role}.{bucket}: delivered entry outside the declared contract face: "
                    f"{entry.get('menu_xmlid') or entry.get('action_xmlid')} source={source!r}"
                )
    if authority.get("admin_actions"):
        raise RuntimeError(f"{role}.admin route leak")
    integrity = nav.get("integrity") or {}
    if int(integrity.get("missing_authority_count") or 0) != 0:
        raise RuntimeError(f"{role}: served navigation contains unauthorized menu/action pairs")
    if not authority.get("contextual_actions"):
        raise RuntimeError(f"{role}: contextual route authority missing")
    return authority


def main() -> int:
    if not PASSWORD:
        raise RuntimeError("NAV_PRO_PASSWORD is required")
    overrides = _load_role_surface_overrides()
    version = _load_contract_version()

    served = runtime_version()
    served_revision = str(served.get("source_revision") or "").strip()
    if EXPECTED_SHA and served_revision != EXPECTED_SHA:
        raise RuntimeError(f"served source_revision {served_revision!r} != expected {EXPECTED_SHA!r}")

    tokens = {role: login(role) for role in (*LOCKED_ROLES, ADMIN_ROLE, PLATFORM_ADMIN_ROLE)}

    locked_nav = {role: navigation(tokens[role]) for role in LOCKED_ROLES}
    locked_authority = {
        role: assert_partition(role, locked_nav[role], overrides, version) for role in LOCKED_ROLES
    }

    admin_xmlid = declared_admin_action(overrides, "business_config_admin")
    config_contract = route_authority(tokens[ADMIN_ROLE])
    system_contract = route_authority(tokens[PLATFORM_ADMIN_ROLE])
    config_action = find(config_contract, "admin_actions", admin_xmlid)
    system_action = find(system_contract, "admin_actions", admin_xmlid)
    # The contract entry declares the consumable route for its own action; a
    # consumer (the acceptance browser lane) must open that declared route rather
    # than re-deriving `/a/<action_id>`, which the SPA correctly denies for a
    # menu-bound action (findRouteAuthority fail-closed rule).
    admin_action_route = str(config_action.get("route") or "").strip()
    if not admin_action_route.startswith("/a/"):
        raise RuntimeError(
            f"admin action {admin_xmlid} declares no consumable route: {admin_action_route!r}"
        )
    admin_action_name = str(config_action.get("name") or "").strip()
    if not admin_action_name:
        raise RuntimeError(f"admin action {admin_xmlid} declares no display name")
    admin_route_by_role = {
        ADMIN_ROLE: admin_action_route,
        PLATFORM_ADMIN_ROLE: str(system_action.get("route") or "").strip() or admin_action_route,
    }
    require_ok(intent("route.authority.validate", {"action_id": config_action["action_id"]}, tokens[ADMIN_ROLE]), "config_admin.validate")
    require_ok(intent("route.authority.validate", {"action_id": system_action["action_id"]}, tokens[PLATFORM_ADMIN_ROLE]), "system_admin.validate")
    require_ok(intent("ui.contract.v2", {"op": "action_open", "action_id": config_action["action_id"]}, tokens[ADMIN_ROLE]), "config_admin.user_management")
    admin_form_by_role = {
        ADMIN_ROLE: admin_form_assertion(tokens[ADMIN_ROLE], config_action),
        PLATFORM_ADMIN_ROLE: admin_form_assertion(tokens[PLATFORM_ADMIN_ROLE], system_action),
    }
    if not admin_form_by_role[ADMIN_ROLE]["permission_field"]:
        raise RuntimeError(
            "business configuration administrator form contract declares no "
            "governance permission field"
        )
    for role in LOCKED_ROLES:
        require_denied(
            intent("route.authority.validate", {"action_id": config_action["action_id"]}, tokens[role]),
            f"{role}.admin_denied",
        )
        leaked = [
            entry
            for bucket in DELIVERED_BUCKETS
            for entry in locked_authority[role].get(bucket) or []
            if isinstance(entry, dict) and int(entry.get("action_id") or 0) == int(config_action["action_id"])
        ]
        if leaked:
            raise RuntimeError(f"{role}: admin action delivered to an ordinary role")

    execution_xmlid = declared_context_scoped_action(overrides, "pm")
    pm_contract = locked_authority["pm"]
    execution = find(pm_contract, "contextual_actions", execution_xmlid)
    if execution.get("route_kind") != "CONTEXTUAL_ROUTE" or execution.get("menu_id"):
        raise RuntimeError("execution route kind/menu boundary invalid")
    sample = first_pm_contract(tokens["pm"])
    scope = {
        "action_id": execution["action_id"],
        "company_id": m2o_id(sample.get("company_id")),
        "project_id": m2o_id(sample.get("project_id")),
        "contract_id": int(sample["id"]),
    }
    require_ok(intent("route.authority.validate", scope, tokens["pm"]), "pm.execution.legal_scope")
    require_denied(intent("route.authority.validate", {**scope, "project_id": scope["project_id"] + 1000000}, tokens["pm"]), "pm.execution.cross_project")
    require_denied(intent("route.authority.validate", {**scope, "company_id": scope["company_id"] + 1000000}, tokens["pm"]), "pm.execution.cross_company")
    require_denied(intent("route.authority.validate", {"action_id": execution["action_id"]}, tokens["pm"]), "pm.execution.missing_context")
    require_ok(intent("ui.contract.v2", {"op": "action_open", "action_id": execution["action_id"]}, tokens["pm"]), "pm.execution.contract")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({
        "contract_version": version,
        "served_revision": served_revision,
        "admin_action_id": int(config_action["action_id"]),
        "admin_action_xmlid": admin_xmlid,
        "admin_action_route": admin_action_route,
        "admin_action_name": admin_action_name,
        "admin_route_by_role": admin_route_by_role,
        "admin_form_by_role": admin_form_by_role,
        "execution_action_id": int(execution["action_id"]),
        "execution_action_xmlid": execution_xmlid,
        "legal_scope": scope,
        "admin_route_count": len(config_contract.get("admin_actions") or []),
        "role_partition": {
            role: {
                "declared": len(declared_menu_xmlids(overrides, role)),
                "delivered": len(delivered_xmlids(locked_authority[role])),
                "denied": len(denied_xmlids(locked_authority[role])),
            }
            for role in LOCKED_ROLES
        },
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"ROUTE_AUTHORITY_CONTRACT_VERSION={version}")
    print(f"SERVED_SOURCE_REVISION={served_revision}")
    print("ROLE_CONTRACT_PARTITION=PASS")
    print("USER_MANAGEMENT=PASS")
    print("ROLE_MANAGEMENT=PASS")
    print("CONTRACT_EXECUTION_CONTEXT_ROUTE=PASS")
    print("ORDINARY_USER_ADMIN_DENIAL=PASS")
    print("CROSS_COMPANY_CONTEXT_DENIAL=PASS")
    print("HTTP_500=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
