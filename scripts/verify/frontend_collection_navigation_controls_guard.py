#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPONENT = ROOT / "frontend/apps/web/src/components/product-list/CollectionPaginationFooter.vue"
LIST_PAGE = ROOT / "frontend/apps/web/src/pages/ListPage.vue"
LIST_STYLE = ROOT / "frontend/apps/web/src/pages/ListPage.css"


def validate(component_source: str | None = None, list_source: str | None = None) -> list[str]:
    component = component_source if component_source is not None else COMPONENT.read_text(encoding="utf-8")
    list_page = list_source if list_source is not None else LIST_PAGE.read_text(encoding="utf-8")
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
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_collection_navigation_controls_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_collection_navigation_controls_guard] PASS modes=3")
