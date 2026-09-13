from pathlib import Path
import json
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]
PY = (ROOT / "scripts/verify/local_dev_personnel_authorization_fixture.py").read_text()
SH = (ROOT / "scripts/verify/local_dev_personnel_authorization_fixture.sh").read_text()
BROWSER = (ROOT / "scripts/verify/local_dev_personnel_authorization_browser.mjs").read_text()
BROWSER_SH = (ROOT / "scripts/verify/local_dev_personnel_authorization_browser.sh").read_text()
SHELL = (ROOT / "scripts/ops/odoo_shell_exec.sh").read_text()
MAKE = (ROOT / "make/dev.mk").read_text()
FAILURE_POLICY = ROOT / "scripts/verify/local_dev_personnel_authorization_failure_policy.mjs"


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
            "inactive_visible_personnel",
            "inactive_visible_data_permission",
            "final_deactivate_and_preserve",
            "const expectedWrites = resumeInactive ? 2 : resumeOwnedCreate ? 3 : 4",
            "persisted assignment project remains editable or changed",
            "auxiliary_onchange_failures",
            "blocking_http_failures",
            "添加项目成员授权",
        ):
            self.assertIn(token, BROWSER)
        self.assertNotIn("loginBody?.data, init:", BROWSER)
        self.assertNotIn("page.route(", BROWSER)
        self.assertNotIn("unlink", BROWSER)
        self.assertNotIn("retire", BROWSER)
        self.assertNotIn("params: body.params", BROWSER)

    def test_browser_wrapper_rejects_implicit_targets(self):
        self.assertIn("PERSON_ID must be an explicit positive integer", BROWSER_SH)
        self.assertIn("PROJECT_ID must be an explicit positive integer", BROWSER_SH)
        self.assertIn("P4_PERSONNEL_AUTH_BATCH is required", BROWSER_SH)
        self.assertIn("product/tool SHA must be full immutable SHAs", BROWSER_SH)

    def test_browser_failure_policy_only_allows_the_exact_bounded_known_failure(self):
        script = r'''
const { classifyPersonnelAuthorizationJourneyFailures: classify } = await import(process.argv[1]);
const personId = 445;
const knownHttp = (overrides = {}) => ({
  status: 500, business_ok: false, intent: 'api.onchange',
  params: { model: 'res.users', op: '', ids: [], action_id: null, menu_id: null, record_id: personId },
  error: { code: 'INTERNAL_ERROR', message: '内部错误' },
  phase: 'personnel_initial_form', url: 'http://127.0.0.1:5176/api/v1/intent', observed_at_ms: 1000,
  ...overrides,
});
const knownConsole = (overrides = {}) => ({
  type: 'console',
  message: 'Failed to load resource: the server responded with a status of 500 (Internal Server Error)',
  phase: 'personnel_initial_form', location_url: 'http://127.0.0.1:5176/api/v1/intent', observed_at_ms: 1001,
  ...overrides,
});
const cases = {
  exact: classify({ httpFailures: [knownHttp()], browserErrors: [knownConsole()], personId }),
  forbidden403: classify({ httpFailures: [knownHttp({ status: 403 })], browserErrors: [knownConsole({ message: '403 Forbidden' })], personId }),
  different500: classify({ httpFailures: [knownHttp({ error: { code: 'INTERNAL_ERROR', message: 'different' } })], browserErrors: [knownConsole()], personId }),
  wrongStage: classify({ httpFailures: [knownHttp({ phase: 'final_assertion' })], browserErrors: [knownConsole({ phase: 'final_assertion' })], personId }),
  unpairedConsole: classify({ httpFailures: [knownHttp()], browserErrors: [knownConsole({ message: 'unrelated console error' })], personId }),
  pageError: classify({
    httpFailures: [],
    browserErrors: [{ type: 'pageerror', message: 'render failed', phase: 'personnel_initial_form', observed_at_ms: 1001 }],
    personId,
  }),
  repeatedExact: classify({
    httpFailures: [0, 1, 2, 3].map((offset) => knownHttp({ observed_at_ms: 1000 + offset * 10 })),
    browserErrors: [0, 1, 2, 3].map((offset) => knownConsole({ observed_at_ms: 1001 + offset * 10 })),
    personId,
  }),
};
console.log(JSON.stringify(cases));
'''
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script, FAILURE_POLICY.as_uri()],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        cases = json.loads(result.stdout)
        self.assertEqual(len(cases["exact"]["auxiliary_http_failures"]), 1)
        self.assertEqual(len(cases["exact"]["blocking_http_failures"]), 0)
        self.assertEqual(len(cases["exact"]["blocking_browser_errors"]), 0)
        for name in ("forbidden403", "different500", "wrongStage", "unpairedConsole"):
            self.assertEqual(len(cases[name]["auxiliary_http_failures"]), 0, name)
            self.assertEqual(len(cases[name]["blocking_http_failures"]), 1, name)
            self.assertEqual(len(cases[name]["blocking_browser_errors"]), 1, name)
        self.assertEqual(len(cases["pageError"]["blocking_http_failures"]), 0)
        self.assertEqual(len(cases["pageError"]["blocking_browser_errors"]), 1)
        self.assertEqual(len(cases["repeatedExact"]["auxiliary_http_failures"]), 4)
        self.assertEqual(len(cases["repeatedExact"]["auxiliary_console_errors"]), 4)
        self.assertEqual(len(cases["repeatedExact"]["blocking_http_failures"]), 0)
        self.assertEqual(len(cases["repeatedExact"]["blocking_browser_errors"]), 0)


if __name__ == "__main__":
    unittest.main()
