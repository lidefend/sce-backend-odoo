#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import re
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BOUNDARY_MODULE_PATH = ROOT / "addons" / "smart_core" / "utils" / "backend_contract_boundaries.py"

# 一份契约，多终端消费。契约必须是终端无关的：业务语义只有一个权威，受管布局语义也
# 只有一个权威，Web、移动 App 等终端各自从同一份契约派生自己的呈现。
#
# 「契约不表达外观」不等于「契约不表达布局」。布局本来就是契约体系里合法的一层：
# 原生视图 arch 投影与低代码呈现配置通过 unified_page_contract_v2.layoutContract
# （containerTree / listProfile / pivotProfile）、layoutType、layoutHints，以及
# view_orchestration.views.form 的 sections[] 表达字段顺序、分组、显隐、列集合与
# 受管尺寸档位。MANAGED_LAYOUT_CHANNEL_KEYS 登记的就是这一层，本规则不禁它。
#
# 本规则只禁那些把契约拉回单一终端实现的载荷：原始视觉值、DOM/CSS 通道、设计系统
# 内部取值、客户端可访问性属性。它们一旦进入契约，其他终端就只能照抄某一个终端的实现。
CONTRACT_APPEARANCE_PATTERNS = (
    re.compile(
        r'"(?:font_size|font_weight|line_height|border_radius|borderRadius|box_shadow'
        r'|boxShadow|z_index|zIndex|background_color|backgroundColor)"\s*:'
    ),
    re.compile(
        r'"(?:css_class|dom_selector|appearance|density|breakpoint|theme|selector'
        r'|aria_label|ariaLabel|css)"\s*:'
    ),
    re.compile(r'"aria-[a-z-]+"\s*:'),
    re.compile(r'"role"\s*:'),
    re.compile(r"style\s*=\s*['\"]"),
    re.compile(r"<div\b"),
    re.compile(r"\bv-if\b|\bv-for\b|@click"),
    re.compile(r"\bScTable\b|\bt-form__"),
)


# 受管布局契约通道的键。它们是合法契约内容：终端无关的布局语义，不是外观。这里登记
# 后由 self_check 保证任何一条都不会被上面的外观规则命中；布局键与外观键不同名，因此
# 不需要逐行白名单过滤。
MANAGED_LAYOUT_CHANNEL_KEYS = (
    "layout",
    "layoutContract",
    "layoutType",
    "layoutHints",
    "layoutNode",
    "containerTree",
    "listProfile",
    "pivotProfile",
    "sections",
    "zone",
    "block",
    "visible",
    "sequence",
    "group_title",
    "columns",
    "cols",
    "width",
    "class",
    "spanClass",
    "field_size",
)

# 多终端边界：契约一旦带上终端标识维度，同一份契约就开始按终端分叉，其他终端只能跟随
# 某个终端的实现。终端的组件选择、密度、断点、可访问性与导航由各终端设计系统自己决定，
# 从同一份契约派生，不写回契约。
#
# 唯一的非契约用途是配置工作台的草稿预览作用域（preview token 绑定 device 仅用于预览），
# 它属于 runtime carrier，不进入已发布契约，因此规则不针对裸 device 键，只针对
# 「终端标识作为契约维度」和「终端取值直接写进契约载荷」。
TERMINAL_BOUND_CONTRACT_PATTERNS = (
    re.compile(
        r'"(?:terminal|render_target|client_kind|device_kind|viewport|viewport_kind'
        r'|device_variants|device_overrides|by_device|per_device|terminal_overrides'
        r'|by_terminal|per_terminal|responsive_overrides)"\s*:'
    ),
    re.compile(
        r'"(?:device|platform|terminal|viewport)"\s*:\s*[\'"](?:desktop|tablet|mobile|h5|ios|android|web)[\'"]'
    ),
)


def scan_contract_appearance(text: str, rel: str) -> list[dict]:
    """Return the appearance/structure leaks found in one contract writer.

    只针对单一终端实现进入契约的载荷。受管布局通道（MANAGED_LAYOUT_CHANNEL_KEYS）
    是合法契约层，不会被本规则命中，并由 managed_layout_channel_conflicts() 自检。
    """
    found = []
    for pattern in CONTRACT_APPEARANCE_PATTERNS:
        for match in pattern.finditer(text):
            found.append({
                "category": "contract_must_not_express_appearance",
                "path": rel,
                "line": text[:match.start()].count("\n") + 1,
                "message": "contract payload expresses client appearance/structure: %s"
                           % match.group(0),
            })
    return found


