from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
PY = (ROOT / "scripts/verify/local_dev_project_profile_write_fixture.py").read_text()
SH = (ROOT / "scripts/verify/local_dev_project_profile_write_fixture.sh").read_text()
MK = (ROOT / "make/dev.mk").read_text()
ODOO_SHELL = (ROOT / "scripts/ops/odoo_shell_exec.sh").read_text()
BROWSER_SH = (ROOT / "scripts/verify/local_dev_project_profile_write_browser.sh").read_text()
BROWSER_MJS = (ROOT / "scripts/verify/local_dev_project_profile_write_browser.mjs").read_text()


class TestLocalDevProjectProfileWriteFixture(unittest.TestCase):
    def test_exact_dev_identity_is_required(self):
        for marker in (
            'EXPECTED_DB = "sc_dev_demo"',
            'EXPECTED_ENV = "dev"',
            '"^sc_dev_demo$"',
            'CANDIDATE_GIT_HEAD',
        ):
            self.assertIn(marker, PY + SH)

    def test_batch_is_bounded_and_namespace_is_fixed(self):
        self.assertIn('re.fullmatch(r"[a-z0-9][a-z0-9-]{2,31}", value)', PY)
        self.assertIn('MODULE = "codex_p4_project_profile_write"', PY)
        self.assertIn('P4_PROJECT_PROFILE_BATCH', SH)

    def test_modes_require_distinct_confirmation(self):
        for mode, confirmation in (("inspect", "INSPECT"), ("dry-run", "DRY_RUN"), ("prepare", "PREPARE"), ("cleanup", "CLEANUP")):
            self.assertIn(mode, SH)
            self.assertIn('"%s"' % confirmation, SH)

    def test_prepare_never_creates_users_or_changes_groups(self):
        self.assertIn("no users are created", PY)
        self.assertNotIn("res.users.*create", PY)
        self.assertNotIn('"groups_id"', PY)

    def test_cleanup_is_namespace_owned_and_external_reference_safe(self):
        self.assertIn("fixture project XMLID is not owned by this batch", PY)
        self.assertIn("external project references exist", PY)
        self.assertIn("_external_references", PY)
        self.assertIn("project.responsibility", PY)

    def test_make_entry_is_local_dev_only(self):
        block = MK[MK.index("local.dev.project_profile_write_fixture:"):]
        self.assertIn("local.dev.ready", block)
        self.assertIn("local.dev", block)
        self.assertIn("local_dev_project_profile_write_fixture.sh", block)

    def test_governed_shell_forwards_only_p4_identity_inputs(self):
        self.assertIn("P4_PROJECT_PROFILE_*", ODOO_SHELL)
        self.assertIn("CANDIDATE_GIT_HEAD", ODOO_SHELL)

    def test_browser_runner_binds_product_candidate_and_dedicated_record(self):
        self.assertIn("PRODUCT_CANDIDATE_SHA", BROWSER_SH)
        self.assertIn("127.0.0.1:5176", BROWSER_SH)
        self.assertIn('PROJECT_ID="${PROJECT_ID:-366}"', BROWSER_SH)

    def test_write_scope_is_explicit(self):
        for field in ("name", "date_start", "date", "description", "responsibility_ids"):
            self.assertIn('"%s"' % field, PY)

    def test_recovery_report_cannot_reuse_normal_save_or_skip_failure_feedback(self):
        self.assertIn("if (!NETWORK_FAILURE_RECOVERY)", BROWSER_MJS)
        self.assertIn("failedMessageVisible", BROWSER_MJS)
        self.assertIn("failure_recovery_evidence_incomplete", BROWSER_MJS)
        self.assertIn("name: 'retry_success'", BROWSER_MJS)

    def test_recovery_pass_compares_actual_draft_and_all_authoritative_facts(self):
        self.assertIn("captureDraftSnapshot", BROWSER_MJS)
        self.assertIn("draft_before_failure", BROWSER_MJS)
        self.assertIn("draft_after_failure", BROWSER_MJS)
        self.assertIn("backend_unchanged: backendUnchanged", BROWSER_MJS)
        self.assertIn("fields: ['id', 'project_id', 'role_key', 'user_id', 'note']", BROWSER_MJS)
        self.assertIn("responsibility_operations_complete", BROWSER_MJS)
        self.assertNotIn("unchanged?.name === report.preflight.authoritative_read.name", BROWSER_MJS)

    def test_recovery_error_must_be_visible_and_screenshot_before_retry(self):
        self.assertIn("feedbackVisible = await feedback.isVisible()", BROWSER_MJS)
        self.assertIn("failure-feedback-visible.png", BROWSER_MJS)
        self.assertIn("element_screenshot: 'failure-feedback-visible.png'", BROWSER_MJS)
        self.assertLess(BROWSER_MJS.index("failure-feedback-visible.png"), BROWSER_MJS.index("await page.unroute"))

    def test_recovery_retry_requires_business_response_and_full_refresh_match(self):
        self.assertIn("'business_success' : 'response_failure'", BROWSER_MJS)
        self.assertIn("retryWrite.outcome === 'business_success'", BROWSER_MJS)
        self.assertIn("refreshConsistent = sameJson(afterRetry, refreshed)", BROWSER_MJS)
        self.assertIn("responsibility_operations_applied", BROWSER_MJS)


if __name__ == "__main__":
    unittest.main()
