"""Read-only probe for governed action scopes on the local.dev project create form."""

import base64
import json
import uuid

from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler
from odoo.addons.smart_core.handlers.execute_button import ExecuteButtonHandler
from odoo.addons.smart_core.handlers.chatter_followers import (
    ChatterFollowersListHandler,
    ChatterFollowersUpdateHandler,
)
from odoo.addons.smart_core.handlers.chatter_timeline import ChatterTimelineHandler


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



def _declared_section_title(node):
    for key in ("title", "string", "label", "semanticTitle"):
        value = str(node.get(key) or "").strip()
        if value:
            return value
    return ""


def _walk_contract_nodes(nodes, visit):
    for node in nodes if isinstance(nodes, list) else []:
        if not isinstance(node, dict):
            continue
        visit(node)
        _walk_contract_nodes(node.get("children"), visit)


def _declared_group_sections(contract):
    """Project the contract-declared native business sections and their fields.

    The record surface must render the sections the contract declares. This is
    the declaration side of the render binding: the browser probe asserts the
    rendered native structure carries exactly these headings and fields.
    """
    sections = []

    def collect(nodes, enclosing):
        for node in nodes if isinstance(nodes, list) else []:
            if not isinstance(node, dict):
                continue
            node_type = str(node.get("type") or "").strip().lower()
            if node_type == "field":
                if enclosing is not None:
                    field_name = str(node.get("name") or "").strip()
                    if field_name:
                        enclosing["fields"].append({
                            "name": field_name,
                            "widget_id": str(node.get("widgetId") or "").strip(),
                        })
                continue
            title = _declared_section_title(node)
            if node_type == "group" and title:
                section = {
                    "name": str(node.get("name") or "").strip(),
                    "title": title,
                    "anchor": str((node.get("attributes") or {}).get("data-sc-anchor") or "").strip(),
                    "fields": [],
                }
                sections.append(section)
                collect(node.get("children"), section)
                continue
            collect(node.get("children"), enclosing)

    collect(((contract.get("layoutContract") or {}).get("containerTree") or []), None)
    return [section for section in sections if section["fields"]]


def _declared_widget_visibility(contract):
    """Project the contract-declared per-occurrence visible status."""
    visibility = {}
    for row in ((contract.get("statusContract") or {}).get("widgetStatus") or []):
        if not isinstance(row, dict):
            continue
        widget_id = str(row.get("widgetId") or "").strip()
        if widget_id:
            visibility[widget_id] = row.get("visible") is not False
    return visibility


def _record_has_display_value(value):
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _declared_notebook_tabs(contract):
    """Project the notebook page labels the contract declares for the surface."""
    tabs = []

    def visit(node):
        if str(node.get("type") or "").strip().lower() != "notebook":
            return
        for page in node.get("children") or []:
            if not isinstance(page, dict):
                continue
            if str(page.get("type") or "").strip().lower() != "page":
                continue
            tabs.append(
                _declared_section_title(page) or str(page.get("name") or "").strip()
            )

    _walk_contract_nodes(((contract.get("layoutContract") or {}).get("containerTree") or []), visit)
    return tabs


def _declared_follower_capability(contract, model_name, record_id):
    """Project the contract-declared follower capability for one record surface.

    This is the declaration side of the follow/unfollow journey. The browser
    probe consumes it together with the live list-intent response instead of a
    follower snapshot, because follow state is per current user and can move
    between the ORM probe and the browser click.
    """
    runtime = contract.get("runtimeContract") if isinstance(contract.get("runtimeContract"), dict) else {}
    collaboration = runtime.get("collaboration") if isinstance(runtime.get("collaboration"), dict) else {}
    if not collaboration:
        collaboration = (
            contract.get("collaboration") if isinstance(contract.get("collaboration"), dict) else {}
        )
    followers = collaboration.get("followers") if isinstance(collaboration.get("followers"), dict) else {}
    if followers.get("enabled") is not True:
        raise AssertionError(
            "follower capability is not declared for %s: %s" % (model_name, followers)
        )
    actions = followers.get("actions") if isinstance(followers.get("actions"), dict) else {}
    follow = actions.get("follow") if isinstance(actions.get("follow"), dict) else {}
    unfollow = actions.get("unfollow") if isinstance(actions.get("unfollow"), dict) else {}
    declaration = {
        "model": model_name,
        "record_id": int(record_id),
        "label": str(followers.get("label") or "").strip(),
        "list_intent": str(followers.get("list_intent") or "").strip(),
        "update_intent": str(followers.get("update_intent") or "").strip(),
        "follow_label": str(follow.get("label") or "").strip(),
        "follow_enabled": follow.get("enabled") is True,
        "unfollow_label": str(unfollow.get("label") or "").strip(),
        "unfollow_enabled": unfollow.get("enabled") is True,
    }
    if (
        declaration["list_intent"] != "chatter.followers.list"
        or declaration["update_intent"] != "chatter.followers.update"
        or not declaration["follow_enabled"]
        or not declaration["unfollow_enabled"]
        or not declaration["follow_label"]
        or not declaration["unfollow_label"]
        or declaration["follow_label"] == declaration["unfollow_label"]
    ):
        raise AssertionError(
            "follower declaration is not governed for %s: %s" % (model_name, declaration)
        )
    return declaration