def scan_terminal_bound_contract(text: str, rel: str) -> list[dict]:
    """Return the terminal-bound leaks found in one contract writer."""
    found = []
    for pattern in TERMINAL_BOUND_CONTRACT_PATTERNS:
        for match in pattern.finditer(text):
            found.append({
                "category": "contract_must_stay_terminal_agnostic",
                "path": rel,
                "line": text[:match.start()].count("\n") + 1,
                "message": "contract payload binds the contract to one terminal: %s"
                           % match.group(0),
            })
    return found


def managed_layout_channel_conflicts() -> list[dict]:
    """Return managed layout keys that the appearance rule would wrongly reject.

    The layout contract is a legal, terminal-agnostic contract layer, so the two rule
    sets must never overlap. A non-empty result means an edit made the appearance rule
    outlaw part of the layout contract.
    """
    conflicts = []
    for key in MANAGED_LAYOUT_CHANNEL_KEYS:
        leaks = scan_contract_appearance('"%s": 1,' % key, "managed-layout-channel")
        if leaks:
            conflicts.append({
                "category": "appearance_rule_outlaws_layout_contract",
                "key": key,
                "message": "the appearance rule matches the managed layout contract key: %s" % key,
            })
    return conflicts


def _load_boundary_constants() -> dict:
    spec = importlib.util.spec_from_file_location("backend_contract_boundaries", BOUNDARY_MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return {
        "LOWCODE_SOURCE_STATUS_TENANT_RUNTIME": module.LOWCODE_SOURCE_STATUS_TENANT_RUNTIME,
        "LOWCODE_SYSTEM_CONFIG_MENU_XMLIDS": module.LOWCODE_SYSTEM_CONFIG_MENU_XMLIDS,
        "VIEW_ORCHESTRATION_SOURCE_FIELD_POLICY": module.VIEW_ORCHESTRATION_SOURCE_FIELD_POLICY,
        "MENU_ORCHESTRATION_SOURCE_TENANT_LOWCODING": module.MENU_ORCHESTRATION_SOURCE_TENANT_LOWCODING,
        "MENU_CONFIG_POLICY_MODEL": module.MENU_CONFIG_POLICY_MODEL,
        "APPROVAL_POLICY_SOURCE_TENANT_LOWCODING": module.APPROVAL_POLICY_SOURCE_TENANT_LOWCODING,
    }


BOUNDARY_CONSTANTS = _load_boundary_constants()
ALLOWED_DIRECT_CONTRACT_WRITERS = {
    "addons/smart_core/model/ui_business_config_contract.py": {
        "layer": "L1",
        "boundary": "contract_infrastructure",
        "reason": "owns ui.business.config.contract persistence and versioning",
        "expected_source": "n/a",
    },
    "addons/smart_core/handlers/form_field_configuration.py": {
        "layer": "L4",
        "boundary": "form_lowcode_runtime_config",
        "reason": "mirrors form field low-code edits into view orchestration contracts",
        "expected_source": BOUNDARY_CONSTANTS["VIEW_ORCHESTRATION_SOURCE_FIELD_POLICY"],
    },
    "addons/smart_core/handlers/menu_configuration.py": {
        "layer": "L4",
        "boundary": "menu_lowcode_runtime_config",
        "reason": "mirrors menu low-code edits into menu orchestration contracts",
        "expected_source": BOUNDARY_CONSTANTS["MENU_ORCHESTRATION_SOURCE_TENANT_LOWCODING"],
    },
    "addons/smart_core/handlers/business_config_change_set.py": {
        "layer": "L1/L4",
        "boundary": "atomic_lowcode_change_set_publish",
        "reason": "atomically publishes validated reversible low-code contract items and owns batch rollback",
        "expected_source": "ui.business.config.change.set",
    },
    "addons/smart_construction_core/models/support/formal_list_contract_sync.py": {
        "layer": "L2",
        "boundary": "industry_formal_list_contract_projection",
        "reason": "upgrades released industry list contracts from transition fields to formal product fields",
        "expected_source": "smart_construction_core.formal_settlement_list_contract_sync",
    },
    "addons/smart_construction_core/migrations/17.0.0.61/post-migration.py": {
        "layer": "L2",
        "boundary": "industry_stale_contract_scope_cleanup_migration",
        "reason": "archives stale action-scoped business config contracts whose action model no longer matches the contract model",
        "expected_source": "smart_construction_core.stale_contract_scope_cleanup",
    },
    "addons/smart_construction_core/hooks.py": {
        "layer": "L2",
        "boundary": "industry_install_contract_source_status_normalization",
        "reason": "normalizes source status on industry contracts during install through the append-only contract lifecycle authority",
        "expected_source": "smart_construction_core.post_init_lowcode_source_status",
    },
}
ALLOWED_APPROVAL_POLICY_RUNTIME_WRITERS = {
    "addons/smart_construction_core/handlers/approval_policy_configuration.py": {
        "layer": "L2/L4",
        "boundary": "approval_policy_runtime_configuration",
        "reason": "business configuration UI writes industry approval policy runtime records",
        "expected_source": BOUNDARY_CONSTANTS["APPROVAL_POLICY_SOURCE_TENANT_LOWCODING"],
        "target_models": ["sc.approval.policy", "sc.approval.step"],
    },
}
ALLOWED_LOWCODING_POLICY_RUNTIME_WRITERS = {
    "addons/smart_core/handlers/business_config_change_set.py": {
        "layer": "L1/L4",
        "boundary": "atomic_menu_change_set_publish",
        "reason": "applies menu policy rows only inside the unified change-set transaction",
        "expected_source": "ui.business.config.change.set",
        "target_models": ["ui.menu.config.policy"],
    },
    "addons/smart_core/handlers/form_field_configuration.py": {
        "layer": "L4",
        "boundary": "form_field_policy_runtime_configuration",
        "reason": "business configuration UI writes form field runtime policies",
        "expected_source": BOUNDARY_CONSTANTS["VIEW_ORCHESTRATION_SOURCE_FIELD_POLICY"],
        "target_models": ["ui.form.field.policy"],
    },
    "addons/smart_core/handlers/menu_configuration.py": {
        "layer": "L4",
        "boundary": "menu_config_policy_runtime_configuration",
        "reason": "business configuration UI writes menu runtime policies",
        "expected_source": BOUNDARY_CONSTANTS["MENU_ORCHESTRATION_SOURCE_TENANT_LOWCODING"],
        "target_models": ["ui.menu.config.policy"],
    },
    "addons/smart_construction_core/models/support/product_policy_sync.py": {
        "layer": "L2",
        "boundary": "industry_product_menu_policy_projection",
        "reason": "industry product policy sync writes baseline menu visibility overlays",
        "expected_source": "smart_construction_core.product_policy_sync",
        "target_models": ["ui.menu.config.policy"],
    },
    "addons/smart_construction_core/migrations/17.0.0.61/post-migration.py": {
        "layer": "L2",
        "boundary": "industry_product_menu_policy_baseline_migration",
        "reason": "normalizes legacy config menu labels in released menu runtime policies during industry module upgrade",
        "expected_source": "smart_construction_core.config_center_label_migration",
        "target_models": ["ui.menu.config.policy"],
    },
}

def _is_contract_writer(text: str) -> bool:
    if "ui.business.config.contract" not in text:
        return False
    write_markers = (
        "Contract.create(",
        "contract.write(",
        "rec.write(",
        "rec.action_publish(",
        "contract.action_publish(",
        "rec.replace_and_publish(",
        "contract.replace_and_publish(",
        "rec.restore_published_version(",
    )
    return any(marker in text for marker in write_markers)


def _is_approval_policy_runtime_writer(text: str) -> bool:
    if "sc.approval.policy" not in text and "sc.approval.step" not in text:
        return False
    write_markers = (
        "Policy.create(",
        "policy.write(",
        "Step.create(",
        "step.write(",
        "_step_writer(",
    )
    return any(marker in text for marker in write_markers)


def _is_lowcoding_policy_runtime_writer(text: str) -> bool:
    uses_menu_policy_constant_writer = any(
        marker in text
        for marker in (
            "Policy = env[MENU_CONFIG_POLICY_MODEL]",
            "Policy = self.env[MENU_CONFIG_POLICY_MODEL]",
        )
    )
    if (
        "ui.form.field.policy" not in text
        and "ui.menu.config.policy" not in text
        and not uses_menu_policy_constant_writer
    ):
        return False
    write_markers = (
        'self.env["ui.form.field.policy"].create(',
        'self.env["ui.menu.config.policy"].create(',
        "Policy.create(",
        "policy.write(",
    )
    return any(marker in text for marker in write_markers)


BOUNDARY_RULES = [
    {
        "category": "business_config_contract",
        "report_key": "allowed_direct_contract_writers",
        "rows_key": "contract_writers",
        "count_key": "contract_writer_count",
        "predicate": _is_contract_writer,
        "allowed": ALLOWED_DIRECT_CONTRACT_WRITERS,
        "error_message": "direct ui.business.config.contract writer must go through an approved backend boundary",
    },
    {
        "category": "approval_policy_runtime",
        "report_key": "allowed_approval_policy_runtime_writers",
        "rows_key": "approval_policy_writers",
        "count_key": "approval_policy_writer_count",
        "predicate": _is_approval_policy_runtime_writer,
        "allowed": ALLOWED_APPROVAL_POLICY_RUNTIME_WRITERS,
        "error_message": "direct approval policy runtime writer must go through the approved approval policy configuration boundary",
    },
    {
        "category": "lowcoding_policy_runtime",
        "report_key": "allowed_lowcoding_policy_runtime_writers",
        "rows_key": "lowcoding_policy_writers",
        "count_key": "lowcoding_policy_writer_count",
        "predicate": _is_lowcoding_policy_runtime_writer,
        "allowed": ALLOWED_LOWCODING_POLICY_RUNTIME_WRITERS,
        "error_message": "direct low-code runtime policy writer must go through an approved business configuration boundary",
    },
]

REQUIRED_BOUNDARY_MARKERS = {
    "addons/smart_core/handlers/form_field_configuration.py": [
        "formal_authority\": \"ui.business.config.contract.view_orchestration",
        "compatibility_write\": \"ui.form.field.policy",
        "已阻止兼容策略表单独生效",
        "def _write_lowcode_form_contract_or_error(",
        "LOWCODE_SOURCE_STATUS_TENANT_RUNTIME",
    ],
    "addons/smart_core/handlers/menu_configuration.py": [
        "contract_source\": MENU_ORCHESTRATION_SOURCE_TENANT_LOWCODING",
        "lowcode_boundary\": \"menu_config",
        "MENU_CONFIG_SCOPE_VIOLATION",
        "LOWCODE_SOURCE_STATUS_TENANT_RUNTIME",
    ],
    "addons/smart_core/model/ui_menu_config_policy.py": [
        "LOWCODE_SYSTEM_CONFIG_MENU_XMLIDS",
    ],
}


def _scan_allowed_boundary(
    *,
    category: str,
    predicate,
    allowed: dict[str, dict],
    error_message: str,
) -> tuple[list[dict], list[dict]]:
    rows = []
    errors = []
    for path in sorted((ROOT / "addons").rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if "/tests/" in rel:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="ignore")
        if not predicate(text):
            continue
        metadata = allowed.get(rel) or {}
        allowed_writer = bool(metadata)
        row = {"category": category, "path": rel, "allowed": allowed_writer, **metadata}
        rows.append(row)
        if not allowed_writer:
            errors.append({"category": category, "path": rel, "message": error_message})
    return rows, errors


def build_report() -> dict:
    rows_by_key = {}
    errors = []
    writer_rows = []
    report = {"guard": "backend_contract_boundary_guard", "schema_version": "1.0"}
    for rule in BOUNDARY_RULES:
        allowed = rule["allowed"]
        rows, rule_errors = _scan_allowed_boundary(
            category=rule["category"],
            predicate=rule["predicate"],
            allowed=allowed,
            error_message=rule["error_message"],
        )
        rows_by_key[rule["rows_key"]] = rows
        writer_rows.extend(rows)
        errors.extend(rule_errors)
        report[rule["report_key"]] = [
            {"path": path, **metadata}
            for path, metadata in sorted(allowed.items())
        ]
        report[rule["count_key"]] = len(rows)

    unique_writer_paths = sorted({row["path"] for row in writer_rows})
    report.update({
        "writer_count": len(writer_rows),
        "writer_boundary_count": len(writer_rows),
        "writer_file_count": len(unique_writer_paths),
        "writer_paths": unique_writer_paths,
        "error_count": len(errors),
        "writers": writer_rows,
        "errors": errors,
    })
    report.update(rows_by_key)
    marker_errors = []
    for rel, markers in REQUIRED_BOUNDARY_MARKERS.items():
        path = ROOT / rel
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in markers:
            if marker not in text:
                marker_errors.append({
                    "category": "required_boundary_marker",
                    "path": rel,
                    "message": "missing required boundary marker: %s" % marker,
                })
    errors.extend(marker_errors)
    report["required_boundary_marker_errors"] = marker_errors
    appearance_errors = []
    for rel in unique_writer_paths:
        path = ROOT / rel
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="ignore")
        appearance_errors.extend(scan_contract_appearance(text, rel))
    errors.extend(appearance_errors)
    report["contract_appearance_errors"] = appearance_errors
    report["managed_layout_channel_keys"] = list(MANAGED_LAYOUT_CHANNEL_KEYS)
    terminal_bound_errors = []
    for rel in unique_writer_paths:
        path = ROOT / rel
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="ignore")
        terminal_bound_errors.extend(scan_terminal_bound_contract(text, rel))
    errors.extend(terminal_bound_errors)
    report["terminal_bound_contract_errors"] = terminal_bound_errors
    layout_conflicts = managed_layout_channel_conflicts()
    errors.extend(layout_conflicts)
    report["managed_layout_channel_conflicts"] = layout_conflicts
    report["error_count"] = len(errors)
    report["errors"] = errors
    return report


def main() -> int:
    report = build_report()
    output = json.dumps(report, ensure_ascii=False, indent=2)
    report_path = os.environ.get("BACKEND_CONTRACT_BOUNDARY_GUARD_REPORT", "").strip()
    if report_path:
        target = Path(report_path)
        if not target.is_absolute():
            target = ROOT / target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
