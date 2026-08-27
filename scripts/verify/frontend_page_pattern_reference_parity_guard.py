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
    ),
    "frontend/apps/web/src/components/design-system/ScCard.vue": (
        "| 'fact' |",
        "fact: { padding: '0' }",
        "[data-appearance='fact']",
    ),
    "frontend/apps/web/src/components/template/FormSection.vue": (
        ":appearance=\"preferReadonlyFacts ? 'fact' : 'form-section'\"",
    ),
    "frontend/apps/web/src/pages/contractForm/ObjectTaskPage.vue": (
        "grid-auto-rows: max-content",
        "align-content: start",
    ),
    "frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue": (
        "grid-auto-rows: max-content",
        "align-content: start",
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
