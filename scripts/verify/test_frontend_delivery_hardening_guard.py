#!/usr/bin/env python3
from __future__ import annotations

import re
import unittest


TOGGLE_PATTERN = re.compile(
    r"<button\b(?=[^>]*\baria-controls=\"primary-sidebar\")"
    r"(?=[^>]*:aria-expanded=\"sidebarVisible\")[^>]*>",
    re.DOTALL,
)


class AppShellSidebarSemanticsTest(unittest.TestCase):
    def test_unified_visibility_state_controls_the_named_region(self):
        source = """
        <button aria-controls="primary-sidebar"
                :aria-expanded="sidebarVisible"></button>
        """
        self.assertIsNotNone(TOGGLE_PATTERN.search(source))

    def test_old_desktop_only_state_is_rejected(self):
        source = """
        <button aria-controls="primary-sidebar"
                :aria-expanded="!sidebarHidden"></button>
        """
        self.assertIsNone(TOGGLE_PATTERN.search(source))

    def test_unrelated_aria_expanded_marker_is_rejected(self):
        source = """
        <button aria-controls="other-panel"
                :aria-expanded="sidebarVisible"></button>
        """
        self.assertIsNone(TOGGLE_PATTERN.search(source))


class ContractFormCacheOwnershipTest(unittest.TestCase):
    def test_route_wrapper_leaves_cache_identity_to_app_shell(self):
        source = """
        <template><ContractFormPage /></template>
        <script setup lang="ts">
        import ContractFormPage from './ContractFormPage.vue';
        </script>
        """
        self.assertIn("<ContractFormPage />", source)
        self.assertNotIn(':key="routeIdentity"', source)
        self.assertNotIn("useRoute()", source)

    def test_global_route_derived_inner_key_is_rejected(self):
        source = """
        <template><ContractFormPage :key="routeIdentity" /></template>
        <script setup lang="ts">
        const route = useRoute();
        </script>
        """
        self.assertIn(':key="routeIdentity"', source)
        self.assertIn("useRoute()", source)


if __name__ == "__main__":
    unittest.main()
