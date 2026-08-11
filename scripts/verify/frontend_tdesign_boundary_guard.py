#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "frontend/apps/web"
SRC = WEB / "src"
ADAPTER = SRC / "components/design-system/tdesignAdapter.ts"
BRIDGE = SRC / "styles/tdesign-bridge.css"
MAIN = SRC / "main.ts"
PACKAGE = WEB / "package.json"

ALLOWED_RUNTIME_IMPORT = ADAPTER.resolve()
TDESIGN_IMPORT_RE = re.compile(
    r"(?:from\s*|import\s*)['\"]tdesign(?:-icons)?-vue-next(?:/[^'\"]*)?['\"]"
)
RAW_CONTROL_RE = re.compile(r"<(button|input|select|textarea|table)\b", re.IGNORECASE)
UNADAPTED_DATA_ENTRY_RE = re.compile(
    r"<(?:select|textarea)\b|<input\b(?![^>]*\btype\s*=\s*['\"](?:radio|file)['\"])[^>]*>",
    re.IGNORECASE | re.DOTALL,
)
EXPECTED_DEPENDENCIES = {
    "tdesign-vue-next": "1.20.5",
    "tdesign-icons-vue-next": "0.4.9",
}
REQUIRED_ADAPTER_EXPORTS = {
    "TButton",
    "TCheckbox",
    "TDatePicker",
    "TDialog",
    "TDrawer",
    "TEnhancedTable",
    "TInput",
    "TSelect",
    "TTag",
    "TTextarea",
}
REQUIRED_SC_ADAPTERS = {
    "ScButton.vue": "TButton",
    "ScCheckbox.vue": "TCheckbox",
    "ScDateField.vue": "TDatePicker",
    "ScDialog.vue": "TDialog",
    "ScDrawer.vue": "TDrawer",
    "ScHierarchyTable.vue": "TEnhancedTable",
    "ScTextField.vue": "TInput",
    "ScSelect.vue": "TSelect",
    "ScMultiSelect.vue": "TSelect",
    "ScStatusBadge.vue": "TTag",
    "ScTextArea.vue": "TTextarea",
}
REQUIRED_SURFACE_CONSUMERS = {
    "contract list": (SRC / "pages/ListPage.vue", "ScButton"),
    "contract form": (SRC / "components/template/FormSection.vue", "ScDateField"),
    "contract form text input": (SRC / "components/template/FormSection.vue", "ScTextField"),
    "contract form multiline input": (SRC / "components/template/FormSection.vue", "ScTextArea"),
    "contract form boolean input": (SRC / "components/template/FormSection.vue", "ScCheckbox"),
    "action surface search": (SRC / "components/action/ActionSurfaceToolbar.vue", "ScTextField"),
    "action surface structured select": (SRC / "components/action/ActionSurfaceToolbar.vue", "ScSelect"),
    "generic view field": (SRC / "components/view/ViewFieldRenderer.vue", "ScTextField"),
    "WBS hierarchy": (SRC / "components/action/HierarchyPlanner.vue", "ScHierarchyTable"),
}
def collect_direct_imports(
    src: Path = SRC,
    root: Path = ROOT,
    allowed_import: Path = ALLOWED_RUNTIME_IMPORT,
) -> list[str]:
    violations: list[str] = []
    for suffix in ("*.ts", "*.vue", "*.js", "*.mjs"):
        for path in src.rglob(suffix):
            if path.resolve() == allowed_import:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if TDESIGN_IMPORT_RE.search(text):
                try:
                    display = path.relative_to(root).as_posix()
                except ValueError:
                    display = path.as_posix()
                violations.append(display)
    return sorted(set(violations))


def collect_native_control_inventory(src: Path = SRC) -> dict[str, int]:
    inventory = {name: 0 for name in ("button", "input", "select", "textarea", "table")}
    for path in src.rglob("*.vue"):
        for control in RAW_CONTROL_RE.findall(path.read_text(encoding="utf-8", errors="ignore")):
            inventory[control.lower()] += 1
    return inventory


