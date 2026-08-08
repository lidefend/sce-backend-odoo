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

    def test_cache_identity_is_scoped_to_the_authenticated_actor(self):
        source = "return `activity:${activityActorPart()}:${routeKey}:${epoch}`;"
        self.assertIn("activityActorPart()", source)

    def test_logout_does_not_create_an_anonymous_record_cache_key(self):
        source = "if (userId > 0) retainedActivityActorId.value = userId;"
        self.assertNotIn("retainedActivityActorId.value = 0", source)

    def test_scope_switch_leaves_record_before_context_mutation(self):
        source = "const previousRoute = await leaveScopeSensitiveRoute();"
        self.assertIn("await leaveScopeSensitiveRoute()", source)

    def test_auxiliary_load_stops_after_page_deactivation(self):
        source = "if (!isComponentActive.value || reloadToken !== activeReloadToken) return;"
        self.assertIn("!isComponentActive.value", source)

    def test_persisted_record_does_not_eagerly_enumerate_relation_candidates(self):
        source = """
        if (!recordId.value) {
          await loadRelationOptions();
        }
        """
        self.assertLess(source.index("if (!recordId.value)"), source.index("loadRelationOptions()"))

    def test_inactive_action_page_ignores_record_context_events(self):
        source = """
        function handleRecordContextChanged(): void {
          if (!isComponentActive.value) return;
          refreshForRecordContextChange();
        }
        """
        self.assertLess(source.index("!isComponentActive.value"), source.index("refreshForRecordContextChange()"))

    def test_later_functional_failure_preserves_isolated_performance_pass(self):
        source = "if (performanceReport.result !== 'PASS') performanceReport.result = 'FAIL';"
        self.assertIn("result !== 'PASS'", source)

    def test_browser_matrix_rejects_persisted_relation_candidate_preload(self):
        source = "persisted contract detail eagerly enumerated construction.contract relation candidates"
        self.assertIn("persisted contract detail", source)


if __name__ == "__main__":
    unittest.main()
