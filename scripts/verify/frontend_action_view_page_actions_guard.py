#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACTION_VIEW = ROOT / "frontend/apps/web/src/views/ActionView.vue"


def validate(source: str | None = None) -> list[str]:
    text = source if source is not None else ACTION_VIEW.read_text(encoding="utf-8")
    failures: list[str] = []
    required_actions = (
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
    if text.count('<ScButton') != 10:
        failures.append(f"ActionView expected 10 governed page-action projections, found {text.count('<ScButton')}")
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_action_view_page_actions_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_action_view_page_actions_guard] PASS sc_button_projections=10 overlay_close=ScDialog")