def collect_unadapted_data_entry_controls(
    src: Path = SRC,
    root: Path = ROOT,
) -> list[str]:
    violations: list[str] = []
    for path in src.rglob("*.vue"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not UNADAPTED_DATA_ENTRY_RE.search(text):
            continue
        try:
            display = path.relative_to(root).as_posix()
        except ValueError:
            display = path.as_posix()
        violations.append(display)
    return sorted(violations)


def validate() -> list[str]:
    errors: list[str] = []
    if not ADAPTER.is_file():
        errors.append("missing design-system TDesign adapter")
    else:
        adapter_text = ADAPTER.read_text(encoding="utf-8")
        for symbol in sorted(REQUIRED_ADAPTER_EXPORTS):
            if symbol not in adapter_text:
                errors.append(f"adapter missing export: {symbol}")
        if "from 'tdesign-vue-next';" in adapter_text:
            errors.append("adapter must use TDesign component subpath imports")
        if "from 'tdesign-icons-vue-next';" in adapter_text:
            errors.append("adapter must use TDesign icon subpath imports")

    if not BRIDGE.is_file():
        errors.append("missing TDesign semantic-token bridge")
    else:
        bridge_text = BRIDGE.read_text(encoding="utf-8")
        if "@import 'tdesign-vue-next/es/style/index.css';" not in bridge_text:
            errors.append("TDesign CSS must be loaded only through the semantic-token bridge")
        for token in (
            "--td-brand-color: var(--sc-semantic-surface-interactive);",
            "--td-bg-color-container: var(--sc-semantic-surface-panel);",
            "--td-text-color-primary: var(--sc-semantic-text-primary);",
            "--td-component-border: var(--sc-semantic-border-strong);",
        ):
            if token not in bridge_text:
                errors.append(f"semantic-token bridge missing: {token}")

    main_text = MAIN.read_text(encoding="utf-8", errors="ignore") if MAIN.is_file() else ""
    if "import './styles/tdesign-bridge.css';" not in main_text:
        errors.append("frontend bootstrap missing TDesign bridge import")

    package = json.loads(PACKAGE.read_text(encoding="utf-8")) if PACKAGE.is_file() else {}
    dependencies = package.get("dependencies", {})
    for name, expected in EXPECTED_DEPENDENCIES.items():
        actual = dependencies.get(name)
        if actual != expected:
            errors.append(f"{name} must be exactly pinned to {expected}; found {actual!r}")

    for path in collect_direct_imports():
        errors.append(f"direct TDesign import outside design-system adapter: {path}")

    for filename, primitive in REQUIRED_SC_ADAPTERS.items():
        path = SRC / "components/design-system" / filename
        text = path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""
        if f"from './tdesignAdapter'" not in text or primitive not in text:
            errors.append(f"{filename} must adapt {primitive} through tdesignAdapter")
        if "data-ui-engine=" not in text:
            errors.append(f"{filename} missing inspectable UI engine marker")

    for surface, (path, primitive) in REQUIRED_SURFACE_CONSUMERS.items():
        text = path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""
        if primitive not in text:
            errors.append(f"{surface} does not consume required SC primitive: {primitive}")
    for path in collect_unadapted_data_entry_controls():
        errors.append(f"source contains an unadapted native data-entry control: {path}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("[frontend-tdesign-boundary] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[frontend-tdesign-boundary] PASS")
    print("- vendor imports: design-system adapter only")
    print("- product theming: SC semantic-token bridge")
    print("- versions: exact and reviewable")
    print(f"- native control inventory: {json.dumps(collect_native_control_inventory(), ensure_ascii=False, sort_keys=True)}")
    print(f"- governed data-entry scope: all {len(list(SRC.rglob('*.vue')))} Vue source files")
    print("- controlled native exceptions: radio and file inputs only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
