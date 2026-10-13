"""Resolve one governed local.dev payment-request parity target without writes."""

import hashlib
import json
import os
import re

from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval
from odoo.addons.smart_construction_core.services.financial_workspace_contract import (
    build_financial_form_business_actions,
)
from odoo.addons.smart_core.delivery.menu_service import MenuService
from odoo.addons.smart_core.identity.identity_resolver import IdentityResolver


def xmlid(record):
    return record.get_external_id().get(record.id, "")


def guidance_reference_paths(value, fields, path="$", depth=0):
    """Locate exact field tokens in bounded declaration JSON/XML, never values."""
    if depth > 80:
        raise ValueError("configuration nesting exceeds reference audit boundary")
    out = []
    if isinstance(value, dict):
        for key, item in value.items():
            out.extend(guidance_reference_paths(str(key), fields, path + ".<key>", depth + 1))
            out.extend(guidance_reference_paths(item, fields, path + "." + str(key), depth + 1))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            out.extend(guidance_reference_paths(item, fields, path + "[%s]" % index, depth + 1))
    elif isinstance(value, str):
        for field in fields:
            if re.search(r"(?<![A-Za-z0-9_])" + re.escape(field) + r"(?![A-Za-z0-9_])", value):
                out.append({"field": field, "path": path})
    return out


def split_layout_authority(value, path="$", permissions=None):
    """Keep every node/field/order/span; separate only explicit access flags."""
    if permissions is None:
        permissions = []
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            child_path = path + "." + str(key)
            if key in {"visible", "readonly", "disabled", "auth"}:
                permissions.append({"path": child_path, "value": item})
            else:
                out[key] = split_layout_authority(item, child_path, permissions)
        return out
    if isinstance(value, list):
        return [split_layout_authority(item, path + "[%s]" % index, permissions) for index, item in enumerate(value)]
    return value


def select_authority_record(target, floorplan_record, editable_record):
    if target == "floorplan":
        return floorplan_record
    if target != "editable":
        raise ValueError("unsupported authority target")
    if not editable_record or editable_record.state != "draft":
        raise ValueError("governed editable authority record must be draft")
    return editable_record


def validate_layout_observation(contract, model, record_id):
    """A successful transport is not proof of a comparable form declaration."""
    if not isinstance(contract, dict):
        raise ValueError("contract must be an object")
    page = contract.get("pageInfo") or {}
    data = contract.get("dataContract") or {}
    if page.get("model") != model or (data.get("mainData") or {}).get("id") != record_id:
        raise ValueError("actor contract target does not match the fixed record")
    layout = contract.get("layoutContract")
    if not isinstance(layout, dict) or not isinstance(layout.get("containerTree"), list) or not layout["containerTree"]:
        raise ValueError("actor contract has no declared nonempty container tree")
    form = contract.get("formStructureContract")
    if (not isinstance(form, dict) or form.get("source") != "ui.contract.v2.form_structure_contract"
            or form.get("model") != model or form.get("viewType") != "form"
            or not isinstance(form.get("structureAuthority"), str) or not form["structureAuthority"].strip()):
        raise ValueError("actor contract form structure identity is missing or inconsistent")
    return {"layoutContract": layout, "formStructureContract": form}


def layout_differences(left, right, path="$"):
    if type(left) is not type(right):
        return [{"path": path, "left": left, "right": right}]
    if isinstance(left, dict):
        out = []
        for key in sorted(set(left) | set(right)):
            if key not in left or key not in right:
                out.append({"path": path + "." + key, "left": left.get(key), "right": right.get(key), "membership_changed": True})
            else:
                out.extend(layout_differences(left[key], right[key], path + "." + key))
        return out
    if isinstance(left, list):
        out = []
        for index in range(max(len(left), len(right))):
            if index >= len(left) or index >= len(right):
                out.append({"path": path + "[%s]" % index, "membership_changed": True})
            else:
                out.extend(layout_differences(left[index], right[index], path + "[%s]" % index))
        return out
    return [] if left == right else [{"path": path, "left": left, "right": right}]


