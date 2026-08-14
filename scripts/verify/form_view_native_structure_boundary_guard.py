#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guard native-form structure ownership boundaries.

The form chain has three responsibilities:

* Backend native/contract layer may preserve Odoo layout and add semantic
  metadata.
* Backend policy/low-code overlays may change field visibility/order/labels.
* Frontend must render native structure without inventing business grouping.

This guard keeps semantic guesses out of user-visible form structure.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ASSEMBLER_PATH = ROOT / "addons/smart_core/core/unified_page_contract_v2_assembler.py"
NATIVE_RENDERER_PATH = ROOT / "frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue"
CONTRACT_FORM_PATH = ROOT / "frontend/apps/web/src/pages/ContractFormPage.vue"
CONTRACT_MODE_SUPPORT_PATH = ROOT / "frontend/apps/web/src/pages/contractForm/ContractModeSupportPanel.vue"
LOW_CODE_FIELD_DIALOG_PATH = ROOT / "frontend/apps/web/src/pages/contractForm/LowCodeFieldCreateDialog.vue"


def _load_assembler():
    package_name = "smart_core_guard.core"
    root_package = sys.modules.setdefault("smart_core_guard", type(sys)("smart_core_guard"))
    core_package = sys.modules.setdefault(package_name, type(sys)(package_name))
    root_package.__path__ = [str(ROOT / "addons/smart_core")]
    core_package.__path__ = [str(ROOT / "addons/smart_core/core")]

    for dependency in ("source_authority", "contract_lifecycle"):
        dependency_path = ROOT / f"addons/smart_core/core/{dependency}.py"
        dependency_spec = importlib.util.spec_from_file_location(
            f"{package_name}.{dependency}", dependency_path,
        )
        dependency_module = importlib.util.module_from_spec(dependency_spec)
        assert dependency_spec and dependency_spec.loader
        sys.modules[f"{package_name}.{dependency}"] = dependency_module
        dependency_spec.loader.exec_module(dependency_module)

    spec = importlib.util.spec_from_file_location(
        f"{package_name}.unified_page_contract_v2_assembler",
        ASSEMBLER_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _walk(nodes: list[dict[str, Any]]):
    stack = list(nodes)
    while stack:
        node = stack.pop(0)
        if not isinstance(node, dict):
            continue
        yield node
        for key in ("children", "tabs", "pages", "nodes", "items"):
            value = node.get(key)
            if isinstance(value, list):
                stack.extend(item for item in value if isinstance(item, dict))


def _assert(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _backend_projection_checks(errors: list[str]) -> None:
    assembler = _load_assembler()
    tree = [
        {
            "type": "sheet",
            "containerType": "sheet",
            "containerId": "main.form.sheet",
            "children": [
                {
                    "type": "group",
                    "containerType": "group",
                    "containerId": "main.info",
                    "children": [
                        {"type": "field", "name": "name", "fieldInfo": {"type": "char", "label": "名称"}},
                    ],
                },
                {
                    "type": "group",
                    "containerType": "group",
                    "containerId": "detail.info",
                    "children": [
                        {"type": "field", "name": "line_ids", "fieldInfo": {"type": "one2many", "label": "明细"}},
                    ],
                },
            ],
        }
    ]
    assembler._standardize_business_form_default_tabs(  # pylint: disable=protected-access
        tree,
        model="payment.request",
        view_type="form",
        container_status=[],
    )
    nodes = list(_walk(tree))
    _assert(
        not any((node.get("containerType") or node.get("type")) == "notebook" for node in nodes),
        "backend must not project generic visible notebooks such as 主信息/业务明细",
        errors,
    )
    _assert(
        not any((node.get("containerType") or node.get("type")) == "page" for node in nodes),
        "backend must not project generic visible pages such as 主信息/业务明细",
        errors,
    )

    assembler._standardize_form_container_semantics(  # pylint: disable=protected-access
        tree,
        model="payment.request",
        view_type="form",
    )
    groups = [node for node in _walk(tree) if (node.get("containerType") or node.get("type")) == "group"]
    _assert(groups, "fixture should contain group nodes", errors)
    for node in groups:
        _assert(
            bool(str(node.get("semanticTitle") or "").strip()),
            "backend semantic standardizer should write semanticTitle metadata",
            errors,
        )
        _assert(
            not str(node.get("title") or node.get("label") or node.get("string") or "").strip(),
            "backend semantic standardizer must not write generated titles into visible title/label/string",
            errors,
        )


def _frontend_boundary_checks(errors: list[str]) -> None:
    native_renderer = NATIVE_RENDERER_PATH.read_text(encoding="utf-8")
    contract_form = CONTRACT_FORM_PATH.read_text(encoding="utf-8")
    contract_mode_support = CONTRACT_MODE_SUPPORT_PATH.read_text(encoding="utf-8")
    low_code_field_dialog = LOW_CODE_FIELD_DIALOG_PATH.read_text(encoding="utf-8")
    _assert(
        "if (type === 'group') return '';" in native_renderer,
        "frontend NativeFormTreeRenderer must keep Odoo group titles hidden",
        errors,
    )
    _assert(
        ':field-group-title="containerPolicyTitle(node, index)"' in native_renderer,
        "frontend should pass hidden group metadata for low-code placement without rendering it",
        errors,
    )
    _assert(
        "<ContractModeSupportPanel" in contract_form and "<LowCodeFieldCreateDialog" in contract_mode_support,
        "contract form should delegate low-code field creation through the support panel",
        errors,
    )
    _assert('class="low-code-field-create-form"' in low_code_field_dialog, "low-code field create dialog should exist", errors)
    _assert(
        "分组" not in low_code_field_dialog,
        "low-code field create dialog must not expose technical group selection",
        errors,
    )


def main() -> int:
    errors: list[str] = []
    _backend_projection_checks(errors)
    _frontend_boundary_checks(errors)
    if errors:
        print("[form_view_native_structure_boundary_guard] FAIL")
        for error in errors:
            print(f" - {error}")
        return 1
    print("[form_view_native_structure_boundary_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
