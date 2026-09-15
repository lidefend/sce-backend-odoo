from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = (ROOT / "scripts/verify/local_dev_tender_award_fixture.py").read_text(encoding="utf-8")
FIXTURE_SH = (ROOT / "scripts/verify/local_dev_tender_award_fixture.sh").read_text(encoding="utf-8")
BROWSER = (ROOT / "scripts/verify/local_dev_tender_award_browser.mjs").read_text(encoding="utf-8")
JOURNEY = (ROOT / "scripts/verify/local_dev_tender_award_journey.sh").read_text(encoding="utf-8")
MAKE = (ROOT / "make/dev.mk").read_text(encoding="utf-8")
ODOO_SHELL = (ROOT / "scripts/ops/odoo_shell_exec.sh").read_text(encoding="utf-8")


class TestLocalDevTenderAwardFixture(unittest.TestCase):
    def test_fixture_is_exact_local_dev_batch_owned(self):
        for value in (
            'EXPECTED_DB = "sc_dev_demo"',
            'EXPECTED_ENV = "dev"',
            'EXPECTED_DBFILTER = "^sc_dev_demo$"',
            'MODULE = "codex_p4_tender_award"',
            'P4_TENDER_AWARD_BATCH',
            'CANDIDATE_GIT_HEAD',
        ):
            self.assertIn(value, FIXTURE)
        self.assertIn('[[ "${COMPOSE_PROJECT_NAME:-}" == "sc-local-dev" ]]', FIXTURE_SH)
        self.assertIn('P4_TENDER_AWARD_BATCH="${BATCH}"', FIXTURE_SH)
        self.assertIn('P4_TENDER_AWARD_CONFIRM="${CONFIRM}"', FIXTURE_SH)

    def test_fixture_uses_required_1200_1000_900_facts_without_creating_master_data(self):
        self.assertIn('"bid_amount": 1200.0', FIXTURE)
        self.assertIn('"line_total": 1000.0', FIXTURE)
        self.assertIn('"award_amount": 900.0', FIXTURE)
        self.assertNotIn('env["res.users"].sudo().create', FIXTURE)
        self.assertNotIn('env["project.project"].sudo().create', FIXTURE)
        self.assertNotIn('env["res.partner"].sudo().create', FIXTURE)

    def test_cleanup_is_xmlid_scoped_and_stops_on_contract_handoff(self):
        self.assertIn('if bid.contract_id:', FIXTURE)
        self.assertIn('cleanup stopped: batch-owned tender has a contract handoff', FIXTURE)
        self.assertIn('bid.sudo().unlink()', FIXTURE)
        self.assertIn('(\"module\", \"=\", MODULE)', FIXTURE)

    def test_browser_binds_product_and_tool_candidates_and_uses_formal_entry(self):
        self.assertIn("PRODUCT_CANDIDATE_SHA", BROWSER)
        self.assertIn("P4_TOOL_CANDIDATE_SHA", BROWSER)
        self.assertIn("authority.formal_entry", BROWSER)
        self.assertIn("action_mark_won", BROWSER)
        self.assertIn("award_confirmed_at", BROWSER)
        self.assertIn("contract was created unexpectedly", BROWSER)
        self.assertIn("failure_page", BROWSER)
        self.assertIn("failure.png", BROWSER)
        browser_shell = (ROOT / "scripts/verify/local_dev_tender_award_browser.sh").read_text(encoding="utf-8")
        self.assertIn('PRODUCT_CANDIDATE_SHA="${PRODUCT_SHA}"', browser_shell)
        self.assertIn('P4_TOOL_CANDIDATE_SHA="${TOOL_SHA}"', browser_shell)

    def test_failure_retains_batch_and_success_cleans_it(self):
        self.assertIn("browser failed; batch retained for diagnosis", JOURNEY)
        self.assertIn("fixture cleanup CLEANUP", JOURNEY)
        self.assertIn("fixture-final-inspect.json", JOURNEY)

    def test_make_exposes_only_governed_entries(self):
        self.assertIn("local.dev.tender_award_fixture: guard.prod.forbid local.dev.ready", MAKE)
        self.assertIn("local.dev.tender_award_browser: guard.prod.forbid local.dev.ready", MAKE)
        self.assertIn("verify.local.dev.tender_award.journey: guard.prod.forbid local.dev.ready", MAKE)

    def test_governed_shell_forwards_tender_award_authority_inputs(self):
        self.assertIn("P4_TENDER_AWARD_*", ODOO_SHELL)
        self.assertIn("CANDIDATE_GIT_HEAD", ODOO_SHELL)


if __name__ == "__main__":
    unittest.main()
