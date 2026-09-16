"""Resolve governed local.dev material-handling browser targets without writes."""

import hashlib
import json

from odoo.addons.smart_construction_core.core_extension_policy_maps import (
    ROLE_SURFACE_OVERRIDES,
)
from odoo.addons.smart_construction_core.services.locked_menu_policy_contract import (
    load_locked_menu_policy_contract,
)


def xmlid(record):
    return record.get_external_id().get(record.id, "")


users = env["res.users"].sudo().search([("login", "=", "demo_full"), ("active", "=", True)])
if len(users) != 1:
    raise RuntimeError("governed demo_full principal is not uniquely available")
user = users.ensure_one()
if not user.has_group(
    "smart_construction_core.group_sc_cap_material_manager"
):
    raise RuntimeError("governed material-manager principal is unavailable")
security_user = env.ref("smart_construction_demo.user_demo_project_read")
project_users = env["res.users"].sudo().search(
    [("login", "=", "demo_role_project_manager"), ("active", "=", True)]
)
if len(project_users) != 1:
    raise RuntimeError("governed project-manager principal is not uniquely available")
project_user = project_users.ensure_one()
finance_users = env["res.users"].sudo().search(
    [("login", "=", "demo_role_finance"), ("active", "=", True)]
)
if len(finance_users) != 1:
    raise RuntimeError("governed finance principal is not uniquely available")
finance_user = finance_users.ensure_one()
config_group = env.ref(
    "smart_construction_core.group_sc_cap_business_config_admin"
)
config_users = [
    candidate
    for candidate in env["res.users"].sudo().search(
        [("share", "=", False), ("active", "=", True)], order="id"
    )
    if config_group in candidate.groups_id
    and str(candidate.login or "").startswith("demo")
]
if not config_users:
    raise RuntimeError("governed business-config principal is unavailable")
config_user = config_users[0]
entry_specs = {
    "inbound": {
        "menu_xmlid": "smart_construction_core.menu_sc_material_inbound",
        "action_xmlid": "smart_construction_core.action_sc_material_inbound_handling",
        "model": "sc.material.inbound",
    },
    "outbound": {
        "menu_xmlid": "smart_construction_core.menu_sc_material_outbound",
        "action_xmlid": "smart_construction_core.action_sc_material_outbound",
        "model": "sc.material.outbound",
        "domain": [("outbound_type", "=", "issue")],
    },
    "return": {
        "menu_xmlid": "smart_construction_core.menu_sc_material_return",
        "action_xmlid": "smart_construction_core.action_sc_material_return",
        "model": "sc.material.outbound",
        "domain": [("outbound_type", "=", "return")],
    },
    "supplier_return": {
        "menu_xmlid": "smart_construction_core.menu_sc_product_material_return_v1",
        "action_xmlid": "smart_construction_core.action_sc_material_supplier_return",
        "model": "sc.material.supplier.return",
    },
}
shared_entry_specs = {
    "project_profile": {
        "menu_xmlid": "smart_construction_core.menu_sc_project_project",
        "action_xmlid": "smart_construction_core.action_sc_project_list",
        "model": "project.project",
        "require_create": False,
    },
    "personnel_profile": {
        "menu_xmlid": "smart_construction_core.menu_sc_runtime_user_management",
        "action_xmlid": "smart_construction_core.action_sc_runtime_user_management",
        "model": "res.users",
        "require_create": False,
    },
    "payment_request": {
        "menu_xmlid": "smart_construction_core.menu_sc_user_payment_apply",
        "action_xmlid": "smart_construction_core.action_payment_request_user_payment_apply",
        "model": "payment.request",
        "require_create": False,
    },
}


