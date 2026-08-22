#!/usr/bin/env python3
"""Guard the shared detail/form product baseline without encoding business-specific fields."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "frontend/apps/web/src"


def read(relative: str) -> str:
    return (WEB / relative).read_text(encoding="utf-8")


def require(source: str, token: str, label: str) -> None:
    if token not in source:
        raise SystemExit(f"[frontend_detail_form_productization_guard] FAIL {label}: missing {token}")


page = read("pages/ContractFormPage.vue")
header = read("pages/contractForm/ContractFormProductHeader.vue")
canvas = read("pages/contractForm/ContractFormNativeCanvas.vue")
fields = read("components/template/FormSection.vue")
debug = read("config/debug.ts")
identity = read("app/pageIdentityAdapters.ts")
relations = read("pages/contractForm/useRecordFormFieldSchemas.ts")
actions = read("pages/contractForm/headerActionPresentation.ts")
settings = read("pages/contractForm/CurrentFormFieldSettingsPanel.css")
field_value = read("components/FieldValue.vue")
x2many = read("components/template/X2ManyRelationRenderer.vue")

require(page, '<ContractFormDriverHost v-if="!showCurrentFormFieldConfigScope"', "canonical product renderer")
require(page, "resolveRequestedContractRenderProfile({ routeName: route.name, recordId: recordId.value })", "explicit detail route semantics")
require(page, ":mode=\"renderProfile\"", "form mode projection")
require(page, ":dirty=\"hasChanges\"", "dirty-state projection")
require(page, "canonicalProductFloorplan.value.blockedActions.some((action) => action.tier === 'primary')", "blocked primary remediation source")
require(page, "blockedCanonicalPrimary.value ? '补充资料' : '继续办理'", "blocked primary remediation label")
require(page, "node.type === 'header' && !showCurrentFormFieldConfigScope.value", "duplicate native header suppression")
require(header, "aria-label=\"页面模式与保存状态\"", "mode and save-state semantics")
require(header, "已修改 ${changedFieldCount} 项", "dirty feedback")
require(header, ':disabled="busy || statusbar.readonly"', "readonly workflow is not interactive")
require(canvas, "填写业务信息", "create guidance")
require(canvas, "编辑业务信息", "edit guidance")
require(canvas, "showDefaultSectionTitle || mode === 'create'", "no redundant edit guidance above real sections")
require(fields, "field-state--required", "required-state label")
require(fields, "v-else-if=\"field.readonly\"", "readonly-state label")
require(identity, "normalizedFieldName === 'display_name'", "concise contract identity preference")
require(relations, "value:[Math.trunc(id),label]", "authorized relation label projection")
require(actions, ".filter((action) => !action.destructive).slice(0, 1)", "single direct action hierarchy")
require(header, "width: max-content", "content-driven workflow step width")
require(canvas, "behavior: 'auto'", "deterministic sticky anchor navigation")
require(settings, ".contract-form-field-search-item span", "designer field label containment")
require(settings, "overflow-wrap: anywhere", "designer field label wrapping")
require(field_value, "class=\"field-value\"", "readonly value containment")
require(x2many, 'v-if="field.readonly" class="relation-readonly" data-readonly-relation', "readonly many2many facts")

object_task_page = read("pages/contractForm/ObjectTaskPage.vue")
require(object_task_page, ".object-task-page--decision .object-task-page__current-task { order: -1; }", "mobile task priority")
require(object_task_page, "grid-template-columns: repeat(2, minmax(0, 1fr));", "mobile summary density")

if "import.meta.env.DEV ||" in debug:
    raise SystemExit("[frontend_detail_form_productization_guard] FAIL development mode still exposes HUD")
if '<FinancialRelationshipWorkspace v-if="financialWorkspace"' in page:
    raise SystemExit("[frontend_detail_form_productization_guard] FAIL edit route still renders readonly workspace first")

print("[frontend_detail_form_productization_guard] PASS")
