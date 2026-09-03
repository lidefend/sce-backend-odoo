from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts.verify import view_type_render_coverage_guard as guard


class ViewTypeRenderCoverageGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = guard.run_runtime_probe()
        cls.schema = json.loads(guard.SCHEMA.read_text(encoding="utf-8"))
        cls.action_view = guard.ACTION_VIEW.read_text(encoding="utf-8")

    def test_current_executable_architecture_passes(self) -> None:
        self.assertEqual(guard.validate_runtime_evidence(self.evidence), [])
        self.assertEqual(guard.validate_activity_schema(self.schema, self.evidence), [])
        self.assertEqual(guard.validate_action_view_structure(self.action_view, activity_page_exists=True), [])

    def test_wrong_registry_state_and_dead_marker_cannot_pass(self) -> None:
        evidence = deepcopy(self.evidence)
        evidence["registrations"]["graph"]["status"] = "fallback"
        evidence["registrations"]["graph"]["activeRendererKey"] = "core.readable_records"
        evidence["deadCode"] = "graph fallback core.readable_records"
        errors = guard.validate_runtime_evidence(evidence)
        self.assertTrue(any("graph registration status" in error for error in errors))
        self.assertTrue(any("graph registration activeRendererKey" in error for error in errors))

    def test_analysis_profile_and_resolver_chain_are_required(self) -> None:
        evidence = deepcopy(self.evidence)
        evidence["analysisProfiles"]["pivot"]["profile"]["sourceAuthority"]["runtime_carrier"] = ""
        evidence["analysisProfiles"]["graph"]["model"]["rows"] = []
        errors = guard.validate_runtime_evidence(evidence)
        self.assertIn("pivot normalized profile carrier is missing", errors)
        self.assertIn("graph dedicated resolver did not consume dimensions and records", errors)

    def test_missing_readable_projection_fails(self) -> None:
        evidence = deepcopy(self.evidence)
        evidence["fallback"]["calendar"]["page"]["rows"] = []
        self.assertTrue(any(
            "calendar readable record projection" in error
            for error in guard.validate_runtime_evidence(evidence)
        ))

    def test_activity_chain_and_fail_closed_reason_are_required(self) -> None:
        evidence = deepcopy(self.evidence)
        evidence["activity"]["storeCarrier"] = ""
        evidence["activity"]["missingReasonCode"] = ""
        errors = guard.validate_runtime_evidence(evidence)
        self.assertIn("activity normalized store carrier is missing", errors)
        self.assertIn("activity missing profile must fail closed", errors)

    def test_coverage_cannot_claim_action_route_or_browser_delivery(self) -> None:
        evidence = deepcopy(self.evidence)
        evidence["deliveryClaims"] = {"actionRouteProven": True, "browserDeliveryProven": True}
        self.assertIn(
            "coverage evidence must not claim action routes or browser delivery",
            guard.validate_runtime_evidence(evidence),
        )

    def test_activity_schema_rejects_invalid_real_carrier_shape(self) -> None:
        evidence = deepcopy(self.evidence)
        evidence["activity"]["payload"]["layoutContract"]["activityProfile"]["fieldOccurrences"][0]["digits"] = [16]
        self.assertTrue(guard.validate_activity_schema(self.schema, evidence))

    def test_comments_strings_and_unreachable_template_nodes_do_not_pass(self) -> None:
        fake_source = """
<template>
  <!-- <ActivityPage v-else-if="viewMode === 'activity'" :model="activitySurfaceModel" /> -->
  <section v-if="false" class="advanced-view">
    <article v-for="row in vm.content.advanced?.rows || []"></article>
  </section>
  <ActivityPage v-if="false" v-else-if="viewMode === 'activity'" :model="activitySurfaceModel" />
  <AnalysisPage v-if="false" v-else-if="viewMode === 'pivot' || viewMode === 'graph'" :model="analysisSurfaceModel" />
</template>
<script setup>
const fake = `import ActivityPage from '../pages/ActivityPage.vue';`;
// import ActivityPage from '../pages/ActivityPage.vue';
</script>
"""
        errors = guard.validate_action_view_structure(fake_source, activity_page_exists=True)
        self.assertIn("ActionView has no reachable ActivityPage bound to activitySurfaceModel", errors)
        self.assertIn("ActionView has no reachable AnalysisPage bound to analysisSurfaceModel", errors)
        self.assertIn("ActionView has no reachable readable advanced-record fallback surface", errors)
        self.assertIn("ActionView does not statically import ActivityPage", errors)
        self.assertIn("ActionView does not statically import AnalysisPage", errors)

    def test_marker_only_payload_fails_closed(self) -> None:
        marker_only = {
            "scope": "view_type_render_coverage",
            "sourceMarkers": "pivot graph calendar gantt dashboard activity core.readable_records core.activity",
            "deliveryClaims": {"actionRouteProven": False, "browserDeliveryProven": False},
        }
        errors = guard.validate_runtime_evidence(marker_only)
        self.assertTrue(any("pivot registration" in error for error in errors))
        self.assertIn("activity decoder carrier is missing", errors)


if __name__ == "__main__":
    unittest.main()
