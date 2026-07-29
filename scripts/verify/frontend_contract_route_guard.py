#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
ROUTER = ROOT / "frontend/apps/web/src/router/index.ts"
CONTRACT_FORM_ROUTE = ROOT / "frontend/apps/web/src/pages/ContractFormRoute.vue"


def fail(msg: str) -> int:
    print("[frontend_contract_route_guard] FAIL")
    print(msg)
    return 1


def main() -> int:
    if not ROUTER.is_file():
        return fail("router file missing: frontend/apps/web/src/router/index.ts")

    text = ROUTER.read_text(encoding="utf-8", errors="ignore")

    required_tokens = [
        "path: '/f/:model/:id'",
        "name: 'model-form'",
        "path: '/r/:model/:id'",
        "name: 'record'",
    ]
    missing = [token for token in required_tokens if token not in text]
    contract_form_tokens = [
        "component: ContractFormPage",
        "component: () => import('../pages/ContractFormPage.vue')",
        'component: () => import("../pages/ContractFormPage.vue")',
    ]
    contract_form_count = sum(text.count(token) for token in contract_form_tokens)
    contract_form_route_tokens = [
        "component: () => import('../pages/ContractFormRoute.vue')",
        'component: () => import("../pages/ContractFormRoute.vue")',
    ]
    contract_form_route_count = sum(text.count(token) for token in contract_form_route_tokens)
    if contract_form_route_count:
        if not CONTRACT_FORM_ROUTE.is_file():
            return fail(
                "ContractFormRoute target missing: "
                "frontend/apps/web/src/pages/ContractFormRoute.vue"
            )
        route_target = CONTRACT_FORM_ROUTE.read_text(encoding="utf-8", errors="ignore")
        compatible_tokens = [
            "<ContractFormPage",
            "import ContractFormPage from './ContractFormPage.vue'",
        ]
        missing_compatible = [token for token in compatible_tokens if token not in route_target]
        if missing_compatible:
            return fail(
                "ContractFormRoute is not a ContractFormPage-compatible target: "
                + ", ".join(missing_compatible)
            )
        contract_form_count += contract_form_route_count
    if contract_form_count < 2:
        missing.extend(["component: ContractFormPage-compatible route target"] * (2 - contract_form_count))
    if missing:
        return fail("missing required router tokens: " + ", ".join(missing))

    forbidden_tokens = [
        "component: ModelFormPage",
        "component: ModelListPage",
        "component: RecordView",
    ]
    found_forbidden = [token for token in forbidden_tokens if token in text]
    if found_forbidden:
        return fail("forbidden legacy route component found: " + ", ".join(found_forbidden))

    print("[frontend_contract_route_guard] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
