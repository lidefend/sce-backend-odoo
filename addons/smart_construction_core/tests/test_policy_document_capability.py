# -*- coding: utf-8 -*-
import ast

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "policy_document")
class TestPolicyDocumentCapability(TransactionCase):
    def test_policy_and_company_archive_entries_are_mutually_isolated(self):
        archive_action = self.env.ref("smart_construction_core.action_sc_company_document_archive")
        policy_action = self.env.ref("smart_construction_core.action_sc_product_policy_document_v1")
        self.assertIn("company_document_archive", archive_action.domain)
        self.assertNotIn("policy_document", archive_action.domain)
        self.assertIn("policy_document", policy_action.domain)
        self.assertNotIn("company_document_archive", policy_action.domain)
        self.assertEqual(ast.literal_eval(policy_action.context)["default_fact_type"], "policy_document")
        self.assertEqual(policy_action.view_id, self.env.ref("smart_construction_core.view_sc_policy_document_tree"))

        policy = self.env["sc.document.admin.document"].with_context(
            default_fact_type="policy_document"
        ).create({"name": "采购管理制度", "document_title": "采购管理制度", "policy_version": "V1.0"})
        self.assertEqual(policy.fact_type, "policy_document")
        self.assertFalse(policy.project_id)

        contract = self.env.ref("smart_construction_core.business_config_contract_policy_document_form_v1")
        self.assertEqual(contract.action_id, policy_action)
        self.assertEqual(
            contract.contract_json["view_orchestration"]["context"]["fact_type_authority"],
            "policy_document",
        )

    def test_only_operational_date_consistency_blocks_completion(self):
        policy = self.env["sc.document.admin.document"].with_context(
            default_fact_type="policy_document"
        ).create(
            {
                "name": "安全管理制度",
                "policy_effective_date": "2026-09-01",
                "policy_expiry_date": "2026-08-31",
            }
        )
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            policy.action_done()
