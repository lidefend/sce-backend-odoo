#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def validate() -> list[str]:
    failures: list[str] = []
    patterns = {
        "TaskFormPattern.vue": ("task-form", "task"),
        "WorkspaceFormPattern.vue": ("workspace-form", "workspace"),
        "CollectionPattern.vue": ("collection", "collection"),
        "DashboardPattern.vue": ("dashboard", "dashboard"),
    }
    for filename, (key, mode) in patterns.items():
        body = source(f"frontend/apps/web/src/components/product-page-patterns/{filename}")
        for marker in (f'data-product-page-pattern="{key}"', f'data-presentation-mode="{mode}"', "<slot />"):
            if marker not in body:
                failures.append(f"{filename} missing {marker}")
    driver = source("frontend/apps/web/src/pages/contractForm/ContractFormDriverHost.vue")
    for marker in ('<TaskFormPattern v-if="floorplan.decisionMode"', '<WorkspaceFormPattern v-else', ':render-profile="renderModel.identity.mode"'):
        if marker not in driver:
            failures.append(f"form driver bypasses formal pattern: {marker}")
    action_view = source("frontend/apps/web/src/views/ActionView.vue")
    if '<component :is="viewMode === \'dashboard\' ? DashboardPattern : CollectionPattern">' not in action_view:
        failures.append("ActionView does not select dashboard/collection pattern from formal view mode")
    model = source("frontend/apps/web/src/app/presentation/productPagePattern.ts")
    for marker in ("PRODUCT_PAGE_PATTERN_MODE_MISMATCH", "PRODUCT_PAGE_PATTERN_PROFILE_MISMATCH"):
        if marker not in model:
            failures.append(f"page pattern model missing fail-closed invariant {marker}")
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_product_page_pattern_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_product_page_pattern_guard] PASS patterns=4")
