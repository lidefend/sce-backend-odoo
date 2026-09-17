# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "uc4_native_lowcode")
class TestReceiptIncomeNativeLowcode(TransactionCase):
    """U-C4 G03: 收款与公司收入 native semantic surface migration.

    Formal entries 637 (公司收入 / 财务中心) and 806 (收入 / 公司收入) share model
    ``sc.receipt.income`` and the native form view 1644
    (``view_sc_receipt_income_form``).  Bypass entry 807 (工程进度款收入登记)
    binds the same form through its action ``view_ids`` entry, so it is part of
    the same consumption surface.

    The rebuilt native arch owns the structure: each released entry contract
    declares ``native_semantic_surface``, while the model-wide section mirror,
    the P1 business-facts layer and the generated sequence mirror are retired.
    Business facts that the retired configuration declared but the native form
    never carried are recovered into the arch itself, so the form body and the
    section navigation consume one structure.
    """

    FORMAL_ACTIONS = (
        ("action_sc_receipt_income", ("name", "project_id", "amount")),
        ("action_sc_receipt_income_user_income", ("name", "project_id", "amount")),
    )
    BYPASS_ACTIONS = (
        ("action_sc_receipt_income_engineering_progress", ("name", "project_id", "amount")),
    )
    # Facts the retired configuration declared but the native form body never
    # presented.  Recovering them is what closes the structure-consumption gap;
    # each one must render exactly once.
    RECOVERED_FIELDS = (
        "legacy_project_name", "company_id", "legacy_company_name", "legacy_partner_name",
        "legacy_contract_no", "legacy_receipt_type", "legacy_receipt_subtype",
        "legacy_source_model", "legacy_source_table", "legacy_record_id",
        "legacy_document_state", "legacy_document_state_label", "legacy_note", "reject_reason",
    )
    SHARED_PRESENT_FIELDS = (
        "state", "validation_status", "receipt_flow_label", "source_origin", "source_kind",
        "business_category_id", "date_receipt", "document_no", "operation_strategy",
        "partner_id", "contract_id", "payment_request_id", "receipt_type", "income_category",
        "payment_method", "bill_no", "invoice_ref", "receiving_account", "receiving_account_name",
        "receiving_account_no", "receiving_bank_name", "amount", "deducted_invoice_amount",
        "deducted_tax_amount", "settlement_amount", "currency_id", "note", "attachment_ids",
        "creator_name", "created_time", "active", "treasury_ledger_id",
        "company_contractor_responsibility_summary_id",
        "company_contractor_responsibility_state",
        "company_contractor_arrival_unprocessed_amount",
        "company_contractor_arrival_over_processed_amount",
        "company_contractor_self_funding_balance",
        "company_contractor_responsibility_notice", "can_review",
    )
    FORM_ANCHORS = (
        "receipt_main", "receipt_project", "receipt_income_items", "receipt_account",
        "receipt_amount", "receipt_note_attachment", "receipt_source_trace",
    )
    # Readonly business facts (historical snapshot / source trace).
    READONLY_FIELDS = (
        "legacy_project_name", "company_id", "legacy_company_name", "legacy_partner_name",
        "legacy_contract_no", "reject_reason", "legacy_source_model", "legacy_source_table",
        "legacy_record_id", "legacy_document_state", "legacy_document_state_label",
        "legacy_note", "creator_name", "created_time",
    )
    # Kept editable on purpose: the model declares them writable and the retired
    # configuration never made them readonly.
    EDITABLE_FIELDS = ("legacy_receipt_type", "legacy_receipt_subtype", "note", "partner_id")
    # Attachment summary: it keeps its list/API duty, but it must not become a
    # second presenter of the attachment fact inside the form body.
    ATTACHMENT_SUMMARY = "receipt_income_attachment_text_display"

    def setUp(self):
        super().setUp()
        from odoo.tools.convert import convert_file
        for source in (
            "views/core/receipt_income_views.xml",
            "data/receipt_income_form_productization_contract.xml",
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
            "view_id": self.ref("view_sc_receipt_income_form").id,
            "view_type": "form", "render_profile": "create", **extra,
        })
        result = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
        self.assertTrue(result.get("ok", True), result)
        return result["data"]

    @staticmethod
    def walk(rows, parent=None):
        for node in rows if isinstance(rows, list) else []:
            if isinstance(node, dict):
                yield node, parent
                for child in node.get("children", []):
                    yield from TestReceiptIncomeNativeLowcode.walk(
                        [child] if not isinstance(child, list) else child, node)

    def tree_nodes(self, data):
        return [n for n, _parent in self.walk(data["layoutContract"]["containerTree"])]

    def field_nodes(self, data, name):
        return [n for n in self.tree_nodes(data)
                if n.get("type") == "field" and n.get("name") == name]

    def field_node(self, data, name):
        nodes = self.field_nodes(data, name)
        self.assertEqual(len(nodes), 1, "expected single occurrence of %s" % name)
        return nodes[0]

    def group_node(self, data, container_id):
        groups = [n for n in self.tree_nodes(data)
                  if n.get("type") == "group" and n.get("containerId") == container_id]
        self.assertEqual(len(groups), 1, "expected single group %s" % container_id)
        return groups[0]

    def entries(self):
        return self.FORMAL_ACTIONS + self.BYPASS_ACTIONS

    def test_entries_retire_legacy_structure_and_recover_facts(self):
        """Three entry contracts spend one native structure, one final tree."""
        self.assertFalse(self.ref("business_config_contract_sc_receipt_income_form_sections_v1").active)
        self.assertFalse(self.ref("business_config_contract_sc_receipt_income_p1_form_business_facts_v1").active)
        self.assertFalse(self.ref("business_config_contract_sc_receipt_income_form_structure_generated").active)
        for contract_key in (
            "business_config_contract_receipt_income_productized_form_v1",
            "business_config_contract_receipt_income_project_productized_form_v1",
            "business_config_contract_receipt_income_engineering_progress_productized_form_v1",
        ):
            record = self.ref(contract_key)
            self.assertTrue(record.active, contract_key)
            form_spec = record.contract_json["view_orchestration"]["views"]["form"]
            self.assertEqual(form_spec["composition_mode"], "native_semantic_surface", contract_key)
            self.assertNotIn("sections", form_spec, contract_key)
            self.assertNotIn("fields", form_spec, contract_key)
        for action_key, required in self.entries():
            data = self.contract(action_key)
            g = data["formStructureContract"]["sourceAuthority"]["governance_source"]
            self.assertEqual(g["resolvedActionId"], self.ref(action_key).id, action_key)
            self.assertEqual(g["resolvedViewId"], self.ref("view_sc_receipt_income_form").id, action_key)
            self.assertEqual(g["formStructureAuthority"], "native_authority", action_key)
            self.assertEqual(g["formPresentationMode"], "task", action_key)
            self.assertEqual(g["compatibilityDependencies"], [], action_key)
            # the duplicated shared-layer projection is gone: no configured
            # section may survive next to the native structure
            self.assertEqual(g["configuredSections"], [], action_key)
            names = [n.get("name") for n in self.tree_nodes(data) if n.get("type") == "field"]
            for field in (*required, *self.RECOVERED_FIELDS, *self.SHARED_PRESENT_FIELDS):
                self.assertIn(field, names, (action_key, field))
                self.assertEqual(names.count(field), 1, (action_key, field))

    def test_recovered_facts_have_one_presentation_and_real_rules(self):
        """Presence is not usability: every recovered fact carries the rule that
        keeps it honest, and no fact is presented twice."""
        for action_key, _required in self.entries():
            data = self.contract(action_key)
            for field in self.READONLY_FIELDS:
                node = self.field_node(data, field)
                self.assertTrue((node.get("modifiers") or {}).get("readonly"), (action_key, field))
            for field in self.EDITABLE_FIELDS:
                node = self.field_node(data, field)
                self.assertFalse((node.get("modifiers") or {}).get("readonly") is True, (action_key, field))
            # the attachment fact keeps exactly one body presenter
            self.assertIn("attachment_ids", [n.get("name") for n in self.tree_nodes(data)])
            self.assertNotIn(self.ATTACHMENT_SUMMARY, [n.get("name") for n in self.tree_nodes(data)])
            # every fact lives in the section that owns it
            for field, container_id in (
                ("receiving_account", "receipt_account"),
                ("legacy_receipt_type", "receipt_income_items"),
                ("reject_reason", "receipt_note_attachment"),
                ("legacy_source_model", "receipt_source_trace"),
                ("active", "receipt_source_trace"),
                ("legacy_project_name", "receipt_project"),
            ):
                parent = [p for n, p in self.walk(data["layoutContract"]["containerTree"])
                          if n.get("type") == "field" and n.get("name") == field and isinstance(p, dict)]
                self.assertEqual(len(parent), 1, (action_key, field))
                self.assertEqual(parent[0].get("containerId"), container_id, (action_key, field))
            # unconditional business groups never carry an invisible expression
            for container_id in ("receipt_main", "receipt_project", "receipt_income_items",
                                 "receipt_account", "receipt_amount", "receipt_note_attachment",
                                 "receipt_source_trace"):
                group = self.group_node(data, container_id)
                self.assertNotIn("invisible", group.get("attributes") or {}, (action_key, container_id))

    def test_native_form_anchors_buttons_and_conditional_pages(self):
        """Action carriers of the native form survive the migration."""
        from lxml import etree
        arch = etree.fromstring(self.ref("view_sc_receipt_income_form").arch_db.encode())
        anchors = {g.get("data-sc-anchor") for g in arch.xpath(".//group[@data-sc-anchor]")}
        self.assertEqual(anchors, set(self.FORM_ANCHORS))
        buttons = {b.get("name") for b in arch.xpath(".//header/button")}
        self.assertEqual(buttons, {"action_confirm", "validate_tier", "reject_tier",
                                   "action_received", "action_cancel"})
        # the notebook action keeps its carrier and its condition
        notebook_buttons = {b.get("name") for b in arch.xpath(".//notebook//button")}
        self.assertEqual(notebook_buttons, {"action_view_company_contractor_responsibility_summary"})
        for page in arch.xpath(".//notebook/page"):
            self.assertIn(page.get("invisible"), ("not company_contractor_responsibility_summary_id",
                                                  "not treasury_ledger_id"))
        form_fields = [node.get("name") for node in arch.xpath(".//field")]
        self.assertEqual(len(form_fields), len(set(form_fields)),
                         "the form body presents a field more than once")
        # static number readonly stays; the manual-number entry point is unchanged
        # by this migration (recorded as an observation, not silently flipped).
        self.assertEqual(arch.xpath('.//field[@name="name"]/@readonly'), ["1"])
        self.assertNotIn(self.ATTACHMENT_SUMMARY, form_fields)
        # the summary keeps its list-column duty
        list_arch = "".join(self.env["ir.ui.view"].search([
            ("model", "=", "sc.receipt.income"), ("type", "=", "tree")]).mapped("arch_db"))
        self.assertIn(self.ATTACHMENT_SUMMARY, list_arch)

    def test_attachment_summary_is_not_registered_as_a_display_copy(self):
        """A registration must be grounded, not guessed.

        ``receipt_income_attachment_text_display`` mirrors the attachment count
        only while no legacy attachment reference exists: the compute falls back
        to ``_receipt_income_attachment_ref_value()``, so it is a dual-source
        derivation rather than a live single-source projection, and
        ``sc.receipt.income`` does not opt into the display-copy protocol at all
        (unlike ``payment.request`` / ``sc.material.inbound``).  Registering it
        would assert a relation that is not guaranteed and would be inert.  The
        duplicate presentation is therefore prevented by retiring the
        configuration projection, which the tests above assert.
        """
        from odoo.addons.smart_core.core.view_orchestrator import ViewOrchestrator
        from odoo.addons.smart_construction_core.models.core.formal_config_contract_fields import (
            FORMAL_DISPLAY_COPY_SOURCES,
        )
        orchestrator = ViewOrchestrator(self.env)
        model = self.env["sc.receipt.income"]
        self.assertFalse(hasattr(model, "_display_copy_source_fields"))
        self.assertEqual(orchestrator._display_copy_field_names("sc.receipt.income"), set())
        self.assertNotIn("sc.receipt.income", FORMAL_DISPLAY_COPY_SOURCES)
        fields = model.fields_get([self.ATTACHMENT_SUMMARY])
        self.assertIn(self.ATTACHMENT_SUMMARY, fields)

    def test_bypass_entry_807_shares_the_same_form_and_keeps_its_domain(self):
        action = self.ref("action_sc_receipt_income_engineering_progress")
        self.assertEqual(action.view_mode, "tree,form")
        views = {row.view_mode: row.view_id.id for row in action.view_ids}
        self.assertEqual(views.get("form"), self.ref("view_sc_receipt_income_form").id)
        self.assertEqual(action.domain, "[('business_category_id.code', '=', 'finance.receipt.income.progress')]")
        data = self.contract("action_sc_receipt_income_engineering_progress")
        g = data["formStructureContract"]["sourceAuthority"]["governance_source"]
        self.assertEqual(g["formStructureAuthority"], "native_authority")
        self.assertEqual(g["configuredSections"], [])
        # the entry's own action context keeps pre-filling the business defaults
        self.assertIn("default_business_category_code", action.context)
        self.assertIn("finance.receipt.income.progress", action.context)

    def test_scoped_lowcode_preview_publish_and_rollback_after_migration(self):
        from odoo.addons.smart_core.handlers.business_config_change_set import (
            BusinessConfigChangeSetOpenHandler, BusinessConfigChangeSetStageHandler,
            BusinessConfigChangeSetPreviewHandler, BusinessConfigChangeSetPublishHandler,
            BusinessConfigChangeSetRollbackHandler,
        )
        from odoo.addons.smart_core.handlers.ui_contract_v2 import authoritative_form_role_key
        role = authoritative_form_role_key(self.env)
        key, outside = "action_sc_receipt_income", "action_sc_receipt_income_engineering_progress"
        baseline, other = self.contract(key), self.contract(outside)
        nodes = self.tree_nodes(baseline)
        labelled = next(n for n in nodes if n.get("name") == "legacy_note" and n["type"] == "field")
        hidden = next(n for n in nodes if n.get("name") == "reject_reason" and n["type"] == "field")

        def bind(node, **change):
            return {"target": node["nativeLocator"],
                    "expected": {"type": node["type"], "name": node.get("name"),
                                 "occurrence_index": node.get("occurrenceIndex")}, **change}

        def call(cls, **params):
            result = cls(self.env).handle(payload={"params": {"role_key": role, **params}})
            self.assertTrue(result.get("ok"), result)
            return result["data"]

        self.assertFalse((self.field_node(baseline, "reject_reason").get("modifiers") or {}).get("invisible"))
        before = self.env["sc.receipt.income"].search([]).read(["write_date", "state"])
        opened = call(BusinessConfigChangeSetOpenHandler)
        call(BusinessConfigChangeSetStageHandler, change_set_token=opened["token"], config_type="form",
             target_key="view_orchestration:uc4_g03_transaction", model="sc.receipt.income", view_type="form",
             action_id=self.ref(key).id, view_id=self.ref("view_sc_receipt_income_form").id,
             draft_payload={"view_orchestration": {"views": {"form": {"node_patches": [
                 bind(labelled, set={"label": "受管来源备注"}),
                 bind(hidden, set={"visible": False})]}}}})
        preview = call(BusinessConfigChangeSetPreviewHandler, change_set_token=opened["token"])
        configured = self.contract(key, preview_token=preview["preview"]["token"], preview_role_key=role)
        self.assertTrue((self.field_node(configured, "reject_reason").get("modifiers") or {}).get("invisible"),
                        "preview must hide reject_reason on the final tree")
        published = call(BusinessConfigChangeSetPublishHandler, change_set_token=opened["token"],
                         request_id="uc4-g03-publish")
        self.assertTrue(published["publish_result"]["published_content_verified"])
        published_contract = self.contract(key)
        self.assertTrue((self.field_node(published_contract, "reject_reason").get("modifiers") or {}).get("invisible"),
                        "published contract must hide reject_reason on the final tree")
        for part in ("layoutContract", "statusContract", "actionContract"):
            self.assertEqual(published_contract[part], configured[part])
            # the sibling entry of the same native form keeps its own contract
            self.assertEqual(self.contract(outside)[part], other[part])
        self.assertIn("受管来源备注", str(configured["layoutContract"]))
        call(BusinessConfigChangeSetRollbackHandler, change_set_token=opened["token"], request_id="uc4-g03-rollback")
        rolled_back = self.contract(key)
        self.assertFalse((self.field_node(rolled_back, "reject_reason").get("modifiers") or {}).get("invisible"),
                         "rollback must restore reject_reason visibility")
        for part in ("layoutContract", "statusContract", "actionContract"):
            self.assertEqual(rolled_back[part], baseline[part])
        self.assertEqual(self.env["sc.receipt.income"].search([]).read(["write_date", "state"]), before)
