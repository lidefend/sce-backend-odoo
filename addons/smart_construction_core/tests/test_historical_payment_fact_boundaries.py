from pathlib import Path

from odoo.tests.common import TransactionCase


ROOT = Path(__file__).resolve().parents[1]


class TestHistoricalPaymentFactBoundaries(TransactionCase):
    def test_model_is_separate_readonly_and_execution_blocked(self):
        Fact = self.env["sc.historical.payment.fact"]
        self.assertNotEqual(Fact._name, "payment.request")
        self.assertNotEqual(Fact._name, "payment.ledger")
        self.assertTrue(Fact._fields["execution_blocked"].readonly)
        self.assertTrue(Fact._fields["has_authoritative_settlement_basis"].readonly)
        self.assertTrue(Fact._fields["source_record_digest"].required)
        self.assertTrue(Fact._fields["partner_id"].readonly)
        self.assertTrue(Fact._fields["partner_active"].readonly)
        self.assertTrue(Fact._fields["historical_difference_amount"].readonly)
        source = (
            ROOT / "models" / "core" / "historical_payment_fact.py"
        ).read_text(encoding="utf-8")
        self.assertIn("sc.tenant.company.registration", source)
        self.assertIn("is_platform_bootstrap_company", source)

    def test_contract_keeps_historical_and_new_system_paid_separate(self):
        Contract = self.env["construction.contract"]
        self.assertIn("historical_confirmed_paid_amount", Contract._fields)
        self.assertIn("new_system_flow_paid_amount", Contract._fields)
        self.assertIn("cumulative_paid_amount", Contract._fields)
        self.assertEqual(
            Contract._fields["settlement_amount"].compute,
            "_compute_execution_amounts",
        )

    def test_form_labels_history_as_non_settlement_reference(self):
        source = (ROOT / "views" / "core" / "contract_views.xml").read_text(
            encoding="utf-8"
        )
        self.assertIn("历史承接，无新系统结算依据", source)
        self.assertIn('create="0" edit="0" delete="0"', source)

    def test_independent_history_entry_is_readonly_and_finance_scoped(self):
        view_source = (
            ROOT / "views" / "core" / "historical_payment_fact_views.xml"
        ).read_text(encoding="utf-8")
        acl_source = (ROOT / "security" / "ir.model.access.csv").read_text(
            encoding="utf-8"
        )
        self.assertIn('id="menu_sc_historical_payment_fact"', view_source)
        self.assertIn('parent="smart_construction_core.menu_sc_finance_center"', view_source)
        self.assertIn("action_sc_historical_payment_fact", view_source)
        self.assertIn('create="0" edit="0" delete="0"', view_source)
        self.assertIn("历史数据，只读且不可再次执行", view_source)
        finance_acl = next(
            line
            for line in acl_source.splitlines()
            if line.startswith("access_sc_historical_payment_fact_finance_read,")
        )
        self.assertIn("group_sc_cap_finance_read", finance_acl)
        self.assertTrue(finance_acl.endswith(",1,0,0,0"))

    def test_import_service_supplies_audited_batch_only_by_model_contract(self):
        source = (
            ROOT.parents[0]
            / "smart_core"
            / "utils"
            / "tenant_payload_import_service.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"migration_batch_id" in target_model._fields', source)
