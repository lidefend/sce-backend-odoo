#!/usr/bin/env python3
"""Generate the M0-M3 static menu governance inventory.

This is deliberately a P4, read-only source audit.  It does not connect to Odoo,
infer runtime visibility, or turn proposed taxonomy into product configuration.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MODULE = "smart_construction_core"
MODULE_ROOT = ROOT / "addons" / MODULE
OUT_DIR = ROOT / "docs" / "engineering_convergence" / "menu_governance"
SCOPE_PATH = OUT_DIR / "menu_governance_scope.json"
INVENTORY_PATH = OUT_DIR / "menu_capability_inventory.json"
SUMMARY_PATH = OUT_DIR / "menu_capability_inventory.md"
MAPPING_PATH = OUT_DIR / "menu_migration_mapping.csv"
M4_PATH = OUT_DIR / "menu_m4_governance.json"
M4_SUMMARY_PATH = OUT_DIR / "M4_RUNTIME_AND_MINIMAL_FIX_PLAN.md"
SCHEMA_VERSION = "sce.menu_governance_inventory.v1"
M4_SCHEMA_VERSION = "sce.menu_governance_m4.v1"
PROPOSED_LABELS = {
    f"{MODULE}.menu_sc_leave_request": "请休假审批",
    f"{MODULE}.menu_sc_material_stock_statistics_report": "库存统计",
    f"{MODULE}.menu_sc_project_manage": "项目配置",
    f"{MODULE}.menu_sc_project_wbs_cost": "成本分解结构",
}
PROPOSED_PARENTS = {
    f"{MODULE}.menu_sc_settlement_adjustment": f"{MODULE}.menu_sc_receipt_payment_group",
    f"{MODULE}.menu_sc_settlement_order": f"{MODULE}.menu_sc_receipt_payment_group",
}
TECHNICAL_NAME = re.compile(
    r"(?:\b(?:legacy|runtime|projection|backend|debug|test|temp|v\d+)\b|"
    r"(?:后台|旧版|临时|测试|新)[）)]?$|[_/]|（(?:后台|旧版|临时|测试|新)）)",
    re.IGNORECASE,
)


class InventoryError(RuntimeError):
    """Raised when a source or generated inventory violates a hard invariant."""


@dataclass(frozen=True)
class Declaration:
    xmlid: str
    source_file: str
    source_index: int
    kind: str
    values: dict[str, Any]


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, encoding="utf-8"
    ).strip()


def _qualify(value: str | None) -> str | None:
    if not value:
        return None
    return value if "." in value else f"{MODULE}.{value}"


def _field_values(record: ET.Element) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for field in record.findall("field"):
        name = field.get("name")
        if not name:
            continue
        if field.get("ref"):
            values[name] = field.get("ref")
        elif field.get("eval") is not None:
            expression = field.get("eval") or ""
            if expression.strip() in {"False", "None"}:
                values[name] = False
            elif name == "groups_id":
                values[name] = re.findall(r"ref\(['\"]([^'\"]+)['\"]\)", expression)
            else:
                values[name] = expression
        else:
            values[name] = (field.text or "").strip()
    return values


def _manifest_xml_files() -> list[Path]:
    manifest = ast.literal_eval((MODULE_ROOT / "__manifest__.py").read_text(encoding="utf-8"))
    files = [MODULE_ROOT / item for item in manifest.get("data", []) if item.endswith(".xml")]
    missing = [path.relative_to(ROOT).as_posix() for path in files if not path.is_file()]
    if missing:
        raise InventoryError(f"manifest XML missing: {missing}")
    return files


def _source_sha256(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        rel = path.relative_to(ROOT).as_posix().encode("utf-8")
        digest.update(rel + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def _scope() -> dict[str, Any]:
    scope = json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
    if set(scope) != {"schema_version", "audited_commit_sha", "module", "runtime_sampling"}:
        raise InventoryError("scope config has missing or extra keys")
    sha = scope["audited_commit_sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise InventoryError("audited_commit_sha must be a full lowercase SHA")
    if scope["module"] != MODULE:
        raise InventoryError("scope module mismatch")
    try:
        _git("cat-file", "-e", f"{sha}^{{commit}}")
    except subprocess.CalledProcessError as exc:
        raise InventoryError("audited commit does not exist") from exc
    changed = subprocess.run(
        ["git", "diff", "--quiet", sha, "--", f"addons/{MODULE}"], cwd=ROOT
    )
    if changed.returncode != 0:
        raise InventoryError("audited module differs from frozen commit")
    return scope


def collect() -> dict[str, Any]:
    scope_config = _scope()
    files = _manifest_xml_files()
    all_xml = sorted(MODULE_ROOT.rglob("*.xml"))
    manifest_set = set(files)
    declarations: list[Declaration] = []
    actions: dict[str, dict[str, Any]] = {}
    groups: dict[str, dict[str, Any]] = {}
    menuitem_count = 0

    for load_index, path in enumerate(files):
        rel = path.relative_to(ROOT).as_posix()
        root = ET.parse(path).getroot()
        element_index = 0
        for element in root.iter():
            element_index += 1
            xmlid = element.get("id")
            if element.tag == "menuitem" and xmlid:
                menuitem_count += 1
                values = {
                    "name": element.get("name"),
                    "parent": element.get("parent"),
                    "action": element.get("action"),
                    "groups": element.get("groups"),
                    "sequence": element.get("sequence"),
                    "web_icon": element.get("web_icon"),
                    "active": element.get("active"),
                }
                declarations.append(
                    Declaration(_qualify(xmlid) or "", rel, load_index * 100000 + element_index, "menuitem", values)
                )
            elif element.tag == "record" and xmlid:
                model = element.get("model", "")
                values = _field_values(element)
                qualified = _qualify(xmlid) or ""
                if model == "ir.ui.menu":
                    declarations.append(
                        Declaration(qualified, rel, load_index * 100000 + element_index, "record_patch", values)
                    )
                elif model.startswith("ir.actions."):
                    actions[qualified] = {
                        "action_xmlid": qualified,
                        "model": model,
                        "name": values.get("name"),
                        "res_model": values.get("res_model"),
                        "source_file": rel,
                    }
                elif model == "res.groups":
                    groups[qualified] = {
                        "group_xmlid": qualified,
                        "name": values.get("name"),
                        "source_file": rel,
                    }

    by_id: dict[str, list[Declaration]] = defaultdict(list)
    for declaration in declarations:
        by_id[declaration.xmlid].append(declaration)

    assets: list[dict[str, Any]] = []
    for xmlid in sorted(by_id):
        history = sorted(by_id[xmlid], key=lambda item: item.source_index)
        merged: dict[str, Any] = {}
        field_authority: dict[str, str] = {}
        for declaration in history:
            for key, value in declaration.values.items():
                if value is not None and value != "":
                    merged[key] = value
                    field_authority[key] = declaration.source_file
        parent_value = merged.get("parent_id") if "parent_id" in merged else merged.get("parent")
        parent = _qualify(parent_value) if parent_value is not False else None
        action_value = merged.get("action")
        action = _qualify(action_value) if action_value is not False else None
        raw_groups = merged.get("groups_id") or merged.get("groups") or ""
        group_items = raw_groups if isinstance(raw_groups, list) else str(raw_groups).split(",")
        group_refs = sorted({_qualify(str(item).strip()) for item in group_items if str(item).strip()})
        assets.append(
            {
                "menu_xmlid": xmlid,
                "source_file": history[0].source_file,
                "source_files": sorted({item.source_file for item in history}),
                "declaration_history": [
                    {"kind": item.kind, "source_file": item.source_file, "source_index": item.source_index}
                    for item in history
                ],
                "effective_authority_source": history[-1].source_file,
                "field_authority": {
                    "name": field_authority.get("name"),
                    "parent": field_authority.get("parent_id") or field_authority.get("parent"),
                    "action": field_authority.get("action"),
                    "groups": field_authority.get("groups_id") or field_authority.get("groups"),
                    "sequence": field_authority.get("sequence"),
                },
                "declaration_count": len(history),
                "declaration_kinds": [item.kind for item in history],
                "current_name": merged.get("name") or None,
                "parent_xmlid": parent,
                "sequence": _safe_int(merged.get("sequence")),
                "action_xmlid": action,
                "group_xmlids": group_refs,
                "web_icon": merged.get("web_icon") or None,
                "active_expression": merged.get("active") or None,
                "capability_key": None,
                "capability_status": "unresolved_requires_product_evidence",
                "product_layer": "P1_candidate_or_P2_P3_override_unknown",
                "context": "unknown_until_runtime_or_product_review",
                "audience_roles": [],
                "runtime_visible": None,
                "route_reachable": None,
                "route_evidence": f"odoo-action://{action}" if action else None,
                "proposed_path": None,
                "decision": "investigate",
                "evidence_refs": [],
            }
        )

    asset_map = {item["menu_xmlid"]: item for item in assets}
    depth_errors: list[str] = []
    for asset in assets:
        path, depth, error = _path_for(asset["menu_xmlid"], asset_map)
        asset["current_path"] = path
        asset["hierarchy_depth_including_app_root"] = depth
        app_root_name = asset_map.get(f"{MODULE}.menu_sc_root", {}).get("current_name")
        asset["level"] = max(0, depth - 1) if depth and path and path[0] == app_root_name else depth
        if error:
            depth_errors.append(error)
        action = asset["action_xmlid"]
        asset["action_reference_status"] = _reference_status(action, actions)
        action_asset = actions.get(action or "", {})
        asset["action_type"] = action_asset.get("model")
        asset["action_res_model"] = action_asset.get("res_model")
        asset["parent_reference_status"] = _reference_status(asset["parent_xmlid"], asset_map)
        asset["technical_name_risk"] = bool(asset["current_name"] and TECHNICAL_NAME.search(asset["current_name"]))
        asset["over_depth_risk"] = bool(asset["level"] and asset["level"] > 3)

    menuitem_ids = [_qualify(item.xmlid.split(".", 1)[-1]) for item in declarations if item.kind == "menuitem"]
    duplicates = sorted(xmlid for xmlid, count in Counter(menuitem_ids).items() if count > 1)
    missing_actions = sorted(
        item["menu_xmlid"] for item in assets if item["action_reference_status"] == "missing_local"
    )
    missing_parents = sorted(
        item["menu_xmlid"] for item in assets if item["parent_reference_status"] == "missing_local"
    )
    technical = sorted(item["menu_xmlid"] for item in assets if item["technical_name_risk"])
    over_depth = sorted(item["menu_xmlid"] for item in assets if item["over_depth_risk"])
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    all_rel = [path.relative_to(ROOT).as_posix() for path in all_xml]
    loaded_rel = [path.relative_to(ROOT).as_posix() for path in files]
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": generated_at,
        "source": {
            "repository": "sce-backend-odoo",
            "commit_sha": scope_config["audited_commit_sha"],
            "tree_sha": _git("rev-parse", f"{scope_config['audited_commit_sha']}^{{tree}}"),
            "branch": _git("branch", "--show-current"),
            "module": MODULE,
            "manifest": f"addons/{MODULE}/__manifest__.py",
            "manifest_xml_files": loaded_rel,
            "manifest_xml_sha256": _source_sha256(files),
            "unloaded_xml_files": sorted(set(all_rel) - set(loaded_rel)),
        },
        "scope": {
            "formal_product_layer": "P4",
            "mode": "static_read_only",
            "runtime_sampling": scope_config["runtime_sampling"],
            "runtime_fields_are_unknown": True,
            "writes_product_facts": False,
        },
        "statistics": {
            "manifest_xml_file_count": len(files),
            "all_module_xml_file_count": len(all_xml),
            "menuitem_declaration_count": menuitem_count,
            "unique_menuitem_xmlid_count": len(set(menuitem_ids)),
            "effective_menu_asset_count": len(assets),
            "menu_record_patch_count": len(declarations) - menuitem_count,
            "local_action_count": len(actions),
            "local_group_count": len(groups),
            "duplicate_menuitem_xmlid_count": len(duplicates),
            "missing_local_action_count": len(missing_actions),
            "missing_local_parent_count": len(missing_parents),
            "technical_name_risk_count": len(technical),
            "over_depth_risk_count": len(over_depth),
            "capability_mapping_resolved_count": 0,
            "static_menu_action_group_mapping_count": len(assets),
            "action_bound_menu_count": sum(bool(item["action_xmlid"]) for item in assets),
            "runtime_visibility_verified_count": 0,
        },
        "initial_hypothesis_comparison": {
            "hypothesis": {"menuitem_declarations": 320, "unique_menuitem_xmlids": 304},
            "observed": {"menuitem_declarations": menuitem_count, "unique_menuitem_xmlids": len(set(menuitem_ids))},
            "matches": menuitem_count == 320 and len(set(menuitem_ids)) == 304,
            "effective_asset_note": "ir.ui.menu record patches can add/update assets; therefore effective assets differ from menuitem-only counts",
        },
        "findings": {
            "duplicate_menuitem_xmlids": duplicates,
            "missing_local_actions": missing_actions,
            "missing_local_parents": missing_parents,
            "depth_graph_errors": sorted(set(depth_errors)),
            "technical_name_risks": technical,
            "over_depth_risks": over_depth,
        },
        "coverage": {
            "static_manifest_menu_assets": {"covered": len(assets), "expected": len(assets), "rate": 1.0},
            "static_menu_action_group_mapping": {"covered": len(assets), "expected": len(assets), "rate": 1.0},
            "capability_mapping": {"covered": 0, "expected": len(assets), "rate": 0.0, "reason": "requires product-owner evidence"},
            "runtime_visibility": {"covered": 0, "expected": len(assets), "rate": 0.0, "reason": "isolated runtime lease/auth not available"},
            "route_reachability": {"covered": 0, "expected": len(assets), "rate": 0.0, "reason": "runtime was intentionally not sampled"},
        },
        "actions": [actions[key] for key in sorted(actions)],
        "groups": [groups[key] for key in sorted(groups)],
        "assets": assets,
    }
    validate_inventory(report)
    return report


def build_m4_governance(report: dict[str, Any]) -> dict[str, Any]:
    findings = report["findings"]
    issue_sets = {
        "duplicate_menuitem": set(findings["duplicate_menuitem_xmlids"]),
        "technical_name": set(findings["technical_name_risks"]),
        "over_depth": set(findings["over_depth_risks"]),
    }
    frozen = sorted(set().union(*issue_sets.values()))
    by_id = {item["menu_xmlid"]: item for item in report["assets"]}
    decisions = []
    for xmlid in frozen:
        asset = by_id[xmlid]
        issue_types = sorted(key for key, values in issue_sets.items() if xmlid in values)
        proposed: dict[str, Any] = {
            "change_scope": [],
            "new_name": PROPOSED_LABELS.get(xmlid),
            "new_parent_xmlid": PROPOSED_PARENTS.get(xmlid),
            "duplicate_resolution": None,
            "apply_status": "not_applied_runtime_evidence_required",
        }
        if "technical_name" in issue_types:
            proposed["change_scope"].append("name_only")
        if "over_depth" in issue_types:
            proposed["change_scope"].append("parent_only")
        if "duplicate_menuitem" in issue_types:
            proposed["change_scope"].append("declaration_form_only")
            proposed["duplicate_resolution"] = (
                "preserve_first_menuitem_create_and_convert_later_redeclarations_to_explicit_ir_ui_menu_patches"
            )
        decisions.append(
            {
                "menu_xmlid": xmlid,
                "issue_types": issue_types,
                "formal_product_owner": "P1_smart_construction_core_candidate_pending_product_review",
                "authority": {
                    "effective_source": asset["effective_authority_source"],
                    "field_sources": asset["field_authority"],
                    "load_order_evidence": asset["declaration_history"],
                },
                "current": {
                    "name": asset["current_name"],
                    "path": asset["current_path"],
                    "level": asset["level"],
                    "parent_xmlid": asset["parent_xmlid"],
                    "action_xmlid": asset["action_xmlid"],
                    "action_type": asset["action_type"],
                    "action_res_model": asset["action_res_model"],
                    "group_xmlids": asset["group_xmlids"],
                    "sequence": asset["sequence"],
                },
                "capability_route_mapping": {
                    "capability_status": "structural_anchor_only_runtime_semantics_unverified",
                    "capability_anchor": {
                        "action_xmlid": asset["action_xmlid"],
                        "action_type": asset["action_type"],
                        "res_model": asset["action_res_model"],
                        "group_xmlids": asset["group_xmlids"],
                    },
                    "route_candidate": asset["route_evidence"],
                    "runtime_visible": None,
                    "route_reachable": None,
                    "page_identity_consistent": None,
                },
                "proposed_minimal_change": proposed,
                "compatibility_invariants": {
                    "preserve_menu_xmlid": True,
                    "preserve_action_xmlid": True,
                    "preserve_group_xmlids": True,
                    "preserve_sequence": True,
                    "no_acl_or_record_rule_change": True,
                    "no_frontend_change": True,
                },
                "runtime_evidence": {
                    "status": "BLOCKED_ON_RUNTIME_EVIDENCE",
                    "reason": "18094_reserved_by_list_topic_and_8070_18081_source_sha_mismatch",
                    "required_lease_capability": "env_portability_isolated_runtime_browser_lease",
                    "evidence_refs": [],
                },
                "decision": "investigate",
            }
        )
    m4 = {
        "schema_version": M4_SCHEMA_VERSION,
        "source_inventory_schema_version": report["schema_version"],
        "source_commit_sha": report["source"]["commit_sha"],
        "status": "BLOCKED_ON_RUNTIME_EVIDENCE",
        "scope": {
            "frozen_issue_count": len(frozen),
            "runtime_sampling_performed": False,
            "menu_xml_modified": False,
            "database_write_performed": False,
            "frontend_modified": False,
        },
        "runtime_admission": {
            "accepted_resources": [],
            "rejected_resources": [
                {"resource": "18094", "reason": "reserved_by_active_list_topic_no_exclusive_lease"},
                {"resource": "8070/18081", "reason": "mounted_source_sha_differs_from_frozen_baseline_and_runtime_identity_endpoint_missing"},
            ],
            "required_before_apply": [
                "exclusive_runtime_database_browser_and_evidence_lease",
                "runtime_service_sha_equals_source_commit_sha",
                "read_only_or_isolated_rehearsal_database_role_resolved",
                "role_company_and_route_evidence_complete",
            ],
        },
        "decisions": decisions,
    }
    validate_m4_governance(m4, report)
    return m4


def validate_m4_governance(m4: dict[str, Any], report: dict[str, Any]) -> None:
    if m4.get("schema_version") != M4_SCHEMA_VERSION:
        raise InventoryError("M4 schema_version mismatch")
    expected = set().union(
        set(report["findings"]["duplicate_menuitem_xmlids"]),
        set(report["findings"]["technical_name_risks"]),
        set(report["findings"]["over_depth_risks"]),
    )
    decisions = m4.get("decisions")
    if not isinstance(decisions, list):
        raise InventoryError("M4 decisions must be a list")
    ids = [item.get("menu_xmlid") for item in decisions]
    if len(ids) != len(set(ids)) or set(ids) != expected:
        raise InventoryError("M4 decision set has duplicate, extra or missing frozen assets")
    by_id = {item["menu_xmlid"]: item for item in report["assets"]}
    for decision in decisions:
        xmlid = decision["menu_xmlid"]
        source = by_id[xmlid]
        current = decision.get("current", {})
        if current.get("action_xmlid") != source["action_xmlid"] or current.get("group_xmlids") != source["group_xmlids"]:
            raise InventoryError(f"M4 compatibility snapshot mismatch: {xmlid}")
        authority = decision.get("authority", {})
        if authority.get("effective_source") != source["effective_authority_source"]:
            raise InventoryError(f"M4 authority mismatch: {xmlid}")
        if decision.get("runtime_evidence", {}).get("status") != "BLOCKED_ON_RUNTIME_EVIDENCE":
            raise InventoryError(f"M4 runtime status is not fail-closed: {xmlid}")
        route = decision.get("capability_route_mapping", {})
        if any(route.get(key) is not None for key in ("runtime_visible", "route_reachable", "page_identity_consistent")):
            raise InventoryError(f"M4 contains unproved runtime claim: {xmlid}")
        proposal = decision.get("proposed_minimal_change", {})
        if "technical_name" in decision["issue_types"]:
            new_name = proposal.get("new_name")
            if not new_name or TECHNICAL_NAME.search(new_name):
                raise InventoryError(f"M4 technical-name proposal is invalid: {xmlid}")
        if "over_depth" in decision["issue_types"] and not proposal.get("new_parent_xmlid"):
            raise InventoryError(f"M4 over-depth proposal lacks parent: {xmlid}")
        invariants = decision.get("compatibility_invariants", {})
        if not all(invariants.values()):
            raise InventoryError(f"M4 compatibility invariant weakened: {xmlid}")


def _safe_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(str(value))
    except ValueError:
        return None


def _reference_status(xmlid: str | None, local: dict[str, Any]) -> str:
    if not xmlid:
        return "none"
    if xmlid in local:
        return "resolved_local"
    if not xmlid.startswith(f"{MODULE}."):
        return "external_not_resolved_by_module_audit"
    return "missing_local"


def _path_for(xmlid: str, assets: dict[str, dict[str, Any]]) -> tuple[list[str], int | None, str | None]:
    names: list[str] = []
    current: str | None = xmlid
    seen: set[str] = set()
    while current:
        if current in seen:
            return list(reversed(names)), None, f"parent_cycle:{xmlid}:{current}"
        seen.add(current)
        asset = assets.get(current)
        if not asset:
            break
        names.append(asset.get("current_name") or current)
        current = asset.get("parent_xmlid")
    names.reverse()
    return names, len(names), None


def validate_inventory(report: dict[str, Any]) -> None:
    if report.get("schema_version") != SCHEMA_VERSION:
        raise InventoryError("schema_version mismatch")
    assets = report.get("assets")
    if not isinstance(assets, list):
        raise InventoryError("assets must be a list")
    ids = [item.get("menu_xmlid") for item in assets]
    if any(not isinstance(item, str) or not item for item in ids):
        raise InventoryError("asset has invalid menu_xmlid")
    if len(ids) != len(set(ids)):
        raise InventoryError("duplicate effective menu XML ID")
    expected = report.get("coverage", {}).get("static_manifest_menu_assets", {}).get("expected")
    covered = report.get("coverage", {}).get("static_manifest_menu_assets", {}).get("covered")
    if expected != len(assets) or covered != len(assets):
        raise InventoryError("extra or missing asset in static coverage set")
    for item in assets:
        if item.get("decision") not in {"keep", "rename", "move", "merge", "hide", "retire", "investigate"}:
            raise InventoryError(f"invalid decision for {item['menu_xmlid']}")
        if item.get("runtime_visible") is not None or item.get("route_reachable") is not None:
            if report.get("scope", {}).get("runtime_sampling", "").startswith("not_run"):
                raise InventoryError("runtime claim exists without runtime sampling")


def assert_release_candidate(report: dict[str, Any]) -> None:
    """Fail closed for a future M4+ candidate; M1 findings remain auditable."""
    validate_inventory(report)
    findings = report.get("findings", {})
    blockers = {
        "duplicate_menuitem_xmlids": findings.get("duplicate_menuitem_xmlids", []),
        "missing_local_actions": findings.get("missing_local_actions", []),
        "missing_local_parents": findings.get("missing_local_parents", []),
        "depth_graph_errors": findings.get("depth_graph_errors", []),
        "technical_name_risks": findings.get("technical_name_risks", []),
        "over_depth_risks": findings.get("over_depth_risks", []),
    }
    active = {key: value for key, value in blockers.items() if value}
    if active:
        raise InventoryError(f"menu release candidate has unresolved blockers: {active}")


def _json_bytes(report: dict[str, Any]) -> bytes:
    return (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _summary(report: dict[str, Any]) -> str:
    stats = report["statistics"]
    coverage = report["coverage"]
    return f"""# 菜单能力静态资产账（生成文件）