if os.environ.get("CONTRACT_REFERENCE_PREFLIGHT") == "project_create":
    actor = env.ref("smart_construction_demo.sc_demo_user_test_admin")
    actor_env = env["project.project"].with_user(actor).sudo(False).with_company(actor.company_id).env
    actor_env["project.project"].check_access_rights("create")
    resolver = IdentityResolver(actor_env)
    roles = resolver.build_role_surface(resolver.user_group_xmlids(actor), [], {"workspace.home"})
    entries = []
    retired_entries = []
    for kind, action_name, menu_name, view_name in (
        ("standard", "action_project_initiation", "menu_sc_project_initiation", "view_project_create_form"),
        ("quick", "action_project_initiation_quick", "menu_sc_project_quick_create", "view_project_create_form_quick"),
    ):
        action_record, menu_record, view_record = [env.ref("smart_construction_core." + name) for name in (action_name, menu_name, view_name)]
        if action_record.res_model != "project.project" or action_record.view_id != view_record or menu_record.action != action_record:
            raise RuntimeError("project create native entry identity mismatch")
        entry = {"kind": kind, "model": "project.project", "action_id": action_record.id,
                        "menu_id": menu_record.id, "view_id": view_record.id,
                        "action_xmlid": xmlid(action_record), "menu_xmlid": xmlid(menu_record), "view_xmlid": xmlid(view_record)}
        if menu_record.active:
            entries.append(entry)
        else:
            retired_entries.append({**entry, "active": False, "reason": "native_menu_retired"})
    if not entries:
        raise RuntimeError("no active native project create entry")
    payload = {"database": env.cr.dbname, "user": {"id": actor.id, "login": actor.login,
               "company_id": actor.company_id.id, "company_name": actor.company_id.name},
               "acceptance_authority": {"role_code": roles.get("role_code"), "sudo": actor_env.su},
               "project_create_entries": entries,
               "retired_project_create_entries": retired_entries,
               "business_fingerprint": hashlib.sha256(json.dumps(actor_env["project.project"].search_read([], ["id", "write_date"], order="id"), default=str, sort_keys=True).encode()).hexdigest()}
    print("LOCAL_DEV_PAYMENT_PARITY_JSON=" + json.dumps(payload, ensure_ascii=False))
    raise SystemExit(0)

user = env.ref("smart_construction_demo.user_demo_role_finance")
security_user = env.ref("smart_construction_demo.user_demo_project_read")
project_create_user = env.ref("smart_construction_demo.sc_demo_user_test_admin")
menu = env.ref("smart_construction_core.menu_sc_user_payment_apply")
action = env.ref("smart_construction_core.action_payment_request_user_payment_apply")
project_create_action = env.ref("smart_construction_core.action_project_initiation")
project_create_menu = env.ref("smart_construction_core.menu_sc_project_initiation")
view = env.ref("smart_construction_core.view_payment_request_form")
candidate = env.ref("smart_construction_demo.sc_demo_pay_req_010_003")
if os.environ.get("CONTRACT_REFERENCE_PREFLIGHT") == "guidance":
    candidate = env.ref("smart_construction_demo.payment_guidance_demo_record")
execution_action = env.ref("smart_construction_core.action_sc_payment_execution_actual_outflow")
execution_menu = env.ref("smart_construction_core.menu_sc_payment_execution")
payment_env = env["payment.request"].with_user(user).with_company(user.company_id).with_context(
    allowed_company_ids=user.company_ids.ids,
    active_test=False,
)
record = payment_env.browse(candidate.id).exists()
if not record:
    raise RuntimeError("governed local.dev payment request is not readable by demo_role_finance")
record.check_access_rights("read")
record.check_access_rule("read")
actionable_fixture = env.ref(
    "smart_construction_demo.payment_request_floorplan_demo_record",
    raise_if_not_found=False,
)
actionable_record = (
    payment_env.browse(actionable_fixture.id).exists()
    if actionable_fixture and actionable_fixture._name == "payment.request"
    else payment_env.browse()
)
if not actionable_record:
    raise RuntimeError("governed submit-ready payment request fixture is missing")
actionable_record.check_access_rights("read")
actionable_record.check_access_rule("read")
actionable_funding_baseline = env["project.funding.baseline"].sudo().search(
    [
        ("project_id", "=", actionable_record.project_id.id),
        ("state", "=", "active"),
        ("normalization_state", "=", "normalized"),
    ],
    limit=2,
)
if len(actionable_funding_baseline) != 1:
    raise RuntimeError("submit-ready payment request requires one active normalized funding baseline")