def _declared_relation_collection(contract, field_name):
    """Project the contract-declared relation collection for one one2many field.

    This is the declaration side of the record relation-area check. The retired
    floorplan relation region no longer exists on the record surface, so the
    browser probe consumes the declared collection (component key, relation,
    capability policies and column count) instead of a region selector.
    """
    layout = contract.get("layoutContract") if isinstance(contract.get("layoutContract"), dict) else {}
    nodes = []

    def visit(node):
        if isinstance(node, list):
            for item in node:
                visit(item)
            return
        if not isinstance(node, dict):
            return
        if (
            str(node.get("type") or "").strip().lower() == "field"
            and str(node.get("name") or node.get("fieldCode") or "").strip() == field_name
        ):
            nodes.append(node)
        visit(node.get("children"))
        visit(node.get("widgetList"))

    visit(layout.get("containerTree") or [])
    if len(nodes) != 1:
        raise AssertionError(
            "declared relation collection %s is not unique: %s" % (field_name, len(nodes))
        )
    node = nodes[0]
    field_info = node.get("fieldInfo") if isinstance(node.get("fieldInfo"), dict) else {}
    subview = field_info.get("subview") if isinstance(field_info.get("subview"), dict) else {}
    policies = subview.get("policies") if isinstance(subview.get("policies"), dict) else {}
    tree = subview.get("tree") if isinstance(subview.get("tree"), dict) else {}
    columns = tree.get("columns") if isinstance(tree.get("columns"), list) else []
    row_actions = tree.get("row_actions") if isinstance(tree.get("row_actions"), list) else []
    declaration = {
        "field": field_name,
        "component_key": str(node.get("componentKey") or "").strip(),
        "relation_model": str(field_info.get("relation") or "").strip(),
        "readonly": node.get("readonly") is True,
        "can_create": policies.get("can_create") is True,
        "can_inline_edit": policies.get("inline_edit") is True,
        "can_unlink": policies.get("can_unlink") is True,
        "column_count": len(columns),
        "row_action_count": len(row_actions),
    }
    if (
        not declaration["component_key"]
        or not declaration["relation_model"]
        or declaration["column_count"] < 1
        or "can_create" not in policies
        or "inline_edit" not in policies
        or "can_unlink" not in policies
    ):
        raise AssertionError(
            "declared relation collection %s is incomplete: %s" % (field_name, declaration)
        )
    # The routed field node mirrors the same policies on its inner widget
    # descriptor; a capability drift between the two is a contract defect.
    def visit_widgets(value):
        if isinstance(value, list):
            for item in value:
                visit_widgets(item)
            return
        if not isinstance(value, dict):
            return
        descriptor = value.get("fieldDescriptor") if isinstance(value.get("fieldDescriptor"), dict) else {}
        nested = descriptor.get("subview") if isinstance(descriptor.get("subview"), dict) else {}
        mirrored = nested.get("policies") if isinstance(nested.get("policies"), dict) else {}
        for key in ("can_create", "inline_edit", "can_unlink"):
            if key in mirrored and mirrored.get(key) != policies.get(key):
                raise AssertionError(
                    "declared relation collection %s mirrors divergent policies: %s"
                    % (field_name, mirrored)
                )
        visit_widgets(value.get("widgetList"))

    visit_widgets(node.get("widgetList"))
    return declaration



