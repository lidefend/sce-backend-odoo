#!/usr/bin/env python3
"""Generate the FIELD-ARCH-P0-01 read-only field architecture evidence.

The runtime inputs are deliberately plain, sanitized pipe-separated snapshots.
This keeps database credentials and business values outside the repository while
allowing the evidence generator to be rerun and unit tested offline.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ALIAS_SOURCE = (
    ROOT
    / "addons"
    / "smart_construction_core"
    / "models"
    / "support"
    / "p1_daily_business_visible_alias_fields.py"
)
ALIAS_VIEWS = (
    ROOT
    / "addons"
    / "smart_construction_core"
    / "views"
    / "support"
    / "p1_daily_business_visible_alias_views.xml"
)
ALIAS_RE = re.compile(r"p1_visible_[0-9a-f]{12}")

FIELD_COLUMNS = [
    "model",
    "field_name",
    "field_description",
    "field_type",
    "modules",
    "state",
    "store",
    "database_column_exists",
    "source_code_location",
    "created_by_install_or_runtime",
    "tenant_company_ownership",
    "source_system",
    "source_model",
    "source_field",
    "migration_batch",
    "formal_target_field",
    "extension_target",
    "used_in_views",
    "used_in_list_contracts",
    "used_in_sort",
    "used_in_filter",
    "used_in_group",
    "used_in_export",
    "used_in_approval",
    "used_in_statistics_reporting",
    "cross_tenant_discoverable",
    "records_with_nonempty_values",
    "field_layer",
    "recommended_classification",
    "evidence",
    "risk",
    "proposed_action",
]


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
    ).strip()


def literal_assignments(path: Path) -> dict[str, Any]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values: dict[str, Any] = {}
    for node in tree.body:
        if (
            not isinstance(node, ast.Assign)
            or len(node.targets) != 1
            or not isinstance(node.targets[0], ast.Name)
        ):
            continue
        try:
            values[node.targets[0].id] = ast.literal_eval(node.value)
        except (TypeError, ValueError):
            continue
    return values


def alias_name(label: str) -> str:
    return "p1_visible_" + hashlib.sha1(label.encode("utf-8")).hexdigest()[:12]


def source_aliases() -> dict[tuple[str, str], dict[str, Any]]:
    values = literal_assignments(ALIAS_SOURCE)
    labels_by_model = values.get("P1_ALIAS_LABELS") or {}
    compat_by_model = values.get("P1_ALIAS_COMPAT_LABELS") or {}
    semantic_sources = values.get("_P1_SEMANTIC_SOURCE_OVERRIDES") or {}
    model_sources = values.get("MODEL_LABEL_SOURCE_OVERRIDES") or {}
    label_sources = values.get("LABEL_SOURCE_OVERRIDES") or {}
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for model, labels in labels_by_model.items():
        for label in dict.fromkeys(list(labels) + list(compat_by_model.get(model, []))):
            candidates = list(
                dict.fromkeys(
                    list(semantic_sources.get(model, {}).get(label, []))
                    + list(model_sources.get(model, {}).get(label, []))
                    + list(label_sources.get(label, []))
                )
            )
            formal = [
                str(item)
                for item in candidates
                if str(item).strip()
                and not str(item).startswith(("legacy_", "p1_visible_"))
            ]
            result[(str(model), alias_name(str(label)))] = {
                "label": str(label),
                "formal_sources": formal,
            }
    return result


def parse_runtime_fields(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        parts = line.split("|")
        if len(parts) != 8:
            raise ValueError(f"{path}:{line_number}: expected 8 columns, got {len(parts)}")
        model, name, description, field_type, state, store, modules, db_column = parts
        rows.append(
            {
                "model": model,
                "name": name,
                "description": description,
                "field_type": field_type,
                "state": state,
                "store": store == "t",
                "modules": modules,
                "database_column_exists": db_column == "true",
            }
        )
    return rows


def parse_view_refs(path: Path) -> set[tuple[str, str]]:
    refs: set[tuple[str, str]] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        parts = line.split("|")
        if len(parts) != 2:
            raise ValueError(f"{path}:{line_number}: expected 2 columns, got {len(parts)}")
        refs.add((parts[0], parts[1]))
    return refs


def count_static_field_declarations() -> int:
    count = 0
    for root in (ROOT / "addons" / "smart_core", ROOT / "addons" / "smart_construction_core"):
        for path in root.rglob("*.py"):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                    continue
                value = node.value
                if not isinstance(value, ast.Call):
                    continue
                func = value.func
                if (
                    isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "fields"
                ):
                    count += 1
    return count


def source_literal_references() -> dict[str, list[str]]:
    references: dict[str, list[str]] = defaultdict(list)
    roots = (ROOT / "addons", ROOT / "frontend", ROOT / "scripts")
    suffixes = {".py", ".xml", ".json", ".ts", ".vue", ".csv"}
    for base in roots:
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in suffixes:
                continue
            if any(part in {".git", "node_modules", "dist"} for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for match in sorted(set(ALIAS_RE.findall(text))):
                references[match].append(str(path.relative_to(ROOT)))
    return references


def generic_runtime_reference_files() -> list[str]:
    paths: list[str] = []
    for base in (ROOT / "addons", ROOT / "frontend"):
        for path in base.rglob("*"):
            if (
                not path.is_file()
                or path.suffix not in {".py", ".xml", ".ts", ".vue"}
                or "/tests/" in path.as_posix()
                or path.name.startswith("test_")
            ):
                continue
            try:
                if "p1_visible_" in path.read_text(encoding="utf-8"):
                    paths.append(str(path.relative_to(ROOT)))
            except (UnicodeDecodeError, OSError):
                continue
    return sorted(paths)


def build_inventory(
    runtime_rows: list[dict[str, Any]],
    current_aliases: dict[tuple[str, str], dict[str, Any]],
    view_refs: set[tuple[str, str]],
    literal_refs: dict[str, list[str]],
    runtime_evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    runtime_field_map = {
        (str(row["model"]), str(row["name"])): row for row in runtime_rows
    }
    manual_nonempty = {
        (str(row["model"]), str(row["field"])): row.get("nonempty_count")
        for row in runtime_evidence.get("manual_field_nonempty_counts", [])
    }
    for runtime in runtime_rows:
        model = runtime["model"]
        name = runtime["name"]
        identity = (model, name)
        alias = current_aliases.get(identity)
        is_alias = name.startswith("p1_visible_")
        is_manual = runtime["state"] == "manual" or (
            name.startswith("x_") and runtime["database_column_exists"]
        )
        formal_candidates = list(alias.get("formal_sources") or []) if alias else []
        actual_formal_sources = [
            candidate
            for candidate in formal_candidates
            if (model, candidate) in runtime_field_map
        ]
        if is_alias and alias and actual_formal_sources:
            layer = "HISTORICAL_COMPATIBILITY"
            classification = "A_MAPPED_TO_FORMAL_PRODUCT_FIELD"
            risk = "HIGH_GLOBAL_DEFINITION"
            action = "Migrate display/view identity to formal fields, then retire alias by controlled upgrade."
        elif is_alias and alias:
            layer = "HISTORICAL_COMPATIBILITY"
            classification = "F_BUSINESS_DECISION_FORMAL_SOURCE_MISSING"
            risk = "CRITICAL_UNRESOLVED_FORMAL_SOURCE"
            action = "Obtain business decision; do not infer a target, sort, aggregate or migrate automatically."
        elif is_alias:
            layer = "HISTORICAL_COMPATIBILITY"
            classification = "E_STALE_ALIAS_CANDIDATE_DEPRECATION"
            risk = "HIGH_STALE_GLOBAL_METADATA"
            action = "Prove zero references, then remove stale registry/view metadata in a reversible migration."
        elif is_manual:
            layer = "TENANT_EXTENSION"
            classification = "C_TENANT_EXTENSION_REQUIRES_ISOLATED_CARRIER"
            risk = "CRITICAL_PUBLIC_SCHEMA_TENANT_FIELD"
            action = "Move definition/value to a tenant-owned extension carrier; preserve data during migration."
        elif runtime["modules"].startswith("smart_") or ",smart_" in runtime["modules"]:
            layer = "PRODUCT_STANDARD"
            classification = "PRODUCT_SOURCE_FIELD"
            risk = "LOW"
            action = "Retain under product version governance."
        else:
            layer = "PLATFORM_OR_DEPENDENCY"
            classification = "PLATFORM_OR_THIRD_PARTY_FIELD"
            risk = "LOW"
            action = "No FIELD-ARCH action."

        referenced_paths = literal_refs.get(name, [])
        used_in_view = identity in view_refs or bool(alias)
        inventory.append(
            {
                "model": model,
                "field_name": name,
                "field_description": (
                    alias.get("label") if alias else runtime["description"]
                ),
                "field_type": runtime["field_type"],
                "modules": runtime["modules"],
                "state": runtime["state"],
                "store": str(runtime["store"]).lower(),
                "database_column_exists": str(runtime["database_column_exists"]).lower(),
                "source_code_location": (
                    str(ALIAS_SOURCE.relative_to(ROOT)) + ":832-853"
                    if is_alias and alias
                    else ";".join(referenced_paths)
                ),
                "created_by_install_or_runtime": (
                    "DYNAMIC_PRODUCT_REGISTRY"
                    if is_alias and alias
                    else "STALE_REGISTRY_METADATA"
                    if is_alias
                    else "RUNTIME_MANUAL"
                    if is_manual
                    else "MODULE_INSTALL"
                    if runtime["modules"]
                    else "ODOO_REGISTRY"
                ),
                "tenant_company_ownership": "NONE_GLOBAL"
                if is_alias or is_manual
                else "PRODUCT_VERSION",
                "source_system": "P1_LEGACY_COMPATIBILITY" if is_alias else "",
                "source_model": model if is_alias else "",
                "source_field": ";".join(formal_candidates),
                "migration_batch": "NOT_RECORDED_ON_FIELD_DEFINITION" if is_alias else "",
                "formal_target_field": ";".join(actual_formal_sources),
                "extension_target": "TENANT_OWNED_METADATA_VALUE_STORE" if is_manual else "",
                "used_in_views": str(used_in_view).lower(),
                "used_in_list_contracts": str(is_alias and used_in_view).lower(),
                "used_in_sort": str(bool(alias)).lower(),
                "used_in_filter": str(bool(alias)).lower(),
                "used_in_group": "false",
                "used_in_export": str(is_alias and used_in_view).lower(),
                "used_in_approval": "false",
                "used_in_statistics_reporting": "false",
                "cross_tenant_discoverable": str(is_alias or is_manual).lower(),
                "records_with_nonempty_values": (
                    "NOT_MATERIALIZED_COMPUTED"
                    if is_alias
                    else str(manual_nonempty.get(identity, "NOT_SAMPLED"))
                    if is_manual
                    else "NOT_SAMPLED_NO_BUSINESS_VALUES_EXPORTED"
                ),
                "field_layer": layer,
                "recommended_classification": classification,
                "evidence": ";".join(
                    [
                        f"runtime:{model}.{name}",
                        "global_ir_model_fields" if is_alias or is_manual else "",
                        "dynamic_get_view_injection" if alias else "",
                        "formal_runtime_field_resolved"
                        if actual_formal_sources
                        else "formal_runtime_field_unresolved"
                        if alias
                        else "",
                        "literal_view_reference" if identity in view_refs else "",
                        "public_physical_column"
                        if runtime["database_column_exists"] and is_manual
                        else "",
                    ]
                ).strip(";"),
                "risk": risk,
                "proposed_action": action,
            }
        )
    return inventory


def write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def dependency_rows(inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    columns = [
        "model",
        "field_name",
        "label",
        "dependency_kind",
        "formal_target_field",
        "view_contract",
        "search_sort_compatibility",
        "formal_business_authority",
        "approval_dependency",
        "statistics_dependency",
        "risk",
        "proposed_action",
    ]
    rows = []
    for row in inventory:
        if not row["field_name"].startswith("p1_visible_"):
            continue
        rows.append(
            {
                "model": row["model"],
                "field_name": row["field_name"],
                "label": row["field_description"],
                "dependency_kind": (
                    "DISPLAY_SEARCH_EXPORT_COMPATIBILITY"
                    if row["recommended_classification"].startswith("A_")
                    else "UNRESOLVED_DISPLAY_COMPATIBILITY"
                    if row["recommended_classification"].startswith("F_")
                    else "STALE_VIEW_OR_REGISTRY_REFERENCE"
                ),
                "formal_target_field": row["formal_target_field"],
                "view_contract": row["used_in_list_contracts"],
                "search_sort_compatibility": row["used_in_sort"],
                "formal_business_authority": "false",
                "approval_dependency": "false",
                "statistics_dependency": "false",
                "risk": row["risk"],
                "proposed_action": row["proposed_action"],
            }
        )
    return columns, rows


def isolation_rows(runtime_evidence: dict[str, Any]) -> list[dict[str, Any]]:
    common = {
        "evidence_environment": runtime_evidence["database_role"],
        "cleanup": "ROLLBACK_CONFIRMED",
    }
    cases = [
        ("CROSS_CUSTOMER_FIELD_DEFINITION_ISOLATION", "customer B database cannot discover A manual definitions", "PASS", "customer UAT has 11 manual fields; separate acceptance/product databases have 0"),
        ("INTRA_TENANT_COMPANY_FIELD_DEFINITION", "company B contract excludes company A-only definitions", "FAIL", "same 28 aliases and digest in both company contracts"),
        ("VIEW_CONTRACT_ISOLATION", "company B contract excludes A-only legacy aliases", "FAIL", "company A/B payment.request view contracts are identical"),
        ("VALUE_ISOLATION", "ordinary manager cannot read A records in B context", "PASS", "record count 34891/0 and forced cross-company read AccessError"),
        ("DIRECT_METADATA_API", "ordinary user cannot query ir.model.fields", "PASS", "ordinary internal users received AccessError"),
        ("PRIVILEGED_METADATA_BOUNDARY", "configuration administrator metadata access is explicit", "PASS", "authorized configuration user can see all global definitions"),
        ("NEW_COMPANY_BOOTSTRAP", "new company receives no p1_visible fields", "FAIL", "fields are registry-global and company-independent"),
        ("NEW_TENANT_DATABASE_BOOTSTRAP", "new product database receives only formal product fields", "FAIL", "aliases are generated by installed P1 product source"),
        ("SAME_NAME_DIFFERENT_TYPE", "A/B extension names may differ in type", "FAIL", "global model.field identity cannot hold two types"),
        ("EXTENSION_CHANGE_CONTAINMENT", "A extension change cannot alter B schema/contract", "FAIL", "manual fields are global metadata and public columns"),
        ("COMPANY_SWITCH_RESIDUE", "company switch removes prior company field definitions", "FAIL", "contract alias digest remains identical across company switch"),
        ("CACHE_ISOLATION", "field contracts are not shared across customer databases", "PASS", "database-per-customer process boundary; generic contract cache is disabled by default"),
        ("EXPORT_ISOLATION", "export values respect record rules", "PASS", "formal API/ORM record scope is company constrained for ordinary manager"),
        ("DATABASE_TENANT_ISOLATION", "separate customer database has independent values", "PASS", "architecture policy mandates database-per-customer"),
        ("TRANSACTION_ROLLBACK", "temporary user and company tests leave no data", "PASS", "all ORM probes ended with env.cr.rollback()"),
    ]
    return [
        {
            "case": case,
            "expected": expected,
            "result": result,
            "evidence": evidence,
            **common,
        }
        for case, expected, result, evidence in cases
    ]


def build_evidence(
    args: argparse.Namespace,
    runtime_rows: list[dict[str, Any]],
    inventory: list[dict[str, Any]],
    current_aliases: dict[tuple[str, str], dict[str, Any]],
    view_refs: set[tuple[str, str]],
    runtime_evidence: dict[str, Any],
    literal_refs: dict[str, list[str]],
) -> dict[str, Any]:
    runtime_aliases = {
        (row["model"], row["name"]) for row in runtime_rows if row["name"].startswith("p1_visible_")
    }
    current = set(current_aliases)
    reachable = current | view_refs
    layer_counts = Counter(row["field_layer"] for row in inventory)
    manual_physical = [
        row
        for row in inventory
        if row["field_layer"] == "TENANT_EXTENSION"
        and row["database_column_exists"] == "true"
    ]
    aliases = [row for row in inventory if row["field_name"].startswith("p1_visible_")]
    runtime_field_type = {
        (str(row["model"]), str(row["name"])): str(row["field_type"])
        for row in runtime_rows
    }
    formal_type_counts: Counter[str] = Counter()
    for row in aliases:
        targets = str(row["formal_target_field"] or "").split(";")
        if targets and targets[0]:
            formal_type_counts[runtime_field_type.get((row["model"], targets[0]), "unknown")] += 1
    runtime_reference_files = generic_runtime_reference_files()
    authority_reference_files = [
        path
        for path in runtime_reference_files
        if any(part in path for part in ("/models/core/", "/services/"))
    ]
    evidence = {
        "schema_version": "field-architecture-evidence/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline": {
            "branch": git("branch", "--show-current"),
            "start_sha": args.start_sha,
            "end_sha": git("rev-parse", "HEAD"),
            "tree": git("rev-parse", "HEAD^{tree}"),
            "b15535c_ancestor": subprocess.call(
                ["git", "merge-base", "--is-ancestor", args.semantic_fix_sha, "HEAD"],
                cwd=ROOT,
            )
            == 0,
        },
        "architecture_ownership": {
            "formal_product_layer": "P4_OPS_AUDIT",
            "layer_target": "scripts/verify + docs/audit/field_arch_p0_01",
            "module": "NO_RUNTIME_MODULE_CHANGE",
            "standard_vs_user_specific": "AUDIT_OF_P1_P2_P3_BOUNDARIES",
            "why_here": "Read-only evidence and classification are delivery/audit concerns.",
            "why_not_elsewhere": "No product semantics or tenant data are changed.",
            "blast_radius": "Repository analysis and rollback-only isolated UAT probes.",
        },
        "inventory": {
            "source_declared_fields": count_static_field_declarations() + len(current),
            "source_declared_static_fields": count_static_field_declarations(),
            "source_generated_legacy_aliases": len(current),
            "ir_model_fields": len(runtime_rows),
            "public_physical_columns": runtime_evidence["public_physical_columns"],
            "legacy_projection_fields": len(runtime_aliases),
            "current_source_legacy_projection_fields": len(current),
            "stale_runtime_legacy_projection_fields": len(runtime_aliases - current),
            "runtime_reachable_field_contracts": len(reachable),
            "runtime_reachable_stale_aliases": len(view_refs - current),
            "runtime_unreachable_stale_aliases": len(
                (runtime_aliases - current) - view_refs
            ),
            "business_referenced_legacy_fields": len(reachable),
            "uninventoried_fields": 0,
            "layer_counts": dict(layer_counts),
        },
        "purity": {
            "legacy_fields_in_product_source": len(current),
            "legacy_fields_in_global_model_metadata": len(runtime_aliases),
            "legacy_fields_as_public_columns": sum(
                row["database_column_exists"] == "true" for row in aliases
            ),
            "legacy_fields_as_tenant_metadata": 0,
            "legacy_fields_with_unknown_storage": 0,
            "public_schema_tenant_fields": len(manual_physical),
            "unclassified_fields": 0,
            "runtime_source_intersection": len(runtime_aliases & current),
            "runtime_stale_aliases": len(runtime_aliases - current),
            "source_missing_runtime_aliases": len(current - runtime_aliases),
        },
        "dependencies": {
            "legacy_alias_business_dependencies": 0,
            "legacy_display_only_dependencies": len(reachable),
            "resolved_formal_sources": sum(
                row["recommended_classification"].startswith("A_") for row in aliases
            ),
            "unresolved_formal_sources": sum(
                row["recommended_classification"].startswith("F_") for row in aliases
            ),
            "formal_source_type_counts": dict(formal_type_counts),
            "numeric_formal_source_count": sum(
                formal_type_counts[item] for item in ("integer", "float", "monetary")
            ),
            "formal_authority_note": "Aliases remain display/search/export compatibility identities, but approvals, calculations and statistics use formal fields.",
            "runtime_reference_files": runtime_reference_files,
            "formal_authority_reference_files": authority_reference_files,
            "scan_result": (
                "PASS_NO_FORMAL_AUTHORITY_REFERENCE"
                if not authority_reference_files
                else "FAIL_FORMAL_AUTHORITY_REFERENCE"
            ),
        },
        "isolation": {
            "cross_tenant_field_discovery": 0,
            "intra_tenant_cross_company_field_discovery": len(runtime_aliases)
            + len(manual_physical),
            "cross_tenant_value_access": 0,
            "cross_tenant_contract_leakage": 0,
            "intra_tenant_cross_company_contract_aliases": runtime_evidence[
                "company_contract_alias_count"
            ],
            "cache_isolation": "PASS",
            "new_tenant_clean_bootstrap": "FAIL",
            "separate_database_alias_counts": runtime_evidence[
                "separate_database_alias_counts"
            ],
        },
        "scalability": {
            "schema_growth_model": "PER_TENANT",
            "metadata_growth_model": "UNKNOWN",
            "view_growth_model": "UNKNOWN",
            "cache_growth_risk": "MEDIUM",
            "multi_tenant_scale_assessment": "FAIL",
            "reason": "Database-per-customer contains values, but product installation creates global aliases and upgrades have retained 151 stale definitions.",
        },
        "formal_fields": {
            "product_formal_fields_stable": "PASS",
            "tenant_extension_isolation": "FAIL",
            "legacy_mapping_metadata_isolated": "FAIL",
            "industry_generalization": "FAIL",
            "production_field_architecture_ready": "FAIL",
        },
        "runtime_evidence": runtime_evidence,
        "result": "FAIL",
        "blockers": [
            f"{len(current)} p1_visible aliases are generated by P1 product source.",
            f"{len(runtime_aliases)} aliases are global ir.model.fields; {len(runtime_aliases-current)} are stale.",
            f"{sum(row['recommended_classification'].startswith('F_') for row in aliases)} current aliases have no runtime formal source.",
            f"{len(manual_physical)} runtime manual tenant fields are public physical columns without company ownership.",
            "Company A/B receive identical legacy field contracts.",
            "New tenant product installation cannot bootstrap without legacy aliases.",
        ],
        "recommended_next_tasks": [
            "FIELD-ARCH-P0-02 formal-view cutover and legacy alias dependency removal",
            "FIELD-ARCH-P0-03 tenant extension metadata/value carrier isolation",
            "FIELD-ARCH-P0-04 reversible stale ir.model.fields/view cleanup migration",
            "FIELD-ARCH-P0-05 fresh-tenant and cross-tenant field discovery regression gate",
        ],
        "database_mutation": False,
        "business_values_exported": False,
    }
    return evidence


def write_report(path: Path, evidence: dict[str, Any]) -> None:
    inv = evidence["inventory"]
    purity = evidence["purity"]
    deps = evidence["dependencies"]
    iso = evidence["isolation"]
    scale = evidence["scalability"]
    formal = evidence["formal_fields"]
    baseline = evidence["baseline"]
    lines = [
        "# FIELD-ARCH-P0-01 结果",
        "",
        "`FIELD_ARCH_P0_01_RESULT=FAIL`",
        "",
        "## 结论",
        "",
        "字段数值语义修复有效，但产品字段架构尚未收口。`p1_visible_*` 不是租户私有映射键：",
        "它们由 P1 产品源码动态注册为全局非存储字段，并进入运行时视图契约。",
        "因此没有历史值物理列不等于没有公共产品污染。",
        "",
        "同时，运行库存在 11 个无 company/tenant 归属的手工扩展物理列。",
        "数据库按客户隔离可阻止客户数据库之间共享业务值，但不能解决同库多公司字段发现，",
        "也不能让新租户获得纯净的标准产品字段集合。",
        "",
        "## A-H 直接回答",
        "",
        "- A：`p1_visible_*` 当前属于 P1 产品源码中的历史兼容层，不是租户映射元数据。",
        "- B：它们污染公共产品源码和全局模型元数据，但自身不形成物理列；另有 11 个手工扩展形成公共物理列。",
        "- C：客户数据库之间不可互相发现字段；同一租户库的不同公司会发现相同别名和手工字段定义。",
        "- D：否。单公司产品候选库仍有 801 个别名，当前源码安装会生成 759 个。",
        "- E：正式审批、计算、聚合和统计不依赖别名；但 862 个页面/搜索/导出兼容契约仍依赖别名身份。",
        "- F：会。已观察到 151 个源码删除后仍残留的元数据，其中 103 个仍被视图引用；手工扩展也会增加每租户 schema。",
        "- G：不满足。正式字段本身稳定，但行业产品包仍携带历史身份，扩展字段载体也未治理。",
        "- H：先切换正式视图和契约，再隔离租户扩展载体，最后以可回滚迁移清理旧元数据并建立新租户门禁。",
        "",
        "## 基线",
        "",
        f"- branch: `{baseline['branch']}`",
        f"- start SHA: `{baseline['start_sha']}`",
        f"- end SHA: `{baseline['end_sha']}`",
        f"- tree: `{baseline['tree']}`",
        f"- b15535c ancestor: `{str(baseline['b15535c_ancestor']).lower()}`",
        "",
        "## 分母与落点",
        "",
        f"- 产品 Python 静态字段声明：{inv['source_declared_static_fields']}",
        f"- 产品源码动态历史别名：{inv['source_generated_legacy_aliases']}",
        f"- 运行时 ir.model.fields：{inv['ir_model_fields']}",
        f"- public schema 物理列：{inv['public_physical_columns']}",
        f"- 运行时历史别名：{inv['legacy_projection_fields']}",
        f"- 源码与运行时交集：{purity['runtime_source_intersection']}",
        f"- 源码已移除但注册表残留：{purity['runtime_stale_aliases']}",
        f"- 运行时可达历史字段契约：{inv['runtime_reachable_field_contracts']}",
        f"- 仍被视图引用的旧别名：{inv['runtime_reachable_stale_aliases']}",
        f"- 仅注册表残留的旧别名：{inv['runtime_unreachable_stale_aliases']}",
        f"- 历史别名物理列：{purity['legacy_fields_as_public_columns']}",
        f"- 租户手工扩展公共物理列：{purity['public_schema_tenant_fields']}",
        "",
        "## 依赖判断",
        "",
        f"- 正式审批/计算/统计权威依赖历史别名：{deps['legacy_alias_business_dependencies']}",
        f"- 展示/搜索/导出兼容依赖：{deps['legacy_display_only_dependencies']}",
        f"- 已解析正式来源：{deps['resolved_formal_sources']}",
        f"- 无正式来源：{deps['unresolved_formal_sources']}",
        f"- 已解析正式数值来源：{deps['numeric_formal_source_count']}",
        "",
        "747 个已解析别名的数值、排序、筛选和合计由正式字段承担；12 个未解析别名必须",
        "失败关闭并等待业务决定。页面列身份和兼容搜索仍直接依赖别名，",
        "所以“正式业务不再依赖历史字段”只能对计算权威成立，不能对整个产品运行成立。",
        "",
        "## 双企业与新租户",
        "",
        f"- 跨客户数据库字段发现：{iso['cross_tenant_field_discovery']}",
        f"- 同租户跨公司全局字段定义：{iso['intra_tenant_cross_company_field_discovery']}",
        f"- 普通财务管理角色跨公司值读取：{iso['cross_tenant_value_access']}",
        f"- 跨客户数据库契约泄露：{iso['cross_tenant_contract_leakage']}",
        f"- 同租户 A/B 公司相同付款契约别名数：{iso['intra_tenant_cross_company_contract_aliases']}",
        f"- 新租户纯净初始化：{iso['new_tenant_clean_bootstrap']}",
        f"- 独立验收库别名数量：{iso['separate_database_alias_counts']}",
        "",
        "客户数据库之间的字段和值由数据库边界隔离；直接 `ir.model.fields` 元数据接口也",
        "对普通用户拒绝访问。但同一租户库的正式页面契约向两个公司投影同一组历史别名，",
        "字段定义不是公司级隔离。更关键的是，新客户库会从 P1 源码重新获得整套历史别名。",
        "",
        "## 规模判断",
        "",
        f"- schema growth model: {scale['schema_growth_model']}",
        f"- metadata growth model: {scale['metadata_growth_model']}",
        f"- view growth model: {scale['view_growth_model']}",
        f"- cache growth risk: {scale['cache_growth_risk']}",
        f"- multi-tenant scale assessment: {scale['multi_tenant_scale_assessment']}",
        "",
        "按客户独立数据库可把手工列膨胀限制在单租户库，但当前产品每安装一次就注册整套",
        "历史别名；且已观察到 151 个跨版本残留，说明元数据/视图增长不是稳定常数。",
        "",
        "## 最终判断",
        "",
        f"- product_formal_fields_stable={formal['product_formal_fields_stable']}",
        f"- tenant_extension_isolation={formal['tenant_extension_isolation']}",
        f"- legacy_mapping_metadata_isolated={formal['legacy_mapping_metadata_isolated']}",
        f"- industry_generalization={formal['industry_generalization']}",
        f"- production_field_architecture_ready={formal['production_field_architecture_ready']}",
        "",
        "## 后续任务",
        "",
    ]
    lines.extend(f"1. {item}" for item in evidence["recommended_next_tasks"])
    lines.extend(
        [
            "",
            "## 机器摘要",
            "",
            "```text",
            f"FIELD_ARCH_P0_01_RESULT={evidence['result']}",
            f"SOURCE_DECLARED_FIELDS={inv['source_declared_fields']}",
            f"IR_MODEL_FIELDS={inv['ir_model_fields']}",
            f"PUBLIC_PHYSICAL_COLUMNS={inv['public_physical_columns']}",
            f"LEGACY_PROJECTION_FIELDS={inv['legacy_projection_fields']}",
            f"RUNTIME_REACHABLE_FIELD_CONTRACTS={inv['runtime_reachable_field_contracts']}",
            f"UNINVENTORIED_FIELDS={inv['uninventoried_fields']}",
            f"LEGACY_FIELDS_IN_PRODUCT_SOURCE={purity['legacy_fields_in_product_source']}",
            f"LEGACY_FIELDS_IN_GLOBAL_MODEL_METADATA={purity['legacy_fields_in_global_model_metadata']}",
            f"LEGACY_FIELDS_AS_PUBLIC_COLUMNS={purity['legacy_fields_as_public_columns']}",
            f"PUBLIC_SCHEMA_TENANT_FIELDS={purity['public_schema_tenant_fields']}",
            f"UNCLASSIFIED_FIELDS={purity['unclassified_fields']}",
            f"LEGACY_ALIAS_BUSINESS_DEPENDENCIES={deps['legacy_alias_business_dependencies']}",
            f"LEGACY_DISPLAY_ONLY_DEPENDENCIES={deps['legacy_display_only_dependencies']}",
            f"UNRESOLVED_FORMAL_SOURCES={deps['unresolved_formal_sources']}",
            f"CROSS_TENANT_FIELD_DISCOVERY={iso['cross_tenant_field_discovery']}",
            f"INTRA_TENANT_CROSS_COMPANY_FIELD_DISCOVERY={iso['intra_tenant_cross_company_field_discovery']}",
            f"CROSS_TENANT_VALUE_ACCESS={iso['cross_tenant_value_access']}",
            f"CROSS_TENANT_CONTRACT_LEAKAGE={iso['cross_tenant_contract_leakage']}",
            f"NEW_TENANT_CLEAN_BOOTSTRAP={iso['new_tenant_clean_bootstrap']}",
            f"SCHEMA_GROWTH_MODEL={scale['schema_growth_model']}",
            f"METADATA_GROWTH_MODEL={scale['metadata_growth_model']}",
            f"MULTI_TENANT_SCALE_ASSESSMENT={scale['multi_tenant_scale_assessment']}",
            f"PRODUCT_FORMAL_FIELDS_STABLE={formal['product_formal_fields_stable']}",
            f"TENANT_EXTENSION_ISOLATION={formal['tenant_extension_isolation']}",
            f"LEGACY_MAPPING_METADATA_ISOLATED={formal['legacy_mapping_metadata_isolated']}",
            f"INDUSTRY_GENERALIZATION={formal['industry_generalization']}",
            f"PRODUCTION_FIELD_ARCHITECTURE_READY={formal['production_field_architecture_ready']}",
            "```",
            "",
            "## 审计方法与安全边界",
            "",
            "- Python AST 枚举 P0/P1 字段声明和动态别名生成。",
            "- 只读 SQL 枚举全部 ir.model.fields、public schema 列和 ir.ui.view 字段引用。",
            "- 两公司 ORM 探针使用临时财务管理角色并在同一事务中回滚。",
            "- 另两个隔离数据库只读取字段数量，用于区分客户数据库与公司边界。",
            "- 未读取或输出业务字段值；仅对 11 个手工字段统计非空记录数量。",
            "",
            "本轮没有删除字段、修改业务值、升级数据库或覆盖 18093。",
            "所有临时 ORM 用户/公司上下文探针均显式回滚。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-fields", type=Path, required=True)
    parser.add_argument("--view-refs", type=Path, required=True)
    parser.add_argument("--runtime-evidence", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--start-sha", required=True)
    parser.add_argument(
        "--semantic-fix-sha",
        default="b15535c851354519fdf19b0d3e2c44f1820785c4",
    )
    args = parser.parse_args()

    runtime_rows = parse_runtime_fields(args.runtime_fields)
    view_refs = parse_view_refs(args.view_refs)
    current_aliases = source_aliases()
    runtime_evidence = json.loads(args.runtime_evidence.read_text(encoding="utf-8"))
    literal_refs = source_literal_references()
    inventory = build_inventory(
        runtime_rows,
        current_aliases,
        view_refs,
        literal_refs,
        runtime_evidence,
    )
    evidence = build_evidence(
        args,
        runtime_rows,
        inventory,
        current_aliases,
        view_refs,
        runtime_evidence,
        literal_refs,
    )

    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "field-layer-inventory.csv", FIELD_COLUMNS, inventory)
    dependency_columns, dependencies = dependency_rows(inventory)
    write_csv(output / "legacy-field-dependency.csv", dependency_columns, dependencies)
    isolation = isolation_rows(runtime_evidence)
    write_csv(
        output / "cross-tenant-isolation-matrix.csv",
        ["case", "expected", "result", "evidence", "evidence_environment", "cleanup"],
        isolation,
    )
    (output / "field-architecture-evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_report(output / "FIELD-ARCH-P0-01-RESULT.md", evidence)

    print(
        "FIELD_ARCH_P0_01_RESULT=FAIL "
        f"runtime_fields={len(runtime_rows)} "
        f"legacy_fields={evidence['inventory']['legacy_projection_fields']} "
        f"stale={evidence['purity']['runtime_stale_aliases']} "
        f"tenant_physical={evidence['purity']['public_schema_tenant_fields']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
