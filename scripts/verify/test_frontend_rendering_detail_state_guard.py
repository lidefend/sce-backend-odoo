from __future__ import annotations

import unittest

from scripts.verify.frontend_rendering_detail_state_guard import INVENTORY, authority_density_token_violations, validate


class FrontendRenderingDetailStateGuardTest(unittest.TestCase):
    def test_current_sources_pass(self) -> None:
        self.assertEqual(validate(), [])

    def test_missing_completion_marker_fails_closed(self) -> None:
        target = "frontend/apps/web/src/components/page/BlockRenderer.vue"
        original = (INVENTORY.ROOT / target).read_text(encoding="utf-8")
        values = {source: (INVENTORY.ROOT / source).read_text(encoding="utf-8") for source in INVENTORY.OWNED_BINDINGS}
        values[target] = original.replace('density="compact"', "")
        failures = validate(lambda source: values[source])
        self.assertTrue(any("remains ungoverned" in failure and target in failure for failure in failures))

    def test_private_state_dom_is_rejected(self) -> None:
        target = "frontend/apps/web/src/components/GlobalMessagePanel.vue"
        values = {source: (INVENTORY.ROOT / source).read_text(encoding="utf-8") for source in INVENTORY.OWNED_BINDINGS}
        values[target] += '<p class="global-message__error sc-alert">legacy</p>'
        failures = validate(lambda source: values[source])
        self.assertTrue(any("private DOM" in failure and target in failure for failure in failures))

    def test_collection_semantic_state_is_required(self) -> None:
        target = "frontend/apps/web/src/components/product-list/CollectionPaginationFooter.vue"
        values = {source: (INVENTORY.ROOT / source).read_text(encoding="utf-8") for source in INVENTORY.OWNED_BINDINGS}
        values[target] = values[target].replace('data-semantic-component="CollectionPaginationFooter"', "")
        failures = validate(lambda source: values[source])
        self.assertTrue(any("remains ungoverned" in failure and target in failure for failure in failures))

    def test_global_accessibility_contracts_are_present(self) -> None:
        self.assertEqual(validate(), [])

    def test_removing_global_reduced_motion_fails_closed(self) -> None:
        target = "frontend/apps/web/src/styles/product-patterns.css"
        original = (INVENTORY.ROOT / target).read_text(encoding="utf-8")
        removed = original.replace("@media (prefers-reduced-motion: reduce)", "@media (prefers-reduced-motion: missing)")

        def fake(source):
            if source == target:
                return removed
            return (INVENTORY.ROOT / source).read_text(encoding="utf-8")

        failures = validate(fake)
        self.assertTrue(any("contract missing" in failure and target in failure for failure in failures))

    def test_topbar_uses_authoritative_shell_token(self) -> None:
        target = "frontend/apps/web/src/layouts/AppShell.css"
        original = (INVENTORY.ROOT / target).read_text(encoding="utf-8")
        regressed = original.replace("min-height: var(--sc-shell-topbar-height)", "min-height: var(--sc-product-toolbar-height)")

        def fake(source):
            if source == target:
                return regressed
            return (INVENTORY.ROOT / source).read_text(encoding="utf-8")

        failures = validate(fake)
        self.assertTrue(any("contract missing" in failure and target in failure for failure in failures))

    def test_authority_density_token_override_is_rejected(self) -> None:
        sources = [
            ("frontend/apps/web/src/pages/SomePage.css", ".page { --sc-table-row-height: 99px; }"),
            ("frontend/apps/web/src/pages/OtherPage.css", ".page { --sc-table-header-height: 30px; }"),
        ]
        failures = authority_density_token_violations(sources)
        self.assertTrue(any("SomePage.css" in failure and "--sc-table-row-height:" in failure for failure in failures))
        self.assertTrue(any("OtherPage.css" in failure and "--sc-table-header-height:" in failure for failure in failures))

    def test_authority_density_token_consumer_is_allowed(self) -> None:
        sources = [("frontend/apps/web/src/pages/ListPage.css", "height: var(--sc-product-table-row-height, 44px);")]
        self.assertEqual(authority_density_token_violations(sources), [])


if __name__ == "__main__":
    unittest.main()
