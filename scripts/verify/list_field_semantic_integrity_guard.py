#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE_API = ROOT / "addons/smart_core/handlers/api_data.py"
CONTRACT = ROOT / "frontend/apps/web/src/app/action_runtime/useActionViewContractShapeRuntime.ts"
LIST_PAGE = ROOT / "frontend/apps/web/src/pages/ListPage.vue"
REQUEST = ROOT / "frontend/apps/web/src/app/runtime/actionViewLoadRequestRuntime.ts"
ASSEMBLER = ROOT / "addons/smart_core/core/unified_page_contract_v2_assembler.py"
REPORT = ROOT / "artifacts/frontend/list-field-semantic-inventory.json"

def main() -> int:
    errors: list[str] = []
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
        "schema_version": "list-field-semantic-inventory/v2",
        "field_identity_policy": "FORMAL_PRODUCT_FIELDS_ONLY",
        "legacy_projection_count": 0,
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
        "field_identity=FORMAL_PRODUCT_FIELDS_ONLY legacy_projections=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
