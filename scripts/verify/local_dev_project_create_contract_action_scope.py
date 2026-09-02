"""Read-only probe for governed action scopes on the local.dev project create form."""

import json

from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler
from odoo.addons.smart_core.handlers.execute_button import ExecuteButtonHandler
from odoo.addons.smart_core.handlers.chatter_followers import (
    ChatterFollowersListHandler,
    ChatterFollowersUpdateHandler,
)


def _layout_occurrence_integrity(contract):
    occurrences = {}
    widgets = {}
    occurrence_owners = {}

    def walk(nodes, parent_id=""):
        for node in nodes if isinstance(nodes, list) else []:
            if not isinstance(node, dict):
                continue
            container_id = str(node.get("containerId") or "").strip()
            widget_id = str(node.get("widgetId") or "").strip()
            if str(node.get("type") or "").strip().lower() == "field" and widget_id:
                occurrences[widget_id] = str(node.get("name") or node.get("fieldCode") or "").strip()
                occurrence_owners[widget_id] = parent_id
            for widget in node.get("widgetList") if isinstance(node.get("widgetList"), list) else []:
                if isinstance(widget, dict) and str(widget.get("widgetId") or "").strip():
                    widgets[str(widget["widgetId"]).strip()] = widget
            walk(node.get("children"), container_id)

    walk(((contract.get("layoutContract") or {}).get("containerTree") or []))
    statuses = {
        str(row.get("widgetId") or "").strip()
        for row in ((contract.get("statusContract") or {}).get("widgetStatus") or [])
        if isinstance(row, dict) and str(row.get("widgetId") or "").strip()
    }
    return {
        "occurrence_count": len(occurrences),
        "widget_count": len(widgets),
        "missing_widgets": sorted(set(occurrences) - set(widgets)),
        "missing_widget_owners": {
            widget_id: occurrence_owners.get(widget_id, "")
            for widget_id in sorted(set(occurrences) - set(widgets))
        },
        "missing_statuses": sorted(set(occurrences) - statuses),
        "missing_descriptors": sorted(
            widget_id
            for widget_id in occurrences
            if widget_id in widgets and not isinstance(widgets[widget_id].get("fieldDescriptor"), dict)
        ),
    }


user = env.ref("smart_construction_demo.sc_demo_user_test_admin")
action = env.ref("smart_construction_core.action_project_initiation")
menu = env.ref("smart_construction_core.menu_sc_project_initiation")
project_record = env.ref("smart_construction_demo.sc_demo_project_001")
workspace_action = env.ref("smart_construction_core.action_sc_product_project_edit_v1")
workspace_menu = env.ref("smart_construction_core.menu_sc_product_project_edit_v1")
payment_action = env.ref("smart_construction_core.action_payment_request_user_payment_apply")
payment_menu = env.ref("smart_construction_core.menu_sc_user_payment_apply")
payment_record = env["payment.request"].sudo().search([
    ("name", "=", "DEMO-PR-FLOORPLAN-001"),
], limit=1)
if not payment_record:
    raise RuntimeError("governed payment request DriverHost probe fixture is missing")
user_env = env(user=user.id, context={
    **env.context,
    "allowed_company_ids": user.company_ids.ids,
})
payload = {
    "op": "action_open",
    "action_id": int(action.id),
    "menu_id": int(menu.id),
    "model": "project.project",
    "view_type": "form",
    "record_id": "new",
    "render_profile": "create",
    "client_type": "web_pc",
    "delivery_profile": "full",
}
result = UiContractV2Handler(user_env, payload=payload).run(payload=payload)
data = result.data if hasattr(result, "data") and isinstance(result.data, dict) else {}
if not getattr(result, "ok", False):
    raise RuntimeError("project create Contract V2 failed: %s" % result)
create_integrity = _layout_occurrence_integrity(data)
if any(create_integrity[key] for key in ("missing_widgets", "missing_statuses", "missing_descriptors")):
    raise AssertionError("project create Contract V2 occurrence integrity failed: %s" % create_integrity)

