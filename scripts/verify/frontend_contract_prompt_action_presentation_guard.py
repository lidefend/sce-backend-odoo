#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
VUE = "frontend/apps/web/src/pages/contractForm/ContractPromptActionForm.vue"
CSS = "frontend/apps/web/src/pages/contractForm/ContractPromptActionForm.css"
PAGE_CSS = "frontend/apps/web/src/pages/contractForm/ContractFormPage.css"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def validate(read_text: Callable[[str], str] = _read) -> list[str]:
    vue = read_text(VUE)
    css = read_text(CSS)
    page_css = read_text(PAGE_CSS)
    errors: list[str] = []
    for component in ("ScFormField", "ScInput", "ScSelect", "ScButton"):
        if f"<{component}" not in vue:
            errors.append(f"prompt presentation must consume {component}")
    for semantic in (
        'data-semantic-component="ContractPromptActionForm"',
        'data-semantic-component="ContractPromptActionBar"',
    ):
        if semantic not in vue:
            errors.append(f"prompt presentation missing semantic identity: {semantic}")
    for boundary in (
        "@submit.prevent=\"$emit('submit')\"",
        "@click=\"$emit('cancel')\"",
        "@update:model-value=\"$emit('value-change', { fieldName: field.name, value: $event })\"",
    ):
        if boundary not in vue:
            errors.append(f"prompt presentation changed event authority: {boundary}")
    if "<input" in vue or "<select" in vue or "<button" in vue:
        errors.append("prompt presentation must not restore private native controls")
    if vue.count(':required="field.required"') != 3:
        errors.append("prompt presentation must preserve field and native control required semantics")
    primitive_input = read_text("frontend/apps/web/src/components/design-system/ScInput.vue")
    primitive_select = read_text("frontend/apps/web/src/components/design-system/ScSelect.vue")
    if ':required="required"' not in primitive_input or ':required="required"' not in primitive_select:
        errors.append("prompt primitives must project required to the native control")
    if 'variant="primary"' not in vue or vue.count('variant="primary"') != 1:
        errors.append("prompt presentation must expose exactly one primary action")
    if "grid-template-columns" not in css or "@media (max-width: 640px)" not in css:
        errors.append("prompt presentation must retain responsive field/action layout")
    parent_rule = re.search(r"\.action-prompt-form\s*\{(?P<body>[^}]*)\}", page_css)
    if not parent_rule or "grid-column: 1 / -1;" not in parent_rule.group("body"):
        errors.append("prompt presentation must retain parent page grid integration")
    if ".contract-mode-prompt {" in page_css:
        errors.append("prompt presentation parent page must use the model-neutral selector")
    if "--sc-space-" in css or "--sc-color-" in css:
        errors.append("prompt presentation directly consumes primitive design tokens")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("[frontend_contract_prompt_action_presentation_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[frontend_contract_prompt_action_presentation_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
