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
OWNERSHIP = ROOT / "docs/frontend_productization/rendering-detail/rendering-surface-ownership-v1.json"

PRIMITIVES = (
    "ScButton", "ScIconButton", "ScCheckbox", "ScRadioGroup", "ScRadio", "ScInput", "ScInputGroup", "ScLayout", "ScAside", "ScHeader", "ScContent", "ScInlineState", "ScTextarea", "ScSelect", "ScDialog", "ScDrawer", "ScTabs", "ScTable",
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
CONSUMER_PRIMITIVE_CHROME = re.compile(
    r":deep\(\.sc-(?:input|btn|select|textarea|checkbox|radio|dialog|drawer|tabs|table)[^)]*\)\s*\{(?P<body>[^}]*)\}",
    re.DOTALL,
)
VISUAL_CHROME_PROPERTY = re.compile(r"(?:^|;)\s*(?:border(?!-(?:collapse|spacing))(?:-[a-z]+)?|background|border-radius|box-shadow|outline|color)\s*:", re.MULTILINE)
SC_ROOT_TAG = re.compile(r"<Sc(?:Button|IconButton|Input|InputGroup|Select|Textarea|Checkbox|Radio|Dialog|Drawer|Tabs|Table)\b(?P<attrs>[^>]*)>", re.DOTALL)
STATIC_CLASS = re.compile(r"(?<!:)\bclass\s*=\s*['\"](?P<value>[^'\"]+)['\"]")
DYNAMIC_CLASS_ATTR = re.compile(r":class\s*=\s*(['\"])(?P<value>.*?)\1", re.DOTALL)
DYNAMIC_CLASS = re.compile(r"(?:['\"](?P<quoted>[A-Za-z][\w-]*)['\"]|(?P<bare>[A-Za-z][\w-]*))\s*:")
ALL_STATIC_CLASS = re.compile(r"(?<!:)\bclass\s*=\s*['\"](?P<value>[^'\"]+)['\"]")
STYLE_RULE = re.compile(r"(?P<selector>[^{}]+)\{(?P<body>[^{}]*)\}", re.DOTALL)
STYLE_SOURCE = re.compile(r"<style\b[^>]*\bsrc\s*=\s*['\"](?P<value>[^'\"]+)['\"][^>]*>", re.IGNORECASE)
PROFESSIONAL_COMPOSITE_OWNERS: set[str] = set()


def p3_scope(root: Path) -> tuple[set[str], tuple[str, ...]]:
    path = root / OWNERSHIP.relative_to(ROOT)
    if not path.is_file():
        return set(), ()
    import json
    payload = json.loads(path.read_text(encoding="utf-8"))
    owner = payload.get("owners", {}).get("p3-low-code-administration", {})
    return set(owner.get("sources", [])), tuple(owner.get("prefixes", []))


def direct_root_visual_overrides(source_text: str, style_text: str | None = None) -> list[str]:
    classes: set[str] = set()
    for tag in SC_ROOT_TAG.finditer(source_text):
        match = STATIC_CLASS.search(tag.group("attrs"))
        if match:
            classes.update(value for value in match.group("value").split() if value and not value.startswith("sc-"))
        for binding in DYNAMIC_CLASS_ATTR.finditer(tag.group("attrs")):
            for dynamic in DYNAMIC_CLASS.finditer(binding.group("value")):
                value = dynamic.group("quoted") or dynamic.group("bare")
                if value and value not in {"active", "selected", "disabled"} and not value.startswith("sc-"):
                    classes.add(value)
    findings = []
    for rule in STYLE_RULE.finditer(style_text if style_text is not None else source_text):
        if not VISUAL_CHROME_PROPERTY.search(rule.group("body")):
            continue
        selector = rule.group("selector")
        for class_name in sorted(classes):
            if re.search(rf"\.{re.escape(class_name)}(?![\w-])", selector):
                findings.append(class_name)
    return sorted(set(findings))


def native_descendant_visual_overrides(source_text: str, style_text: str | None = None) -> list[str]:
    if not SC_ROOT_TAG.search(source_text):
        return []
    container_classes = {
        value
        for match in ALL_STATIC_CLASS.finditer(source_text)
        for value in match.group("value").split()
        if value and not value.startswith("sc-")
    }
    findings: list[str] = []
    for rule in STYLE_RULE.finditer(style_text if style_text is not None else source_text):
        selector = rule.group("selector")
        if "<style" in selector:
            selector = selector.rsplit("<style", 1)[1].split(">", 1)[-1]
        if not re.search(r"(?:^|[\s>+~])(?:button|input|select|textarea)(?:\b|[:.#[])", selector):
            continue
        if not re.search(r"(?:^|;)\s*(?:border(?:-[a-z]+)?|background|border-radius|box-shadow|outline|color|padding(?:-[a-z]+)?|width|min-width|max-width|height|min-height|max-height)\s*:", rule.group("body"), re.MULTILINE):
            continue
        for class_name in sorted(container_classes):
            if re.search(rf"\.{re.escape(class_name)}(?![\w-])", selector):
                findings.append(selector.strip())
                break
    return sorted(set(findings))


def component_style_text(path: Path, source_text: str) -> str:
    styles = [source_text]
    for match in STYLE_SOURCE.finditer(source_text):
        target = (path.parent / match.group("value")).resolve()
        if target.is_file() and target.suffix == ".css":
            styles.append(target.read_text(encoding="utf-8"))
    return "\n".join(styles)


def validate(root: Path = ROOT) -> list[str]:
    design = root / "frontend/apps/web/src/components/design-system"
    index = (design / "index.ts").read_text(encoding="utf-8") if (design / "index.ts").is_file() else ""
    bridge = (design / "tdesignPrimitiveBridge.ts").read_text(encoding="utf-8") if (design / "tdesignPrimitiveBridge.ts").is_file() else ""
    ui_primitives_path = root / "frontend/packages/ui/src/primitives.ts"
    ui_primitives = ui_primitives_path.read_text(encoding="utf-8") if ui_primitives_path.is_file() else ""
    ui_theme_path = root / "frontend/packages/ui/src/kits/tdesign/theme.css"
    ui_theme = ui_theme_path.read_text(encoding="utf-8") if ui_theme_path.is_file() else ""
    errors: list[str] = []

    source_root = root / "frontend/apps/web/src"
    p3_files, p3_prefixes = p3_scope(root)
    if source_root.is_dir():
        for path in sorted(source_root.rglob("*.vue")):
            relative = path.relative_to(root).as_posix()
            if "/components/design-system/" in f"/{relative}" or relative in PROFESSIONAL_COMPOSITE_OWNERS:
                continue
            if relative in p3_files or relative.startswith(p3_prefixes):
                continue
            source_text = path.read_text(encoding="utf-8")
            style_text = component_style_text(path, source_text)
            if any(VISUAL_CHROME_PROPERTY.search(match.group("body")) for match in CONSUMER_PRIMITIVE_CHROME.finditer(style_text)):
                errors.append(f"consumer primitive visual chrome must move to an adapter appearance: {relative}")
            root_overrides = direct_root_visual_overrides(source_text, style_text)
            if root_overrides:
                errors.append(f"consumer primitive root classes must not own visual chrome: {relative} classes={','.join(root_overrides)}")
            descendant_overrides = native_descendant_visual_overrides(source_text, style_text)
            if descendant_overrides:
                errors.append(f"consumer containers must not repaint primitive native controls: {relative} selectors={','.join(descendant_overrides)}")

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
    if input_text.count(':data-appearance="appearance"') != 2:
        errors.append("ScInput must project its registered appearance to both standard and specialized drivers")
    if ':size="normalizePrimitiveSize(size)"' not in input_text or ':status="status"' not in input_text:
        errors.append("ScInput must delegate size and status to the official TDesign API")
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
        ':data-appearance="appearance"',
    ):
        if marker not in button_text:
            errors.append(f"ScButton missing governed interaction-state marker: {marker}")
    if "TDesignButton" not in bridge or "TDesignButton" not in ui_primitives:
        errors.append("ScButton must consume the public project TDesign button authority")
    icon_button_text = (design / "ScIconButton.vue").read_text(encoding="utf-8") if (design / "ScIconButton.vue").is_file() else ""
    if "<TDesignButton" not in icon_button_text or ':data-appearance="appearance"' not in icon_button_text:
        errors.append("ScIconButton must use the TDesign button driver and project registered appearances")

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
        "--td-text-color-placeholder: var(--sc-semantic-text-secondary)",
        "--td-border-level-2-color: var(--sc-semantic-border-strong)",
        ".sc-btn.t-button",
        ".sc-btn.t-button.sc-btn-primary[data-status='default']",
        ".sc-btn.t-button.sc-btn-primary[data-status='default']:hover:not(:disabled)",
        "background-color: var(--sc-semantic-surface-interactive)",
        "background-color: var(--sc-semantic-surface-interactive-hover)",
        "color: var(--sc-semantic-text-on-interactive)",
        "--sc-component-button-height-md",
    )
    if not ui_theme:
        errors.append("missing project TDesign visual projection bridge")
    else:
        for marker in visual_projection_markers:
            if marker not in ui_theme:
                errors.append(f"TDesign visual projection bridge missing marker: {marker}")
        if ".sc-btn.t-button.sc-btn-primary {" in ui_theme or ".sc-btn.t-button.sc-btn-primary:hover" in ui_theme:
            errors.append("primary button visual projection must preserve non-default status themes")
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
