#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def validate(read_text=lambda path: (ROOT / path).read_text(encoding="utf-8")) -> list[str]:
    failures: list[str] = []
    component = read_text("frontend/apps/web/src/components/professional-fields/ProfessionalDetailCollectionControl.vue")
    model = read_text("frontend/apps/web/src/components/professional-fields/professionalDetailCollectionModel.ts")
    section = read_text("frontend/apps/web/src/components/template/FormSection.vue")
    renderer = read_text("frontend/apps/web/src/components/template/X2ManyRelationRenderer.vue")
    cell_editor = read_text("frontend/apps/web/src/components/template/One2ManyCellEditor.vue")
    sc_select = read_text("frontend/apps/web/src/components/design-system/ScSelect.vue")
    relation_types = read_text("frontend/apps/web/src/components/template/relationField.types.ts")
    relation_utils = read_text("frontend/apps/web/src/pages/contractForm/one2manyUtils.ts")
    relation_runtime = "\n".join((
        read_text("frontend/apps/web/src/pages/contractForm/useRecordRelationships.ts"),
        read_text("frontend/apps/web/src/pages/contractForm/one2manyColumnOptionsRuntime.ts"),
    ))
    relation_query = read_text("frontend/apps/web/src/components/template/one2manyRelationQuery.ts")
    relation_descriptor = read_text("frontend/apps/web/src/pages/contractForm/relationDescriptor.ts")
    action_presentation = read_text("frontend/apps/web/src/pages/contractForm/useRecordActionPresentation.ts")
    load_contract = read_text("addons/smart_core/handlers/load_contract.py")
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
        'data-semantic-component="ProfessionalDetailCollectionControl"', 'data-professional-field-family="detail-collection"', ':data-row-count', ':data-column-count',
        ':data-can-create', ':data-can-inline-edit', ':data-removed-row-count', ':data-validation-visible', ':data-summary-present',
    ):
        if marker not in component:
            failures.append(f"professional detail collection missing marker {marker}")
    for marker in ("data-detail-collection-heading", "data-detail-collection-title", "data-detail-collection-count", "data-detail-collection-actions", "data-detail-collection-content"):
        if marker not in renderer:
            failures.append(f"detail collection hierarchy missing {marker}")
    if "usesProfessionalOne2many(field) && relationAdapter" not in section:
        failures.append("FormSection does not route one2many through the detail collection adapter")
    if '!detailCollectionOwnsVisibleTitle(field)' not in section:
        failures.append("FormSection does not defer editable detail title ownership to the detail collection")
    if "if (!props.relationAdapter) return false;" not in section or "if (field.readonly || !props.relationAdapter)" in section:
        failures.append("readonly detail collections duplicate the collection-owned title as an external field label")
    if "return usesProfessionalOne2many(field) || usesPaymentSettlementDetailCollection(field);" not in section:
        failures.append("detail collection title ownership is not shared across formal detail renderers")
    if "<X2ManyRelationRenderer" not in section:
        failures.append("detail collection bypasses the governed x2many runtime")
    if "data-detail-collection-pagination" not in renderer or "one2manyPageSize = 20" not in renderer:
        failures.append("detail collection pagination is not bounded and explicit")
    if ("detailCollectionColumnPresentation(column, columnIndex, false)" not in renderer
            or "ellipsis: readonly &&" not in model):
        failures.append("detail collection editable controls are wrapped by TDesign text ellipsis")
    if ('<ScPopover' not in renderer
            or 'readonlyCellCanExpand(column, row[column.name])' not in renderer
            or ':aria-label="`查看完整${column.label}：${readonlyCellValue(row[column.name])}`"' not in renderer):
        failures.append("readonly detail truncation does not provide an actionable complete-value viewer")
    if ("detailCollectionMobileColumnSplit" not in model
            or "detailCollectionMobileColumnSplit" not in renderer
            or '<ScDisclosure' not in renderer
            or '查看其余 ${readonlyMobileAdditionalColumns.length} 项信息' not in renderer):
        failures.append("readonly mobile details do not preserve trailing facts behind an actionable disclosure")
    if "return one2manyRows.value.reduce" not in renderer:
        failures.append("detail collection amount total is not authoritative across every visible row")
    if "return paginatedOne2manyRows.value.reduce" in renderer:
        failures.append("detail collection amount total is incorrectly narrowed to the current page")
    if "if (!amountColumns.length || !one2manyRows.value.length) return [];" not in renderer:
        failures.append("detail collection does not preserve an explicit zero amount total")
    if "if (!o2mAmountTotal.value) return [];" in renderer:
        failures.append("detail collection hides the authoritative amount total when it is zero")
    if "_stateLabel: `全部 ${one2manyRows.value.length} 条合计`" not in renderer:
        failures.append("detail collection amount total does not explain its all-row aggregate scope")
    if ".filter(isO2mAmountColumn)" not in renderer or "amountColumns.forEach" not in renderer:
        failures.append("detail collection does not aggregate every authoritative monetary column")
    if ".find(isO2mAmountColumn)" in renderer:
        failures.append("detail collection silently narrows aggregation to the first monetary column")
    if "one2manyCanUnlink: (name: string) => boolean;" not in relation_types:
        failures.append("detail collection adapter omits backend unlink authority")
    if "return policies.can_create === true;" not in relation_utils:
        failures.append("detail collection create authority does not fail closed")
    if "return policies.can_unlink === true;" not in relation_utils:
        failures.append("detail collection unlink authority does not fail closed")
    if 'v-if="adapter.one2manyCanUnlink(field.name)"' not in renderer:
        failures.append("detail collection exposes row removal without unlink authority")
    if "if (!one2manyCanUnlink(fieldName)) return;" not in action_presentation:
        failures.append("detail collection row removal handler does not fail closed")
    if "one2manyRemovalLabels: (name: string, removedCount?: number)" not in relation_types:
        failures.append("detail collection adapter omits authoritative removal labels")
    if "one2manyRemovalLabelsFromPolicies" not in relation_utils:
        failures.append("detail collection removal labels do not consume backend policy")
    if renderer.count("adapter.one2manyRemovalLabels(field.name)") < 5:
        failures.append("detail collection removal actions do not use authoritative labels")
    if '>移除</ScButton>' in renderer:
        failures.append("detail collection hardcodes ambiguous removal wording")
    if '"解除关联" if field_meta.get("type") == "many2many" else "删除"' not in load_contract:
        failures.append("legacy relation actions do not distinguish unlink from child deletion")
    if "one2manyCanInlineEdit: (name: string) => boolean;" not in relation_types:
        failures.append("detail collection adapter omits backend inline-edit authority")
    if "return policies.inline_edit === true;" not in relation_utils:
        failures.append("detail collection inline-edit authority does not fail closed")
    if cell_editor.count("!adapter.one2manyCanInlineEdit(fieldName)") != 4:
        failures.append("detail collection inputs do not consistently consume inline-edit authority")
    if "queryOne2manyColumnOptions" not in relation_types or "column.relationReadable !== true" not in renderer:
        failures.append("detail collection relation columns do not consume authoritative relation access")
    if "one2manyColumnQueryScope" not in relation_types or "relationDependencies" not in relation_types:
        failures.append("detail collection relation query scope omits authoritative dependencies")
    if ("createOne2manyRelationRequestAuthority" not in renderer
            or "one2manyRelationResponseIsRelevant" not in renderer
            or renderer.count("one2manyRelationResponseIsRelevant(key, revision)") < 2
            or "return relationQueryAuthority.isCurrent(key, revision)" not in renderer
            or "relationActiveRequestRevisions[key] === revision" not in renderer
            or "!relationQueryTimers[key]" not in renderer):
        failures.append("detail collection relation requests are not latest-condition authoritative")
    if "JSON.stringify(row.values)" in renderer:
        failures.append("detail collection relation queries still depend on unrelated row values")
    if "preserveSelectedOne2manyRelationOption" not in renderer or "currentValue" not in relation_query:
        failures.append("detail collection search can discard the selected relation label")
    if ("selectedOne2manyRelationOption" not in renderer
            or "selectedOne2manyRelationOption" not in relation_query):
        failures.append("detail collection cannot render a selected relation without enumerating candidates")
    if "relationPopupAuthority.isOpen(key) && relationColumnCanQuery" not in renderer:
        failures.append("detail collection eagerly enumerates relation candidates before interaction")
    if ("popup-change" not in renderer
            or "o2mRelationSearchMap.value[key] === normalizedKeyword" not in renderer
            or '@search="onSearch"' not in sc_select
            or '@input-change=' in sc_select):
        failures.append("detail collection search lifecycle is not explicitly controlled")
    if "data-relation-query-state=\"error\"" not in cell_editor or "@click=\"$emit('retry')\"" not in cell_editor:
        failures.append("detail collection relation failure does not expose retry")
    if "analyzeDynamicRelationDomain" not in relation_descriptor or "relationDomainSupported" not in relation_utils:
        failures.append("unsupported detail relation domains do not fail closed")
    if "rowKey: string" not in relation_types or "rowValues[normalized] ?? formData[normalized]" not in relation_runtime:
        failures.append("detail collection relation domain is not bound to the current row and parent form")
    if "one2manyCellError" not in relation_types or 'role="alert"' not in cell_editor:
        failures.append("detail collection cell validation is not associated with its control")
    for marker in (
        ':id="controlId"',
        ':aria-label="column.label"',
        ':described-by="describedBy"',
        ':invalid="invalid"',
        "errorText.value ? props.errorId",
        "props.relationError ? relationErrorId.value",
        ':id="relationErrorId"',
    ):
        if marker not in cell_editor:
            failures.append(f"detail collection cell feedback association missing {marker}")
    if cell_editor.count(':id="controlId"') != 4 or cell_editor.count(':described-by="describedBy"') != 4:
        failures.append("detail collection controls do not consistently receive unique identity and active feedback references")
    if (renderer.count(':control-id="one2manyCellControlId(') != 2
            or ':control-id="one2manyCellControlId(field.name, row._key, column.name)"' not in renderer
            or ':control-id="one2manyCellControlId(field.name, row.key, column.name, \'mobile\')"' not in renderer):
        failures.append("desktop and mobile detail controls do not receive layout-scoped identities")
    if ':for="one2manyCellControlId(field.name, row.key, column.name, \'mobile\')"' not in renderer:
        failures.append("mobile detail labels are not associated with their visible controls")
    if "function one2manyCellControlId" not in renderer or "suffix = 'desktop'" not in renderer:
        failures.append("detail collection control identities are not stable and responsive-layout scoped")
    if renderer.count("<One2ManyCellEditor") != 2:
        failures.append("desktop and mobile detail layouts do not share the same cell editor")
    if renderer.count("adapter.one2manyEffectiveColumn(field.name,") != 2:
        failures.append("desktop and mobile detail cells do not consume row-specific modifiers")
    readonly_columns = renderer.split("const readonlyO2mTableColumns", 1)[-1].split("const o2mTableData", 1)[0]
    if "title: '行变更'" in readonly_columns or "stateColumn" in readonly_columns:
        failures.append("readonly detail collections expose draft row-change status as a primary column")
    readonly_template = renderer.split('<div v-if="field.readonly" class="o2m-readonly"', 1)[-1].split("<template v-else>", 1)[0]
    if "one2manyRowStateLabel(row)" in readonly_template:
        failures.append("readonly mobile detail cards expose draft row-change status")
    if "第 {{ (one2manyPage - 1) * one2manyPageSize + rowIndex + 1 }} 条" not in readonly_template:
        failures.append("readonly mobile detail cards omit stable row identity")
    if "one2manyEffectiveColumn: (name: string, row: RelationFieldRow, column: RelationFieldColumn)" not in relation_types:
        failures.append("detail collection adapter omits row-specific modifier consumption")
    if "title: column.label" not in renderer:
        failures.append("detail collection columns do not expose authoritative labels")
    if "if (!one2manyCanInlineEdit(fieldName)) return;" not in action_presentation:
        failures.append("detail collection field update handler does not fail closed")
    if "if (!one2manyCanCreate(fieldName)) return;" not in action_presentation:
        failures.append("detail collection row creation handler does not fail closed")
    if "Promise.resolve(dependencies.ensureRelationFieldDescriptors" in action_presentation:
        failures.append("detail collection row creation incorrectly waits for optional column hydration")
    if "one2manyCanOpenRow: (name: string, row: RelationFieldRow) => boolean;" not in relation_types:
        failures.append("detail collection adapter omits governed row-open authority")
    if 'v-if="adapter.one2manyCanOpenRow(field.name, row._row)"' not in renderer:
        failures.append("detail collection does not hide row-open without authority")
    if "recordId <= 0 || !dependencies.canOpenRelationRecord(" not in action_presentation:
        failures.append("detail collection row-open handler does not fail closed")
    if "<ScInput" not in cell_editor or "<ScSelect" not in cell_editor:
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
