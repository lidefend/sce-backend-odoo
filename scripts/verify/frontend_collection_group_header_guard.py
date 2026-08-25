#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIST_PAGE = ROOT / "frontend/apps/web/src/pages/ListPage.vue"
HEADER = ROOT / "frontend/apps/web/src/components/product-list/CollectionGroupHeader.vue"
HEADER_CSS = ROOT / "frontend/apps/web/src/components/product-list/CollectionGroupHeader.css"
VISUAL_SMOKE = ROOT / "scripts/verify/local_dev_candidate_visual_smoke.mjs"


def validate(list_source: str | None = None, header_source: str | None = None, css_source: str | None = None, visual_source: str | None = None) -> list[str]:
    list_text = list_source if list_source is not None else LIST_PAGE.read_text(encoding="utf-8")
    header_text = header_source if header_source is not None else HEADER.read_text(encoding="utf-8")
    css_text = css_source if css_source is not None else HEADER_CSS.read_text(encoding="utf-8")
    visual_text = visual_source if visual_source is not None else VISUAL_SMOKE.read_text(encoding="utf-8")
    failures: list[str] = []
    for marker in (
        'data-semantic-component="CollectionGroupHeader"',
        ':data-group-key="groupKey"',
        ":data-group-state=\"collapsed ? 'collapsed' : 'expanded'\"",
        ':aria-expanded="!collapsed"',
        'aria-live="polite"',
        '<slot name="pagination" />',
        'v-if="openEnabled"',
        "toggle: []",
        "open: []",
    ):
        if marker not in header_text:
            failures.append(f"collection group header missing {marker}")
    if list_text.count("<CollectionGroupHeader") != 1:
        failures.append("ListPage must expose exactly one shared group header adapter")
    for legacy in ('class="group-head"', 'class="group-toggle"', 'class="group-open-btn"'):
        if legacy in list_text:
            failures.append(f"ListPage retains legacy group header control {legacy}")
    for marker in (
        ':count-text="groupCountText(group)"',
        ':collapsed="isGroupCollapsed(group.key)"',
        '@toggle="toggleGroupCollapsed(group.key)"',
        ':open-enabled="Boolean(onOpenGroup)"',
        '@open="openGroup(group)"',
        '<template #pagination>',
        '<CollectionGroupPageControls',
    ):
        if marker not in list_text:
            failures.append(f"collection group header adapter missing {marker}")
    for marker in (
        "var(--sc-space-xs)",
        "var(--sc-app-info-border)",
        "var(--sc-semantic-focus-ring)",
        "var(--sc-touch-target-min)",
        "prefers-reduced-motion",
    ):
        if marker not in css_text:
            failures.append(f"collection group header styles missing {marker}")
    for marker in (
        "exerciseCollectionGroupHeader",
        "collectionGroupHeaderEvidence",
        "data-group-state",
        "togglePrimitive",
        "toggledExpanded",
        "openActionPrimitiveCount",
        "touchTarget",
    ):
        if marker not in visual_text:
            failures.append(f"collection group header browser evidence missing {marker}")
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_collection_group_header_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_collection_group_header_guard] PASS owner=1 actions=toggle,open pagination=slot")
