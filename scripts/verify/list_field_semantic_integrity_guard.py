#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
ALIASES = ROOT / "addons/smart_construction_core/models/support/p1_daily_business_visible_alias_fields.py"
ALIAS_VIEWS = ROOT / "addons/smart_construction_core/views/support/p1_daily_business_visible_alias_views.xml"
CORE_API = ROOT / "addons/smart_core/handlers/api_data.py"
CONTRACT = ROOT / "frontend/apps/web/src/app/action_runtime/useActionViewContractShapeRuntime.ts"
LIST_PAGE = ROOT / "frontend/apps/web/src/pages/ListPage.vue"
REQUEST = ROOT / "frontend/apps/web/src/app/runtime/actionViewLoadRequestRuntime.ts"
ASSEMBLER = ROOT / "addons/smart_core/core/unified_page_contract_v2_assembler.py"
REPORT = ROOT / "artifacts/frontend/list-field-semantic-inventory.json"


def _assignments(path: Path) -> dict[str, object]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        try:
            values[node.targets[0].id] = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            continue
    return values


def _alias_name(label: str) -> str:
    return "p1_visible_" + hashlib.sha1(label.encode("utf-8")).hexdigest()[:12]


def main() -> int:
    errors: list[str] = []
    values = _assignments(ALIASES)
    labels_by_model = values.get("P1_ALIAS_LABELS") or {}
    compat_by_model = values.get("P1_ALIAS_COMPAT_LABELS") or {}
    semantic_sources = values.get("_P1_SEMANTIC_SOURCE_OVERRIDES") or {}
    model_sources = values.get("MODEL_LABEL_SOURCE_OVERRIDES") or {}
    label_sources = values.get("LABEL_SOURCE_OVERRIDES") or {}
    reverse_labels: dict[str, str] = {}
    inventory: list[dict[str, object]] = []
    for model, labels in labels_by_model.items():
        all_labels = list(dict.fromkeys(list(labels) + list(compat_by_model.get(model, []))))
        for label in all_labels:
            alias = _alias_name(label)
            reverse_labels[alias] = label
            candidates = (
                list(semantic_sources.get(model, {}).get(label, []))
                + list(model_sources.get(model, {}).get(label, []))
                + list(label_sources.get(label, []))
            )
            formal = [
                str(name)
                for name in dict.fromkeys(candidates)
                if str(name).strip() and not str(name).startswith(("legacy_", "p1_visible_"))
            ]
            inventory.append({
                "model": model,
                "display_field": alias,
                "label": label,
                "formal_source_candidates": formal,
                "mapping_status": "DECLARED" if formal else "UNRESOLVED",
            })

    root = ET.parse(ALIAS_VIEWS).getroot()
    aggregate_aliases: list[dict[str, str]] = []
    for record in root.findall(".//record"):
        model_node = record.find("./field[@name='model']")
        model = (model_node.text or "").strip() if model_node is not None else ""
        for field in record.findall(".//field[@sum]"):
            name = str(field.get("name") or "").strip()
            if not name.startswith("p1_visible_"):
                continue
            label = reverse_labels.get(name, "")
            aggregate_aliases.append({"model": model, "display_field": name, "label": label})
            candidates = (
                list(semantic_sources.get(model, {}).get(label, []))
                + list(model_sources.get(model, {}).get(label, []))
                + list(label_sources.get(label, []))
            )
            if not label:
                errors.append(f"aggregate alias has no stable label identity: {model}.{name}")
            if not any(
                str(candidate).strip()
                and not str(candidate).startswith(("legacy_", "p1_visible_"))
                for candidate in candidates
            ):
                errors.append(f"aggregate alias has no formal source declaration: {model}.{name}")

    required_tokens = {
        CORE_API: [
            "def _normalize_list_field_semantics(",
            "def _build_semantic_aggregates(",
            '"page_sum": page_value',
            "self._translate_semantic_order(order, field_semantics)",
        ],
        CONTRACT: [
            "extractListFieldSemanticsFromContract",
            "aggregation_field",
            "value_field",
            "export_field",
        ],
        REQUEST: ["field_semantics:", "need_aggregates: true"],
        ASSEMBLER: ['"aggregation_field"', '"export_field"', '"semantic_status"'],
        LIST_PAGE: [
            "function isAggregateColumn(",
            "pageAggregateValue(field)",
            "columnOption(col)?.sortField",
        ],
    }
    for path, tokens in required_tokens.items():
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            if token not in text:
                errors.append(f"{path.relative_to(ROOT)} missing semantic contract token: {token}")
    list_text = LIST_PAGE.read_text(encoding="utf-8")
    if "includes('金额')" in list_text or "replace(/,/g, '')" not in list_text:
        # Formatted numeric parsing remains a display-only fallback for direct
        # numeric fields; business labels must never decide aggregation.
        if "includes('金额')" in list_text:
            errors.append("frontend must not infer aggregation from Chinese labels")

    report = {
        "schema_version": "list-field-semantic-inventory/v1",
        "projection_model_count": len(labels_by_model),
        "projection_field_count": len(inventory),
        "declared_mapping_count": sum(row["mapping_status"] == "DECLARED" for row in inventory),
        "unresolved_mapping_count": sum(row["mapping_status"] != "DECLARED" for row in inventory),
        "aggregate_projection_count": len(aggregate_aliases),
        "aggregate_projections": aggregate_aliases,
        "inventory": inventory,
        "errors": errors,
        "result": "PASS" if not errors else "FAIL",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if errors:
        print("[list_field_semantic_integrity_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "[list_field_semantic_integrity_guard] PASS "
        f"models={report['projection_model_count']} fields={report['projection_field_count']} "
        f"declared={report['declared_mapping_count']} aggregate_aliases={report['aggregate_projection_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
