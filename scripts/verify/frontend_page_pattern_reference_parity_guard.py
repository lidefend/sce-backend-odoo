#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS = {
    "frontend/apps/web/src/views/LoginView.vue": (
        'class="login-masthead"',
        'class="brand-visual"',
        "pageText('brand_name', config.appBrand.name)",
        "grid-template-areas: 'auth brand'",
        'v-if="!dbInputDisabled"',
        '<ScIcon name="user"',
        '<ScIcon name="lock"',
    ),
    "frontend/apps/web/src/components/design-system/ScCard.vue": (
        "| 'fact' |",
        "fact: { padding: '0' }",
        "[data-appearance='fact']",
        "| 'task-section' |",
        "[data-appearance='task-section']",
    ),
    "frontend/apps/web/src/components/template/FormSection.vue": (
        ":appearance=\"preferReadonlyFacts ? 'fact' : 'form-section'\"",
    ),
    "frontend/apps/web/src/pages/contractForm/ObjectTaskPage.vue": (
        'appearance="task-section"',
        "grid-auto-rows: max-content",
        "align-content: start",
    ),
    "frontend/apps/web/src/pages/contractForm/CanonicalFormNodeRenderer.vue": (
        "fields.value.every((field) => field.readonly)",
        ':prefer-readonly-facts="readonlyFactLayout"',
        "canonical-form-node--readonly-fact",
    ),
    "frontend/apps/web/src/components/action/ActionSurfaceToolbar.vue": (
        'class="toolbar-total"',
        "grid-template-areas: 'view search total sort primary'",
    ),
    "frontend/apps/web/src/components/product-list/CollectionRowCell.css": (
        "text-overflow: ellipsis",
        "white-space: nowrap",
    ),
    "frontend/apps/web/src/components/template/X2ManyRelationRenderer.vue": (
        "grid-template-columns: minmax(72px, max-content) minmax(0, 1fr)",
        ".o2m-readonly-row:last-child",
    ),
    "frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue": (
        "grid-auto-rows: max-content",
        "align-content: start",
    ),
    "frontend/apps/web/src/layouts/AppShell.css": (
        "max-height: 100%",
        "max-block-size: 100%",
        ".shell :deep(.sidebar--scroll)",
        "overflow: hidden",
    ),
    "frontend/apps/web/src/layouts/AppShell.vue": (
        "workspacePanelMode === 'catalog'",
        "平台应用",
        "workspacePanelMode === 'navigation'",
    ),
}
FORBIDDEN_PRODUCT_HINTS = (
    "payment.request",
    "project.project",
    "action_id=",
    "menu_id=",
)


def validate(read_text=lambda source: (ROOT / source).read_text(encoding="utf-8")) -> list[str]:
    failures: list[str] = []
    for source, requirements in REQUIREMENTS.items():
        text = read_text(source)
        for requirement in requirements:
            if requirement not in text:
                failures.append(f"page-pattern parity requirement missing: {source}: {requirement}")
        for forbidden in FORBIDDEN_PRODUCT_HINTS:
            if forbidden in text:
                failures.append(f"page-pattern parity contains product-specific routing hint: {source}: {forbidden}")
    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("[frontend_page_pattern_reference_parity_guard] FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"[frontend_page_pattern_reference_parity_guard] PASS surfaces={len(REQUIREMENTS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
