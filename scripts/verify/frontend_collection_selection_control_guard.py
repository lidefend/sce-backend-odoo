#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIST_PAGE = ROOT / "frontend/apps/web/src/pages/ListPage.vue"
CONTROL = ROOT / "frontend/apps/web/src/components/product-list/CollectionSelectionControl.vue"
CONTROL_CSS = ROOT / "frontend/apps/web/src/components/product-list/CollectionSelectionControl.css"
VISUAL_SMOKE = ROOT / "scripts/verify/local_dev_candidate_visual_smoke.mjs"


def validate(list_source: str | None = None, control_source: str | None = None, css_source: str | None = None, visual_source: str | None = None) -> list[str]:
    list_text = list_source if list_source is not None else LIST_PAGE.read_text(encoding="utf-8")
    control_text = control_source if control_source is not None else CONTROL.read_text(encoding="utf-8")
    css_text = css_source if css_source is not None else CONTROL_CSS.read_text(encoding="utf-8")
    visual_text = visual_source if visual_source is not None else VISUAL_SMOKE.read_text(encoding="utf-8")
    failures: list[str] = []
    if list_text.count("<CollectionSelectionControl") != 5:
        failures.append("collection list must project exactly five shared selection-control adapters")
    if 'type="checkbox"' in list_text:
        failures.append("ListPage retains parallel native checkbox DOM")
    required_list = (
        ':indeterminate="someSelected"',
        ':indeterminate="isGroupSomeSelected(group)"',
        'size="touch"',
        ':label="rowSelectionLabel(row)"',
        'function onSelectAllChange(checked: boolean)',
        'function onRowCheckboxChange(row: Record<string, unknown>, checked: boolean)',
        'function onGroupSelectAllChange(group: { sampleRows?: Array<Record<string, unknown>> }, selected: boolean)',
    )
    for marker in required_list:
        if marker not in list_text:
            failures.append(f"collection selection adapter missing {marker}")
    required_control = (
        'data-semantic-component="CollectionSelectionControl"',
        ':data-selection-state="presentation.state"',
        ':data-selection-interactive="presentation.interactive"',
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
    print("[frontend_collection_selection_control_guard] PASS owner=1 adapters=5 states=4")
