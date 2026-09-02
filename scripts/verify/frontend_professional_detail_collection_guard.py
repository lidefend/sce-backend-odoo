#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def validate(read_text=lambda path: (ROOT / path).read_text(encoding="utf-8")) -> list[str]:
    failures: list[str] = []
    component = read_text("frontend/apps/web/src/components/professional-fields/ProfessionalDetailCollectionControl.vue")
    model = read_text("frontend/apps/web/src/components/professional-fields/professionalDetailCollectionModel.ts")
    section = read_text("frontend/apps/web/src/components/template/FormSection.vue")
    renderer = read_text("frontend/apps/web/src/components/template/X2ManyRelationRenderer.vue")
    registry = read_text("frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts")
    assembler = read_text("addons/smart_core/core/unified_page_contract_v2_assembler.py")
    project_layout = read_text("addons/smart_construction_core/core_extension_project_layout.py")
    example = read_text("docs/architecture/unified_page_contract_v2/examples/nested_form_relation.json")
    if "sc.relation.table" not in model or "ProfessionalDetailCollectionControl" not in registry:
        failures.append("detail collection registry authority is incomplete")
    if 'field_type == "one2many"' not in assembler or 'return "sc.relation.table"' not in assembler:
        failures.append("one2many is not projected to the detail collection authority")
    if '"componentKey": "sc.table.data"' in project_layout:
        failures.append("project layout extension still emits legacy sc.table.data component keys")
    if '"sc.relation.table"' not in project_layout or '"sc.relation.many2many"' not in project_layout:
        failures.append("project layout extension does not register formal relation component keys")
    if '"componentKey": "sc.table.relation"' in example or '"sc.table.relation": {' in example:
        failures.append("nested form relation example still uses legacy sc.table.relation authority")
    if '"componentKey": "sc.relation.table"' not in example or '"sc.relation.table": {' not in example:
        failures.append("nested form relation example does not document formal sc.relation.table authority")
    for marker in (
        'data-professional-field-family="detail-collection"', ':data-row-count', ':data-column-count',
        ':data-can-create', ':data-removed-row-count', ':data-validation-visible', ':data-summary-present',
    ):
        if marker not in component:
            failures.append(f"professional detail collection missing marker {marker}")
    if "usesProfessionalOne2many(field) && relationAdapter" not in section:
        failures.append("FormSection does not route one2many through the detail collection adapter")
    if "<X2ManyRelationRenderer" not in section:
        failures.append("detail collection bypasses the governed x2many runtime")
    if "data-detail-collection-pagination" not in renderer or "one2manyPageSize = 20" not in renderer:
        failures.append("detail collection pagination is not bounded and explicit")
    if "return one2manyRows.value.reduce" not in renderer:
        failures.append("detail collection amount total is not authoritative across every visible row")
    if "return paginatedOne2manyRows.value.reduce" in renderer:
        failures.append("detail collection amount total is incorrectly narrowed to the current page")
    if "if (!amountCol || !one2manyRows.value.length) return [];" not in renderer:
        failures.append("detail collection does not preserve an explicit zero amount total")
    if "if (!o2mAmountTotal.value) return [];" in renderer:
        failures.append("detail collection hides the authoritative amount total when it is zero")
    if "<ScInput" not in renderer or "<ScSelect" not in renderer:
        failures.append("editable detail rows bypass the governed input/select primitives")
    if "--sc-component-relation-dropdown-z-index" not in renderer or "--sc-component-relation-dropdown-shadow" not in renderer:
        failures.append("relation dropdown stacking and elevation are not token governed")
    for forbidden in ("payment.request", "project.project", "action_id", "menu_id", "付款", "项目"):
        if forbidden in component or forbidden in model:
            failures.append(f"detail collection contains forbidden product special case {forbidden}")
    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("[frontend_professional_detail_collection_guard] FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("[frontend_professional_detail_collection_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