if not actionable_record.date_request or not (
    actionable_funding_baseline.period_start
    <= actionable_record.date_request
    <= actionable_funding_baseline.period_end
):
    raise RuntimeError("submit-ready payment request date is outside the active funding baseline")
execution_env = env["sc.payment.execution"].with_user(user).with_company(user.company_id).with_context(
    allowed_company_ids=user.company_ids.ids,
    active_test=False,
)
execution_record = execution_env.search([("source_kind", "=", "actual_outflow")], order="id desc", limit=1)
if not execution_record:
    raise RuntimeError("governed local.dev payment execution reuse target is missing")
execution_record.check_access_rights("read")
execution_record.check_access_rule("read")
if menu.action != action or action.res_model != "payment.request":
    raise RuntimeError("payment request menu/action authority mismatch")
if view.model != "payment.request" or view.type != "form":
    raise RuntimeError("payment request native form authority mismatch")
if not menu.active or menu.id not in env["ir.ui.menu"].with_user(user)._visible_menu_ids():
    raise RuntimeError("payment request menu is not active and visible to demo_role_finance")

action_domain = safe_eval(
    action.domain or "[]",
    {"uid": user.id, "user": user, "context": dict(payment_env.env.context)},
)
record_in_action_domain = payment_env.search_count(
    expression.AND([action_domain, [("id", "=", record.id)]])
)
if record_in_action_domain != 1:
    raise RuntimeError("governed local.dev payment request is outside the formal action domain")

identity_resolver = IdentityResolver(payment_env.env)
role_surface = identity_resolver.build_role_surface(
    identity_resolver.user_group_xmlids(user),
    [],
    {"workspace.home"},
)
route_authority = MenuService(payment_env.env).build_route_authority(role_surface)
route_matches = [
    (bucket, entry)
    for bucket in ("primary_actions", "role_home_actions", "contextual_actions", "admin_actions")
    for entry in route_authority.get(bucket) or []
    if int(entry.get("menu_id") or 0) == menu.id
    and int(entry.get("action_id") or 0) == action.id
]
if len(route_matches) != 1:
    raise RuntimeError("payment request route authority is not uniquely projected for demo_role_finance")


project_create_env = env["project.project"].with_user(project_create_user).with_company(
    project_create_user.company_id
).with_context(allowed_company_ids=project_create_user.company_ids.ids)
project_create_env.check_access_rights("create")
if project_create_action.res_model != "project.project" or project_create_menu.action != project_create_action:
    raise RuntimeError("project create action/menu authority mismatch")

candidate_rows = []
for item in payment_env.search([("type", "=", "pay")], order="id"):
    item_xmlid = xmlid(item)
    if not item_xmlid.startswith("smart_construction_demo.") and not str(item.name or "").startswith("DEMO-PR-"):
        continue
    business_projection = build_financial_form_business_actions(payment_env.env, item._name, item.id) or {}
    submit_actions = [
        action for action in business_projection.get("actions", [])
        if action.get("action_key") == "submit" and action.get("method") == "action_submit"
    ]
    submit_action = submit_actions[0] if submit_actions else {}
    candidate_rows.append({
        "id": int(item.id),
        "xmlid": item_xmlid,
        "name": str(item.name or ""),
        "state": str(item.state or ""),
        "validation_status": str(item.validation_status or ""),
        "amount": float(item.amount or 0.0),
        "unpaid_amount": float(item.unpaid_amount or 0.0),
        "has_active_payment_execution": bool(item.has_active_payment_execution),
        "legal_next_action": str(item.legal_next_action_display or ""),
        "blocking_reason": str(item.payment_blocking_reason_display or ""),
        "has_contract": bool(item.contract_id),
        "has_settlement": bool(item.settlement_id),
        "submit_business_available": bool(submit_action.get("business_available")),
        "submit_authorization_allowed": bool(submit_action.get("authorization_allowed")),
        "submit_enabled": bool(submit_action.get("enabled")),
        "submit_reason_code": str(submit_action.get("reason_code") or ""),
    })

