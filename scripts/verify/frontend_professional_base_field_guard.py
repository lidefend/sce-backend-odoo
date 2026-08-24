#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def validate(read_text=lambda path: (ROOT / path).read_text(encoding="utf-8")) -> list[str]:
    failures: list[str] = []
    component = read_text("frontend/apps/web/src/components/professional-fields/ProfessionalBaseFieldControl.vue")
    model = read_text("frontend/apps/web/src/components/professional-fields/professionalBaseFieldModel.ts")
    section = read_text("frontend/apps/web/src/components/template/FormSection.vue")
    renderer = read_text("frontend/apps/web/src/pages/contractForm/canonicalFormRenderer.ts")
    registry = read_text("frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts")
    for field_type in ("char", "text", "html", "integer", "float", "date", "datetime", "boolean", "selection"):
        if f"'{field_type}'" not in model:
            failures.append(f"base field model missing {field_type}")
    for marker in (
        'data-professional-field-family="base"', ":data-professional-field-type", ":data-control-kind",
        ":data-presentation-mode", ":data-render-profile", ":data-control-state",
    ):
        if marker not in component:
            failures.append(f"professional base field missing marker {marker}")
    if "<ProfessionalBaseFieldControl" not in section or "isProfessionalBaseFieldCandidate" not in section:
        failures.append("FormSection does not route through the professional base field family")
    if "ProfessionalBaseFieldControl" not in registry or "rendererByFieldType[fieldType]" not in registry:
        failures.append("component registry does not authorize the professional base field renderer")
    for marker in ("presentationMode: field.presentationMode", "renderProfile: field.renderProfile"):
        if marker not in renderer:
            failures.append(f"canonical renderer missing profile projection {marker}")
    for forbidden in ("payment.request", "project.project", "action_id", "menu_id", "付款", "项目"):
        if forbidden in component or forbidden in model:
            failures.append(f"base field family contains forbidden product special case {forbidden}")
    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("[frontend_professional_base_field_guard] FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("[frontend_professional_base_field_guard] PASS fields=9")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
