#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIST_PAGE = ROOT / "frontend/apps/web/src/pages/ListPage.vue"
CONTROL = ROOT / "frontend/apps/web/src/components/product-list/CollectionSelectionControl.vue"
CONTROL_CSS = ROOT / "frontend/apps/web/src/components/product-list/CollectionSelectionControl.css"
VISUAL_SMOKE = ROOT / "scripts/verify/local_dev_candidate_visual_smoke.mjs"
MOBILE_ROW = ROOT / "frontend/apps/web/src/components/product-list/CollectionMobileRecordRow.vue"


def validate(list_source: str | None = None, control_source: str | None = None, css_source: str | None = None, visual_source: str | None = None, mobile_row_source: str | None = None) -> list[str]:
    list_text = list_source if list_source is not None else LIST_PAGE.read_text(encoding="utf-8")
    control_text = control_source if control_source is not None else CONTROL.read_text(encoding="utf-8")
    css_text = css_source if css_source is not None else CONTROL_CSS.read_text(encoding="utf-8")
    visual_text = visual_source if visual_source is not None else VISUAL_SMOKE.read_text(encoding="utf-8")
    mobile_row_text = mobile_row_source if mobile_row_source is not None else MOBILE_ROW.read_text(encoding="utf-8")
    failures: list[str] = []
    if list_text.count(':columns="collectionTableColumns(') != 2:
        failures.append("collection desktop surfaces must project exactly two TDesign selection adapters")
    if list_text.count(':selected-row-keys="selectedIds || []"') != 2:
        failures.append("collection desktop surfaces must bind exactly two selected-row-keys authorities")
    if mobile_row_text.count("<CollectionSelectionControl") != 1:
        failures.append("collection mobile row must retain one touch selection adapter")
    if 'type="checkbox"' in list_text:
        failures.append("ListPage retains parallel native checkbox DOM")
    required_list = (
        "type: 'multiple'",
        'checkProps:',
        '@select-change="onTableSelectionChange($event, group.sampleRows)"',
        '@select-change="onTableSelectionChange($event, records)"',
        'function onTableSelectionChange(keys: Array<string | number>, sourceRows: Array<Record<string, unknown>>)',
        'if (!changed.length) return;',
        'props.onToggleSelectionAll(sourceIds, sourceIds.every((id) => next.has(id)))',
        'props.onToggleSelection?.(id, next.has(id))',
    )
    for marker in required_list:
        if marker not in list_text:
            failures.append(f"collection selection adapter missing {marker}")
    for marker in ('size="touch"', ':label="selectionLabel"', "emit('selection-change', $event)"):
        if marker not in mobile_row_text:
            failures.append(f"mobile collection selection adapter missing {marker}")
    required_control = (
        'data-semantic-component="CollectionSelectionControl"',
        ':data-selection-state="presentation.state"',
        ':data-selection-interactive="presentation.interactive"',
        ':data-selection-scope="scope"',
        'type="checkbox"',
        ':aria-label="label"',
        '@click.stop',
        'inputRef.value.indeterminate = props.indeterminate',
        'resolveCollectionSelectionPresentation(props)',
        "emit('change', Boolean((event.target as HTMLInputElement | null)?.checked))",
    )
    for marker in required_control:
        if marker not in control_text:
            failures.append(f"CollectionSelectionControl missing {marker}")
    required_css = (
        "[data-selection-state='checked']",
        "[data-selection-state='mixed']",
        ':focus-within',
        ':has(input:disabled)',
        'var(--sc-semantic-surface-interactive)',
        '@media (prefers-reduced-motion: reduce)',
    )
    for marker in required_css:
        if marker not in css_text:
            failures.append(f"CollectionSelectionControl CSS missing {marker}")
    required_visual = (
        'target.exerciseCollectionSelection === true',
        "selectedHeaderState === 'mixed'",
        'headerIndeterminate === true',
        "restoredHeaderState === 'unchecked'",
        "Number(touchTarget?.width || 0) >= 44",
        'focusContained',
    )
    for marker in required_visual:
        if marker not in visual_text:
            failures.append(f"collection selection browser evidence missing {marker}")
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_collection_selection_control_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_collection_selection_control_guard] PASS desktop_driver=tdesign adapters=2 mobile_touch_adapter=1 states=4")
