#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "frontend/apps/web/src/pages/KanbanPage.vue"
CARD = ROOT / "frontend/apps/web/src/components/product-list/CollectionKanbanRecordCard.vue"
STYLE = ROOT / "frontend/apps/web/src/components/product-list/CollectionKanbanRecordCard.css"
LANE = ROOT / "frontend/apps/web/src/components/product-list/CollectionKanbanLane.vue"
VISUAL = ROOT / "scripts/verify/local_dev_candidate_visual_smoke.mjs"
SEMANTICS_BROWSER = ROOT / "scripts/verify/collection_view_semantics_browser.mjs"

def validate(page_source: str | None = None, card_source: str | None = None, style_source: str | None = None, lane_source: str | None = None, visual_source: str | None = None, semantics_browser_source: str | None = None) -> list[str]:
    page = page_source if page_source is not None else PAGE.read_text(encoding="utf-8")
    card = card_source if card_source is not None else CARD.read_text(encoding="utf-8")
    style = style_source if style_source is not None else STYLE.read_text(encoding="utf-8")
    lane = lane_source if lane_source is not None else LANE.read_text(encoding="utf-8")
    visual = visual_source if visual_source is not None else VISUAL.read_text(encoding="utf-8")
    semantics_browser = semantics_browser_source if semantics_browser_source is not None else SEMANTICS_BROWSER.read_text(encoding="utf-8")
    failures: list[str] = []
    if page.count("<CollectionKanbanRecordCard") != 1:
        failures.append("KanbanPage must expose exactly one shared kanban card adapter")
    for marker in (':title="rowTitle(row)"', ':statuses="cardStatuses(row)"', ':primary-facts="cardFacts(row, primaryMetaFields)"', ':secondary-facts="cardFacts(row, secondaryMetaFields)"', '@open="handleCard(row)"'):
        if marker not in page: failures.append(f"kanban adapter missing {marker}")
    for legacy in ('class="card"', 'class="status-chip"', 'class="card-meta'):
        if legacy in page: failures.append(f"KanbanPage retains inline card presentation {legacy}")
    if page.count("<CollectionPaginationFooter") != 1 or ':show-page-size="false"' not in page:
        failures.append("KanbanPage must consume one shared pagination footer without page-size authority")
    for legacy in ('class="pagination-bar"', 'class="pagination-btn"', 'class="pagination-input"'):
        if legacy in page: failures.append(f"KanbanPage retains inline pagination presentation {legacy}")
    if page.count("<CollectionKanbanLane") != 1 or ':record-count="lane.records.length"' not in page:
        failures.append("KanbanPage must expose exactly one shared lane adapter")
    if 'class="workflow-lane-header"' in page:
        failures.append("KanbanPage retains inline lane presentation")
    for marker in ('data-semantic-component="CollectionKanbanLane"', ':data-lane-key="laneKey"', ':count="recordCount"', '<slot />'):
        if marker not in lane: failures.append(f"shared kanban lane missing {marker}")
    for marker in ('captureCollectionKanban', 'collectionKanbanEvidence', 'CollectionKanbanRecordCard', 'paginationOwnerCount === 1'):
        if marker not in visual: failures.append(f"kanban browser evidence missing {marker}")
    for marker in ('CollectionKanbanRecordCard', 'CollectionKanbanLane', 'collection-kanban-record-card__fact'):
        if marker not in semantics_browser: failures.append(f"collection semantics browser missing {marker}")
    for legacy in ('.card-title', '.meta-row dt', 'explicit_card"] .card'):
        if legacy in semantics_browser: failures.append(f"collection semantics browser retains legacy selector {legacy}")
    for marker in ('data-semantic-component="CollectionKanbanRecordCard"', ':data-record-key="recordKey"', ':aria-label="openAriaLabel"', '@keydown.enter', '@keydown.space.prevent', 'ScStatusBadge', ':data-fact-key="fact.key"'):
        if marker not in card: failures.append(f"shared kanban card missing {marker}")
    for marker in ('var(--sc-semantic-focus-ring)', 'var(--sc-semantic-shadow-panel)', 'prefers-reduced-motion', '.collection-kanban-record-card__fact'):
        if marker not in style: failures.append(f"shared kanban card style missing {marker}")
    return failures

if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_collection_kanban_record_card_guard] FAIL")
        for error in errors: print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_collection_kanban_record_card_guard] PASS owner=1 keyboard=open_passthrough")
