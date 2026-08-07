#!/usr/bin/env python3
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]


def records(path: str):
    return {
        row.attrib.get("id"): row
        for row in ET.parse(ROOT / path).getroot().findall("record")
    }


def field_text(record, name: str) -> str:
    field = record.find(f"field[@name='{name}']")
    return "" if field is None else (field.text or field.attrib.get("ref") or field.attrib.get("eval") or "").strip()


actions = records("addons/smart_construction_core/actions/project_list_actions.xml")
project_actions = records("addons/smart_construction_core/actions/project_actions.xml")
overrides = records("addons/smart_construction_core/actions/project_native_action_overrides.xml")
views = records("addons/smart_construction_core/views/core/project_lifecycle_kanban_views.xml")

# fresh_project_ledger_defaults_to_table / table_and_card_modes_available
assert field_text(actions["action_sc_project_list"], "view_mode") == "tree,kanban,form"
assert field_text(overrides["action_sc_project_list_tree_view"], "sequence") == "10"
assert field_text(overrides["action_sc_project_list_kanban_view"], "view_id").endswith("view_sc_project_kanban_card")

# card_label_not_workflow_board: the ledger card projection has no grouping declaration.
card_arch = ET.tostring(views["view_sc_project_kanban_card"], encoding="unicode")
assert "default_group_by" not in card_arch
assert all(name in card_arch for name in ("project_code", "manager_id", "lifecycle_state", "end_date"))

# workflow_board_requires_group_semantics for overview/management.
lifecycle_arch = ET.tostring(views["view_sc_project_kanban_lifecycle"], encoding="unicode")
assert 'default_group_by="lifecycle_state"' in lifecycle_arch
for action_id in ("action_sc_project_overview", "action_sc_project_manage"):
    assert field_text(project_actions[action_id], "view_mode") == "kanban,tree,form"
    assert field_text(project_actions[action_id], "view_id").endswith("view_sc_project_kanban_lifecycle")

# No project/action/menu/role branch is allowed in the P0 frontend semantic resolver.
resolver = (ROOT / "frontend/apps/web/src/app/contracts/actionViewSurfaceContract.ts").read_text(encoding="utf-8")
for forbidden in ("project.project", "action_sc_project_list", "menu_sc_project", "role_code"):
    assert forbidden not in resolver

menu_contract = (ROOT / "addons/smart_core/handlers/ui_contract.py").read_text(encoding="utf-8")
assert "for row in action.view_ids.sorted" in menu_contract
assert "bound_view_id = action_views.get(v)" in menu_contract
assert 'p2["view_type"] = requested_view_type' in menu_contract

dispatcher = (ROOT / "addons/smart_core/app_config_engine/services/dispatchers/action_dispatcher.py").read_text(encoding="utf-8")
assert "p.get('view_type') or info.get('view_mode')" in dispatcher

contract_mixin = (ROOT / "addons/smart_core/app_config_engine/models/contract_mixin.py").read_text(encoding="utf-8")
assert "'kanban'," in contract_mixin
assert "passthrough=k in passthrough_roots" in contract_mixin

print("[collection-view-semantics-guard] PASS")