> 由 `scripts/verify/menu_governance_inventory.py` 生成，禁止人工修改。
> 来源提交：`{report['source']['commit_sha']}`
> 模式：P4 静态只读；运行时可见性和路由可达性均未宣称通过。

## 统计口径

| 指标 | 数量 |
| --- | ---: |
| manifest 加载 XML | {stats['manifest_xml_file_count']} |
| `<menuitem>` 声明 | {stats['menuitem_declaration_count']} |
| 唯一 `<menuitem>` XML ID | {stats['unique_menuitem_xmlid_count']} |
| 合并 `ir.ui.menu` patch 后有效资产 | {stats['effective_menu_asset_count']} |
| 本模块 action | {stats['local_action_count']} |
| 本模块权限组 | {stats['local_group_count']} |
| 重复 `<menuitem>` XML ID 风险 | {stats['duplicate_menuitem_xmlid_count']} |
| 本地 action 断链 | {stats['missing_local_action_count']} |
| 本地 parent 断链 | {stats['missing_local_parent_count']} |
| 技术/临时命名风险 | {stats['technical_name_risk_count']} |
| 超过三级风险 | {stats['over_depth_risk_count']} |

初查假设 320/304：`{'MATCH' if report['initial_hypothesis_comparison']['matches'] else 'DIFF'}`。有效资产数量不同，是因为正式加载链中还包含 `ir.ui.menu` record patch；JSON 保留每个 XML ID 的完整声明历史和来源文件。

