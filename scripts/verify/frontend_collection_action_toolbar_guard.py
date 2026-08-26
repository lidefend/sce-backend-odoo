#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLBAR = ROOT / "frontend/apps/web/src/components/action/ActionSurfaceToolbar.vue"
LIST_PAGE = ROOT / "frontend/apps/web/src/pages/ListPage.vue"
BATCH_BAR = ROOT / "frontend/apps/web/src/components/product-list/CollectionBatchActionBar.vue"
OVERFLOW_CONTROLLER = ROOT / "frontend/apps/web/src/app/presentation/useCollectionBatchOverflow.ts"


def validate(
    source: str | None = None,
    list_source: str | None = None,
    overflow_source: str | None = None,
    batch_source: str | None = None,
) -> list[str]:
    text = source if source is not None else TOOLBAR.read_text(encoding="utf-8")
    list_text = list_source if list_source is not None else LIST_PAGE.read_text(encoding="utf-8")
    overflow_text = overflow_source if overflow_source is not None else OVERFLOW_CONTROLLER.read_text(encoding="utf-8")
    batch_text = batch_source if batch_source is not None else BATCH_BAR.read_text(encoding="utf-8")
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
        'import ScInput',
        '<ScInput',
        'import ScInputGroup',
        '<ScInputGroup class="collection-search-control">',
        'import ScSelect',
        '<ScSelect v-model="customFilterField" size="small" :placeholder=',
        ':options="customFilterFields.map(',
        '<ScSelect v-model="customFilterOperator" size="small" :options=',
        ':options="activeCustomFilterOperators.map(',
        '<ScButton type="button" variant="primary" size="small" :disabled="!canApplyCustomFilter || loading"',
        '<ScButton type="button" variant="primary" size="small" :disabled="!favoriteName.trim() || loading"',
        'v-if="hasStructuredConditions"\n                class="toolbar-clear-all"',
        '<ScButton\n          v-if="canCreateRecord"\n          class="toolbar-overflow-create"',
        "'search-input': [value: string]",
        'var(--sc-semantic-focus-ring)',
        '@media (prefers-reduced-motion: reduce)',
    )
    for marker in required:
        if marker not in text:
            failures.append(f"collection toolbar missing {marker}")
    forbidden_legacy_actions = (
        '<button\n          v-if="hasStructuredConditions"\n          class="toolbar-clear-all"',
        '<button type="button" :disabled="!canApplyCustomFilter || loading"',
        '<button type="button" :disabled="!favoriteName.trim() || loading"',
        '<button\n          v-if="canCreateRecord"\n          class="toolbar-overflow-create"',
    )
    if any(marker in text for marker in forbidden_legacy_actions):
        failures.append("collection toolbar retains a generic legacy action control")
    native_searchbox_style = text[text.find(".native-searchbox {"):text.find(".collection-search-control {")]
    if any(marker in native_searchbox_style for marker in ("border:", "border-radius:", "background:", "padding:")):
        failures.append("collection toolbar legacy searchbox retains visual chrome outside ScInputGroup")
    stateful_semantic_controls = (
        'class="contract-chip"',
        'class="search-facet"',
        'class="search-menu-toggle"',
        'class="search-menu-item"',
        'class="toolbar-overflow-toggle"',
        '<ScCheckbox',
    )
    for marker in stateful_semantic_controls:
        if marker not in text:
            failures.append(f"collection toolbar lost stateful semantic control {marker}")
    if any(marker in text for marker in ("<button", "<input", "<select", "<textarea")):
        failures.append("collection toolbar retains a raw control outside primitive adapters")
    if 'role="menu"' in text or 'role="menuitem"' in text:
        failures.append("collection toolbar disclosure must preserve native button semantics")
    required_list = (
        '<CollectionBatchActionBar',
        ':actions="selectionActions"',
        '@action="runSelectionAction"',
        '@clear="clearSelection"',
    )
    for marker in required_list:
        if marker not in list_text:
            failures.append(f"collection list adapter missing {marker}")
    required_batch = (
        'data-semantic-component="CollectionBatchActionBar"',
        ':data-direct-action-keys=',
        ':data-overflow-action-keys=',
        'resolveCollectionBatchActionSettlement(props.actions)',
        'aria-controls="collection-batch-overflow"',
        'useCollectionBatchOverflow()',
        '<ScButton',
        'aria-live="polite"',
    )
    for marker in required_batch:
        if marker not in batch_text:
            failures.append(f"collection batch action bar missing {marker}")
    required_overflow = (
        "document.addEventListener('keydown', closeOnEscape)",
        "document.removeEventListener('keydown', closeOnEscape)",
        "root?.matches('button')",
        "root?.querySelector<HTMLElement>('button')",
    )
    for marker in required_overflow:
        if marker not in overflow_text:
            failures.append(f"collection batch overflow controller missing {marker}")
    batch_css = (ROOT / "frontend/apps/web/src/components/product-list/CollectionBatchActionBar.css").read_text(encoding="utf-8")
    if "var(--sc-toolbar-gap)" not in batch_css or "var(--sc-z-overlay)" not in batch_css:
        failures.append("collection batch action bar missing token-backed layout authority")
    if 'data-semantic-component="CollectionBatchActionBar"' in list_text:
        failures.append("list page retains parallel batch action bar DOM")
    if 'v-for="(action, actionIndex) in actions"' in batch_text:
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
