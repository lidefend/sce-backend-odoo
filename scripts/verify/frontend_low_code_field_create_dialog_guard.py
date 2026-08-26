#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
VUE = "frontend/apps/web/src/pages/contractForm/LowCodeFieldCreateDialog.vue"
CSS = "frontend/apps/web/src/pages/contractForm/LowCodeFieldCreateDialog.css"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def validate(read_text: Callable[[str], str] = _read) -> list[str]:
    vue = read_text(VUE)
    css = read_text(CSS)
    errors: list[str] = []
    for component in ("ScDialog", "ScFormField", "ScInput", "ScSelect", "ScButton"):
        if f"<{component}" not in vue:
            errors.append(f"field create dialog must consume {component}")
    for identity in (
        'data-semantic-component="LowCodeFieldCreateForm"',
        'data-semantic-component="LowCodeFieldCreateActions"',
    ):
        if identity not in vue:
            errors.append(f"field create dialog missing semantic identity: {identity}")
    for boundary in (
        "@submit.prevent=\"$emit('submit')\"",
        "@click=\"$emit('close')\"",
        "@update:model-value=\"$emit('update:label', $event)\"",
        "@update:model-value=\"$emit('update:ttype', $event)\"",
    ):
        if boundary not in vue:
            errors.append(f"field create dialog changed event authority: {boundary}")
    if any(tag in vue for tag in ("<input", "<select", "<button")):
        errors.append("field create dialog must not restore private native controls")
    if vue.count(" required") < 4 or "autofocus" not in vue:
        errors.append("field create dialog must preserve required and autofocus semantics")
    if vue.count('variant="primary"') != 1:
        errors.append("field create dialog must expose exactly one primary action")
    options = ('value="char"', 'value="text"', 'value="integer"', 'value="float"', 'value="boolean"', 'value="date"', 'value="datetime"', 'value="html"')
    if any(vue.count(option) != 1 for option in options):
        errors.append("field create dialog changed the formal field type options")
    if "@media (max-width: 480px)" not in css:
        errors.append("field create dialog must retain responsive action layout")
    if "contract-mode" in vue or "contract-mode" in css or ".chip-btn" in css or ".ghost" in css:
        errors.append("field create dialog must not retain legacy prompt styling")
    if "--sc-space-" in css or "--sc-color-" in css:
        errors.append("field create dialog directly consumes primitive design tokens")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("[frontend_low_code_field_create_dialog_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[frontend_low_code_field_create_dialog_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