record_payload = {
    **payload,
    "record_id": int(project_record.id),
    "render_profile": "readonly",
}
record_result = UiContractV2Handler(user_env, payload=record_payload).run(payload=record_payload)
record_data = (
    record_result.data
    if hasattr(record_result, "data") and isinstance(record_result.data, dict)
    else {}
)
if not getattr(record_result, "ok", False):
    raise RuntimeError("project readonly Contract V2 failed: %s" % record_result)
record_integrity = _layout_occurrence_integrity(record_data)
if any(record_integrity[key] for key in ("missing_widgets", "missing_statuses", "missing_descriptors")):
    raise AssertionError("project readonly Contract V2 occurrence integrity failed: %s" % record_integrity)

record_rules = [
    row
    for row in ((record_data.get("actionContract") or {}).get("actionRuleList") or [])
    if isinstance(row, dict) and row.get("backendIdentity") == "window_action:338"
]
record_statuses = [
    row
    for row in ((record_data.get("statusContract") or {}).get("buttonStatus") or [])
    if isinstance(row, dict) and row.get("backendIdentity") == "window_action:338"
]
if len(record_rules) != 1 or len(record_statuses) != 1:
    raise AssertionError("project share action authority is not unique")
share_rule = record_rules[0]
share_status = record_statuses[0]
project_fingerprint_before = project_record.read(["write_date"])[0]
share_execute = ExecuteButtonHandler(
    user_env,
    payload={
        "params": {
            "model": "project.project",
            "res_id": int(project_record.id),
            "button": {
                "name": str((share_rule.get("button") or {}).get("name") or ""),
                "type": str((share_rule.get("button") or {}).get("type") or ""),
                "action_id": str(share_rule.get("actionId") or ""),
                "backend_identity": str(share_rule.get("backendIdentity") or ""),
                "source_widget_id": str(share_rule.get("sourceWidgetId") or ""),
            },
        },
        "meta": {"action_id": int(action.id), "menu_id": int(menu.id)},
    },
    context=dict(user_env.context),
).handle()
project_fingerprint_after = project_record.read(["write_date"])[0]
share_result = (
    ((share_execute.get("data") or {}).get("result") or {})
    if isinstance(share_execute, dict)
    else {}
)
share_entry_target = share_result.get("entry_target") or {}
if (
    not isinstance(share_execute, dict)
    or share_execute.get("ok") is not True
    or share_entry_target.get("route") != "/f/project.share.wizard/new"
    or project_fingerprint_before != project_fingerprint_after
):
    raise AssertionError("project share action execution adapter failed: %s" % {
        "execute": share_execute,
        "before": project_fingerprint_before,
        "after": project_fingerprint_after,
    })

project_action_integrity = []
for action_xmlid, menu_xmlid in (
    ("smart_construction_core.action_sc_project_list", "smart_construction_core.menu_sc_project_project"),
    ("smart_construction_core.action_sc_project_manage", "smart_construction_core.menu_sc_project_manage"),
    ("smart_construction_core.action_project_dashboard", "smart_construction_core.menu_sc_project_dashboard"),
    ("smart_construction_demo.action_sc_project_list_showcase", "smart_construction_demo.menu_sc_project_list_showcase"),
    ("smart_construction_demo.action_project_dashboard_showcase", "smart_construction_demo.menu_project_dashboard_showcase"),
):
    candidate_action = env.ref(action_xmlid, raise_if_not_found=False)
    candidate_menu = env.ref(menu_xmlid, raise_if_not_found=False)
    if not candidate_action or not candidate_menu:
        continue
    candidate_payload = {
        **payload,
        "action_id": int(candidate_action.id),
        "menu_id": int(candidate_menu.id),
        "record_id": int(project_record.id),
        "render_profile": "readonly",
    }
    candidate_result = UiContractV2Handler(user_env, payload=candidate_payload).run(
        payload=candidate_payload
    )
    candidate_data = (
        candidate_result.data
        if hasattr(candidate_result, "data") and isinstance(candidate_result.data, dict)
        else {}
    )
    candidate_integrity = _layout_occurrence_integrity(candidate_data)
    candidate_rules = [
        {
            "actionId": row.get("actionId"),
            "actionKey": row.get("actionKey"),
            "backendIdentity": row.get("backendIdentity"),
            "label": row.get("label"),
            "button": row.get("button"),
            "target": row.get("target"),
            "nativeIdentity": row.get("nativeIdentity"),
            "sourceWidgetId": row.get("sourceWidgetId"),
            "allowed": row.get("allowed"),
            "enabled": row.get("enabled"),
            "disabled": row.get("disabled"),
            "entitlementEvaluated": row.get("entitlementEvaluated"),
        }
        for row in ((candidate_data.get("actionContract") or {}).get("actionRuleList") or [])
        if isinstance(row, dict)
        and str(row.get("backendIdentity") or "").startswith(("window_action:", "window_action_ref:"))
    ]
    project_action_integrity.append({
        "action_xmlid": action_xmlid,
        "menu_xmlid": menu_xmlid,
        "action_id": int(candidate_action.id),
        "menu_id": int(candidate_menu.id),
        "ok": bool(getattr(candidate_result, "ok", False)),
        "window_actions": candidate_rules,
        **candidate_integrity,
    })

