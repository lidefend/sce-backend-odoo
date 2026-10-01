#!/usr/bin/env python3
"""Self-test: the row-activation identity guard must reject placement inference.

The guard previously only asserted that the literal string ``row_click`` existed
in the navigation runtime.  That literal can never appear on a decoded contract
rule, so the assertion proved nothing while the runtime resolved row activation
with an over-broad match that could hand it to a header action.  These cases bind
the guard to the real rule and prove it fails on each weakened variant.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from web_unified_page_contract_v2_guard import (  # noqa: E402
    ROW_PLACEMENT_WIDGET_ID,
    check_row_activation_identity,
)

ROOT = Path(__file__).resolve().parents[2]
NAV_RUNTIME = ROOT / "frontend/apps/web/src/app/action_runtime/useActionViewNavigationRuntime.ts"


def run_guard(nav_source: str) -> list[str]:
    errors: list[str] = []
    check_row_activation_identity(nav_source, errors)
    return errors


class RowActivationIdentityGuardTests(unittest.TestCase):
    def test_factory_source_is_accepted(self) -> None:
        source = NAV_RUNTIME.read_text(encoding="utf-8")
        self.assertEqual(run_guard(source), [])
        self.assertIn(ROW_PLACEMENT_WIDGET_ID, source)

    def test_placement_inference_from_target_scope_is_rejected(self) -> None:
        source = NAV_RUNTIME.read_text(encoding="utf-8")
        mutated = source.replace(
            "    const rowAction = rows.find((action) => isRowPlacementAction(action));",
            "    const rowAction = rows.find((action) => (\n"
            "      String((action as unknown as Dict).targetScope || '').trim() === 'page'\n"
            "    ));",
        )
        self.assertNotEqual(mutated, source, "mutation must apply")
        errors = run_guard(mutated)
        self.assertTrue(
            any("targetScope" in item for item in errors),
            f"targetScope inference must be rejected, got {errors}",
        )

    def test_reintroduced_retired_trigger_is_rejected(self) -> None:
        source = NAV_RUNTIME.read_text(encoding="utf-8")
        mutated = source.replace(
            "export const ROW_PLACEMENT_WIDGET_ID = 'page.row';",
            "export const ROW_PLACEMENT_WIDGET_ID = 'row_click';",
        )
        self.assertNotEqual(mutated, source, "mutation must apply")
        errors = run_guard(mutated)
        self.assertTrue(errors, "retired row_click trigger must be rejected")

    def test_dropped_row_placement_identity_is_rejected(self) -> None:
        source = NAV_RUNTIME.read_text(encoding="utf-8")
        mutated = source.replace(
            "  return String((action as Dict).sourceWidgetId || '').trim() === ROW_PLACEMENT_WIDGET_ID;",
            "  return false;",
        )
        self.assertNotEqual(mutated, source, "mutation must apply")
        errors = run_guard(mutated)
        self.assertTrue(
            any("sourceWidgetId" in item for item in errors),
            f"missing row placement identity must be rejected, got {errors}",
        )

    def test_comments_do_not_satisfy_the_guard(self) -> None:
        commented_only = (
            "// row identity is sourceWidgetId page.row and never targetScope or row_click\n"
            "function resolveRowOpenAction() { return undefined; }\n"
        )
        errors = run_guard(commented_only)
        self.assertTrue(errors, "comments must not be accepted as evidence of the rule")

    def test_dropped_contract_rule_consumption_is_rejected(self) -> None:
        errors = run_guard(
            "function resolveRowOpenAction() { return undefined; }"
        )
        self.assertTrue(
            any("v2 list contracts" in item for item in errors),
            f"unconsumed v2 action rules must be rejected, got {errors}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
