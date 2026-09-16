# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "uc4_native_lowcode")
class TestInvoiceNativeLowcode(TransactionCase):
    """U-C4 G02: invoice four-entry native semantic surface migration.

    Formal entries 785/786/787/788 share model ``sc.invoice.registration`` and
    form view 1651.  Their four action contracts now declare
    ``native_semantic_surface``; the model-wide section mirror and the P1
    business-facts layer are retired.  Bypass actions (input tax report,
    invoice general ledger) keep working on the rebuilt native form without
    any legacy section projection.
    """

    FORMAL_ACTIONS = (
        ("action_sc_invoice_input", ("cost_category_name", "caliber", "recipient_unit_name", "invoice_provider_name")),
        ("action_sc_invoice_application_user", ("applicant_name", "expected_receipt_date", "invoice_content")),
        ("action_sc_invoice_registration_user", ("applicant_name", "expected_receipt_date", "push_result")),
        ("action_sc_invoice_prepaid_tax_user", ("prepaid_tax_date", "tax_certificate_no", "tax_type")),
    )
    SHARED_PRESENT_FIELDS = (
        "company_id", "note_display", "invoice_attachment_text",
        "legacy_source_model", "legacy_source_table", "legacy_record_id",
        "legacy_document_state", "legacy_partner_id", "legacy_partner_name",
        "source_created_by", "source_created_at", "attachment_ids", "note",
    )

    def setUp(self):
        super().setUp()
        from odoo.tools.convert import convert_file
        for source in (
            "views/core/invoice_registration_views.xml",
            "data/invoice_input_form_productization_contract.xml",
            "data/invoice_output_tax_form_productization_contract.xml",
            "data/view_orchestration_form_section_contract_data.xml",
            "data/p1_daily_business_form_orchestration_contract_data.xml",
        ):
            convert_file(self.env, "smart_construction_core", source, {}, mode="update", noupdate=False)

    def ref(self, key):
        return self.env.ref("smart_construction_core." + key)

    def contract(self, action_key, **extra):
        from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler
        action = self.ref(action_key)
        result = UiContractV2Handler(self.env, su_env=self.env["ir.model"].sudo().env).handle({
            "op": "model", "model": action.res_model, "action_id": action.id,
            "view_id": self.ref("view_sc_invoice_registration_form").id,
            "view_type": "form", "render_profile": "create", **extra,
        })
        result = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
        self.assertTrue(result.get("ok", True), result)
        return result["data"]

    @staticmethod
    def walk(rows):
        for node in rows:
            yield node
            yield from TestInvoiceNativeLowcode.walk(node.get("children", []))

    def test_four_entries_retire_legacy_structure_and_keep_fields(self):
        self.assertFalse(self.ref("business_config_contract_sc_invoice_registration_form_sections_v1").active)
        self.assertFalse(self.ref("business_config_contract_sc_invoice_registration_p1_form_business_facts_v1").active)
        self.assertFalse(self.ref("business_config_contract_sc_invoice_registration_form_structure_generated").active)
        for contract_key in (
            "business_config_contract_invoice_input_productized_form_v1",
            "business_config_contract_invoice_output_application_productized_form_v1",
            "business_config_contract_invoice_output_registration_productized_form_v1",
            "business_config_contract_invoice_prepaid_tax_productized_form_v1",
        ):
            record = self.ref(contract_key)
            self.assertTrue(record.active)
            form_spec = record.contract_json["view_orchestration"]["views"]["form"]
            self.assertEqual(form_spec["composition_mode"], "native_semantic_surface")
            self.assertNotIn("sections", form_spec)
            self.assertNotIn("fields", form_spec)
        for action_key, required in self.FORMAL_ACTIONS:
            data = self.contract(action_key)
            governance = data["formStructureContract"]["sourceAuthority"]["governance_source"]
            self.assertEqual(governance["resolvedActionId"], self.ref(action_key).id)
            self.assertEqual(governance["resolvedViewId"], self.ref("view_sc_invoice_registration_form").id)
            self.assertEqual(governance.get("compatibilityDependencies", []), [])
            self.assertEqual(governance.get("configuredSections", []), [])
            names = {n.get("name") for n in self.walk(data["layoutContract"]["containerTree"])}
            for field in (*required, *self.SHARED_PRESENT_FIELDS):
                self.assertIn(field, names, (action_key, field))

    def test_shared_native_form_anchors_and_bypass_actions(self):
        from lxml import etree
        arch = etree.fromstring(self.ref("view_sc_invoice_registration_form").arch_db.encode())
        anchors = {g.get("data-sc-anchor") for g in arch.xpath('.//group[@data-sc-anchor]')}
        self.assertEqual(anchors, {
            "invoice_main", "invoice_project", "invoice_tax_details", "invoice_prepaid_tax",
            "invoice_amount", "invoice_output_business", "invoice_handling", "invoice_notes",
            "invoice_source_trace",
        })
        buttons = {b.get("name") for b in arch.xpath(".//header/button")}
        self.assertEqual(buttons, {"action_confirm", "validate_tier", "reject_tier", "action_register", "action_cancel"})
        retired_titles = ("发票标题", "受票方信息", "开票方信息", "本次开票信息", "开票详情", "发票实开详情")
        for bypass_key in ("action_sc_invoice_input_report_user", "action_sc_invoice_registration"):
            data = self.contract(bypass_key)
            governance = data["formStructureContract"]["sourceAuthority"]["governance_source"]
            self.assertEqual(governance.get("form_structure_authority") or governance.get("formStructureAuthority") or "native_authority", "native_authority")
            self.assertEqual(governance.get("configuredSections", []), [])
            serialized = str(data["layoutContract"])
            for name in ("project_id", "partner_id", "amount_total", "attachment_ids"):
                self.assertIn(name, serialized, (bypass_key, name))
            for title in retired_titles:
                self.assertNotIn(title, serialized, (bypass_key, title))

    def test_scoped_lowcode_preview_publish_and_rollback_after_migration(self):
        from odoo.addons.smart_core.handlers.business_config_change_set import (
            BusinessConfigChangeSetOpenHandler, BusinessConfigChangeSetStageHandler,
            BusinessConfigChangeSetPreviewHandler, BusinessConfigChangeSetPublishHandler,
            BusinessConfigChangeSetRollbackHandler,
        )
        from odoo.addons.smart_core.handlers.ui_contract_v2 import authoritative_form_role_key
        role = authoritative_form_role_key(self.env)
        key, outside = "action_sc_invoice_input", "action_sc_invoice_registration_user"
        baseline, other = self.contract(key), self.contract(outside)
        nodes = list(self.walk(baseline["layoutContract"]["containerTree"]))
        field = next(n for n in nodes if n.get("name") == "invoice_no" and n["type"] == "field")
        hidden = next(n for n in nodes if n.get("name") == "note_display" and n["type"] == "field")

        def bind(node, **change):
            return {"target": node["nativeLocator"], "expected": {"type": node["type"], "name": node.get("name"), "occurrence_index": node.get("occurrenceIndex")}, **change}

        def call(cls, **params):
            result = cls(self.env).handle(payload={"params": {"role_key": role, **params}})
            self.assertTrue(result.get("ok"), result)
            return result["data"]

        before = self.env["sc.invoice.registration"].search([]).read(["write_date", "state"])
        opened = call(BusinessConfigChangeSetOpenHandler)
        call(BusinessConfigChangeSetStageHandler, change_set_token=opened["token"], config_type="form",
             target_key="view_orchestration:uc4_transaction", model="sc.invoice.registration", view_type="form",
             action_id=self.ref(key).id, view_id=self.ref("view_sc_invoice_registration_form").id,
             draft_payload={"view_orchestration": {"views": {"form": {"node_patches": [
                 bind(field, set={"label": "受管发票号码"}),
                 bind(hidden, set={"visible": False})]}}}})
        preview = call(BusinessConfigChangeSetPreviewHandler, change_set_token=opened["token"])
        configured = self.contract(key, preview_token=preview["preview"]["token"], preview_role_key=role)
        published = call(BusinessConfigChangeSetPublishHandler, change_set_token=opened["token"], request_id="uc4-publish")
        self.assertTrue(published["publish_result"]["published_content_verified"])
        for part in ("layoutContract", "statusContract", "actionContract"):
            self.assertEqual(self.contract(key)[part], configured[part])
            self.assertEqual(self.contract(outside)[part], other[part])
        self.assertIn("受管发票号码", str(configured["layoutContract"]))
        call(BusinessConfigChangeSetRollbackHandler, change_set_token=opened["token"], request_id="uc4-rollback")
        for part in ("layoutContract", "statusContract", "actionContract"):
            self.assertEqual(self.contract(key)[part], baseline[part])
        self.assertEqual(self.env["sc.invoice.registration"].search([]).read(["write_date", "state"]), before)
