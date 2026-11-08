#!/usr/bin/env python3
"""Guard the shared frontend business-value authority and its consumers."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend/apps/web/src"
AUTHORITY = "app/presentation/businessValuePresentation.ts"
KANBAN_ADAPTER = "app/presentation/collectionKanbanPresentation.ts"


def _read(path: str, read_text: Callable[[str], str]) -> str:
    return read_text(path)


def validate(read_text: Callable[[str], str] | None = None) -> list[str]:
    read_text = read_text or (lambda path: (FRONTEND / path).read_text(encoding="utf-8"))
    failures: list[str] = []

    semantic = FRONTEND / "utils/semantic.ts"
    if semantic.exists():
        failures.append("utils/semantic.ts is a second business-level status/value vocabulary")

    authority = _read(AUTHORITY, read_text)
    kanban_adapter = _read(KANBAN_ADAPTER, read_text)
    for marker in (
        "function formatMonetaryDisplayValue(",
        "function presentDeclaredBusinessValue(",
        "function statusBadgeSemantic(",
        "FIELD_VALUE_EMPTY_TEXT",
    ):
        if marker not in authority:
            failures.append(f"business-value authority missing {marker}")
    if "function declaredBusinessFieldType(" not in authority:
        failures.append("business-value authority is missing native-type-first field type normalization")
    if not re.search(
        r"const nativeType\s*=\s*normalizeFieldType\(field\);\s*"
        r"if \(nativeType !== 'unknown'\) return nativeType;\s*"
        r"return normalizeFieldType\(String\(field\.dataType \|\| ''\)\);",
        authority,
    ):
        failures.append("dataType fallback must apply only after native type/ttype is unknown")
    if not re.search(
        r"statusType\s*===\s*'selection'\s*&&\s*!selection\.length",
        authority,
    ):
        failures.append("selection-backed status does not fail closed when selection metadata is missing")
    if not re.search(
        r"if \(kind === 'status'\)\s*\{\s*"
        r"const key = selectionValue\(input\.value\);\s*"
        r"const statusType = declaredBusinessFieldType\(input\.field\);",
        authority,
    ):
        failures.append("status presentation does not resolve its declared field type")
    if not re.search(
        r"if \(statusType !== 'selection' && statusType !== 'char'\)",
        authority,
    ):
        failures.append("status type identity must be explicitly selection or char")
    if "presentDeclaredBusinessValue" not in kanban_adapter:
        failures.append("Kanban adapter does not consume declared business-value semantics")

    money_consumers = (
        "components/FieldValue.vue",
        "components/template/FormSection.vue",
        "components/professional-fields/ProfessionalBusinessValueControl.vue",
        "components/professional-fields/PaymentSettlementIntroduceDialog.vue",
        "components/action/HierarchicalWorksheet.vue",
        "pages/ListPage.vue",
        "pages/KanbanPage.vue",
        "app/presentation/productMyWorkPresentation.ts",
        "app/contracts/actionViewActivityContract.ts",
    )
    for path in money_consumers:
        text = _read(path, read_text)
        if "businessValuePresentation" not in text and not (
            path == "pages/KanbanPage.vue" and "collectionKanbanPresentation" in text
        ):
            failures.append(f"{path} does not consume the shared business-value authority")
        if "formSection.mapper" in text and path != "components/template/FormSection.vue":
            failures.append(f"{path} still imports business-value formatting from formSection.mapper")

    kanban = _read("pages/KanbanPage.vue", read_text)
    if "semanticValueByField" in kanban:
        failures.append("KanbanPage still infers business semantics from field names")
    if "presentCollectionKanbanCell" not in kanban:
        failures.append("KanbanPage does not consume the shared declared-field adapter")
    if "columnOptions" not in kanban:
        failures.append("KanbanPage does not accept contract-derived column metadata")

    list_page = _read("pages/ListPage.vue", read_text)
    if "document_status.*state.*status.*lifecycle_state" in list_page:
        failures.append("ListPage still derives status columns from field names")
    if "COLLECTION_NUMERIC_EMPTY_TEXT" in list_page:
        failures.append("ListPage still renders missing numeric values as zero")

    list_cells = _read("pages/listPage/listCellPresentation.ts", read_text)
    if (
        "COLLECTION_NUMERIC_EMPTY_TEXT" in list_cells
        or "numeric ? '0'" in list_cells
        or re.search(r"missing\)\s+text\s*=\s*['\"]0['\"]", list_cells)
    ):
        failures.append("list cells still turn missing numeric facts into zero")

    professional_status = _read(
        "components/professional-fields/professionalBusinessValueModel.ts",
        read_text,
    )
    if "function statusSemantic(" in professional_status:
        failures.append("professional business values keep a second status tone table")

    approval = _read("components/business/MyWorkApprovalWorkspace.vue", read_text)
    if "function statusSemantic(" in approval or "statusBadgeSemantic(" not in approval:
        failures.append("approval summary does not use the shared status tone adapter")

    for path in (
        "components/template/formSection.mapper.ts",
        "components/template/FormSection.vue",
        "components/FieldValue.vue",
    ):
        text = _read(path, read_text)
        if "Intl.NumberFormat" in text or "style: 'currency'" in text:
            failures.append(f"{path} defines a second monetary formatter")

    form_section = _read("components/template/FormSection.vue", read_text)
    if "resolveReadonlyEmptyText(field, '-')" in form_section:
        failures.append("FormSection uses a local dash instead of the platform empty-value rule")

    professional_base = _read(
        "components/professional-fields/professionalBaseFieldModel.ts",
        read_text,
    )
    if "fallback = '—'" in professional_base:
        failures.append("Professional fields use a local em dash instead of the platform empty-value rule")
    if "FIELD_VALUE_EMPTY_TEXT" not in professional_base:
        failures.append("Professional fields do not consume the platform empty-value rule")

    native_canvas = _read("pages/contractForm/ContractFormNativeCanvas.vue", read_text)
    if "resolveReadonlyEmptyText(field, '未填写')" in native_canvas:
        failures.append("Native form canvas uses a local unfilled text instead of the platform empty-value rule")
    if "resolveReadonlyEmptyText(field)" not in native_canvas:
        failures.append("Native form canvas does not consume the platform empty-value rule")

    relation_renderer = _read("components/template/X2ManyRelationRenderer.vue", read_text)
    if "FIELD_VALUE_EMPTY_TEXT" not in relation_renderer or "|| '—'" in relation_renderer:
        failures.append("Detail collection cells do not consume the platform empty-value rule")

    boq_panel = _read("components/boq/BoqImportPreviewPanel.vue", read_text)
    if "FIELD_VALUE_EMPTY_TEXT" not in boq_panel or "|| '—'" in boq_panel:
        failures.append("Industry preview empty values bypass the platform rule")

    relation_search = _read("pages/contractForm/RelationSearchDialog.vue", read_text)
    if "|| '未填写'" in relation_search or "FIELD_VALUE_EMPTY_TEXT" not in relation_search:
        failures.append("Relation search empty values bypass the platform rule")

    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("[frontend_business_semantics_guard] FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("[frontend_business_semantics_guard] PASS authority=shared consumers=declared")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
