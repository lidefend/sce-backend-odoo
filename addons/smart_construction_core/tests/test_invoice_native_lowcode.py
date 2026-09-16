# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "uc4_native_lowcode")
class TestInvoiceNativeLowcode(TransactionCase):
    """U-C4 G02: invoice four-entry native semantic surface migration.

    Formal entries 785/786/787/788 share model ``sc.invoice.registration`` and
    form view 1651.  Their four action contracts now declare
    ``native_semantic_surface``; the model-wide section mirror, the P1
    business-facts layer and the generated sequence mirror are retired (seven
    legacy structure responsibilities retired: four converted, three
    deactivated).  Bypass actions (input tax report 789, invoice general
    ledger 639) keep working on the rebuilt native form without any legacy
    section projection.
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
    PREPAID_INVISIBLE = "source_kind != 'prepaid_tax' and direction != 'prepaid'"
    OUTPUT_INVISIBLE = "source_kind not in ['output_invoice_tax'] and direction != 'output'"

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
    def walk(rows, parent=None):
        for node in rows if isinstance(rows, list) else []:
            if isinstance(node, dict):
                yield node, parent
                for child in node.get("children", []):
                    yield from TestInvoiceNativeLowcode.walk(
                        [child] if not isinstance(child, list) else child, node)

    def field_nodes(self, data, name):
        return [n for n, _parent in self.walk(data["layoutContract"]["containerTree"])
                if n.get("type") == "field" and n.get("name") == name]

    def field_node(self, data, name):
        nodes = self.field_nodes(data, name)
        self.assertEqual(len(nodes), 1, "expected single occurrence of %s" % name)
        return nodes[0]

    def field_parent(self, data, name):
        for node, parent in self.walk(data["layoutContract"]["containerTree"]):
            if node.get("type") == "field" and node.get("name") == name and isinstance(parent, dict):
                return parent
        self.fail("no parented occurrence of %s" % name)

    def group_node(self, data, container_id):
        groups = [n for n, _parent in self.walk(data["layoutContract"]["containerTree"])
                  if n.get("type") == "group" and n.get("containerId") == container_id]
        self.assertEqual(len(groups), 1, "expected single group %s" % container_id)
        return groups[0]

    def tree_nodes(self, data):
        return [n for n, _parent in self.walk(data["layoutContract"]["containerTree"])]

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
            g = data["formStructureContract"]["sourceAuthority"]["governance_source"]
            self.assertEqual(g["resolvedActionId"], self.ref(action_key).id)
            self.assertEqual(g["resolvedViewId"], self.ref("view_sc_invoice_registration_form").id)
            self.assertIn("formStructureAuthority", g)
            self.assertEqual(g["formStructureAuthority"], "native_authority")
            self.assertIn("formPresentationMode", g)
            self.assertEqual(g["formPresentationMode"], "task")
            self.assertEqual(g["compatibilityDependencies"], [])
            self.assertEqual(g["configuredSections"], [])
            names = {n.get("name") for n in self.tree_nodes(data)}
            for field in (*required, *self.SHARED_PRESENT_FIELDS):
                self.assertIn(field, names, (action_key, field))
                self.assertEqual(len(self.field_nodes(data, field)), 1, (action_key, field))

    def test_shared_form_effective_field_rules(self):
        """Field presence is not usability: ownership, conditional visibility
        expressions and readonly constraints are asserted on the final tree
        for every formal entry."""
        for action_key, _required in self.FORMAL_ACTIONS:
            data = self.contract(action_key)
            # prepaid-only group owns the prepaid fields and carries the
            # preexisting direction condition (unchanged by the migration,
            # see test_tax_type_input_visibility_is_preexisting_native_rule)
            prepaid = self.group_node(data, "invoice_prepaid_tax")
            self.assertEqual(prepaid["attributes"]["invisible"], self.PREPAID_INVISIBLE)
            self.assertEqual(prepaid["modifiers"]["invisible"]["raw"], self.PREPAID_INVISIBLE)
            for field in ("tax_type", "prepaid_tax_date", "tax_certificate_no"):
                self.field_node(data, field)
                self.assertEqual(self.field_parent(data, field).get("containerId"),
                                 "invoice_prepaid_tax", (action_key, field))
            # output-only business group owns the applicant fields
            output = self.group_node(data, "invoice_output_business")
            self.assertEqual(output["attributes"]["invisible"], self.OUTPUT_INVISIBLE)
            for field in ("applicant_name", "expected_receipt_date"):
                self.field_node(data, field)
                self.assertEqual(self.field_parent(data, field).get("containerId"),
                                 "invoice_output_business", (action_key, field))
            # unconditional groups must not carry an invisible expression
            for container_id in ("invoice_main", "invoice_project", "invoice_tax_details",
                                 "invoice_amount", "invoice_handling", "invoice_notes"):
                group = self.group_node(data, container_id)
                self.assertNotIn("invisible", group.get("attributes") or {}, (action_key, container_id))
            # readonly constraints survive on the final tree
            for field in ("company_id", "note_display", "invoice_attachment_text",
                          "legacy_source_model", "legacy_source_table", "legacy_record_id",
                          "legacy_document_state", "source_created_by", "source_created_at"):
                node = self.field_node(data, field)
                self.assertTrue((node.get("modifiers") or {}).get("readonly"), (action_key, field))
            # editable business fields are not silently readonly
            for field in ("partner_id", "contract_id", "settlement_id", "note"):
                node = self.field_node(data, field)
                self.assertFalse((node.get("modifiers") or {}).get("readonly") is True, (action_key, field))

    def test_tax_type_input_visibility_is_preexisting_native_rule(self):
        """The retired input contract listed tax_type in its section while the
        native view kept it in the prepaid-only group.  Reconstruct the legacy
        composite (entry contract + active shared layers + no native contract)
        in-transaction and prove the legacy projection never changed the
        tax_type node modifiers: the input-direction hiding is a preexisting
        native rule, not a migration regression."""
        migrated = self.contract("action_sc_invoice_input")
        native_config = self.ref("business_config_contract_invoice_input_productized_form_v1")
        native_config.active = False
        self.ref("business_config_contract_sc_invoice_registration_form_sections_v1").active = True
        self.ref("business_config_contract_sc_invoice_registration_p1_form_business_facts_v1").active = True
        self.ref("business_config_contract_sc_invoice_registration_form_structure_generated").active = True
        # Mechanism-equivalent replica of the retired input contract for
        # tax_type: section membership plus a field row without semantic keys
        # (the retired contract declared no readonly/visible on tax_type).
        legacy_replica = self.env["ui.business.config.contract"].create({
            "name": "uc4_legacy_input_replica_for_tax_type",
            "model": "sc.invoice.registration",
            "view_type": "form",
            "action_id": self.ref("action_sc_invoice_input").id,
            "priority": 700,
            "company_id": False,
            "active": True,
            "status": "published",
            "version_no": 1,
            "contract_json": {"view_orchestration": {
                "context": {"source": "smart_construction_core.product_release",
                            "source_status": "product_release"},
                "views": {"form": {
                    "title": "进项发票",
                    "composition_mode": "entry_semantic_surface",
                    "columns": 2,
                    "sections": [
                        {"title": "办理主信息", "sequence": 10, "columns": 2,
                         "fields": ["state", "validation_status", "name", "direction"]},
                        {"title": "进项税务信息", "sequence": 40, "columns": 2,
                         "fields": ["tax_rate", "tax_type", "invoice_content", "cost_category_name"]},
                    ],
                    "fields": [
                        {"name": "tax_type", "sequence": 270},
                        {"name": "cost_category_name", "sequence": 290},
                    ],
                }},
            }},
        })
        legacy = self.contract("action_sc_invoice_input")
        legacy_g = legacy["formStructureContract"]["sourceAuthority"]["governance_source"]
        # sanity: the reconstruction actually engages the legacy path
        self.assertEqual(legacy_g["formStructureAuthority"], "entry_semantic_surface")
        self.assertTrue(legacy_g["configuredSections"])
        # the compared nodes are structurally identical between composites
        m_node, l_node = self.field_node(migrated, "tax_type"), self.field_node(legacy, "tax_type")
        self.assertEqual(l_node.get("modifiers"), m_node.get("modifiers"))
        self.assertEqual(l_node.get("attributes"), m_node.get("attributes"))
        m_group = self.group_node(migrated, "invoice_prepaid_tax")
        l_group = self.group_node(legacy, "invoice_prepaid_tax")
        self.assertEqual(l_group["attributes"]["invisible"], self.PREPAID_INVISIBLE)
        self.assertEqual(l_group["modifiers"]["invisible"]["raw"], m_group["modifiers"]["invisible"]["raw"])
        # an input-direction record keeps the prepaid group hidden under the
        # legacy composite too: the section listing never flipped it
        self.assertIn("prepaid_tax", l_group["attributes"]["invisible"])
        legacy_replica.active = False

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
            g = data["formStructureContract"]["sourceAuthority"]["governance_source"]
            # authority must be stated explicitly; absence fails (no fallback)
            self.assertIn("formStructureAuthority", g, bypass_key)
            self.assertEqual(g["formStructureAuthority"], "native_authority", bypass_key)
            self.assertIn("formPresentationMode", g, bypass_key)
            self.assertEqual(g["formPresentationMode"], "workspace", bypass_key)
            self.assertEqual(g["configuredSections"], [])
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
        nodes = self.tree_nodes(baseline)
        field = next(n for n in nodes if n.get("name") == "invoice_no" and n["type"] == "field")
        hidden = next(n for n in nodes if n.get("name") == "note_display" and n["type"] == "field")

        def bind(node, **change):
            return {"target": node["nativeLocator"], "expected": {"type": node["type"], "name": node.get("name"), "occurrence_index": node.get("occurrenceIndex")}, **change}

        def call(cls, **params):
            result = cls(self.env).handle(payload={"params": {"role_key": role, **params}})
            self.assertTrue(result.get("ok"), result)
            return result["data"]

        # baseline visibility precondition: note_display is visible (readonly)
        self.assertFalse((self.field_node(baseline, "note_display").get("modifiers") or {}).get("invisible"))

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
        # the previewed contract hides note_display, not merely carries the patch
        self.assertTrue((self.field_node(configured, "note_display").get("modifiers") or {}).get("invisible"),
                        "preview must hide note_display on the final tree")
        published = call(BusinessConfigChangeSetPublishHandler, change_set_token=opened["token"], request_id="uc4-publish")
        self.assertTrue(published["publish_result"]["published_content_verified"])
        published_contract = self.contract(key)
        self.assertTrue((self.field_node(published_contract, "note_display").get("modifiers") or {}).get("invisible"),
                        "published contract must hide note_display on the final tree")
        for part in ("layoutContract", "statusContract", "actionContract"):
            self.assertEqual(published_contract[part], configured[part])
            self.assertEqual(self.contract(outside)[part], other[part])
        self.assertIn("受管发票号码", str(configured["layoutContract"]))
        call(BusinessConfigChangeSetRollbackHandler, change_set_token=opened["token"], request_id="uc4-rollback")
        rolled_back = self.contract(key)
        # rollback restores the visible readonly state
        self.assertFalse((self.field_node(rolled_back, "note_display").get("modifiers") or {}).get("invisible"),
                         "rollback must restore note_display visibility")
        for part in ("layoutContract", "statusContract", "actionContract"):
            self.assertEqual(rolled_back[part], baseline[part])
        self.assertEqual(self.env["sc.invoice.registration"].search([]).read(["write_date", "state"]), before)
