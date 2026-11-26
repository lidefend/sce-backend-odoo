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
    field_semantics = _read("utils/fieldSemantics.ts", read_text)
    kanban_adapter = _read(KANBAN_ADAPTER, read_text)
    for marker in (
        "function formatMonetaryDisplayValue(",
        "function presentDeclaredBusinessValue(",
        "function presentDeclaredRelation(",
        "function presentDeclaredRelationCollection(",
        "function relationLabel(value: unknown, locale?: LocalizedDisplayOptions)",
        "resolveLocalizedDisplayValue(",
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
    if "function resolveDeclaredStatusContract(" not in authority:
        failures.append("status presentation does not resolve its declared field contract")
    if not re.search(
        r"if \(statusType !== 'selection' && statusType !== 'char'\)",
        authority,
    ):
        failures.append("status type identity must be explicitly selection or char")
    status_contract_marker = (
        "const statusContract = kind === 'status'\n"
        "    ? resolveDeclaredStatusContract(input.field)\n"
        "    : null;"
    )
    status_position = authority.find(status_contract_marker)
    empty_position = authority.find("if (isEmptyFieldValue(input.value))", status_position + 1)
    if status_position < 0 or empty_position < 0:
        failures.append("status declaration validation must precede empty-value return")
    if "function requireDeclaredBusinessDigits(" not in authority:
        failures.append("money and percentage values do not require declared precision")
    if "function requireDeclaredBusinessUnit(" not in authority:
        failures.append("percentage and duration values do not require declared units")
    if "unit?.kind === 'duration'" not in authority or "unit?.kind === 'percent'" not in authority:
        failures.append("percentage and duration unit kinds are not consumed")
    if "Math.round(absolute * 3_600_000)" in authority:
        failures.append("duration still rounds through a hard-coded hour/minute algorithm")
    if "function resolveDeclaredTemporal(" not in authority:
        failures.append("date and datetime values do not require declared temporal authority")
    if "temporal.kind" not in authority or "timezoneAuthority" not in authority:
        failures.append("temporal kind and timezone authority are not consumed")
    if "if (kind === 'date') return date;" not in field_semantics:
        failures.append("temporal display does not branch on the declared date kind")
    if "00:00:00') return date" in field_semantics:
        failures.append("datetime display still downgrades midnight values by value shape")
    if ".resolvedOptions().maximumFractionDigits" in authority:
        failures.append("monetary precision still falls back to currency-code metadata")
    if "const scale = resolveMonetaryScale(digits);" not in authority:
        failures.append("monetary helpers do not validate declared digits through the shared scale authority")
    if "presentDeclaredBusinessValue" not in kanban_adapter:
        failures.append("Kanban adapter does not consume declared business-value semantics")
    if "unit: option?.unit" not in kanban_adapter:
        failures.append("Kanban adapter drops the declared field unit")

    shape_runtime = _read("app/action_runtime/useActionViewContractShapeRuntime.ts", read_text)
    if "isRegisteredComponentKey(declaredComponentKey)" not in shape_runtime:
        failures.append("collection projection does not validate declared component identity through the semantic registry")
    if "['sc.value.duration', 'sc.value.percentage'].includes(declaredComponentKey)" in shape_runtime:
        failures.append("collection projection still hard-codes a partial component identity allowlist")

    canonical_form = _read("pages/contractForm/canonicalFormRenderer.ts", read_text)
    if "function declaredSelectionOptions(field: CanonicalFormField)" not in canonical_form:
        failures.append("canonical form projection does not consolidate declared selection authority")
    if "const selection = declaredSelectionOptions(field);" not in canonical_form:
        failures.append("canonical form controls do not consume the declared selection projection")
    if "selectionOptions: selection," not in canonical_form:
        failures.append("canonical form controls do not consume the declared selection projection")
    if "selectionOptions: selectionOptions(config.selection)" in canonical_form:
        failures.append("canonical form controls still read component selection instead of the declared projection")
    if "String(item[1] ?? item[0] ?? '')" in canonical_form:
        failures.append("canonical form still synthesizes a selection label from its storage key")

    relation_descriptor = _read("pages/contractForm/relationDescriptor.ts", read_text)
    if "relation_model_consistency" not in relation_descriptor:
        failures.append("relation target consumers do not reject conflicting relation and relationEntry models")
    if "relation !== entryModel" not in relation_descriptor:
        failures.append("relation target consistency does not compare both declared carriers")
    relation_field_utils = _read("pages/contractForm/fieldUtils.ts", read_text)
    if "#${id}" in relation_descriptor or "#${id}" in relation_field_utils:
        failures.append("relation display still synthesizes a #id label from record identity")

    display = _read("utils/display.ts", read_text)
    if "presentDeclaredBusinessValue({" not in display:
        failures.append("[CFG-001] generic display does not delegate declared business values to the shared authority")
    if "missing: 'fieldDescriptor'" not in display or "formatUndeclaredDisplayValue" in display:
        failures.append("[CFG-001] generic display retains an undeclared value-formatting fallback")
    if "containsAttachmentReference(" in display:
        failures.append("[CFG-010] generic display still infers attachment behavior from text appearance")
    for forbidden in (
        "isSelectionFieldType",
        "isScalarRelationFieldType",
        "formatNumericFieldValue",
        "formatTemporalFieldValue",
        "match ? String(item[1]) : String(value)",
    ):
        if forbidden in display:
            failures.append(
                f"[CFG-009] generic display retains an independent declared-value semantic branch: {forbidden}"
            )

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
    if (
        "function hasAttachmentIdentity(field: string)" not in list_page
        or "return hasDeclaredAttachmentIdentity(columnSemanticInput(field));" not in list_page
    ):
        failures.append("[CFG-010] ListPage does not require declared attachment identity")

    list_cells = _read("pages/listPage/listCellPresentation.ts", read_text)
    if "presentDeclaredBusinessValue" not in list_cells:
        failures.append("[CFG-002] List cells bypass the shared declared business-value authority")
    if "unit: column.unit" not in list_cells:
        failures.append("[CFG-004] List cells drop the declared field unit")
    for forbidden in ("selectionText", "String(displayRaw)", "String(raw)"):
        if forbidden in list_cells:
            failures.append(f"[CFG-002] List cells retain a raw-value fallback: {forbidden}")
    if (
        "COLLECTION_NUMERIC_EMPTY_TEXT" in list_cells
        or "numeric ? '0'" in list_cells
        or re.search(r"missing\)\s+text\s*=\s*['\"]0['\"]", list_cells)
    ):
        failures.append("list cells still turn missing numeric facts into zero")

    if "function selectionLabel(" in list_page:
        failures.append("[CFG-002] ListPage computes selection labels outside the shared authority")

    professional_status = _read(
        "components/professional-fields/professionalBusinessValueModel.ts",
        read_text,
    )
    if "function statusSemantic(" in professional_status:
        failures.append("professional business values keep a second status tone table")

    my_work = _read("app/presentation/productMyWorkPresentation.ts", read_text)
    if "normalizeDeclaredDigits([20, Number(value)])" not in my_work:
        failures.append("my-work money facts do not require declared digits")
    if "product_my_work.fact.money.digits" not in my_work:
        failures.append("my-work money facts do not report the missing precision contract")

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

    field_value = _read("components/FieldValue.vue", read_text)
    if "hasDeclaredAttachmentIdentity(props.field)" not in field_value:
        failures.append("[CFG-010] FieldValue does not require declared attachment identity")
    for marker in (
        "return presentDeclaredBusinessValue({",
        "hasDeclaredAttachmentIdentity(props.field)",
        "componentKey: props.componentKey",
        "widget: props.widget",
        "cellRole: props.cellRole",
        "dataType: props.dataType",
        "currencyField: props.currencyField",
    ):
        if marker not in field_value:
            failures.append(f"[CFG-004] FieldValue drops declared semantic marker {marker}")
    if "computed(() => parseAttachmentReferenceLinks(props.value))" in field_value:
        failures.append("[CFG-010] FieldValue derives attachment actions from value appearance")

    base_control = _read(
        "components/professional-fields/ProfessionalBaseFieldControl.vue",
        read_text,
    )
    for marker in (
        "presentDeclaredBusinessValue({",
        "componentKey: props.field.componentKey",
        "widget: props.field.widget",
        "currencyField: props.field.currencyField",
        "unit: props.field.unit",
    ):
        if marker not in base_control:
            failures.append(
                f"[CFG-004] ProfessionalBaseFieldControl drops declared semantic marker {marker}"
            )

    form_section = _read("components/template/FormSection.vue", read_text)
    for marker in (
        "presentDeclaredBusinessValue({",
        "componentKey: field.componentKey",
        "widget: field.widget",
        "digits: field.digits",
        "unit: field.unit",
        "currencyField: field.currencyField",
    ):
        if marker not in form_section:
            failures.append(f"[CFG-004] FormSection drops declared semantic marker {marker}")

    kanban = _read("pages/KanbanPage.vue", read_text)
    if "presentCollectionKanbanTitle({" not in kanban:
        failures.append("[CFG-004] Kanban title does not consume the declared title adapter")
    row_title_start = kanban.find("function rowTitle(")
    row_title_end = kanban.find("\n}", row_title_start + 1)
    row_title = kanban[row_title_start:row_title_end] if row_title_start >= 0 else ""
    for forbidden in ("formatValue(", "row.name", "row.display_name", "String(row.id"):
        if forbidden in row_title:
            failures.append(f"[CFG-004] Kanban title retains an undeclared fallback: {forbidden}")

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
    print(
        "[frontend_business_semantics_guard] PASS "
        "authority=shared consumers=declared rules=CFG-001,CFG-002,CFG-004,CFG-009"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