failed_project_actions = [
    row
    for row in project_action_integrity
    if not row["ok"]
    or any(row[key] for key in ("missing_widgets", "missing_statuses", "missing_descriptors"))
]
if failed_project_actions:
    raise AssertionError("project action Contract V2 occurrence integrity failed: %s" % failed_project_actions)

rules = ((data.get("actionContract") or {}).get("actionRuleList") or [])
record_bound = [
    row for row in rules
    if isinstance(row, dict) and row.get("sourceChannel") == "bound_model_action"
]
if record_bound:
    raise AssertionError("create contract exposed record-bound actions: %s" % [
        row.get("actionId") for row in record_bound
    ])
mode_actions = [
    row for row in rules
    if isinstance(row, dict) and str(row.get("sourceWidgetId") or "").startswith("mode.")
]
if any(row.get("targetScope") != "runtime" for row in mode_actions):
    raise AssertionError("mode-local actions must remain in Contract V2 runtime scope: %s" % [
        {
            "actionId": row.get("actionId"),
            "sourceChannel": row.get("sourceChannel"),
            "sourceWidgetId": row.get("sourceWidgetId"),
            "targetScope": row.get("targetScope"),
            "intent": row.get("intent"),
        }
        for row in mode_actions
    ])
save_actions = [
    row for row in rules
    if isinstance(row, dict) and row.get("actionId") == "form.save"
]
if len(save_actions) != 1:
    raise AssertionError("project create form.save authority is not unique: %s" % save_actions)
save_action = save_actions[0]
if (
    save_action.get("label") != "创建项目"
    or (save_action.get("presentation") or {}).get("tier") != "primary"
):
    raise AssertionError("project create primary action is not governed: %s" % {
        "action": save_action,
        "head": data.get("head"),
        "render_profile": data.get("render_profile"),
        "form_governance": data.get("form_governance"),
    })
field_roles = ((data.get("formStructureContract") or {}).get("fieldRoles") or {})
expected_roles = {
    "intake_next_action_display": "task",
    "intake_blocking_reason_display": "risk",
}
actual_roles = {
    field_name: (field_roles.get(field_name) or {}).get("role")
    for field_name in expected_roles
}
if actual_roles != expected_roles:
    raise AssertionError("project intake semantic roles are incomplete: %s" % actual_roles)
statuses = {
    str(row.get("btnId") or ""): row
    for row in ((data.get("statusContract") or {}).get("buttonStatus") or [])
    if isinstance(row, dict)
}
rows = []
for rule in rules:
    if not isinstance(rule, dict):
        continue
    action_id = str(rule.get("actionId") or "")
    status = statuses.get("btn.%s" % action_id.removeprefix("action."), {})
    row = {
        "actionId": action_id,
        "actionKey": rule.get("actionKey"),
        "label": rule.get("label"),
        "intent": rule.get("intent"),
        "sourceWidgetId": rule.get("sourceWidgetId"),
        "targetScope": rule.get("targetScope"),
        "dispatchMode": rule.get("dispatchMode"),
        "sourceChannel": rule.get("sourceChannel"),
        "presentation": rule.get("presentation"),
        "entitlementEvaluated": rule.get("entitlementEvaluated"),
        "visible": status.get("visible"),
        "disabled": status.get("disabled"),
        "reasonCode": status.get("reasonCode"),
    }
    if (
        str(row.get("sourceWidgetId") or "").startswith("mode.")
        or row.get("sourceChannel") == "governed_platform_action"
        or (row.get("targetScope") == "page" and row.get("visible") is True)
    ):
        rows.append(row)