user = env.ref("smart_construction_demo.sc_demo_user_test_admin")
action = env.ref("smart_construction_core.action_project_initiation")
menu = env.ref("smart_construction_core.menu_sc_project_initiation")
project_record = env.ref("smart_construction_demo.sc_demo_project_001")
workspace_action = env.ref("smart_construction_core.action_sc_project_list")
workspace_menu = env.ref("smart_construction_core.menu_sc_project_project")
payment_action = env.ref("smart_construction_core.action_payment_request_user_payment_apply")
payment_menu = env.ref("smart_construction_core.menu_sc_user_payment_apply")
# Resolve the governed fixture by its stable xmlid instead of a hardcoded name:
# the managed reset step renames the carrier (DEMO-PR-FLOORPLAN-002, ...) whenever
# the previous carrier already holds ledger history, and it rebinds this xmlid to
# the live record. The probe must walk the declared draft carrier, so a missing,
# renamed-away or non-draft fixture fails closed here instead of timing out in the
# middle of a write journey.
payment_record = env.ref(
    "smart_construction_demo.payment_request_floorplan_demo_record",
    raise_if_not_found=False,
)
if not payment_record or payment_record._name != "payment.request":
    raise RuntimeError(
        "governed payment request DriverHost probe fixture is missing: run "
        "'make local.dev.reset_payment_request_fixture'"
    )
if payment_record.state != "draft":
    raise RuntimeError(
        "governed payment request DriverHost probe fixture is not in its declared draft "
        "state (state=%s): run 'make local.dev.reset_payment_request_fixture'"
        % payment_record.state
    )
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
record_collaboration_contract = (
    (record_data.get("runtimeContract") or {}).get("collaboration")
    if isinstance(record_data.get("runtimeContract"), dict)
    else record_data.get("collaboration")
) or {}
if record_collaboration_contract.get("user_search_intent") != "collaboration.users.search":
    raise AssertionError("project collaboration user search intent was not exact: %s" % record_collaboration_contract)

# The 项目台账 entry is the single project record surface. It must resolve to
# the unified native overview declaration (view_project_overview_form) through
# native authority and must project the declared sections; a notebook tab is
# only asserted when the declaration itself declares one.
workspace_payload = {
    **payload,
    "action_id": int(workspace_action.id),
    "menu_id": int(workspace_menu.id),
    "record_id": int(project_record.id),
    "render_profile": "readonly",
}
workspace_result = UiContractV2Handler(user_env, payload=workspace_payload).run(payload=workspace_payload)
workspace_data = (
    workspace_result.data
    if hasattr(workspace_result, "data") and isinstance(workspace_result.data, dict)
    else {}
)
if not getattr(workspace_result, "ok", False):
    raise RuntimeError("project workspace Contract V2 failed: %s" % workspace_result)
workspace_structure_contract = workspace_data.get("formStructureContract") or {}
workspace_governance = (
    (workspace_structure_contract.get("sourceAuthority") or {}).get("governance_source") or {}
)
overview_view = env.ref("smart_construction_core.view_project_overview_form")
if (
    workspace_governance.get("formStructureAuthority") != "native_authority"
    or workspace_structure_contract.get("layoutPolicy") != "container_tree_authority"
    or workspace_structure_contract.get("mode") != "native_structured_form"
    or int(workspace_governance.get("resolvedViewId") or 0) != int(overview_view.id)
):
    raise AssertionError("project workspace is not projected from the unified overview declaration: %s" % {
        "form_structure_authority": workspace_governance.get("formStructureAuthority"),
        "layout_policy": workspace_structure_contract.get("layoutPolicy"),
        "mode": workspace_structure_contract.get("mode"),
        "resolved_view_id": workspace_governance.get("resolvedViewId"),
        "overview_view_id": overview_view.id,
    })
workspace_sections = _declared_group_sections(workspace_data)
if not workspace_sections:
    raise AssertionError(
        "project workspace declaration exposed no native business sections: %s"
        % (workspace_structure_contract.get("objectProfile") or {})
    )
