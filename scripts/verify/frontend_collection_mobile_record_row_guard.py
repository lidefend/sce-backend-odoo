#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIST_PAGE = ROOT / "frontend/apps/web/src/pages/ListPage.vue"
LIST_CSS = ROOT / "frontend/apps/web/src/pages/ListPage.css"
MOBILE_CSS = ROOT / "frontend/apps/web/src/pages/listPage/ListPageMobile.css"
ROW = ROOT / "frontend/apps/web/src/components/product-list/CollectionMobileRecordRow.vue"
ROW_CSS = ROOT / "frontend/apps/web/src/components/product-list/CollectionMobileRecordRow.css"
VISUAL_SMOKE = ROOT / "scripts/verify/local_dev_candidate_visual_smoke.mjs"


def validate(
    list_source: str | None = None,
    row_source: str | None = None,
    row_css_source: str | None = None,
    legacy_css_source: str | None = None,
    visual_source: str | None = None,
) -> list[str]:
    list_text = list_source if list_source is not None else LIST_PAGE.read_text(encoding="utf-8")
    row_text = row_source if row_source is not None else ROW.read_text(encoding="utf-8")
    row_css = row_css_source if row_css_source is not None else ROW_CSS.read_text(encoding="utf-8")
    legacy_css = legacy_css_source if legacy_css_source is not None else (
        LIST_CSS.read_text(encoding="utf-8") + MOBILE_CSS.read_text(encoding="utf-8")
    )
    visual_text = visual_source if visual_source is not None else VISUAL_SMOKE.read_text(encoding="utf-8")
    failures: list[str] = []

    if list_text.count("<CollectionMobileRecordRow") != 1:
        failures.append("ListPage must expose exactly one shared mobile-record-row adapter")
    for marker in (
        ':facts="mobileRecordFacts(row)"',
        ':selection-enabled="showSelectionColumn"',
        '@selection-change="onRowCheckboxChange(row, $event)"',
        '@open="handleRow(row)"',
        ":open-label=\"uiLabel('open_record_detail', '查看详情')\"",
    ):
        if marker not in list_text:
            failures.append(f"mobile record row adapter missing {marker}")
    for legacy in ('class="mobile-record-row"', '<ScMobileRecordCard', '<ScStatusBadge'):
        if legacy in list_text:
            failures.append(f"ListPage retains inline mobile record presentation {legacy}")

    for marker in (
        'data-semantic-component="CollectionMobileRecordRow"',
        ':data-record-key="recordKey"',
        ':aria-selected="selectionEnabled ? selected : undefined"',
        ':aria-label="openAriaLabel"',
        ':data-fact-key="fact.key"',
        "CollectionSelectionControl",
        "ScMobileRecordCard",
        "ScStatusBadge",
        "emit('selection-change', $event)",
        "emit('open')",
    ):
        if marker not in row_text:
            failures.append(f"shared mobile record row missing {marker}")

    for marker in (
        "var(--sc-touch-target-min)",
        "var(--sc-app-border-strong)",
        "var(--sc-app-hover-bg)",
        ".collection-mobile-record-row__identity",
        ".collection-mobile-record-row__fact",
        ".collection-mobile-record-row__open",
    ):
        if marker not in row_css:
            failures.append(f"shared mobile record row style missing {marker}")
    for stale in (".mobile-record-row", ".mobile-record-fact", ".mobile-record-card__open", ".mobile-record-card__head"):
        if stale in legacy_css:
            failures.append(f"legacy mobile record style remains outside shared owner: {stale}")
    for marker in (
        "captureCollectionMobileRecords",
        "collectionMobileRecordEvidence",
        "data-semantic-component=\"CollectionMobileRecordRow\"",
        "row.openAriaLabel.includes(row.identity)",
        "row.selectionWidth >= 44",
        "row.facts.every",
    ):
        if marker not in visual_text:
            failures.append(f"mobile record browser evidence missing {marker}")
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_collection_mobile_record_row_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_collection_mobile_record_row_guard] PASS owner=1 selection=open_passthrough")
