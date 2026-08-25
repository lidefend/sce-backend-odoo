#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLBAR = ROOT / "frontend/apps/web/src/components/action/ActionSurfaceToolbar.vue"
LIST_PAGE = ROOT / "frontend/apps/web/src/pages/ListPage.vue"


def validate(source: str | None = None, list_source: str | None = None) -> list[str]:
    text = source if source is not None else TOOLBAR.read_text(encoding="utf-8")
    list_text = list_source if list_source is not None else LIST_PAGE.read_text(encoding="utf-8")
    failures: list[str] = []
    required = (
        'data-semantic-component="CollectionActionToolbar"',
        ':data-open-layer=',
        'aria-controls="collection-search-disclosure"',
        'aria-controls="collection-toolbar-overflow"',
        ':aria-expanded="searchMenuOpen"',
        ':aria-expanded="overflowMenuOpen"',
        ':aria-pressed="currentViewMode === mode"',
        ':aria-pressed="option.value === sortValue"',
        "document.addEventListener('keydown', handleDocumentKeyDown)",
        "document.removeEventListener('keydown', handleDocumentKeyDown)",
        'searchMenuToggle.value?.focus()',
        'overflowMenuToggle.value?.focus()',
        'focusOpenLayer',
    )
    for marker in required:
        if marker not in text:
            failures.append(f"collection toolbar missing {marker}")
    if 'role="menu"' in text or 'role="menuitem"' in text:
        failures.append("collection toolbar disclosure must preserve native button semantics")
    required_list = (
        'data-semantic-component="CollectionBatchActionBar"',
        ':data-direct-action-keys=',
        ':data-overflow-action-keys=',
        'resolveCollectionBatchActionSettlement(selectionActions.value)',
        'selectionDirectActions',
        'selectionOverflowActions',
        'aria-controls="collection-batch-overflow"',
        "document.addEventListener('keydown', closeBatchOverflowOnEscape)",
        'batchOverflowToggle.value?.focus()',
    )
    for marker in required_list:
        if marker not in list_text:
            failures.append(f"collection batch action bar missing {marker}")
    if 'v-for="(action, actionIndex) in selectionActions"' in list_text:
        failures.append("collection batch actions must not duplicate overflow actions in the direct row")
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_collection_action_toolbar_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_collection_action_toolbar_guard] PASS disclosures=2")
