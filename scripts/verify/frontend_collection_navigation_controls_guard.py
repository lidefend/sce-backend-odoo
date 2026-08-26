#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPONENT = ROOT / "frontend/apps/web/src/components/product-list/CollectionPaginationFooter.vue"
GROUPING_COMPONENT = ROOT / "frontend/apps/web/src/components/product-list/CollectionGroupingToolbar.vue"
COLUMN_COMPONENT = ROOT / "frontend/apps/web/src/components/product-list/CollectionColumnHeaderControl.vue"
GROUP_PAGE_COMPONENT = ROOT / "frontend/apps/web/src/components/product-list/CollectionGroupPageControls.vue"
LIST_PAGE = ROOT / "frontend/apps/web/src/pages/ListPage.vue"
LIST_STYLE = ROOT / "frontend/apps/web/src/pages/ListPage.css"


def validate(
    component_source: str | None = None,
    list_source: str | None = None,
    grouping_source: str | None = None,
    column_source: str | None = None,
    group_page_source: str | None = None,
) -> list[str]:
    component = component_source if component_source is not None else COMPONENT.read_text(encoding="utf-8")
    list_page = list_source if list_source is not None else LIST_PAGE.read_text(encoding="utf-8")
    grouping = grouping_source if grouping_source is not None else GROUPING_COMPONENT.read_text(encoding="utf-8")
    column = column_source if column_source is not None else COLUMN_COMPONENT.read_text(encoding="utf-8")
    group_page = group_page_source if group_page_source is not None else GROUP_PAGE_COMPONENT.read_text(encoding="utf-8")
    failures: list[str] = []
    required = (
        'data-semantic-component="CollectionPaginationFooter"',
        ':data-pagination-mode="mode"',
        ':aria-label="labels.region"',
        'aria-live="polite"',
        '<ScButton',
        '<ScInput',
        '<ScSelect',
        "mode === 'grouped'",
        "mode === 'paged'",
    )
    for marker in required:
        if marker not in component:
            failures.append(f"collection pagination footer missing {marker}")
    list_required = (
        '<CollectionPaginationFooter',
        'resolveCollectionPaginationMode({',
        'resolveCollectionPageOffset({',
        'resolveCollectionPageJump({',
        'resolveCollectionPageLimit(raw, listLimit.value)',
    )
    for marker in list_required:
        if marker not in list_page:
            failures.append(f"list page missing collection pagination authority {marker}")
    if '<section v-if="showGroupedWindowPagination" class="pagination-footer">' in list_page:
        failures.append("list page retains parallel grouped pagination DOM")
    if '<section v-else-if="showPagination" class="pagination-footer">' in list_page:
        failures.append("list page retains parallel paged pagination DOM")
    legacy_style = LIST_STYLE.read_text(encoding="utf-8")
    if ".pagination-btn {" in legacy_style or ".pagination-input {" in legacy_style:
        failures.append("list page retains parallel pagination component styles")
    grouping_required = (
        'data-semantic-component="CollectionGroupingToolbar"',
        ':data-group-count="groupCount"',
        '<ScButton',
        '<ScSelect',
        'aria-live="polite"',
    )
    for marker in grouping_required:
        if marker not in grouping:
            failures.append(f"collection grouping toolbar missing {marker}")
    if '<header class="grouped-toolbar">' in list_page:
        failures.append("list page retains parallel grouping toolbar DOM")
    column_required = (
        'data-semantic-component="CollectionColumnHeaderControl"',
        '<div',
        'class="column-drag-handle"',
        ':label="dragLabel"',
        'class="column-resize-handle"',
        ':label="resizeLabel"',
        "@dragstart.stop=\"$emit('drag-start', $event)\"",
        "@mousedown.stop.prevent=\"$emit('resize-start', $event)\"",
    )
    for marker in column_required:
        if marker not in column:
            failures.append(f"collection column header missing {marker}")
    if any(marker in column for marker in ("<button", "<input", "<select", "<textarea")):
        failures.append("collection column header retains a raw control outside primitive adapters")
    if list_page.count('h(CollectionColumnHeaderControl') != 1 or 'title: () => collectionHeader(field)' not in list_page:
        failures.append("list page must use one shared TDesign column-header adapter for flat and grouped tables")
    if '<th\n              v-for="col in displayedColumns"' in list_page:
        failures.append("list page retains parallel column header DOM")
    legacy_style = LIST_STYLE.read_text(encoding="utf-8")
    if ".column-drag-handle {" in legacy_style or ".column-resize-handle {" in legacy_style:
        failures.append("list page retains parallel column header component styles")
    group_page_required = (
        'data-semantic-component="CollectionGroupPageControls"',
        ':data-group-key="groupKey"',
        ':aria-label="regionLabel"',
        'aria-live="polite"',
        '<ScButton',
        '<ScInput',
    )
    for marker in group_page_required:
        if marker not in group_page:
            failures.append(f"collection group page controls missing {marker}")
    if '<CollectionGroupPageControls' not in list_page:
        failures.append("list page missing shared group page controls")
    if 'class="group-page-btn"' in list_page or 'class="group-page-input"' in list_page:
        failures.append("list page retains parallel group page controls DOM")
    if ".group-page-btn {" in legacy_style or ".group-page-input {" in legacy_style:
        failures.append("list page retains parallel group page control styles")
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_collection_navigation_controls_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_collection_navigation_controls_guard] PASS modes=3 shared_controls=4")
