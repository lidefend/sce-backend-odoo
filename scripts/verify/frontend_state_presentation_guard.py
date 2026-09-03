#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = {
    "activity": ROOT / "frontend/apps/web/src/pages/ActivityPage.vue",
    "status": ROOT / "frontend/apps/web/src/components/StatusPanel.vue",
    "tabs": ROOT / "frontend/apps/web/src/components/product-shell/ActivityPageTabs.vue",
    "contract_form": ROOT / "frontend/apps/web/src/pages/ContractFormPage.vue",
    "theme": ROOT / "frontend/packages/ui/src/kits/tdesign/theme.css",
}


def validate(sources: dict[str, str] | None = None) -> list[str]:
    values = sources or {key: path.read_text(encoding="utf-8") for key, path in FILES.items()}
    failures: list[str] = []
    activity = values["activity"]
    for primitive in ("<ScLoading", "<ScEmptyState", "<ScErrorState"):
        if primitive not in activity:
            failures.append(f"activity state bypasses governed primitive: {primitive}")
    for legacy in ('<p v-if="loading"', '<div v-else class="activity-page__state"'):
        if legacy in activity:
            failures.append(f"activity retains private state DOM: {legacy}")
    for marker in (':data-state="loading ?', 'appearance="surface-tile"', "prefers-reduced-motion"):
        if marker not in activity:
            failures.append(f"activity interaction state missing: {marker}")
    for marker in (".sc-btn:focus-visible", "var(--sc-semantic-focus-ring)"):
        if marker not in values["theme"]:
            failures.append(f"activity adapter focus authority missing: {marker}")

    status = values["status"]
    if status.count("<ScButton") < 3:
        failures.append("status recovery actions bypass governed buttons")
    for legacy in ("<button v-if=", "<button\n"):
        if legacy in status:
            failures.append(f"status retains private action DOM: {legacy}")
    for marker in ('data-semantic-state-surface="page"', ':data-state="busy ?', 'aria-live=', 'aria-busy=', "prefers-reduced-motion"):
        if marker not in status:
            failures.append(f"status accessibility state missing: {marker}")
    tabs = values["tabs"]
    for marker in ('<TDesignTabs', '<TDesignTabPanel', 'tdesignPrimitiveBridge', '@change="handleChange"', '@remove="handleRemove"', "'focus-exit'"):
        if marker not in tabs:
            failures.append(f"activity tabs governed TDesign component contract missing: {marker}")
    if '<button class="activity-tab-close"' in tabs:
        failures.append("activity tablist contains a non-tab close button")
    contract_form = values["contract_form"]
    dirty_publication = (
        "session.updateActiveActivityDirty(dirty); }, "
        "{ immediate: true, flush: 'sync' });"
    )
    if dirty_publication not in contract_form:
        failures.append("activity draft dirty state is not published synchronously before tab navigation")
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_state_presentation_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_state_presentation_guard] PASS surfaces=3 states=loading,empty,error,disabled,focus")