# The record surface renders the declared sections; within a declared section the
# readonly fact rule omits only empty, non-relation facts. The browser probe must
# therefore require every declared-and-visible field that carries a value on this
# record, and must reject any rendered field that the declaration does not place
# there. Both bounds come from the declaration plus the record, not from a
# hardcoded field list.
workspace_visibility = _declared_widget_visibility(workspace_data)
workspace_field_names = [
    field["name"] for section in workspace_sections for field in section["fields"]
]
workspace_row = project_record.read(workspace_field_names)[0]
for section in workspace_sections:
    for field in section["fields"]:
        field["visible"] = workspace_visibility.get(field["widget_id"], True)
        field["valued"] = _record_has_display_value(workspace_row.get(field["name"]))
    section["must_render_fields"] = [
        field["name"] for field in section["fields"] if field["visible"] and field["valued"]
    ]
workspace_structure_projection = {
    "form_structure_authority": workspace_governance.get("formStructureAuthority"),
    "layout_policy": workspace_structure_contract.get("layoutPolicy"),
    "mode": workspace_structure_contract.get("mode"),
    "resolved_view_id": int(workspace_governance.get("resolvedViewId") or 0),
    "notebook_tabs": _declared_notebook_tabs(workspace_data),
    "sections": workspace_sections,
}

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
form_structure_contract = data.get("formStructureContract") or {}
governance_source = (
    (form_structure_contract.get("sourceAuthority") or {}).get("governance_source") or {}
)
field_roles = form_structure_contract.get("fieldRoles") or {}
expected_roles = {
    "intake_next_action_display": "task",
    "intake_blocking_reason_display": "risk",
}
expected_anchor_groups = {
    "intake_next_action_display": "current_task",
    "intake_blocking_reason_display": "intake_risk",
}
actual_roles = {}
anchor_groups = {}
anchor_sections = {}
# U-C4 G12 retired the entry-level structure declaration for 项目立项 (724 /
# view 1503): the resolved native view owns field placement, so the contract
# projects formStructureAuthority=native_authority with
# layoutPolicy=container_tree_authority / mode=native_structured_form and the
# compatibility re-layout that produced fieldRoles is closed. The declared
# business-group identity (current_task / intake_risk) is carried by the native
# arch data-sc-anchor groups and must be projected through the container tree.
# Assert the carrier the declaration actually names instead of the retired one;
# do not re-open the closed re-layout and do not drop the coverage.
if governance_source.get("formStructureAuthority") == "native_authority":
    if (
        form_structure_contract.get("layoutPolicy") != "container_tree_authority"
        or form_structure_contract.get("mode") != "native_structured_form"
    ):
        raise AssertionError("project intake native authority is not projected: %s" % {
            "form_structure_authority": governance_source.get("formStructureAuthority"),
            "layout_policy": form_structure_contract.get("layoutPolicy"),
            "mode": form_structure_contract.get("mode"),
        })
    if field_roles or governance_source.get("fieldSemanticRoles"):
        raise AssertionError("project intake re-opened the retired compatibility layout: %s" % {
            "field_roles": field_roles,
            "field_semantic_roles": governance_source.get("fieldSemanticRoles"),
        })

    def _section_label(node):
        for key in ("title", "string", "label"):
            label = str(node.get(key) or "").strip()
            if label:
                return label
        return ""

    def _collect_anchor_groups(nodes, enclosing=None):
        for node in nodes if isinstance(nodes, list) else []:
            if not isinstance(node, dict):
                continue
            node_type = str(node.get("type") or "").strip().lower()
            node_name = str(node.get("name") or "").strip()
            if node_type == "field":
                if node_name in expected_anchor_groups and node_name not in anchor_groups:
                    anchor_groups[node_name] = enclosing[0] if enclosing else ""
                    if enclosing:
                        anchor_sections[enclosing[0]] = enclosing[1]
                continue
            _collect_anchor_groups(
                node.get("children"),
                (node_name, _section_label(node)) if node_type == "group" else enclosing,
            )

    _collect_anchor_groups((data.get("layoutContract") or {}).get("containerTree") or [])
    if anchor_groups != expected_anchor_groups:
        raise AssertionError("project intake native semantic anchors are incomplete: %s" % anchor_groups)
    if any(not label for label in anchor_sections.values()):
        raise AssertionError("project intake native section headings are not declared: %s" % anchor_sections)
else:
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
        raise AssertionError("collaboration handler failed: %r" % (result,))
    return data