def resolve_entry(key, spec, principal=user):
    menu = env.ref(spec["menu_xmlid"])
    action = env.ref(spec["action_xmlid"])
    if menu.action != action or action.res_model != spec["model"]:
        raise RuntimeError("material %s menu/action authority mismatch" % key)
    record_env = (
        env[spec["model"]]
        .with_user(principal)
        .with_company(principal.company_id)
        .with_context(
            allowed_company_ids=principal.company_ids.ids, active_test=False
        )
    )
    record_env.check_access_rights("read")
    if spec.get("require_create", True):
        record_env.check_access_rights("create")
    domain = list(spec.get("domain", []))
    record = record_env.search(domain, order="id desc", limit=1)
    editable_record = (
        record_env.search(domain + [("state", "=", "draft")], order="id desc", limit=1)
        if "state" in record_env._fields
        else record_env.browse()
    )
    record_payload = None
    fingerprint_payload = {"model": spec["model"], "record": None}
    if record:
        record.check_access_rule("read")
        record_payload = {
            "id": int(record.id),
            "xmlid": xmlid(record),
            "name": str(record.display_name or record.id),
            "state": str(getattr(record, "state", "") or ""),
        }
        fingerprint_payload["record"] = {
            "id": int(record.id),
            "write_date": record.write_date.isoformat() if record.write_date else "",
            "state": str(getattr(record, "state", "") or ""),
            "name": str(record.display_name or record.id),
            "line_count": len(getattr(record, "line_ids", [])),
        }
    editable_payload = None
    if editable_record:
        editable_record.check_access_rule("read")
        editable_record.check_access_rights("write")
        editable_record.check_access_rule("write")
        editable_payload = {
            "id": int(editable_record.id),
            "xmlid": xmlid(editable_record),
            "name": str(editable_record.display_name or editable_record.id),
            "state": str(getattr(editable_record, "state", "") or ""),
        }
        fingerprint_payload["editable_record"] = {
            "id": int(editable_record.id),
            "write_date": editable_record.write_date.isoformat() if editable_record.write_date else "",
            "state": str(getattr(editable_record, "state", "") or ""),
            "name": str(editable_record.display_name or editable_record.id),
            "line_count": len(getattr(editable_record, "line_ids", [])),
        }
    return {
        "key": key,
        "model": spec["model"],
        "user": {
            "id": int(principal.id),
            "login": principal.login,
            "xmlid": xmlid(principal),
        },
        "menu": {"id": int(menu.id), "xmlid": xmlid(menu)},
        "action": {"id": int(action.id), "xmlid": xmlid(action)},
        "record": record_payload,
        "editable_record": editable_payload,
        "business_fingerprint": hashlib.sha256(
            json.dumps(
                fingerprint_payload, ensure_ascii=False, sort_keys=True
            ).encode("utf-8")
        ).hexdigest(),
    }


entries = {key: resolve_entry(key, spec) for key, spec in entry_specs.items()}
locked_menu_contract = load_locked_menu_policy_contract()
locked_menus = {
    menu.get("menu_xmlid"): menu
    for product in locked_menu_contract["products"].values()
    for group in product.get("menu_groups") or []
    for menu in group.get("menus") or []
}
return_menu = env.ref("smart_construction_core.menu_sc_material_return")
return_menu_xmlid = xmlid(return_menu)
outbound_menu_xmlid = "smart_construction_core.menu_sc_material_outbound"
outbound_allowed_codes = sorted(
    {
        str(code)
        for product in locked_menu_contract["products"].values()
        for group in product.get("menu_groups") or []
        for menu in group.get("menus") or []
        if menu.get("menu_xmlid") == outbound_menu_xmlid
        for code in menu.get("allowed_business_category_codes") or []
    }
)
return_route_roles = sorted(
    role
    for role, policy in ROLE_SURFACE_OVERRIDES.items()
    if return_menu_xmlid in (policy.get("contextual_menu_xmlids") or [])
    or return_menu_xmlid in (policy.get("primary_menu_xmlids") or [])
    or return_menu_xmlid in (policy.get("role_home_menu_xmlids") or [])
)
shared_entries = {
    "project_profile": resolve_entry(
        "project_profile", shared_entry_specs["project_profile"], project_user
    ),
    "personnel_profile": resolve_entry(
        "personnel_profile",
        shared_entry_specs["personnel_profile"],
        config_user,
    ),
    "payment_request": resolve_entry(
        "payment_request", shared_entry_specs["payment_request"], finance_user
    ),
}
inbound = entries["inbound"]
if not inbound["record"]:
    raise RuntimeError("governed local.dev material inbound is unavailable")
payload = {
    "database": env.cr.dbname,
    "user": {"id": int(user.id), "login": user.login, "xmlid": xmlid(user)},
    "security_user": {
        "id": int(security_user.id),
        "login": security_user.login,
        "xmlid": xmlid(security_user),
    },
    "entries": entries,
    "formal_return_path": {
        "status": "product_decision_required",
        "formally_reachable": False,
        "return_menu_xmlid": return_menu_xmlid,
        "return_action_xmlid": xmlid(env.ref("smart_construction_core.action_sc_material_return")),
        "return_menu_in_formal_baseline": return_menu_xmlid in locked_menus,
        "return_menu_parent_xmlid": xmlid(return_menu.parent_id),
        "return_menu_parent_active": bool(return_menu.parent_id.active),
        "route_authority_roles": return_route_roles,
        "outbound_allowed_business_category_codes": outbound_allowed_codes,
        "supplier_return_model": "sc.material.supplier.return",
        "reason": "no_formal_menu_or_authorized_category_path",
    },
    "shared_entries": shared_entries,
    # Keep the original inbound shape for the established full-domain journey.
    "menu": inbound["menu"],
    "action": inbound["action"],
    "record": inbound["record"],
    "business_fingerprint": inbound["business_fingerprint"],
}
print(
    "LOCAL_DEV_MATERIAL_DOMAIN_JSON=%s"
    % json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
)
