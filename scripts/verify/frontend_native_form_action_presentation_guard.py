#!/usr/bin/env python3
from pathlib import Path
import re
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[2]
RENDERER = ROOT / "frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue"
SMART_ACTION = ROOT / "frontend/apps/web/src/components/template/NativeSmartAction.vue"
OVERFLOW_MENU = ROOT / "frontend/apps/web/src/components/template/NativeActionOverflowMenu.vue"
VISUAL_SMOKE = ROOT / "scripts/verify/local_dev_candidate_visual_smoke.mjs"


def native_button_ownership_errors(source: str) -> list[str]:
    template = re.sub(r"<!--[\s\S]*?-->", "", source.split("<script", 1)[0])
    class Buttons(HTMLParser):
        def __init__(self):
            super().__init__()
            self.calls = []
            self.duplicate_attributes = []

        def handle_starttag(self, tag, attrs):
            if tag == "scbutton":
                names = [name for name, _ in attrs]
                if len(names) != len(set(names)):
                    self.duplicate_attributes.append(names)
                self.calls.append(dict(attrs))

    parser = Buttons()
    parser.feed(template)
    attrs = parser.calls
    actions = [item for item in attrs if item.get("class") == "native-action-btn"]
    toggles = [item for item in attrs if item.get("v-else-if") == "isCollapsibleContainer(node)"]
    anchors = [item for item in attrs if item.get("v-else-if") == "node.nodeComponent?.kind === 'anchor'"]
    failures = []
    if parser.duplicate_attributes:
        failures.append("native button/anchor has duplicate attributes")
    if len(actions) != 2:
        failures.append("native form expected two ordinary action branches and one container disclosure")
    # Classify every control; do not just raise the global count from 3 to 4.
    # The declared anchor is navigation, not an ordinary business action.
    if any(sum((item in actions, item in toggles, item in anchors)) != 1 for item in attrs):
        failures.append("native form has an unclassified or multiply classified button")
    anchor_expected = {
        "v-else-if": "node.nodeComponent?.kind === 'anchor'",
        "type": "button", "variant": "ghost",
        ":data-contract-container-id": "node.containerId",
        "@click": "navigateExplicit(node, $event)",
    }
    if len(anchors) != 1 or anchors[0] != anchor_expected:
        failures.append("declared anchor must only navigate within the current form")
    for node in ("buttonNode", "node"):
        expected = {"v-if": f"!isSmartButtonNode({node})", "v-bind": f"nativeActionEvidenceAttributes({node})",
                    "type": "button", ":disabled": f"nativeActionDisabled({node})", ":title": f"nativeActionTitle({node})",
                    "@click.stop.prevent": f"emitNativeAction({node})"}
        if sum(all(item.get(key) == value for key, value in expected.items()) for item in actions) != 1:
            failures.append(f"native ordinary action must retain disabled and event authority: {node}")
    expected = {"type": "button", "variant": "ghost", "appearance": "context-action",
                ":aria-expanded": "String(!isContainerCollapsed(node, index))",
                "@click": "toggleContainerCollapsed(node, index)"}
    if (len(toggles) != 1 or any(toggles[0].get(key) != value for key, value in expected.items())
            or set(toggles[0]) - {*expected, "v-else-if", "size"}):
        failures.append("container disclosure must only toggle local collapsed state")
    return failures


def validate(source: str | None = None, smart_action: str | None = None, overflow_menu: str | None = None, visual_smoke: str | None = None) -> list[str]:
    text = source if source is not None else RENDERER.read_text(encoding="utf-8")
    smart = smart_action if smart_action is not None else SMART_ACTION.read_text(encoding="utf-8")
    overflow = overflow_menu if overflow_menu is not None else OVERFLOW_MENU.read_text(encoding="utf-8")
    smoke = visual_smoke if visual_smoke is not None else VISUAL_SMOKE.read_text(encoding="utf-8")
    failures: list[str] = []
    required = (
        "import ScButton from '../design-system/ScButton.vue'",
        "import ScInput from '../design-system/ScInput.vue'",
        "import ScTabs, { type ScTabItem } from '../design-system/ScTabs.vue'",
        '<ScInput\n            v-if="fieldConfigEditable && isEditableGroupNode(node)"',
        'v-if="!isSmartButtonNode(buttonNode)"',
        'class="native-action-btn"',
        'size="small"',
        'variant="secondary"',
        '@click.stop.prevent="emitNativeAction(buttonNode)"',
        'v-else-if="nodeType(node) === \'button\'"',
        'v-if="!isSmartButtonNode(node)"',
        '@click.stop.prevent="emitNativeAction(node)"',
        '<ScTabs',
        ':items="notebookTabItems(node)"',
    )
    for marker in required:
        if marker not in text:
            failures.append(f"native ordinary action lost governed presentation: {marker}")
    if "function nativeActionButtonClass" in text:
        failures.append("native form must not retain a parallel ordinary-button class resolver")
    if any(marker in text for marker in ("<button", "<input", "<select", "<textarea")):
        failures.append("native form retains a raw interactive control outside the primitive adapters")
    private_appearance = (
        ".native-action-btn {\n  display:",
        ".native-action-btn {\n  border:",
        ".native-action-btn:hover",
        ".native-action-btn:focus-visible",
        ".native-action-btn:disabled",
    )
    if any(marker in text for marker in private_appearance):
        failures.append("native ordinary actions must not override ScButton appearance or states")
    failures.extend(native_button_ownership_errors(text))
    for event in ('@click.stop.prevent="emitNativeAction(buttonNode)"', '@click.stop.prevent="emitNativeAction(node)"'):
        if text.count(event) != 2:
            failures.append(f"native form changed action event authority: {event}")
    if "labelClass: `native-tab${" not in text:
        failures.append("stateful notebook tabs must retain their semantic identity")
    if "import ScIconButton from '../design-system/ScIconButton.vue'" not in text or '<ScIconButton\n              v-if="titleFieldForNode(node)?.favoriteToggle"' not in text:
        failures.append("native title favorite must consume the shared icon-button primitive")
    if '<ScInput\n              v-if="!titleFieldForNode(node)?.readonly"' not in text:
        failures.append("native editable title must consume the shared input primitive")
    if ".native-container-title-editor {\n  min-width: 140px;\n  max-width: 260px;\n  height:" in text:
        failures.append("native group title editor overrides shared ScInput appearance")
    smart_required = (
        "import NativeSmartAction from './NativeSmartAction.vue'",
        "import ScButton from '../design-system/ScButton.vue'",
        '<ScButton',
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
    if 'buttonChildren(node).filter((button) => segment.nodes.includes(button))' not in text:
        failures.append("native action group must render the complete ordered visible children")
    for marker in ("SMART_BUTTON_DIRECT_LIMIT", "visibleActionButtons(", "overflowActionButtons(",
                   "<NativeActionOverflowMenu", "openMoreKeys", "toggleMore(", "closeMore("):
        if marker in text:
            failures.append(f"native action group has undeclared folding: {marker}")
    smart_layout = re.search(r"\.native-actions--smart\s*\{([^}]*)\}", text)
    if not smart_layout or re.search(r"overflow\s*:\s*(hidden|clip)", smart_layout.group(1)):
        failures.append("native smart group must not clip declared actions")
    for evidence in ("exerciseNativeActionGroup", "expectedNativeActionKeys", "declaredKeys", "renderedKeys"):
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
    print("[frontend_native_form_action_presentation_guard] PASS ordinary_sc_buttons=2 container_disclosures=1 declared_anchors=1")
