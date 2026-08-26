#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = (
    ROOT / "frontend/apps/web/src/components/action/HierarchyBrowser.vue",
    ROOT / "frontend/apps/web/src/components/action/HierarchyPlanner.vue",
)
ACTION_VIEW = ROOT / "frontend/apps/web/src/views/ActionView.vue"
HEADER = ROOT / "frontend/apps/web/src/components/product-list/ProductListHeader.vue"


def require(text: str, needle: str, message: str, errors: list[str]) -> None:
    if needle not in text:
        errors.append(message)


def forbid(text: str, needle: str, message: str, errors: list[str]) -> None:
    if needle in text:
        errors.append(message)


def main() -> int:
    components = [(path.stem, path.read_text(encoding="utf-8")) for path in COMPONENTS]
    action_view = ACTION_VIEW.read_text(encoding="utf-8")
    header = HEADER.read_text(encoding="utf-8")
    errors: list[str] = []

    for component_name, component in components:
        for needle, label in (
            ("ProductListHeader", "standard ProductListHeader"),
            ("ScButton", "standard ScButton"),
            ("ScTable", "standard ScTable adapter"),
            ("ScEmptyState", "standard ScEmptyState"),
            ("hierarchyCollectionDataSource", "action-runtime hierarchy data source"),
            ("executeHierarchyCommand", "contract command runtime"),
            ("formatDisplayValue", "shared field display formatter"),
        ):
            require(component, needle, f"{component_name} must reuse {label}", errors)

        for needle, label in (
            ("../../api/", "API modules"),
            ("vue-router", "router modules"),
            ("<table", "a raw table"),
            ("<input", "a raw input"),
        ):
            forbid(component, needle, f"{component_name} presentation must not directly depend on {label}", errors)

        for needle in (
            "WBS", "LBS", "清单", "定额", "工作包", "分项", "标段",
            "project_id", "parent_id", "work_id", "boq_line_id", "construction.", "project.boq",
        ):
            forbid(component, needle, f"{component_name} must not contain business semantic token: {needle}", errors)

    require(action_view, '@open-record="handleRowClick"', "Hierarchy record navigation must use ActionView navigation runtime", errors)
    require(action_view, '@open-action="openHierarchyAction"', "Hierarchy actions must use the ActionView navigation adapter", errors)
    require(header, "product-list-header__tools--aligned", "ProductListHeader must own the reusable aligned-toolbar mode", errors)

    if errors:
        print("[hierarchy-browser-architecture] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[hierarchy-browser-architecture] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
