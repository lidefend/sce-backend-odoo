import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
PY = (ROOT / "scripts/verify/local_dev_project_profile_write_fixture.py").read_text()
SH = (ROOT / "scripts/verify/local_dev_project_profile_write_fixture.sh").read_text()
MK = (ROOT / "make/dev.mk").read_text()
ODOO_SHELL = (ROOT / "scripts/ops/odoo_shell_exec.sh").read_text()
BROWSER_SH = (ROOT / "scripts/verify/local_dev_project_profile_write_browser.sh").read_text()
BROWSER_MJS = (ROOT / "scripts/verify/local_dev_project_profile_write_browser.mjs").read_text()
BROWSER_MJS_PATH = ROOT / "scripts/verify/local_dev_project_profile_write_browser.mjs"
BROWSER_SH_PATH = ROOT / "scripts/verify/local_dev_project_profile_write_browser.sh"


TEST_BATCH = "scope-safe-0913"
TEST_PROJECT_ID = 374
TEST_TOOL_SHA = "1" * 40


def _authority(batch=TEST_BATCH, project_id=TEST_PROJECT_ID):
    suffix = batch.replace("-", "_")
    marker = "CODEX-P4-%s" % batch.upper()
    return {
        "mode": "inspect",
        "database": "sc_dev_demo",
        "environment": "dev",
        "dbfilter": "^sc_dev_demo$",
        "candidate_sha": TEST_TOOL_SHA,
        "batch": batch,
        "namespace": "codex_p4_project_profile_write",
        "existing_batch": True,
        "project": {
            "xmlid": "codex_p4_project_profile_write.project_%s" % suffix,
            "id": project_id,
            "name": "Codex P4 project %s" % batch,
            "ownership_marker": marker,
            "responsibility_ids": [24, 25],
        },
        "responsibilities": [
            {
                "xmlid": "codex_p4_project_profile_write.responsibility_%s_manager" % suffix,
                "id": 24,
                "project_id": project_id,
            },
            {
                "xmlid": "codex_p4_project_profile_write.responsibility_%s_cost" % suffix,
                "id": 25,
                "project_id": project_id,
            },
        ],
    }


def _facts(project_id=TEST_PROJECT_ID, responsibility_ids=None):
    ids = list(responsibility_ids or [24, 25])
    return {
        "project": {
            "id": project_id,
            "project_code": "CODEX-P4-%s" % TEST_BATCH.upper(),
            "responsibility_ids": ids,
        },
        "responsibilities": [
            {"id": value, "project_id": project_id}
            for value in ids
        ],
    }


