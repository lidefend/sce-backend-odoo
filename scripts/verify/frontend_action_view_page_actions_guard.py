#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACTION_VIEW = ROOT / "frontend/apps/web/src/views/ActionView.vue"

# The page renders its governed action projections through ScButton. The
# adopted official list template renders the same toolbar projections in a
# second, mutually exclusive placement — the list card's leading slot, selected
# by `standardListOperationsInCard` — so the source carries 11 base projections
# plus the 3 relocated ones. The total stays exact: a 15th tag is a parallel
# page action that no placement declares.
EXPECTED_SC_BUTTON_PROJECTIONS = 14


def validate(source: str | None = None) -> list[str]:
    text = source if source is not None else ACTION_VIEW.read_text(encoding="utf-8")
    failures: list[str] = []
    required_actions = (
        '<ScButton data-page-action="reload"',
        '<ScButton v-for="action in vm.header.actions"',
        '<ScButton class="clear-btn"',
        '<ScButton v-for="item in vm.focus.actions"',
        'v-for="btn in vm.actions.primary"',
        'v-for="btn in group.actions"',
        '<ScButton variant="primary" size="small" type="button" @click="openFocusAction(vm.empty.primaryAction)"',
        'v-if="vm.empty.secondaryAction"',
        'class="contract-chip ghost"',
        'class="business-category-picker-option"',
        '<ScDialog\n      :open="businessCategoryCreatePickerVisible"',
        '@close="closeBusinessCategoryCreatePicker"',
        '<template #leading>',
        "import ScButton from '../components/design-system/ScButton.vue';",
    )
    for marker in required_actions:
        if marker not in text:
            failures.append(f"ActionView page action missing {marker}")
    forbidden_legacy = (
        '<button v-for="action in vm.header.actions"',
        '<button class="clear-btn"',
        '<button v-for="item in vm.focus.actions"',
        '<button class="contract-chip primary" @click="openFocusAction(vm.empty.primaryAction)"',
        '<button class="business-category-picker-close"',
    )
    if any(marker in text for marker in forbidden_legacy):
        failures.append("ActionView retains a generic legacy page action")
    stateful_native = (
        'v-for="chip in vm.filters.quickFilters.primary"',
        'v-for="chip in vm.filters.savedFilters.primary"',
        'v-for="chip in vm.filters.groupBy.primary"',
        'v-if="vm.filters.quickFilters.overflow.length"',
        'v-if="vm.actions.overflowGroups.length"',
        'v-for="(option, optionIndex) in businessCategoryCreateOptions"',
    )
    for marker in stateful_native:
        if marker not in text:
            failures.append(f"ActionView lost stateful native control {marker}")
    if text.count('<ScButton') != EXPECTED_SC_BUTTON_PROJECTIONS:
        failures.append(
            f"ActionView expected {EXPECTED_SC_BUTTON_PROJECTIONS} governed page-action projections, "
            f"found {text.count('<ScButton')}"
        )
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_action_view_page_actions_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(
        f"[frontend_action_view_page_actions_guard] PASS "
        f"sc_button_projections={EXPECTED_SC_BUTTON_PROJECTIONS} overlay_close=ScDialog"
    )
