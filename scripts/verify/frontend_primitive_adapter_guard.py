#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
DESIGN_SYSTEM = ROOT / "frontend/apps/web/src/components/design-system"
INDEX = DESIGN_SYSTEM / "index.ts"
BRIDGE = DESIGN_SYSTEM / "tdesignPrimitiveBridge.ts"
UI_PRIMITIVES = ROOT / "frontend/packages/ui/src/primitives.ts"
UI_THEME = ROOT / "frontend/packages/ui/src/kits/tdesign/theme.css"

PRIMITIVES = (
    "ScButton", "ScCheckbox", "ScRadioGroup", "ScRadio", "ScInput", "ScInputGroup", "ScInlineState", "ScTextarea", "ScSelect", "ScDialog", "ScDrawer", "ScTabs", "ScTable",
    "ScBadge", "ScTooltip", "ScDropdown", "ScFormField", "ScLoading", "ScEmptyState", "ScErrorState",
    "ScActionBar", "ScAutoComplete", "ScNumberInput", "ScDatePicker", "ScUpload", "ScForm", "ScFormItem",
    "ScCard", "ScCollapse", "ScDisclosure", "ScProgress", "ScSkeleton", "ScDescriptions", "ScList", "ScTimeline",
    "ScSteps", "ScPagination", "ScSwitch", "ScTimePicker", "ScPopconfirm",
)
FORBIDDEN_PRIVATE_TDESIGN = re.compile(r"tdesign-vue-next/(?:lib|cjs|src)/")
FORBIDDEN_BUSINESS_IDENTITY = re.compile(
    r"\b(?:project\.project|payment\.request|construction\.contract|action_id|menu_id|role_code)\b",
    re.IGNORECASE,
)