class TestLocalDevProjectProfileWriteFixture(unittest.TestCase):
    def _direct_runner(self, overrides=None, remove=()):
        env = os.environ.copy()
        for name in (
            "PROJECT_ID",
            "READ_ONLY",
            "PREFLIGHT_ONLY",
            "NETWORK_FAILURE_RECOVERY",
            "P4_PROJECT_PROFILE_BATCH",
            "P4_TOOL_CANDIDATE_SHA",
            "P4_PROJECT_PROFILE_AUTHORITY_JSON",
            "P4_RUNNER_FACTS_JSON",
        ):
            env.pop(name, None)
        env.update({
            "PROJECT_ID": str(TEST_PROJECT_ID),
            "PRODUCT_CANDIDATE_SHA": "2" * 40,
            "P4_RUNNER_SERVED_PRODUCT_SHA": "2" * 40,
            "DB_NAME": "sc_dev_demo",
            "SC_ENVIRONMENT": "dev",
            "ODOO_DBFILTER": "^sc_dev_demo$",
            "P4_PROJECT_PROFILE_BATCH": TEST_BATCH,
            "P4_TOOL_CANDIDATE_SHA": TEST_TOOL_SHA,
            "P4_PROJECT_PROFILE_AUTHORITY_JSON": json.dumps(_authority()),
            "P4_RUNNER_FACTS_JSON": json.dumps(_facts()),
            "P4_RUNNER_VALIDATE_ONLY": "1",
        })
        env.update(overrides or {})
        for name in remove:
            env.pop(name, None)
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact_dir = Path(temp_dir) / "must-not-be-created"
            env["ARTIFACT_DIR"] = str(artifact_dir)
            result = subprocess.run(
                ["node", str(BROWSER_MJS_PATH)],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            artifact_created = artifact_dir.exists()
        return result, artifact_created

    def _assert_direct_denied(self, expected, overrides=None, remove=()):
        result, artifact_created = self._direct_runner(overrides, remove)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(expected, result.stderr)
        self.assertFalse(artifact_created, "ownership rejection must occur before browser/write setup")

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
        browser_make = MK[MK.index("local.dev.project_profile_write_browser:"):]
        self.assertIn("PRODUCT_CANDIDATE_SHA", BROWSER_SH)
        self.assertIn("127.0.0.1:5176", BROWSER_SH)
        self.assertNotIn("366", BROWSER_SH + BROWSER_MJS)
        self.assertIn("PROJECT_ID must be an explicit positive integer", BROWSER_SH)
        self.assertIn("requiredPositiveInteger('PROJECT_ID')", BROWSER_MJS)
        self.assertIn("local_dev_project_profile_write_fixture.sh", BROWSER_MJS)
        self.assertIn('source "${ROOT_DIR}/scripts/common/env.sh"', BROWSER_SH)
        self.assertIn('COMPOSE_PROJECT_NAME:-}" == "sc-local-dev"', BROWSER_SH)
        self.assertIn("SC_ENVIRONMENT=dev SC_ALLOW_DEMO_DATA=0", browser_make)
        self.assertLess(BROWSER_MJS.index("const WRITE_AUTHORITY"), BROWSER_MJS.index("const { chromium }"))

    def test_shell_rejects_missing_and_invalid_project_id_before_browser_setup(self):
        base = os.environ.copy()
        base.update({"ROOT_DIR": str(ROOT), "PRODUCT_CANDIDATE_SHA": "2" * 40})
        for value in (None, "0", "-1", "abc", "1.5", str(2**53)):
            env = dict(base)
            if value is None:
                env.pop("PROJECT_ID", None)
            else:
                env["PROJECT_ID"] = value
            result = subprocess.run(
                ["bash", str(BROWSER_SH_PATH)], cwd=ROOT, env=env,
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 2, value)
            self.assertIn("PROJECT_ID", result.stderr)

    def test_direct_mjs_rejects_missing_project_id(self):
        self._assert_direct_denied("PROJECT_ID must be an explicit positive integer", remove=("PROJECT_ID",))

    def test_direct_mjs_rejects_invalid_project_ids(self):
        for value in ("0", "-1", "abc", "1.5", str(2**53)):
            self._assert_direct_denied("PROJECT_ID", {"PROJECT_ID": value})

    def test_direct_mjs_rejects_wrong_batch(self):
        self._assert_direct_denied("authority batch or namespace mismatch", {"P4_PROJECT_PROFILE_BATCH": "wrong-batch"})

    def test_direct_mjs_rejects_project_xmlid_mismatch(self):
        authority = _authority()
        authority["project"]["xmlid"] = "codex_p4_project_profile_write.project_other"
        self._assert_direct_denied("authority project XMLID mismatch", {"P4_PROJECT_PROFILE_AUTHORITY_JSON": json.dumps(authority)})

    def test_direct_mjs_rejects_target_project_id_mismatch(self):
        self._assert_direct_denied(
            "authority target project ID mismatch",
            {"P4_PROJECT_PROFILE_AUTHORITY_JSON": json.dumps(_authority(project_id=375))},
        )

    def test_direct_mjs_rejects_environment_mismatch(self):
        self._assert_direct_denied("write mode requires SC_ENVIRONMENT=dev", {"SC_ENVIRONMENT": "acceptance"})
        authority = _authority()
        authority["database"] = "sc_dev_sample"
        self._assert_direct_denied("authority environment/database identity mismatch", {"P4_PROJECT_PROFILE_AUTHORITY_JSON": json.dumps(authority)})

    def test_direct_mjs_rejects_product_candidate_mismatch(self):
        self._assert_direct_denied("product candidate SHA mismatch", {"P4_RUNNER_SERVED_PRODUCT_SHA": "3" * 40})

    def test_direct_mjs_rejects_authority_read_failure(self):
        self._assert_direct_denied("P4_PROJECT_PROFILE_AUTHORITY_JSON is required", remove=("P4_PROJECT_PROFILE_AUTHORITY_JSON",))
        self._assert_direct_denied("P4_PROJECT_PROFILE_AUTHORITY_JSON is not valid JSON", {"P4_PROJECT_PROFILE_AUTHORITY_JSON": "{"})

    def test_direct_mjs_rejects_out_of_scope_responsibility(self):
        self._assert_direct_denied(
            "authoritative project has out-of-scope responsibility rows",
            {"P4_RUNNER_FACTS_JSON": json.dumps(_facts(responsibility_ids=[24, 99]))},
        )

    def test_direct_mjs_accepts_legal_owned_write_target(self):
        result, artifact_created = self._direct_runner()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"validated_only":true', result.stdout)
        self.assertFalse(artifact_created)

    def test_direct_mjs_readonly_preflight_cannot_enter_write_or_recovery(self):
        result, artifact_created = self._direct_runner(
            {"PROJECT_ID": "8", "READ_ONLY": "1"},
            remove=("P4_PROJECT_PROFILE_BATCH", "P4_TOOL_CANDIDATE_SHA", "P4_PROJECT_PROFILE_AUTHORITY_JSON", "P4_RUNNER_FACTS_JSON"),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"write_mode":false', result.stdout)
        self.assertFalse(artifact_created)
        self._assert_direct_denied(
            "read-only preflight cannot enable failure injection or retry",
            {"PROJECT_ID": "8", "READ_ONLY": "1", "NETWORK_FAILURE_RECOVERY": "1"},
            remove=("P4_PROJECT_PROFILE_BATCH", "P4_TOOL_CANDIDATE_SHA", "P4_PROJECT_PROFILE_AUTHORITY_JSON", "P4_RUNNER_FACTS_JSON"),
        )

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
