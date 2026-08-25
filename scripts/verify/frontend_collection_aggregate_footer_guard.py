#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIST_PAGE = ROOT / "frontend/apps/web/src/pages/ListPage.vue"
PRESENTATION = ROOT / "frontend/apps/web/src/app/presentation/collectionAggregatePresentation.ts"
FOOTER = ROOT / "frontend/apps/web/src/components/product-list/CollectionAggregateFooter.vue"
FOOTER_CSS = ROOT / "frontend/apps/web/src/components/product-list/CollectionAggregateFooter.css"
VISUAL_SMOKE = ROOT / "scripts/verify/local_dev_candidate_visual_smoke.mjs"


def validate(list_source: str | None = None, footer_source: str | None = None, css_source: str | None = None, visual_source: str | None = None, presentation_source: str | None = None) -> list[str]:
    list_text = list_source if list_source is not None else LIST_PAGE.read_text(encoding="utf-8")
    footer_text = footer_source if footer_source is not None else FOOTER.read_text(encoding="utf-8")
    css_text = css_source if css_source is not None else FOOTER_CSS.read_text(encoding="utf-8")
    visual_text = visual_source if visual_source is not None else VISUAL_SMOKE.read_text(encoding="utf-8")
    presentation_text = presentation_source if presentation_source is not None else PRESENTATION.read_text(encoding="utf-8")
    failures: list[str] = []

    for marker in (
        'data-semantic-component="CollectionAggregateFooter"',
        ':data-aggregate-context="context"',
        ':data-aggregate-scope="row.scope"',
        ':data-aggregate-field="column.key"',
        'scope="row"',
        "data-aggregate-layout=\"summary\"",
        "data-aggregate-row-label",
        "rows: readonly CollectionAggregateRow[]",
    ):
        if marker not in footer_text:
            failures.append(f"collection aggregate footer missing {marker}")

    if list_text.count('<CollectionAggregateFooter') != 3:
        failures.append("collection list must expose flat table, flat mobile and grouped aggregate adapters")
    if '<tfoot' in list_text or 'footer-number-value' in list_text or 'footer-row-label' in list_text:
        failures.append("collection list retains parallel aggregate footer presentation")
    for marker in (
        'context="flat"',
        'context="group"',
        'layout="summary"',
        ':columns="aggregateFooterColumns"',
        ':rows="flatAggregateFooterRows"',
        ':rows="groupAggregateFooterRows(group)"',
    ):
        if marker not in list_text:
            failures.append(f"collection aggregate adapter missing {marker}")

    for marker in (
        "var(--sc-app-muted-bg)",
        "var(--sc-app-info-bg)",
        "var(--sc-app-border-strong)",
        "font-variant-numeric: tabular-nums",
        "[data-aggregate-scope='total']",
    ):
        if marker not in css_text:
            failures.append(f"collection aggregate footer styles missing {marker}")
    for marker in (
        "exerciseCollectionAggregate",
        "collectionAggregateEvidence",
        "captureCollectionAggregate",
        "contractAggregates",
        "listAggregates",
        "data-aggregate-context",
        "data-aggregate-scope",
        "misalignedNumericCells",
    ):
        if marker not in visual_text:
            failures.append(f"collection aggregate browser evidence missing {marker}")
    for marker in (
        "resolveCollectionAggregateEntry",
        "aggregates[displayKey]",
        "aggregates[sourceKey]",
    ):
        if marker not in presentation_text:
            failures.append(f"collection aggregate authority resolver missing {marker}")
    if list_text.count("resolveCollectionAggregateEntry(") != 4:
        failures.append("flat and grouped page/total aggregates must share one authority resolver")
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_collection_aggregate_footer_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_collection_aggregate_footer_guard] PASS owners=1 adapters=3 layouts=table,summary scopes=page,total")
