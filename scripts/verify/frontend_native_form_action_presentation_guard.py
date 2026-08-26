#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RENDERER = ROOT / "frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue"
SMART_ACTION = ROOT / "frontend/apps/web/src/components/template/NativeSmartAction.vue"


def validate(source: str | None = None, smart_action: str | None = None) -> list[str]:
    text = source if source is not None else RENDERER.read_text(encoding="utf-8")
    smart = smart_action if smart_action is not None else SMART_ACTION.read_text(encoding="utf-8")
    failures: list[str] = []
    required = (
        "import ScButton from '../design-system/ScButton.vue'",
        'v-if="!isSmartButtonNode(buttonNode)"',
        'class="native-action-btn"',
        'size="small"',
        'variant="secondary"',
        '@click.stop.prevent="emitNativeAction(buttonNode)"',
        'v-else-if="nodeType(node) === \'button\'"',
        'v-if="!isSmartButtonNode(node)"',
        '@click.stop.prevent="emitNativeAction(node)"',
    )
    for marker in required:
        if marker not in text:
            failures.append(f"native ordinary action lost governed presentation: {marker}")
    if "function nativeActionButtonClass" in text:
        failures.append("native form must not retain a parallel ordinary-button class resolver")
    private_appearance = (
        ".native-action-btn {\n  display:",
        ".native-action-btn {\n  border:",
        ".native-action-btn:hover",
        ".native-action-btn:focus-visible",
        ".native-action-btn:disabled",
    )
    if any(marker in text for marker in private_appearance):
        failures.append("native ordinary actions must not override ScButton appearance or states")
    if text.count("<ScButton") != 3:
        failures.append(f"native form expected two ordinary action branches and one disclosure trigger, found {text.count('<ScButton')}")
    for event in ('@click.stop.prevent="emitNativeAction(buttonNode)"', '@click.stop.prevent="emitNativeAction(node)"'):
        if text.count(event) != 2:
            failures.append(f"native form changed action event authority: {event}")
    if 'class="native-tab"' not in text or 'class="native-title-favorite"' not in text:
        failures.append("stateful tab and favorite controls must remain native semantic controls")
    smart_required = (
        "import NativeSmartAction from './NativeSmartAction.vue'",
        '<NativeSmartAction',
        ':label="buttonLabel(buttonNode)"',
        ':label="buttonLabel(node)"',
        'data-semantic-component="NativeSmartAction"',
        'data-semantic-role="smart-action"',
        'class="native-smart-action"',
    )
    combined = f"{text}\n{smart}"
    for marker in smart_required:
        if marker not in combined:
            failures.append(f"native smart action lost governed semantic presentation: {marker}")
    if text.count("<NativeSmartAction") != 2:
        failures.append(f"native form expected two smart action branches, found {text.count('<NativeSmartAction')}")
    if ".native-action-btn--smart" in text:
        failures.append("native renderer must not retain parallel smart-action appearance")
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_native_form_action_presentation_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_native_form_action_presentation_guard] PASS ordinary_sc_buttons=2")
