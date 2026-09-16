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


@tagged("post_install", "-at_install", "uc3_native_lowcode")
class TestDocumentNativeLowcode(TransactionCase):
    def setUp(self):
        super().setUp()
        from odoo.tools.convert import convert_file
        for source in ("views/core/document_admin_document_views.xml", "data/policy_document_contract.xml",
                       "data/document_admin_form_productization_contract.xml"):
            convert_file(self.env, "smart_construction_core", source, {}, mode="update", noupdate=False)

    def ref(self, key):
        return self.env.ref("smart_construction_core." + key)

    def contract(self, action_key, **extra):
        from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler
        action = self.ref(action_key)
        result = UiContractV2Handler(self.env, su_env=self.env["ir.model"].sudo().env).handle({
            "op": "model", "model": action.res_model, "action_id": action.id,
            "view_id": self.ref("view_sc_document_admin_document_form").id,
            "view_type": "form", "render_profile": "create", **extra,
        })
        result = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
        self.assertTrue(result.get("ok", True), result)
        return result["data"]

    @staticmethod
    def walk(rows):
        for node in rows:
            yield node
            yield from TestDocumentNativeLowcode.walk(node.get("children", []))

    def test_two_entries_retire_only_redundant_structure(self):
        self.assertFalse(self.ref("business_config_contract_sc_document_admin_document_form_structure_generated").active)
        for key, required in (
            ("action_sc_certificate_registration", ("project_id", "certificate_name", "certificate_no", "holder_name", "valid_until")),
            ("action_sc_product_policy_document_v1", ("document_title", "policy_category", "policy_version", "confidentiality_level")),
        ):
            c = self.contract(key)
            g = c["formStructureContract"]["sourceAuthority"]["governance_source"]
            self.assertEqual(g["resolvedActionId"], self.ref(key).id)
            self.assertEqual(g["resolvedViewId"], self.ref("view_sc_document_admin_document_form").id)
            self.assertEqual(g.get("compatibilityDependencies", []), [])
            self.assertEqual(g.get("configuredSections", []), [])
            names = {n.get("name") for n in self.walk(c["layoutContract"]["containerTree"])}
            for field in (*required, "legacy_document_no", "legacy_document_state", "legacy_source_table", "legacy_source_id", "attachment_ids", "description", "result_note"):
                self.assertIn(field, names, (key, field))

    def test_shared_archive_borrow_keep_capabilities_and_classification(self):
        from lxml import etree
        arch = etree.fromstring(self.ref("view_sc_document_admin_document_form").arch_db.encode())
        self.assertEqual(len(arch.xpath('.//sheet/group/group')), 0, 'unnamed wrapper prevents named native sections')
        self.assertEqual(len(arch.xpath('.//group[@data-sc-anchor]')), 6)
        self.assertIsNone(arch.xpath('.//field[@name="fact_type"]')[0].get("readonly"))
        buttons = {b.get("name"): b.get("invisible") for b in arch.xpath('.//header/button')}
        self.assertEqual(buttons, {"action_submit": "state != 'draft'", "action_done": "state not in ['draft', 'in_progress']",
                                   "action_cancel": "state in ['done', 'cancel']", "action_reset_draft": "state == 'draft'"})
        for key in ("action_sc_company_document_archive", "action_sc_document_borrow"):
            c = self.contract(key)
            serialized = str(c["layoutContract"])
            for name in ("document_title", "attachment_ids", "legacy_document_no", "legacy_source_id"):
                self.assertIn(name, serialized, (key, name))
        policy = self.ref("business_config_contract_policy_document_form_v1").contract_json["view_orchestration"]["views"]["form"]
        self.assertEqual(policy["fields"], [{"name": "fact_type", "readonly": True}])
        initiator = self.ref("group_sc_cap_business_initiator")
        admin = self.ref("group_sc_cap_business_config_admin")
        self.assertEqual(self.ref("action_sc_certificate_registration").groups_id, initiator | admin)
        self.assertEqual(self.ref("action_sc_product_policy_document_v1").groups_id, admin)
        for group, expected in ((initiator, (True, True, True, False)), (admin, (True, True, True, True))):
            acl = self.env["ir.model.access"].search([("model_id.model", "=", "sc.document.admin.document"), ("group_id", "=", group.id)])
            self.assertTrue(acl)
            self.assertEqual(tuple(any(row[key] for row in acl) for key in ("perm_read", "perm_write", "perm_create", "perm_unlink")), expected)

    def test_scoped_lowcode_preview_publish_and_rollback_after_migration(self):
        from odoo.addons.smart_core.handlers.business_config_change_set import (
            BusinessConfigChangeSetOpenHandler, BusinessConfigChangeSetStageHandler,
            BusinessConfigChangeSetPreviewHandler, BusinessConfigChangeSetPublishHandler, BusinessConfigChangeSetRollbackHandler,
        )
        from odoo.addons.smart_core.handlers.ui_contract_v2 import authoritative_form_role_key
        role = authoritative_form_role_key(self.env)
        key, outside = "action_sc_certificate_registration", "action_sc_product_policy_document_v1"
        baseline, other = self.contract(key), self.contract(outside)
        nodes = list(self.walk(baseline["layoutContract"]["containerTree"]))
        field = next(n for n in nodes if n.get("name") == "issue_authority" and n["type"] == "field")
        hidden = next(n for n in nodes if n.get("name") == "result_note" and n["type"] == "field")
        parent = next(n for n in nodes if field in n.get("children", []))
        def bind(node, **change):
            return {"target": node["nativeLocator"], "expected": {"type": node["type"], "name": node.get("name"), "occurrence_index": node.get("occurrenceIndex")}, **change}
        def call(cls, **params):
            result = cls(self.env).handle(payload={"params": {"role_key": role, **params}})
            self.assertTrue(result.get("ok"), result)
            return result["data"]
        before = self.env["sc.document.admin.document"].search([]).read(["write_date", "state"])
        opened = call(BusinessConfigChangeSetOpenHandler)
        call(BusinessConfigChangeSetStageHandler, change_set_token=opened["token"], config_type="form",
             target_key="view_orchestration:uc3_transaction", model="sc.document.admin.document", view_type="form",
             action_id=self.ref(key).id, view_id=self.ref("view_sc_document_admin_document_form").id,
             draft_payload={"view_orchestration": {"views": {"form": {"node_patches": [
                 bind(field, set={"label": "受管发证单位"}), bind(hidden, set={"visible": False}),
                 bind(parent, order=[n["nativeLocator"] for n in reversed(parent["children"])],
                      group={"key": "issuer", "label": "发证信息配置", "members": [field["nativeLocator"]]})]}}}})
        preview = call(BusinessConfigChangeSetPreviewHandler, change_set_token=opened["token"])
        configured = self.contract(key, preview_token=preview["preview"]["token"], preview_role_key=role)
        published = call(BusinessConfigChangeSetPublishHandler, change_set_token=opened["token"], request_id="uc3-publish")
        self.assertTrue(published["publish_result"]["published_content_verified"])
        for part in ("layoutContract", "statusContract", "actionContract"):
            self.assertEqual(self.contract(key)[part], configured[part])
            self.assertEqual(self.contract(outside)[part], other[part])
        self.assertIn("受管发证单位", str(configured["layoutContract"]))
        call(BusinessConfigChangeSetRollbackHandler, change_set_token=opened["token"], request_id="uc3-rollback")
        for part in ("layoutContract", "statusContract", "actionContract"):
            self.assertEqual(self.contract(key)[part], baseline[part])
        self.assertEqual(self.env["sc.document.admin.document"].search([]).read(["write_date", "state"]), before)
