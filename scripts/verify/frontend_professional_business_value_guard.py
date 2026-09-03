#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def validate(read_text=lambda path: (ROOT / path).read_text(encoding="utf-8")) -> list[str]:
    failures: list[str] = []
    component = read_text("frontend/apps/web/src/components/professional-fields/ProfessionalBusinessValueControl.vue")
    model = read_text("frontend/apps/web/src/components/professional-fields/professionalBusinessValueModel.ts")
    section = read_text("frontend/apps/web/src/components/template/FormSection.vue")
    registry = read_text("frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts")
    assembler = read_text("addons/smart_core/core/unified_page_contract_v2_assembler.py")
    keys = (
        "sc.value.money", "sc.value.percentage", "sc.display.status",
        "sc.value.duration",
    )
    for key in keys:
        if key not in model or key not in registry or key not in assembler:
            failures.append(f"business value authority is incomplete for {key}")
    for marker in (
        'data-professional-field-family="business-value"', ':data-business-value-kind',
        ':data-presentation-mode', ':data-render-profile', ':data-control-state',
    ):
        if marker not in component:
            failures.append(f"professional business value missing marker {marker}")
    if "<ProfessionalBusinessValueControl" not in section or "isProfessionalBusinessValueField" not in section:
        failures.append("FormSection does not route through the professional business-value family")
    if "ProfessionalBusinessValueControl" not in registry:
        failures.append("component registry does not authorize the business-value renderer")
    for forbidden in ("payment.request", "project.project", "action_id", "menu_id", "付款", "项目"):
        if forbidden in component or forbidden in model:
            failures.append(f"business-value family contains forbidden product special case {forbidden}")
    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("[frontend_professional_business_value_guard] FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("[frontend_professional_business_value_guard] PASS families=7")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