## 覆盖率

| 维度 | 覆盖 | 预期 | 比例 | 结论 |
| --- | ---: | ---: | ---: | --- |
| 静态 manifest 菜单资产 | {coverage['static_manifest_menu_assets']['covered']} | {coverage['static_manifest_menu_assets']['expected']} | 100% | 完成 |
| 静态菜单/action/group 链 | {coverage['static_menu_action_group_mapping']['covered']} | {coverage['static_menu_action_group_mapping']['expected']} | 100% | 完成 |
| 能力语义映射 | 0 | {coverage['capability_mapping']['expected']} | 0% | 等待产品证据，不猜测 |
| 运行时角色可见性 | 0 | {coverage['runtime_visibility']['expected']} | 0% | 未取得隔离租约/认证 |
| 路由真实可达性 | 0 | {coverage['route_reachability']['expected']} | 0% | 未运行服务 |

## 使用限制

- 本报告不是正式菜单树，也不是运行时权限证明。
- `decision=investigate` 与空 `proposed_path` 是刻意的失败关闭状态。
- M4 之前必须由产品证据补齐能力、角色、路径及处置决定。
"""


def _mapping_csv(report: dict[str, Any]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow([
        "menu_xmlid", "current_path", "current_name", "action_xmlid", "group_xmlids",
        "level", "technical_name_risk", "proposed_level_1", "proposed_level_2",
        "proposed_level_3", "decision", "product_owner_evidence", "runtime_evidence",
        "migration_compatibility", "unresolved_reason",
    ])
    for item in report["assets"]:
        writer.writerow([
            item["menu_xmlid"], " / ".join(item["current_path"]), item["current_name"] or "",
            item["action_xmlid"] or "", ",".join(item["group_xmlids"]), item["level"] or "",
            str(item["technical_name_risk"]).lower(), "", "", "", "investigate", "", "",
            "preserve_xmlid_action_until_M5", "product_and_runtime_evidence_not_yet_available",
        ])
    return stream.getvalue()


def _m4_summary(m4: dict[str, Any]) -> str:
    issue_counts = Counter(
        issue for decision in m4["decisions"] for issue in decision["issue_types"]
    )
    return f"""# M4：运行时准入与最小修复计划（生成文件）

