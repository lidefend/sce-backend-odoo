#!/usr/bin/env python3
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def validate(read_text=lambda path: (ROOT / path).read_text(encoding="utf-8")) -> list[str]:
    failures: list[str] = []
    component = read_text("frontend/apps/web/src/components/professional-fields/ProfessionalBusinessValueControl.vue")
    model = read_text("frontend/apps/web/src/components/professional-fields/professionalBusinessValueModel.ts")
    section = read_text("frontend/apps/web/src/components/template/FormSection.vue")
    registry = read_text("frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts")
    assembler = read_text("addons/smart_core/core/unified_page_contract_v2_assembler.py")
    money = read_text("frontend/apps/web/src/components/design-system/ScMoney.vue")
    patterns = read_text("frontend/apps/web/src/styles/product-patterns.css")
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
    # 金额的重复文本来自无障碍标签：`ScMoney` 为读屏保留可访问名称，视觉隐藏交给共享
    # 样式。两者必须同时成立——删掉可访问名称是退化，共享样式失效则标签会「意外可见」，
    # 同一句话在页面上出现两次。该不变量此前只有截图佐证（`shot-price_unit.png`，工作树内
    # 已不存在），现固定为可重复断言。
    if 'class="sc-visually-hidden"' not in money or "{{ label }}：" not in money:
        failures.append("money control dropped its accessible label carrier")
    money_style = money.split("<style", 1)[1] if "<style" in money else ""
    if "sc-visually-hidden" in money_style:
        failures.append("money control overrides the shared visually-hidden style")
    rules = re.findall(r"\.sc-visually-hidden\s*\{(?P<body>[^}]*)\}", patterns)
    if len(rules) != 1:
        failures.append(
            "styles/product-patterns.css must declare .sc-visually-hidden exactly once, "
            f"got {len(rules)}"
        )
    hidden_body = rules[0] if rules else ""
    for prop in (
        "position: absolute !important",
        "width: 1px !important",
        "height: 1px !important",
        "overflow: hidden !important",
        "clip: rect(0, 0, 0, 0) !important",
        "clip-path: inset(50%) !important",
    ):
        if prop not in hidden_body:
            failures.append(f"shared visually-hidden style lost {prop}")
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
