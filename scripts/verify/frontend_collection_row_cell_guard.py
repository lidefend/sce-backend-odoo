#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIST_PAGE = ROOT / "frontend/apps/web/src/pages/ListPage.vue"
ROW_CELL = ROOT / "frontend/apps/web/src/components/product-list/CollectionRowCell.vue"
ROW_CELL_CSS = ROOT / "frontend/apps/web/src/components/product-list/CollectionRowCell.css"


def validate(list_source: str | None = None, cell_source: str | None = None, css_source: str | None = None) -> list[str]:
    list_text = list_source if list_source is not None else LIST_PAGE.read_text(encoding="utf-8")
    cell_text = cell_source if cell_source is not None else ROW_CELL.read_text(encoding="utf-8")
    css_text = css_source if css_source is not None else ROW_CELL_CSS.read_text(encoding="utf-8")
    failures: list[str] = []
    if list_text.count("h(CollectionRowCell") != 1 or list_text.count(":columns=\"collectionTableColumns(") != 2:
        failures.append("flat and grouped collection rows must share one TDesign column cell adapter")
    required_list = (
        "...collectionRowCellProps(row, field)",
        "onToggleFavorite: () => toggleRecordFavorite(row, field)",
        "onOpenRecord: () => handleRow(row)",
        "onOpenAttachment: (link:",
        "onOpenAttachmentCount: () => previewRecordAttachmentCount(row, columnValue(row, field))",
        "relationItems,",
    )
    for marker in required_list:
        if marker not in list_text:
            failures.append(f"collection row adapters missing shared event contract {marker}")
    forbidden_list = (
        'class="favorite-toggle"',
        'class="status-badge"',
        'class="cell-primary-link"',
        'class="attachment-links"',
        'class="attachment-count-link"',
    )
    for marker in forbidden_list:
        if marker in list_text:
            failures.append(f"ListPage retains parallel row-cell DOM {marker}")
    required_cell = (
        'data-semantic-component="CollectionRowCell"',
        "export type CollectionRowCellKind",
        "'toggle-favorite': []",
        "'open-record': []",
        "'open-attachment': [link: CollectionAttachmentLink]",
        "'open-attachment-count': []",
        "data-semantic-cell-kind=\"relation-tags\"",
    )
    for marker in required_cell:
        if marker not in cell_text:
            failures.append(f"CollectionRowCell missing {marker}")
    for selector in (".favorite-toggle", ".status-badge", ".cell-primary-link", ".attachment-links", ".attachment-count-link", ".relation-tags", ".relation-tag"):
        if selector not in css_text:
            failures.append(f"CollectionRowCell missing style ownership {selector}")
    for marker in ("white-space: nowrap", "overflow: hidden", "text-overflow: ellipsis"):
        if marker not in css_text:
            failures.append(f"CollectionRowCell primary identity missing truncation contract {marker}")
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_collection_row_cell_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_collection_row_cell_guard] PASS owners=1 adapters=tdesign-columns-flat,group")