> 由 `scripts/verify/menu_governance_inventory.py` 生成，禁止人工修改。

## 当前裁决

- 状态：`{m4['status']}`
- 冻结资产：{m4['scope']['frozen_issue_count']}
- 重复 `<menuitem>`：{issue_counts['duplicate_menuitem']}
- 技术/临时命名：{issue_counts['technical_name']}
- 第四级路径：{issue_counts['over_depth']}
- 菜单 XML 修改：否
- 数据库写入：否
- 浏览器/运行时事实声明：否

## 资源准入

- `18094` 属于当前列表专题，缺少独占租约，拒绝使用。
- `8070/18081` 的挂载源码 SHA 与冻结基线不同，且运行时身份端点缺失，拒绝作为证据。
- 后续依赖 env-portability 提供数据库、服务、浏览器 profile 和证据目录的统一独占租约。

## 最小修复边界

- 16 个重复声明仅允许改为显式 `ir.ui.menu` patch 或在运行时等价证明后移除后置重声明；不得重建 XML ID。
- 4 个命名候选仅改变 `name`，不改变 action、groups、sequence 或权限。
- 2 个第四级候选仅改变 parent，使业务深度回到三级；空容器的后续处置另行评审。
- 所有候选在运行时角色、路由、页面身份和兼容证据完成前均保持 `not_applied_runtime_evidence_required`。
"""


def write_outputs(report: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    m4 = build_m4_governance(report)
    INVENTORY_PATH.write_bytes(_json_bytes(report))
    SUMMARY_PATH.write_text(_summary(report), encoding="utf-8")
    MAPPING_PATH.write_text(_mapping_csv(report), encoding="utf-8", newline="")
    M4_PATH.write_text(json.dumps(m4, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    M4_SUMMARY_PATH.write_text(_m4_summary(m4), encoding="utf-8")


def check_outputs(report: dict[str, Any]) -> None:
    m4 = build_m4_governance(report)
    expected = {
        INVENTORY_PATH: _json_bytes(report),
        SUMMARY_PATH: _summary(report).encode("utf-8"),
        MAPPING_PATH: _mapping_csv(report).encode("utf-8"),
        M4_PATH: (json.dumps(m4, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        M4_SUMMARY_PATH: _m4_summary(m4).encode("utf-8"),
    }
    for path, content in expected.items():
        if not path.exists() or path.read_bytes() != content:
            raise InventoryError(f"generated output is stale or missing: {path.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify generated files are current")
    parser.add_argument("--release-candidate", action="store_true", help="apply future M4+ fail-closed rules")
    args = parser.parse_args()
    try:
        report = collect()
        if args.release_candidate:
            assert_release_candidate(report)
        if args.check:
            # Generated timestamp is provenance, so compare after preserving the committed value.
            existing = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
            report["generated_at_utc"] = existing.get("generated_at_utc")
            check_outputs(report)
        else:
            write_outputs(report)
    except (InventoryError, ET.ParseError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[menu-governance] FAIL: {exc}", file=sys.stderr)
        return 2
    print("[menu-governance] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
