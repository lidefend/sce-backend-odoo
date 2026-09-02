import unittest
from pathlib import Path

from scripts.verify.frontend_systemwide_public_metric_report import normalize


def coverage(covered=88, gaps=0):
    return {"status": "PASS" if gaps == 0 else "FAIL", "summary": {
        "primaryCenterCount": 10, "runtimeSurfaceCount": 88,
        "coveredSurfaceCount": covered, "uncoveredSurfaceCount": 88 - covered,
        "excludedSurfaceCount": 1, "gapCount": gaps,
    }}


def row(key, mode, route):
    return {
        "key": key, "url": f"http://127.0.0.1:18081{route}", "h1": 1,
        "pageHeader": 1, "selectedNavigationItem": 1, "primaryActions": 1,
        "duplicateFields": [], "duplicateTitles": [],
        "disabledFakeReadonlyControls": 0, "unregisteredComponents": 0,
        "mobile390Overflow": 0, "presentationMode": mode,
        "contractPresentationMode": mode,
        "renderProfile": "readonly" if route.startswith("/r/") or mode == "collection" else "edit",
    }


def browser():
    return {
        "pass": True, "head": "a" * 40, "target": {"database": "sc_dev_demo"},
        "rows": [row("collection", "collection", "/a/1"), row("task", "task", "/f/x/1"), row("workspace", "workspace", "/r/x/1")],
        "errors": [], "mutations": [],
    }


class SystemwidePublicMetricReportTest(unittest.TestCase):
    def test_complete_matrix_passes(self):
        self.assertEqual(normalize(coverage(), browser())["status"], "PASS")

    def test_coverage_gap_fails(self):
        result = normalize(coverage(87, 1), browser())
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("SYSTEMWIDE_COVERAGE_NOT_88_OF_88", result["errors"])

    def test_each_public_metric_fails_closed(self):
        for key, value in (
            ("h1", 2), ("pageHeader", 0), ("selectedNavigationItem", 0),
            ("primaryActions", 2), ("duplicateFields", ["name"]),
            ("duplicateTitles", ["Title"]), ("disabledFakeReadonlyControls", 1),
            ("unregisteredComponents", 1), ("mobile390Overflow", 1),
        ):
            with self.subTest(key=key):
                evidence = browser()
                evidence["rows"][0][key] = value
                self.assertEqual(normalize(coverage(), evidence)["status"], "FAIL")

    def test_contract_mode_mismatch_fails(self):
        evidence = browser()
        evidence["rows"][1]["contractPresentationMode"] = "workspace"
        self.assertIn("task:PRESENTATION_MODE_NOT_AUTHORITATIVE", normalize(coverage(), evidence)["errors"])

    def test_errors_and_mutations_fail(self):
        evidence = browser()
        evidence["errors"] = ["boom"]
        evidence["mutations"] = [{"intent": "api.data.write"}]
        result = normalize(coverage(), evidence)
        self.assertIn("BROWSER_ERRORS_PRESENT", result["errors"])
        self.assertIn("BUSINESS_MUTATIONS_PRESENT", result["errors"])

    def test_browser_collector_fails_closed_for_every_http_error(self):
        source = Path("scripts/verify/frontend_systemwide_public_metric_browser.mjs").read_text(encoding="utf-8")
        self.assertIn("response.status() >= 400", source)
        self.assertNotIn("response.status() >= 500", source)

    def test_browser_collector_does_not_exempt_disabled_control_types(self):
        source = Path("scripts/verify/frontend_systemwide_public_metric_browser.mjs").read_text(encoding="utf-8")
        self.assertIn("input:disabled, textarea:disabled, select:disabled", source)
        self.assertNotIn("['checkbox', 'radio'].includes(node.type)", source)

    def test_browser_projection_expectations_come_from_runtime_contract(self):
        browser_source = Path("scripts/verify/frontend_systemwide_public_metric_browser.mjs").read_text(encoding="utf-8")
        target_source = Path("scripts/verify/local_dev_systemwide_public_metric_ids.py").read_text(encoding="utf-8")
        self.assertIn("metrics.contractPagePattern", browser_source)
        self.assertIn("metrics.presentationMode === metrics.contractPresentationMode", browser_source)
        self.assertNotIn("spec.presentationMode", browser_source)
        self.assertNotIn("spec.renderProfile", browser_source)
        self.assertNotIn('"presentationMode":', target_source)
        self.assertNotIn('"renderProfile":', target_source)

    def test_browser_page_title_expectation_comes_from_action_authority(self):
        browser_source = Path("scripts/verify/frontend_systemwide_public_metric_browser.mjs").read_text(encoding="utf-8")
        target_source = Path("scripts/verify/local_dev_systemwide_public_metric_ids.py").read_text(encoding="utf-8")
        self.assertIn("metrics.h1Text[0] === spec.expectedTitle.trim()", browser_source)
        self.assertIn('"expectedTitle": report_action.name', target_source)
        self.assertIn('"expectedTitle": payment_action.name', target_source)
        self.assertIn('"expectedTitle": project_action.name', target_source)

    def test_browser_counts_native_and_header_primary_actions_together(self):
        source = Path("scripts/verify/frontend_systemwide_public_metric_browser.mjs").read_text(encoding="utf-8")
        self.assertIn('[data-product-primary-action], [data-action-tier="primary"]', source)
        self.assertIn("metrics.primaryActions <= 1", source)
        self.assertIn("metrics.enabledPrimaryActions <= 1", source)

    def test_browser_rejects_empty_readonly_scalar_facts(self):
        source = Path("scripts/verify/frontend_systemwide_public_metric_browser.mjs").read_text(encoding="utf-8")
        self.assertIn("emptyReadonlyScalarFacts", source)
        self.assertIn("readonly surface exposes empty scalar facts", source)
        self.assertIn("emptyFormSections", source)
        self.assertIn("readonly surface exposes empty form sections", source)


if __name__ == "__main__":
    unittest.main()
