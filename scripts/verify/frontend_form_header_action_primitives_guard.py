#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
HEADER = "frontend/apps/web/src/pages/contractForm/ContractFormProductHeader.vue"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def validate(read_text: Callable[[str], str] = _read) -> list[str]:
    source = read_text(HEADER)
    errors: list[str] = []
    if "import ScButton" not in source or source.count("<ScButton") < 8:
        errors.append("form header actions must consume the shared ScButton primitive")
    if source.count("<button") != 0 or "import ScSteps" not in source or "<ScSteps" not in source or '@select="activateStatus(String($event))"' not in source:
        errors.append("workflow status steps must consume the shared ScSteps primitive")
    if "import ScDropdown" not in source or len(re.findall(r"<ScDropdown(?:\s|>)", source)) != 2:
        errors.append("header overflow actions must consume the shared ScDropdown primitive")
    for event in (
        "@click=\"$emit('back')\"",
        "@click=\"$emit('continue-processing')\"",
        "@click=\"$emit('run-primary')\"",
        "@click=\"$emit('run-action', action)\"",
        "@click=\"$emit('canonical-action', action)\"",
        "@click=\"$emit('canonical-save')\"",
        "@click=\"$emit('discard')\"",
    ):
        if event not in source:
            errors.append(f"form header changed action event authority: {event}")
    for evidence in (
        'v-bind="actionEvidenceAttributes(action)"',
        'v-bind="canonicalActionEvidenceAttributes(action)"',
        'data-product-primary-action',
        ':data-mobile-action-keys=',
        'dispatchDropdownAction',
    ):
        if evidence not in source:
            errors.append(f"form header lost action evidence: {evidence}")
    if "function buttonVariant" not in source or "action.destructive ? 'danger'" not in source:
        errors.append("form header must preserve destructive and primary business variants")
    if "function canonicalButtonVariant" not in source or "action.tier === 'primary'" not in source:
        errors.append("form header must preserve canonical primary variants")
    if "buttonClass(" in source or "canonicalButtonClass(" in source:
        errors.append("form header must not retain private button class adapters")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("[frontend_form_header_action_primitives_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[frontend_form_header_action_primitives_guard] PASS shared_action_and_workflow_drivers=1 raw_buttons=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
