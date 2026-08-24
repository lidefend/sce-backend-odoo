#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def validate(read_text=lambda path: (ROOT / path).read_text(encoding="utf-8")) -> list[str]:
    failures: list[str] = []
    component = read_text("frontend/apps/web/src/components/professional-fields/ProfessionalRelationFieldControl.vue")
    model = read_text("frontend/apps/web/src/components/professional-fields/professionalRelationFieldModel.ts")
    section = read_text("frontend/apps/web/src/components/template/FormSection.vue")
    registry = read_text("frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts")
    assembler = read_text("addons/smart_core/core/unified_page_contract_v2_assembler.py")
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
    for forbidden in ("payment.request", "project.project", "action_id", "menu_id", "付款", "项目"):
        if forbidden in component or forbidden in model:
            failures.append(f"relation family contains forbidden product special case {forbidden}")
    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("[frontend_professional_relation_field_guard] FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("[frontend_professional_relation_field_guard] PASS relation_types=2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