fingerprint_payload = {
    "id": int(record.id),
    "write_date": record.write_date.isoformat() if record.write_date else "",
    "state": str(record.state or ""),
    "name": str(record.name or ""),
    "amount": float(record.amount or 0.0),
    "payment_count": int(env["sc.payment.execution"].with_user(user).search_count([
        ("payment_request_id", "=", record.id),
    ])),
}
actionable_fingerprint_payload = {
    "id": int(actionable_record.id),
    "write_date": actionable_record.write_date.isoformat() if actionable_record.write_date else "",
    "state": str(actionable_record.state or ""),
    "validation_status": str(actionable_record.validation_status or ""),
    "name": str(actionable_record.name or ""),
    "amount": float(actionable_record.amount or 0.0),
}
payload = {
    "database": env.cr.dbname,
    "user": {"id": int(user.id), "login": user.login, "xmlid": xmlid(user),
             "company_id": int(user.company_id.id), "company_name": user.company_id.name},
    "security_user": {
        "id": int(security_user.id),
        "login": security_user.login,
        "xmlid": xmlid(security_user),
    },
    "project_create_user": {
        "id": int(project_create_user.id),
        "login": project_create_user.login,
        "xmlid": xmlid(project_create_user),
        "can_create_project": True,
    },
    "project_create_entry": {
        "action_id": int(project_create_action.id),
        "action_xmlid": xmlid(project_create_action),
        "menu_id": int(project_create_menu.id),
        "menu_xmlid": xmlid(project_create_menu),
    },
    "menu": {"id": int(menu.id), "xmlid": xmlid(menu)},
    "action": {"id": int(action.id), "xmlid": xmlid(action)},
    "view": {"id": int(view.id), "xmlid": xmlid(view)},
    "acceptance_authority": {
        "role_code": str(role_surface.get("role_code") or ""),
        "route_bucket": route_matches[0][0],
        "menu_active": bool(menu.active),
        "menu_visible": True,
        "record_in_action_domain": True,
        "action_domain": action_domain,
        "funding_baseline": {
            "id": int(actionable_funding_baseline.id),
            "period_start": str(actionable_funding_baseline.period_start),
            "period_end": str(actionable_funding_baseline.period_end),
            "request_date": str(actionable_record.date_request),
        },
    },
    "reuse_target": {
        "model": "sc.payment.execution",
        "action_id": int(execution_action.id),
        "action_xmlid": xmlid(execution_action),
        "menu_id": int(execution_menu.id),
        "menu_xmlid": xmlid(execution_menu),
        "record_id": int(execution_record.id),
        "name": str(execution_record.display_name or ""),
    },
    "execution_contract_inventory": [
        {
            "id": int(contract.id),
            "name": str(contract.name or ""),
            "active": bool(contract.active),
            "priority": int(contract.priority or 0),
            "action_id": int(contract.action_id.id or 0),
            "has_creator_name": "creator_name" in str(contract.contract_json or {}),
        }
        for contract in env["ui.business.config.contract"].sudo().search([
            ("model", "=", "sc.payment.execution"),
            ("view_type", "=", "form"),
        ], order="priority desc, id")
    ],
    "record": {
        "id": int(record.id),
        "xmlid": xmlid(record),
        "name": record.name,
        "state": str(record.state or ""),
        "validation_status": str(record.validation_status or ""),
        "type": str(record.type or ""),
        "amount": float(record.amount or 0.0),
        "has_active_payment_execution": bool(record.has_active_payment_execution),
        "payment_count": fingerprint_payload["payment_count"],
        "legal_next_action": str(record.legal_next_action_display or ""),
        "blocking_reason": str(record.payment_blocking_reason_display or ""),
    },
    "actionable_record": {
        "id": int(actionable_record.id),
        "name": str(actionable_record.name or ""),
        "state": str(actionable_record.state or ""),
        "validation_status": str(actionable_record.validation_status or ""),
        "amount": float(actionable_record.amount or 0.0),
        "legal_next_action": str(actionable_record.legal_next_action_display or ""),
        "blocking_reason": str(actionable_record.payment_blocking_reason_display or ""),
    },
    "business_fingerprint": hashlib.sha256(
        json.dumps(fingerprint_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest(),
    "actionable_fingerprint": hashlib.sha256(
        json.dumps(actionable_fingerprint_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest(),
    "candidate_inventory": candidate_rows,
}
payload["contract_resolution"] = {
    "schema": "acceptance.record_identity_resolution.v1",
    "producer": "scripts/verify/local_dev_payment_request_native_parity_ids.py",
    "targets": {
        "companies": {"local": int(user.company_id.id)},
        "payment_request": {"model": record._name, "record_id": int(record.id),
                            "record_xmlid": xmlid(record), "action_id": int(action.id), "menu_id": int(menu.id)},
    },
}
if not xmlid(record):
    raise RuntimeError("approved contract target requires a real fixture external id")
if os.environ.get("CONTRACT_REFERENCE_PREFLIGHT") == "1":
    fields = ("intake_next_action_display", "intake_blocking_reason_display",
              "legal_next_action_display", "payment_blocking_reason_display")
    references = []
    carriers = []
    models = ["project.project", "payment.request"]
    for item in env["ir.ui.view"].sudo().search([("active", "=", True), ("model", "in", models)]):
        identity = {"carrier": "ir.ui.view", "id": item.id, "xmlid": xmlid(item), "model": item.model,
                    "active": bool(item.active), "inherit_id": item.inherit_id.id or None}
        hits = guidance_reference_paths(item.arch_db or "", fields)
        if hits:
            references.append(dict(identity, references=hits))
    for item in env["ui.business.config.contract"].sudo().search([("model", "in", models)]):
        definition = item.contract_json or {}
        identity = {"carrier": "ui.business.config.contract", "id": item.id, "xmlid": xmlid(item),
                    "model": item.model, "active": bool(item.active), "status": item.status,
                    "version": item.version_no, "action_id": item.action_id.id or None,
                    "view_id": item.view_id.id or None, "role_key": item.role_key or "",
                    "company_id": item.company_id.id or None}
        carriers.append(identity)
        if item.active and item.status == "published":
            hits = guidance_reference_paths(definition, fields)
            if hits:
                references.append(dict(identity, references=hits))
    for item in env["sc.business.category"].sudo().search([("active", "=", True), ("target_model", "in", models)]):
        definition = json.loads(item.form_policy_json or "{}")
        identity = {"carrier": "sc.business.category", "id": item.id, "xmlid": xmlid(item),
                    "model": item.target_model, "active": bool(item.active),
                    "composition_mode": definition.get("composition_mode"),
                    "structure_owner": "sc.business.category.form_policy_json"}
        carriers.append(identity)
        hits = guidance_reference_paths(definition, fields)
        if hits:
            references.append(dict(identity, references=hits))
    admin_record = actionable_record.with_user(project_create_user).sudo(False)
    admin_record.check_access_rights("read")
    admin_record.check_access_rule("read")
    payload["guidance_reference_preflight"] = {
        "fields": list(fields), "models": models, "references": references, "carriers": carriers,
        "scope": "metadata only; two models/three declared carriers; no retirement decision",
        "system_admin_floorplan": {"actor_id": project_create_user.id, "login": project_create_user.login,
            "actor_xmlid": xmlid(project_create_user), "company_id": project_create_user.company_id.id,
            "record_id": admin_record.id, "record_xmlid": xmlid(admin_record),
            "model": admin_record._name, "env_su": admin_record.env.su,
            "action_id": action.id, "action_xmlid": xmlid(action), "menu_id": menu.id, "menu_xmlid": xmlid(menu)},
    }
if os.environ.get("CONTRACT_REFERENCE_PREFLIGHT") == "authority":
    from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler
    from odoo.addons.smart_core.core.form_structure_authority import authenticated_form_role_key
    form_bindings = action.view_ids.filtered(lambda binding: binding.view_mode == "form")
    if len(form_bindings) != 1 or not form_bindings.view_id:
        raise RuntimeError("payment entry must declare one exact form view")
    authority_view = form_bindings.view_id
    expected_view = env.ref("smart_construction_core.view_payment_request_pay_form")
    if authority_view != expected_view:
        raise RuntimeError("payment action form view XMLID does not match the declared pay entry")
    target_name = os.environ.get("CONTRACT_AUTHORITY_TARGET", "floorplan")
    selected_record = select_authority_record(target_name, actionable_record, record)
    comparison = []
    company = selected_record.company_id
    common = {"target_selection": target_name, "state": selected_record.state, "model": selected_record._name, "record_id": selected_record.id,
              "record_xmlid": xmlid(selected_record), "company_id": company.id,
              "action_id": action.id, "action_xmlid": xmlid(action), "menu_id": menu.id,
              "menu_xmlid": xmlid(menu), "view_id": authority_view.id, "view_xmlid": xmlid(authority_view), "render_profile": "edit",
              "model_base_view": {"id": view.id, "xmlid": xmlid(view)},
              "action_selected_view": {"id": authority_view.id, "xmlid": xmlid(authority_view)}}
    for actor in (project_create_user, user):
        actor_model = env["payment.request"].with_user(actor).sudo(False).with_company(company).with_context(allowed_company_ids=[company.id])
        actor_env = actor_model.env
        result = {"actor_id": actor.id, "login": actor.login, "actor_xmlid": xmlid(actor),
                  "company_id": company.id, "env_su": actor_env.su, "status": "not_comparable"}
        try:
            if company not in actor.company_ids:
                raise ValueError("actor is not authorized for the fixed comparison company")
            actor_record = actor_model.browse(selected_record.id)
            actor_record.check_access_rights("read")
            actor_record.check_access_rule("read")
            role_key = authenticated_form_role_key(actor_env)
            result["authenticated_role_key"] = role_key
            configs = actor_env["ui.business.config.contract"]._effective_view_orchestration_contracts(
                actor_record._name, view_type="form", action_id=action.id, view_id=authority_view.id, role_key=role_key)
            result["effective_configs"] = [{"id": item.id, "version": item.version_no,
                "role_key": item.role_key or "", "model": actor_record._name,
                "company_id": actor_env["ui.business.config.contract"].sudo().browse(item.id).company_id.id if item.id else None,
                "action_id": item.action_id or None, "view_id": item.view_id or None,
                "source_kind": item.source_kind, "status": item.status,
                "composition": (item.contract_json or {}).get("view_orchestration", {})} for item in configs]
            result["metadata_selection_authority"] = "existing effective-config resolver; metadata sudo is not actor contract authority"
            request = {"op": "action_open", "model": actor_record._name, "record_id": actor_record.id,
                       "action_id": action.id, "menu_id": menu.id, "view_id": authority_view.id,
                       "view_type": "form", "render_profile": "edit", "client_type": "web_pc",
                       "delivery_profile": "full", "context": {"allowed_company_ids": [company.id]}}
            result["request"] = request
            response = UiContractV2Handler(actor_env, su_env=actor_env["ir.model"].sudo().env).handle({"params": request})
            envelope = response.to_legacy_dict() if hasattr(response, "to_legacy_dict") else response
            if not isinstance(envelope, dict) or envelope.get("ok") is not True:
                result["error"] = envelope.get("error") if isinstance(envelope, dict) else "invalid envelope"
            else:
                contract = envelope.get("data") or {}
                actual_record_id = (contract.get("dataContract") or {}).get("mainData", {}).get("id")
                declared_structure = validate_layout_observation(contract, actor_record._name, actor_record.id)
                result["observed_record_id"] = actual_record_id
                flags = []
                structure = split_layout_authority(declared_structure, permissions=flags)
                result.update(status="observed", effective_render_profile=(contract.get("statusContract") or {}).get("globalStatus", {}).get("effectiveRenderProfile"), page_info=contract.get("pageInfo"), raw_structure=declared_structure, structure=structure,
                    structure_sha256=hashlib.sha256(json.dumps(structure, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                    layout_access_flags=flags, status_contract=contract.get("statusContract"),
                    action_contract=contract.get("actionContract"))
        except Exception as exc:
            result["error"] = {"type": type(exc).__name__, "message": str(exc)[:1000]}
        comparison.append(result)
    differences = layout_differences(comparison[0]["structure"], comparison[1]["structure"]) if all(item["status"] == "observed" for item in comparison) else None
    payload["layout_authority_comparison"] = {"fixed_identity": common, "actors": comparison, "structure_differences": differences,
        "structure_difference_count": len(differences) if differences is not None else None,
        "status": "observed" if all(item["status"] == "observed" for item in comparison) else "not_comparable",
        "same_edit_mode_comparable": all(item.get("status") == "observed" and item.get("effective_render_profile") == "edit" for item in comparison),
        "source_sha": {"value": os.environ.get("CONTRACT_AUTHORITY_SOURCE_SHA"), "authority": "caller candidate declaration; not backend deployment attestation"},
        "comparison_scope": "fixed action-selected view/entry/record/company/requested edit; structural differences and access flags reported separately; differences require classification, not automatic role causality"}
print("LOCAL_DEV_PAYMENT_PARITY_JSON=%s" % json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