def validate(root: Path = ROOT) -> list[str]:
    design = root / "frontend/apps/web/src/components/design-system"
    index = (design / "index.ts").read_text(encoding="utf-8") if (design / "index.ts").is_file() else ""
    bridge = (design / "tdesignPrimitiveBridge.ts").read_text(encoding="utf-8") if (design / "tdesignPrimitiveBridge.ts").is_file() else ""
    ui_primitives_path = root / "frontend/packages/ui/src/primitives.ts"
    ui_primitives = ui_primitives_path.read_text(encoding="utf-8") if ui_primitives_path.is_file() else ""
    ui_theme_path = root / "frontend/packages/ui/src/kits/tdesign/theme.css"
    ui_theme = ui_theme_path.read_text(encoding="utf-8") if ui_theme_path.is_file() else ""
    errors: list[str] = []

    for component in PRIMITIVES:
        source = design / f"{component}.vue"
        if not source.is_file():
            errors.append(f"missing primitive source: {source.relative_to(root)}")
            continue
        text = source.read_text(encoding="utf-8")
        if f"data-semantic-component=\"{component}\"" not in text and f"semanticPrimitiveIdentity('{component}')" not in text:
            errors.append(f"{component} missing exact semantic component identity")
        if "data-semantic-layer=\"primitive\"" not in text and "semanticPrimitiveIdentity(" not in text:
            errors.append(f"{component} missing primitive layer identity")
        if FORBIDDEN_PRIVATE_TDESIGN.search(text):
            errors.append(f"{component} imports a private TDesign path")
        if FORBIDDEN_BUSINESS_IDENTITY.search(text):
            errors.append(f"{component} contains business-specific identity")
        if f"export {{ default as {component} }}" not in index:
            errors.append(f"index.ts does not export {component}")

    for modal in ("ScDialog", "ScDrawer"):
        text = (design / f"{modal}.vue").read_text(encoding="utf-8") if (design / f"{modal}.vue").is_file() else ""
        driver = f"TDesign{modal.removeprefix('Sc')}"
        if f"<{driver}" not in text or 'role="dialog"' not in text or 'aria-modal="true"' not in text:
            errors.append(f"{modal} must use its TDesign overlay driver and preserve dialog semantics")
        overlay_kind = modal.removeprefix("Sc").lower()
        if f'data-overlay-kind="{overlay_kind}"' not in text or ':data-state="open ? \'open\' : \'closed\'"' not in text:
            errors.append(f"{modal} must expose deterministic overlay state")
        if f"--sc-component-{overlay_kind}-z-index" not in text:
            errors.append(f"{modal} must consume its registered overlay stacking token")

    input_text = (design / "ScInput.vue").read_text(encoding="utf-8") if (design / "ScInput.vue").is_file() else ""
    if "<TDesignInput" not in input_text or "v-native-control-projection" not in input_text or 'data-primitive-driver="browser-specialized"' not in input_text:
        errors.append("ScInput must use the TDesign driver with an explicit browser-specialized fallback")
    if ':aria-describedby="describedBy"' not in input_text or ':aria-invalid=' not in input_text:
        errors.append("ScInput must preserve accessible state through the adapter")
    if ':data-loading="loading || undefined"' not in input_text or ':aria-busy="loading || undefined"' not in input_text:
        errors.append("ScInput must expose loading state on the native input control")
    input_group_text = (design / "ScInputGroup.vue").read_text(encoding="utf-8") if (design / "ScInputGroup.vue").is_file() else ""
    if "<TDesignInputAdornment" not in input_group_text or 'data-primitive-driver="tdesign"' not in input_group_text:
        errors.append("ScInputGroup must delegate grouped input chrome to TDesign InputAdornment")
    if "TDesignInputAdornment" not in bridge or "TDesignInputAdornment" not in ui_primitives:
        errors.append("ScInputGroup must consume the public project TDesign InputAdornment authority")

    textarea_text = (design / "ScTextarea.vue").read_text(encoding="utf-8") if (design / "ScTextarea.vue").is_file() else ""
    if "<TDesignTextarea" not in textarea_text or "v-native-control-projection" not in textarea_text:
        errors.append("ScTextarea must use the TDesign driver and native accessibility projection")
    if ':aria-describedby="describedBy"' not in textarea_text or ':aria-invalid=' not in textarea_text:
        errors.append("ScTextarea must preserve accessible state through the adapter")
    if ':data-loading="loading || undefined"' not in textarea_text or ':aria-busy="loading || undefined"' not in textarea_text:
        errors.append("ScTextarea must expose loading state on the native textarea control")

    button_text = (design / "ScButton.vue").read_text(encoding="utf-8") if (design / "ScButton.vue").is_file() else ""
    for marker in (
        '<TDesignButton',
        ':data-loading="loading || undefined"',
        ':aria-disabled="disabled || loading || undefined"',
        ':loading="loading"',
        'tdesignButtonPresentation',
        'v-bind="attrs"',
        'inheritAttrs: false',
    ):
        if marker not in button_text:
            errors.append(f"ScButton missing governed interaction-state marker: {marker}")
    if "TDesignButton" not in bridge or "TDesignButton" not in ui_primitives:
        errors.append("ScButton must consume the public project TDesign button authority")

    checkbox_text = (design / "ScCheckbox.vue").read_text(encoding="utf-8") if (design / "ScCheckbox.vue").is_file() else ""
    for marker in (
        '<TDesignCheckbox',
        'v-native-control-projection',
        ':data-checked="checked || undefined"',
        ':data-indeterminate="indeterminate || undefined"',
        ':data-disabled="disabled || undefined"',
        "'aria-checked': props.indeterminate ? 'mixed' : String(props.checked)",
        "'aria-label': props.label",
    ):
        if marker not in checkbox_text:
            errors.append(f"ScCheckbox missing governed selection marker: {marker}")

    radio_text = (design / "ScRadioGroup.vue").read_text(encoding="utf-8") if (design / "ScRadioGroup.vue").is_file() else ""
    for marker in ('<TDesignRadioGroup', "semanticPrimitiveIdentity('ScRadioGroup')", ':options="options"', ':aria-required="required || undefined"'):
        if marker not in radio_text:
            errors.append(f"ScRadioGroup missing governed selection marker: {marker}")

    radio_item_text = (design / "ScRadio.vue").read_text(encoding="utf-8") if (design / "ScRadio.vue").is_file() else ""
    for marker in ('<TDesignRadio', "semanticPrimitiveIdentity('ScRadio')", ':checked="checked"', ':aria-required="required || undefined"'):
        if marker not in radio_item_text:
            errors.append(f"ScRadio missing governed selection marker: {marker}")

    select_text = (design / "ScSelect.vue").read_text(encoding="utf-8") if (design / "ScSelect.vue").is_file() else ""
    if ':data-readonly="readonly || undefined"' not in select_text or ':aria-readonly="readonly || undefined"' not in select_text:
        errors.append("ScSelect must expose readonly state without inventing write authority")
    if "<TDesignSelect" not in select_text or ':options="tdesignOptions"' not in select_text or "v-native-control-projection" not in select_text:
        errors.append("ScSelect must use the TDesign option driver and native accessibility projection")

    state_contracts = {
        "ScLoading": ('data-state', 'aria-busy'),
        "ScInlineState": (':data-state="state"', ':aria-busy="state === \'loading\' || undefined"'),
        "ScEmptyState": ('data-state="empty"', 'role="status"'),
        "ScErrorState": ('data-state="error"', 'role="alert"'),
        "ScFormField": (':data-state=', ':data-required='),
    }
    for component, markers in state_contracts.items():
        text = (design / f"{component}.vue").read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                errors.append(f"{component} missing deterministic state marker: {marker}")
    if "<TDesignEmpty" not in (design / "ScEmptyState.vue").read_text(encoding="utf-8"):
        errors.append("ScEmptyState must use the TDesign empty-state driver")
    if "<TDesignAlert" not in (design / "ScErrorState.vue").read_text(encoding="utf-8"):
        errors.append("ScErrorState must use the TDesign alert driver")

    if not bridge:
        errors.append("missing TDesign primitive bridge")
    else:
        if "@sc/ui/primitives" not in bridge or "tdesign-vue-next" in bridge:
            errors.append("web primitive bridge must consume the project UI authority")
        for driver in ("TDesignAlert", "TDesignButton", "TDesignCheckbox", "TDesignRadioGroup", "TDesignRadio", "TDesignDialog", "TDesignDrawer", "TDesignEmpty", "TDesignInput", "TDesignSelect", "TDesignTextarea"):
            if driver not in bridge or driver not in ui_primitives:
                errors.append(f"missing public project primitive driver: {driver}")
        for path in design.glob("*.vue"):
            text = path.read_text(encoding="utf-8")
            if "tdesign-vue-next" in text:
                errors.append(f"{path.name} bypasses the TDesign primitive bridge")

    if not ui_primitives:
        errors.append("missing project UI primitive driver authority")
    elif FORBIDDEN_PRIVATE_TDESIGN.search(ui_primitives) or "tdesign-vue-next/es/" not in ui_primitives:
        errors.append("project UI primitive driver must use TDesign public entrypoints")

    visual_projection_markers = (
        "--td-bg-color-specialcomponent: var(--sc-semantic-surface-input)",
        "--td-text-color-placeholder: var(--sc-semantic-text-muted)",
        "--td-border-level-2-color: var(--sc-semantic-border-strong)",
        ".sc-input.t-input__wrap[data-size='large'] > .t-input",
        ".sc-select[data-size='medium'] .t-input",
        ".sc-textarea .t-textarea__inner",
        ".sc-btn.t-button",
        "--sc-component-input-height-md",
        "--sc-component-button-height-md",
    )
    if not ui_theme:
        errors.append("missing project TDesign visual projection bridge")
    else:
        for marker in visual_projection_markers:
            if marker not in ui_theme:
                errors.append(f"TDesign visual projection bridge missing marker: {marker}")
        if FORBIDDEN_BUSINESS_IDENTITY.search(ui_theme):
            errors.append("TDesign visual projection bridge contains business-specific identity")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("[frontend_primitive_adapter_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"[frontend_primitive_adapter_guard] PASS components={len(PRIMITIVES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
