#!/usr/bin/env python3
"""Guard the list-to-form loading state against structural layout regressions."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "frontend/apps/web/src/pages/ContractFormPage.vue"
SKELETON = ROOT / "frontend/apps/web/src/components/product-record/ProductFormLoadingSkeleton.vue"
CSS = ROOT / "frontend/apps/web/src/pages/contractForm/ContractFormPage.css"


def require(source: str, token: str, label: str) -> None:
    if token not in source:
        raise SystemExit(f"[frontend_form_loading_continuity_guard] FAIL {label}: missing {token}")


page = PAGE.read_text(encoding="utf-8")
skeleton = SKELETON.read_text(encoding="utf-8")
css = CSS.read_text(encoding="utf-8")

for token in (
    "ProductFormLoadingSkeleton",
    "v-if=\"initialFormLoading\"",
    "status.value === 'loading' && !contract.value",
    ":busy=\"busy || status === 'loading'\"",
    "'is-refreshing': status === 'loading'",
):
    require(page, token, "form loading orchestration")
if "v-else-if=\"status === 'loading'\"" in page:
    raise SystemExit("[frontend_form_loading_continuity_guard] FAIL generic StatusPanel loading branch restored")

for token in (
    "height: 38px",
    "gap: 18px",
    "min-height: max(560px, calc(100vh - 265px))",
    "grid-template-columns: repeat(2, minmax(0, 1fr))",
    "prefers-reduced-motion: reduce",
):
    require(skeleton, token, "structural form skeleton")
for token in (".card.is-refreshing", "contract-form-refresh-progress"):
    require(css, token, "retained-content refresh")

print("[frontend_form_loading_continuity_guard] PASS")
