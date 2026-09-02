#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def validate(read_text=lambda path: (ROOT / path).read_text(encoding="utf-8")) -> list[str]:
    failures: list[str] = []
    component = read_text("frontend/apps/web/src/components/professional-fields/ProfessionalRelationFieldControl.vue")
    many2one = read_text("frontend/apps/web/src/components/professional-fields/ProfessionalMany2oneFieldControl.vue")
    model = read_text("frontend/apps/web/src/components/professional-fields/professionalRelationFieldModel.ts")
    section = read_text("frontend/apps/web/src/components/template/FormSection.vue")
    registry = read_text("frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts")
    assembler = read_text("addons/smart_core/core/unified_page_contract_v2_assembler.py")
    x2many = read_text("frontend/apps/web/src/components/template/X2ManyRelationRenderer.vue")
    relationship_fields = read_text("frontend/apps/web/src/pages/contractForm/useRecordRelationshipFields.ts")
    for key in ("sc.relation.many2one", "sc.relation.many2many", "sc.select.tags"):
        if key not in model or key not in registry or key not in assembler:
            failures.append(f"relation authority is incomplete for {key}")
    for marker in (
        'data-professional-field-family="relation"', ':data-relation-kind', ':data-relation-model',
        ':data-relation-create-mode', ':data-presentation-mode', ':data-render-profile', ':data-control-state',
    ):
        if marker not in component:
            failures.append(f"professional relation field missing marker {marker}")
    if section.count("<ProfessionalRelationFieldControl") < 2:
        failures.append("FormSection does not route many2one and many2many through the relation family")
    if "import ScButton from '../design-system/ScButton.vue'" not in many2one or many2one.count("<ScButton") != 5:
        failures.append("many2one options and lifecycle commands must consume five shared ScButton primitives")
    if "import ScInput from '../design-system/ScInput.vue'" not in section or '<ScInput\n              v-else-if="fieldConfigEditable"' not in section:
        failures.append("field configuration label editor must consume the shared ScInput primitive")
    if ".field-label-editor {\n  flex: 1 1 140px;\n  min-width: 96px;\n  max-width: 220px;\n  height:" in section:
        failures.append("field configuration label editor overrides shared ScInput appearance")
    for marker in (
        'v-if="field.many2oneOpenToken"',
        'v-if="field.many2oneSearchToken"',
        'field.many2oneCreateToken',
        'v-if="showInlineCreate"',
    ):
        if marker not in many2one:
            failures.append(f"many2one lifecycle command authority is incomplete: {marker}")
    if ".many2one-action:hover" in many2one or ".many2one-action {\n  min-height:" in many2one:
        failures.append("many2one lifecycle commands override shared ScButton presentation")
    if '<ScButton\n                type="button"' not in many2one:
        failures.append("many2one stateful listbox options must consume the shared ScButton primitive")
    for marker in (
        'adapter.isOne2manyHydrating(field.name)',
        'data-readonly-relation-loading',
        'state="loading"',
    ):
        if marker not in x2many:
            failures.append(f"readonly one2many loading semantics are incomplete: {marker}")
    for marker in (
        'const one2manyHydrating = reactive<Record<string, boolean>>({})',
        'one2manyHydrating[name] = true',
        'one2manyHydrating[name] = false',
        'finally',
    ):
        if marker not in relationship_fields:
            failures.append(f"one2many hydration lifecycle is incomplete: {marker}")
    for forbidden in ("payment.request", "project.project", "action_id", "menu_id", "付款", "项目"):
        if forbidden in component or forbidden in many2one or forbidden in model:
            failures.append(f"relation family contains forbidden product special case {forbidden}")
    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("[frontend_professional_relation_field_guard] FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("[frontend_professional_relation_field_guard] PASS relation_types=2 readonly_hydration=field_scoped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