def _handler_data(handler_class, params):
    result = handler_class(user_env, payload={"params": params}).run(payload={"params": params})
    if isinstance(result, tuple):
        data = result[0] if result and isinstance(result[0], dict) else {}
    else:
        data = result.data if hasattr(result, "data") and isinstance(result.data, dict) else result
    if not isinstance(data, dict) or data.get("ok") is False:
        raise AssertionError("follower handler failed: %r" % (result,))
    return data


follower_journeys = []
for target_record in (project_record, payment_record):
    target_params = {"model": target_record._name, "res_id": int(target_record.id)}
    before = _handler_data(ChatterFollowersListHandler, target_params)
    mutation = "unfollow" if before.get("is_following") else "follow"
    expected_after = mutation == "follow"
    try:
        changed = _handler_data(ChatterFollowersUpdateHandler, {**target_params, "action": mutation})
        after = _handler_data(ChatterFollowersListHandler, target_params)
        if after.get("is_following") is not expected_after:
            raise AssertionError("follower state did not change: %s" % {
                "model": target_record._name, "before": before, "after": after,
            })
    finally:
        restore = "follow" if before.get("is_following") else "unfollow"
        _handler_data(ChatterFollowersUpdateHandler, {**target_params, "action": restore})
    restored = _handler_data(ChatterFollowersListHandler, target_params)
    if restored.get("is_following") is not bool(before.get("is_following")):
        raise AssertionError("follower fixture was not restored: %s" % {
            "model": target_record._name, "before": before, "restored": restored,
        })
    follower_journeys.append({
        "model": target_record._name,
        "record_id": int(target_record.id),
        "mutation": mutation,
        "before": {
            "count": before.get("count"), "is_following": before.get("is_following"),
            "can_follow": before.get("can_follow"), "can_unfollow": before.get("can_unfollow"),
        },
        "after": {
            "count": after.get("count"), "is_following": after.get("is_following"),
        },
        "restored": {
            "count": restored.get("count"), "is_following": restored.get("is_following"),
        },
        "write_result": changed.get("result"),
    })

print("LOCAL_DEV_PROJECT_CREATE_ACTION_SCOPE_JSON=" + json.dumps({
    "database": env.cr.dbname,
    "login": user.login,
    "user_xmlid": user.get_external_id().get(user.id, ""),
    "action_id": int(action.id),
    "menu_id": int(menu.id),
    "project_record_id": int(project_record.id),
    "project_record_xmlid": project_record.get_external_id().get(project_record.id, ""),
    "workspace_action_id": int(workspace_action.id),
    "workspace_menu_id": int(workspace_menu.id),
    "create_occurrence_integrity": create_integrity,
    "readonly_occurrence_integrity": record_integrity,
    "record_collaboration_contract": (
        (record_data.get("runtimeContract") or {}).get("collaboration")
        if isinstance(record_data.get("runtimeContract"), dict)
        else record_data.get("collaboration")
    ),
    "share_action_execute": {
        "actionId": share_rule.get("actionId"),
        "backendIdentity": share_rule.get("backendIdentity"),
        "button": share_rule.get("button"),
        "status": {
            "visible": share_status.get("visible"),
            "disabled": share_status.get("disabled"),
        },
        "entry_target": share_entry_target,
        "record_unchanged": project_fingerprint_before == project_fingerprint_after,
    },
    "project_action_occurrence_integrity": project_action_integrity,
    "payment_action_id": int(payment_action.id),
    "payment_menu_id": int(payment_menu.id),
    "payment_record_id": int(payment_record.id),
    "rules": rows,
    "record_bound_create_actions": len(record_bound),
    "mode_runtime_actions": len(mode_actions),
    "primary_save_action": {
        "actionId": save_action.get("actionId"),
        "label": save_action.get("label"),
        "presentation": save_action.get("presentation"),
    },
    "intake_semantic_roles": actual_roles,
    "follower_journeys": follower_journeys,
}, ensure_ascii=False, sort_keys=True))