payment_record_payload = {
    **payload,
    "action_id": int(payment_action.id),
    "menu_id": int(payment_menu.id),
    "record_id": int(payment_record.id),
    "render_profile": "readonly",
}
payment_record_result = UiContractV2Handler(user_env, payload=payment_record_payload).run(
    payload=payment_record_payload
)
payment_record_data = (
    payment_record_result.data
    if hasattr(payment_record_result, "data") and isinstance(payment_record_result.data, dict)
    else {}
)
if not getattr(payment_record_result, "ok", False):
    raise RuntimeError("payment request Contract V2 failed: %s" % payment_record_result)
payment_record_integrity = _layout_occurrence_integrity(payment_record_data)
if any(
    payment_record_integrity[key]
    for key in ("missing_widgets", "missing_statuses", "missing_descriptors")
):
    raise AssertionError(
        "payment request Contract V2 occurrence integrity failed: %s" % payment_record_integrity
    )

# The record relation area consumes the declared detail collection instead of
# the retired floorplan relation region. The browser probe binds the rendered
# relation field to this declaration.
payment_detail_declaration = [
    _declared_relation_collection(payment_record_data, "outflow_line_ids"),
]

# The follow/unfollow journey is declared by the contract (intents + action
# labels) and resolved against the live per-user list authority in the browser.
# The handler round-trip below stays as backend evidence only; it deliberately
# does not become the browser expectation, because follower state is per current
# user and a captured snapshot can go stale before the browser clicks.
# The declaration is bound to the surface the browser journeys actually load:
# the 项目台账 workspace entry (519) for project.project and the user payment
# apply entry (809) for payment.request.
follower_declaration = [
    _declared_follower_capability(workspace_data, project_record._name, project_record.id),
    _declared_follower_capability(payment_record_data, payment_record._name, payment_record.id),
]

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

attachment_delete_journeys = []
for target_record in (project_record, payment_record):
    fixture_name = "codex-delete-journey-%s-%s.txt" % (
        target_record._name.replace(".", "-"),
        uuid.uuid4().hex[:10],
    )
    attachment = user_env["ir.attachment"].create({
        "name": fixture_name,
        "type": "binary",
        "mimetype": "text/plain",
        "datas": base64.b64encode(("temporary %s attachment" % target_record._name).encode("utf-8")),
        "res_model": target_record._name,
        "res_id": int(target_record.id),
    })
    timeline = _handler_data(ChatterTimelineHandler, {
        "model": target_record._name,
        "res_id": int(target_record.id),
        "limit": 80,
        "include_audit": False,
    })
    row = next((
        item for item in timeline.get("items", [])
        if isinstance(item, dict)
        and item.get("type") == "attachment"
        and int((item.get("attachment") or {}).get("id") or 0) == int(attachment.id)
    ), None)
    if not row or (row.get("attachment") or {}).get("can_delete") is not True:
        raise AssertionError("attachment delete authority was not projected: %s" % {
            "model": target_record._name, "attachment_id": attachment.id, "row": row,
        })
    if (row.get("attachment") or {}).get("delete_intent") != "chatter.attachment.delete":
        raise AssertionError("attachment delete intent was not exact: %s" % row)
    if (row.get("attachment") or {}).get("download_intent") != "file.download":
        raise AssertionError("attachment download intent was not exact: %s" % row)
    attachment_delete_journeys.append({
        "model": target_record._name,
        "record_id": int(target_record.id),
        "attachment_id": int(attachment.id),
        "name": fixture_name,
        "can_delete": True,
        "delete_intent": "chatter.attachment.delete",
        "download_intent": "file.download",
    })

