#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIST_PAGE = ROOT / "frontend/apps/web/src/pages/ListPage.vue"
SUMMARY = ROOT / "frontend/apps/web/src/components/product-list/CollectionSummaryStrip.vue"
SUMMARY_CSS = ROOT / "frontend/apps/web/src/components/product-list/CollectionSummaryStrip.css"
VISUAL_SMOKE = ROOT / "scripts/verify/local_dev_candidate_visual_smoke.mjs"


def validate(
    list_source: str | None = None,
    summary_source: str | None = None,
    css_source: str | None = None,
    visual_source: str | None = None,
) -> list[str]:
    list_text = list_source if list_source is not None else LIST_PAGE.read_text(encoding="utf-8")
    summary_text = summary_source if summary_source is not None else SUMMARY.read_text(encoding="utf-8")
    css_text = css_source if css_source is not None else SUMMARY_CSS.read_text(encoding="utf-8")
    visual_text = visual_source if visual_source is not None else VISUAL_SMOKE.read_text(encoding="utf-8")
    failures: list[str] = []

    for marker in (
        'data-semantic-component="CollectionSummaryStrip"',
        ':aria-label="ariaLabel"',
        ':data-summary-key="item.key"',
        ':data-summary-tone="resolveTone(item.tone)"',
        "resolveCollectionSummaryTone",
    ):
        if marker not in summary_text:
            failures.append(f"collection summary strip missing {marker}")

    if list_text.count("<CollectionSummaryStrip") != 1:
        failures.append("ListPage must expose exactly one shared summary strip adapter")
    for legacy in ('class="summary-card"', 'class="summary-label"', 'class="summary-value"'):
        if legacy in list_text:
            failures.append(f"ListPage retains legacy summary rendering {legacy}")
    for marker in (
        'v-if="enableSummaryStrip"',
        ':aria-label="uiLabel(\'list_summary\', \'列表摘要\')"',
        ':items="summaryItems"',
    ):
        if marker not in list_text:
            failures.append(f"collection summary strip adapter missing {marker}")

    for marker in (
        "repeat(auto-fit, minmax(180px, 1fr))",
        "var(--sc-space-xs)",
        "var(--sc-app-danger-bg)",
        "var(--sc-app-warning-bg)",
        "var(--sc-app-success-bg)",
        "var(--sc-app-info-bg)",
        "max-width: 420px",
        "grid-template-columns: minmax(0, 1fr)",
    ):
        if marker not in css_text:
            failures.append(f"collection summary strip styles missing {marker}")
    for marker in (
        "summarizeContractSummaryItems",
        "captureCollectionSummary",
        "collectionSummaryEvidence",
        "authorityItems",
        "JSON.stringify(domItems) === JSON.stringify(expectedItems)",
        "bootSummaryFixtureApplied",
        "applyFirstContractSummaryFixture",
        "value.projection.summary_items = fixture",
        "normalizeSummaryTone",
        "data-summary-key",
        "collection-summary-strip__label",
        "collection-summary-strip__value",
    ):
        if marker not in visual_text:
            failures.append(f"collection summary browser evidence missing {marker}")
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_collection_summary_strip_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_collection_summary_strip_guard] PASS owner=1 tone_authority=collectionSummaryPresentation")
