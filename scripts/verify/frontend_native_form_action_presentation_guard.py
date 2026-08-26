#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RENDERER = ROOT / "frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue"
SMART_ACTION = ROOT / "frontend/apps/web/src/components/template/NativeSmartAction.vue"
OVERFLOW_MENU = ROOT / "frontend/apps/web/src/components/template/NativeActionOverflowMenu.vue"
VISUAL_SMOKE = ROOT / "scripts/verify/local_dev_candidate_visual_smoke.mjs"


def validate(source: str | None = None, smart_action: str | None = None, overflow_menu: str | None = None, visual_smoke: str | None = None) -> list[str]:
    text = source if source is not None else RENDERER.read_text(encoding="utf-8")
    smart = smart_action if smart_action is not None else SMART_ACTION.read_text(encoding="utf-8")
    overflow = overflow_menu if overflow_menu is not None else OVERFLOW_MENU.read_text(encoding="utf-8")
    smoke = visual_smoke if visual_smoke is not None else VISUAL_SMOKE.read_text(encoding="utf-8")
    failures: list[str] = []
    required = (
        "import ScButton from '../design-system/ScButton.vue'",
        "import ScInput from '../design-system/ScInput.vue'",
        '<ScInput\n            v-if="fieldConfigEditable && isEditableGroupNode(node)"',
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
    if text.count("<ScButton") != 2:
        failures.append(f"native form expected two ordinary action primitive branches, found {text.count('<ScButton')}")
    for event in ('@click.stop.prevent="emitNativeAction(buttonNode)"', '@click.stop.prevent="emitNativeAction(node)"'):
        if text.count(event) != 2:
            failures.append(f"native form changed action event authority: {event}")
    if 'class="native-tab"' not in text or 'class="native-title-favorite"' not in text:
        failures.append("stateful tab and favorite controls must remain native semantic controls")
    if ".native-container-title-editor {\n  min-width: 140px;\n  max-width: 260px;\n  height:" in text:
        failures.append("native group title editor overrides shared ScInput appearance")
    smart_required = (
        "import NativeSmartAction from './NativeSmartAction.vue'",
        '<NativeSmartAction',
        ':label="buttonLabel(buttonNode)"',
        ':label="buttonLabel(node)"',
        'data-semantic-component="NativeSmartAction"',
        'data-semantic-role="smart-action"',
        'class="native-smart-action native-action-btn native-action-btn--smart"',
        'native-action-btn--smart',
    )
    combined = f"{text}\n{smart}"
    for marker in smart_required:
        if marker not in combined:
            failures.append(f"native smart action lost governed semantic presentation: {marker}")
    if text.count("<NativeSmartAction") != 2:
        failures.append(f"native form expected two smart action branches, found {text.count('<NativeSmartAction')}")
    if ".native-action-btn--smart" in text:
        failures.append("native renderer must not retain parallel smart-action appearance")
    overflow_required = (
        "import NativeActionOverflowMenu from './NativeActionOverflowMenu.vue'",
        '<NativeActionOverflowMenu',
        '@select="emitNativeAction"',
        'data-semantic-component="NativeActionOverflowMenu"',
        'native-action-more-menu',
        'aria-haspopup="menu"',
        ':aria-expanded="open"',
        ':aria-controls="menuId"',
        'role="menu"',
        'role="menuitem"',
        '@keydown.down.stop.prevent="openMenu(\'first\')"',
        '@keydown.up.stop.prevent="openMenu(\'last\')"',
        '@keydown.esc.stop.prevent="close(true)"',
        '@keydown.tab="close()"',
        '@keydown="onMenuKeydown"',
        "const instanceId = useId()",
        "event.key === 'ArrowDown'",
        "event.key === 'ArrowUp'",
        "event.key === 'Home'",
        "event.key === 'End'",
        "event.key === 'Escape'",
        "if (!items.length) return",
        "document.addEventListener('pointerdown', onDocumentPointerDown)",
    )
    combined = f"{text}\n{overflow}"
    for marker in overflow_required:
        if marker not in combined:
            failures.append(f"native action overflow lost disclosure/menu semantics: {marker}")
    for private_state in ("openMoreKeys", "toggleMore(", "closeMore(", ".native-action-more-menu"):
        if private_state in text:
            failures.append(f"native renderer retained private overflow implementation: {private_state}")
    for evidence in (
        "exerciseNativeActionOverflow",
        'data-semantic-component="NativeSmartAction"',
        'data-semantic-component="NativeActionOverflowMenu"',
        "focusRestored",
        "menuItemCount > 0",
    ):
        if evidence not in smoke:
            failures.append(f"governed visual smoke lost native action evidence: {evidence}")
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_native_form_action_presentation_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_native_form_action_presentation_guard] PASS ordinary_sc_buttons=2")