message_delete_journeys = []
for target_record in (project_record, payment_record):
    fixture_body = "codex-message-delete-journey-%s-%s" % (
        target_record._name.replace(".", "-"),
        uuid.uuid4().hex[:10],
    )
    message = user_env["mail.message"].with_context(
        mail_create_nosubscribe=True,
        mail_notify_noemail=True,
        mail_notify_force_send=False,
        mail_post_autofollow=False,
        tracking_disable=True,
    ).create({
        "model": target_record._name,
        "res_id": int(target_record.id),
        "body": "<p>%s</p>" % fixture_body,
        "subject": "消息删除旅程",
        "message_type": "comment",
        "subtype_id": int(env.ref("mail.mt_comment").id),
        "author_id": int(user.partner_id.id),
        "email_from": "%s@example.invalid" % (user.login or "demo-user"),
    })
    timeline = _handler_data(ChatterTimelineHandler, {
        "model": target_record._name,
        "res_id": int(target_record.id),
        "limit": 80,
        "include_audit": False,
    })
    row = next((
        item for item in timeline.get("items", [])
        if isinstance(item, dict)
        and item.get("type") == "message"
        and int((item.get("message") or {}).get("id") or 0) == int(message.id)
    ), None)
    if not row or (row.get("message") or {}).get("can_delete") is not True:
        raise AssertionError("message delete authority was not projected: %s" % {
            "model": target_record._name, "message_id": message.id, "row": row,
        })
    if (row.get("message") or {}).get("delete_intent") != "chatter.message.delete":
        raise AssertionError("message delete intent was not exact: %s" % row)
    if (row.get("message") or {}).get("can_reply") is not True:
        raise AssertionError("message reply authority was not projected: %s" % row)
    if (row.get("message") or {}).get("reply_intent") != "chatter.post":
        raise AssertionError("message reply intent was not exact: %s" % row)
    message_delete_journeys.append({
        "model": target_record._name,
        "record_id": int(target_record.id),
        "message_id": int(message.id),
        "body": fixture_body,
        "can_delete": True,
        "delete_intent": "chatter.message.delete",
        "can_reply": True,
        "reply_intent": "chatter.post",
        "reply_body": "%s-reply" % fixture_body,
    })

activity_cancel_journeys = []
activity_type = env.ref("mail.mail_activity_data_todo")
for target_record in (project_record, payment_record):
    fixture_summary = "codex-activity-cancel-journey-%s-%s" % (
        target_record._name.replace(".", "-"),
        uuid.uuid4().hex[:10],
    )
    activity = user_env["mail.activity"].create({
        "activity_type_id": int(activity_type.id),
        "summary": fixture_summary,
        "note": "temporary governed activity cancellation fixture",
        "date_deadline": "2026-12-31",
        "res_model_id": int(env["ir.model"]._get_id(target_record._name)),
        "res_id": int(target_record.id),
        "user_id": int(user.id),
    })
    timeline = _handler_data(ChatterTimelineHandler, {
        "model": target_record._name,
        "res_id": int(target_record.id),
        "limit": 80,
        "include_audit": False,
    })
    row = next((
        item for item in timeline.get("items", [])
        if isinstance(item, dict)
        and item.get("type") == "activity"
        and int((item.get("activity") or {}).get("id") or 0) == int(activity.id)
    ), None)
    if not row or (row.get("activity") or {}).get("can_cancel") is not True:
        raise AssertionError("activity cancel authority was not projected: %s" % {
            "model": target_record._name, "activity_id": activity.id, "row": row,
        })
    if (row.get("activity") or {}).get("update_intent") != "chatter.activity.update":
        raise AssertionError("activity update intent was not exact: %s" % row)
    if "can_edit" in (row.get("activity") or {}) or "can_delete" in (row.get("activity") or {}):
        raise AssertionError("activity projection retained ghost capabilities: %s" % row)
    activity_cancel_journeys.append({
        "model": target_record._name,
        "record_id": int(target_record.id),
        "activity_id": int(activity.id),
        "summary": fixture_summary,
        "can_cancel": True,
        "update_intent": "chatter.activity.update",
    })

# The browser runs in a separate Odoo transaction. Persist only these uniquely
# prefixed fixtures; the shell wrapper's EXIT trap removes any survivor.
env.cr.commit()

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
    "record_collaboration_contract": record_collaboration_contract,
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
    "workspace_structure_contract": workspace_structure_projection,
    "intake_semantic_contract": {
        "form_structure_authority": governance_source.get("formStructureAuthority"),
        "layout_policy": form_structure_contract.get("layoutPolicy"),
        "mode": form_structure_contract.get("mode"),
        "field_roles": field_roles,
        "anchor_groups": anchor_groups,
        "anchor_sections": anchor_sections,
        "roles": actual_roles,
    },
    "payment_record_occurrence_integrity": payment_record_integrity,
    "payment_detail_declaration": payment_detail_declaration,
    "follower_declaration": follower_declaration,
    "follower_journeys": follower_journeys,
    "attachment_delete_journeys": attachment_delete_journeys,
    "message_delete_journeys": message_delete_journeys,
    "activity_cancel_journeys": activity_cancel_journeys,
}, ensure_ascii=False, sort_keys=True))
