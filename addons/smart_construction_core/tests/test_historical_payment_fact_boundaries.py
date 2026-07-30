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

    def test_import_service_supplies_audited_batch_only_by_model_contract(self):
        source = (
            ROOT.parents[0]
            / "smart_core"
            / "utils"
            / "tenant_payload_import_service.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"migration_batch_id" in target_model._fields', source)
