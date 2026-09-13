from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
PY = (ROOT / "scripts/verify/local_dev_personnel_authorization_fixture.py").read_text()
SH = (ROOT / "scripts/verify/local_dev_personnel_authorization_fixture.sh").read_text()
BROWSER = (ROOT / "scripts/verify/local_dev_personnel_authorization_browser.mjs").read_text()
BROWSER_SH = (ROOT / "scripts/verify/local_dev_personnel_authorization_browser.sh").read_text()
SHELL = (ROOT / "scripts/ops/odoo_shell_exec.sh").read_text()
MAKE = (ROOT / "make/dev.mk").read_text()


class PersonnelAuthorizationFixtureSafetyTest(unittest.TestCase):
    def test_fixture_is_exact_local_dev_batch_owned(self):
        for token in (
            'EXPECTED_DB = "sc_dev_demo"',
            'EXPECTED_DBFILTER = "^sc_dev_demo$"',
            'MODULE = "codex_p4_personnel_authorization"',
            "P4_PERSONNEL_AUTH_BATCH",
            "CANDIDATE_GIT_HEAD must be a full 40-character SHA",
            "fixture person XMLID is not owned by this batch",
            "fixture project XMLID is not owned by this batch",
            "outside the owned batch",
        ):
            self.assertIn(token, PY)

    def test_target_is_non_login_non_privileged_and_operator_is_unchanged(self):
        self.assertIn('OPERATOR_XMLID = "smart_construction_demo.sc_demo_user_test_admin"', PY)
        self.assertIn('"password": secrets.token_urlsafe(32)', PY)
        self.assertIn('"groups_id": [(6, 0, internal_group.ids)]', PY)
        self.assertIn('"administrator_group_ids"', PY)
        self.assertNotIn('person.write({"password"', PY)
        self.assertNotIn('operator.write(', PY)

    def test_retirement_is_explicit_and_never_deletes_assignment_history(self):
        retire = PY[PY.index("def retire("):]
        self.assertIn('assignments.with_user(_operator(env)).write({"active": False})', retire)
        self.assertIn('result["physical_delete_count"] = 0', retire)
        self.assertNotIn(".unlink(", retire)
        self.assertNotIn("finally", retire)

    def test_shell_and_make_are_governed_and_exact(self):
        self.assertIn('[[ "${COMPOSE_PROJECT_NAME:-}" == "sc-local-dev" ]]', SH)
        self.assertIn('[[ "${DB_NAME:-}" == "sc_dev_demo" ]]', SH)
        self.assertIn("P4_PERSONNEL_AUTH_*", SHELL)
        self.assertIn("local.dev.personnel_authorization_fixture:", MAKE)
        self.assertIn("local.dev.personnel_authorization_browser:", MAKE)

    def test_browser_requires_authority_and_only_runs_the_required_journey(self):
        for token in (
            "inspectAuthority()",
            "authority person identity mismatch",
            "authority project identity mismatch",
            "target person is not a non-privileged managed user",
            "create_and_readback",
            "deactivate_and_readback",
            "reactivate_and_readback",
            "refresh_consistency",
            "second_entry_same_fact",
            "writes.length === 3",
            "persisted assignment project remains editable or changed",
        ):
            self.assertIn(token, BROWSER)
        self.assertNotIn("page.route(", BROWSER)
        self.assertNotIn("unlink", BROWSER)
        self.assertNotIn("retire", BROWSER)

    def test_browser_wrapper_rejects_implicit_targets(self):
        self.assertIn("PERSON_ID must be an explicit positive integer", BROWSER_SH)
        self.assertIn("PROJECT_ID must be an explicit positive integer", BROWSER_SH)
        self.assertIn("P4_PERSONNEL_AUTH_BATCH is required", BROWSER_SH)
        self.assertIn("product/tool SHA must be full immutable SHAs", BROWSER_SH)


if __name__ == "__main__":
    unittest.main()
