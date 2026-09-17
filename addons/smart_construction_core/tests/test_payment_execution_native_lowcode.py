# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "uc4_native_lowcode")
class TestPaymentExecutionNativeLowcode(TransactionCase):
    """U-C4 G04: 实付与公司支出 native semantic surface migration.

    Formal entries 837 (实付登记 / 财务中心) and 808 (公司财务支出) share model
    ``sc.payment.execution`` and the native form view 1647
    (``view_sc_payment_execution_form``).  Bypass entry 811 (往来单位付款 /
    menu 561) binds the same form through its action ``view_ids`` entry, so it
    belongs to the same consumption surface.

    The rebuilt native arch owns the structure: every released entry contract
    declares ``native_semantic_surface`` and the model-wide section mirror and
    P1 business-facts layer are retired.  The released model-wide productized
    form keeps its sparse ``semantic_anchors`` annotation but drops its own
    structural body, so body and section navigation consume one structure.

    The retired P1 layer also declared display projections of canonical fields
    that the native form already presents.  Those stay on the model with their
    list/API duty and are deliberately *not* re-presented in the body: the
    duplication inside one context is exactly what the retirement removes.  The
    one independent audit fact it declared (``created_time``) is recovered.
    """

    FORMAL_ACTIONS = (
        ("action_sc_payment_execution_actual_outflow", ("name", "project_id", "paid_amount")),
        ("action_sc_payment_execution_company_finance_expense", ("name", "project_id", "paid_amount")),
    )
    BYPASS_ACTIONS = (
        ("action_sc_payment_execution_partner_payment", ("name", "project_id", "paid_amount")),
    )
    # Business sections are opt-in through ``data-sc-anchor``; the three
    # untitled containers that arrange two sections side by side stay
    # layout-only on purpose and must not become navigation entries.
    FORM_ANCHORS = (
        "payment_main", "payment_basis", "payment_amount", "payment_note", "receipt_account",
        "payment_account", "payment_attachment", "payment_responsibility", "payment_source_trace",
    )
    # 来源与系统追溯 is a conditional section: it only resolves once a record
    # carries the legacy source state.  Every other section is unconditional.
    CONDITIONAL_ANCHORS = ("payment_source_trace",)
    RECOVERED_FIELDS = ("creator_name", "created_time")
    HEADER_BUTTONS = (
        "action_confirm", "validate_tier", "reject_tier", "action_paid", "action_cancel",
        "action_reverse_payment",
    )
    RETIRED_CONTRACTS = (
        "business_config_contract_sc_payment_execution_form_sections_v1",
        "business_config_contract_sc_payment_execution_p1_form_business_facts_v1",
        "business_config_contract_sc_payment_execution_form_structure_generated",
    )
    NATIVE_AUTHORITY_CONTRACTS = (
        "business_config_contract_payment_execution_actual_outflow_productized_form_v1",
        "business_config_contract_payment_execution_company_finance_expense_productized_form_v1",
        "business_config_contract_payment_execution_partner_payment_productized_form_v1",
        "business_config_contract_payment_execution_from_request_productized_form_v1",
    )

    def setUp(self):
        super().setUp()
        from odoo.tools.convert import convert_file
        for source in (
            "views/core/payment_execution_views.xml",
            "data/payment_execution_actual_outflow_form_productization_contract.xml",
            "data/payment_request_form_productization_contract.xml",
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
            "view_id": self.ref("view_sc_payment_execution_form").id,
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
                for child in node.get("children", []) or []:
                    yield from TestPaymentExecutionNativeLowcode.walk(
                        [child] if not isinstance(child, list) else child, node)

    def tree_nodes(self, data):
        return [n for n, _parent in self.walk(data["layoutContract"]["containerTree"])]

    def field_names(self, data):
        return [n.get("name") for n in self.tree_nodes(data) if n.get("type") == "field"]

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

    def retired_projection_fields(self):
        """Facts the retired P1 layer declared that the native arch never carried."""
        retired = self.ref("business_config_contract_sc_payment_execution_p1_form_business_facts_v1")
        form = retired.contract_json["view_orchestration"]["views"]["form"]
        declared = {row["name"] for row in form["fields"]}
        from lxml import etree
        arch = etree.fromstring(self.ref("view_sc_payment_execution_form").arch_db.encode())
        native = {node.get("name") for node in arch.xpath(".//field")}
        return sorted(declared - native)

    def test_entry_contracts_spend_one_native_structure(self):
        """Four released configurations, one native authority, no second root."""
        for contract_key in self.RETIRED_CONTRACTS:
            self.assertFalse(self.ref(contract_key).active, contract_key)
        for contract_key in self.NATIVE_AUTHORITY_CONTRACTS:
            record = self.ref(contract_key)
            self.assertTrue(record.active, contract_key)
            form_spec = record.contract_json["view_orchestration"]["views"]["form"]
            self.assertEqual(form_spec["composition_mode"], "native_semantic_surface", contract_key)
            self.assertNotIn("sections", form_spec, contract_key)
            self.assertNotIn("fields", form_spec, contract_key)
            self.assertNotIn("columns", form_spec, contract_key)
        # the model-wide released form keeps its semantic annotation only
        model_wide = self.ref("business_config_contract_payment_execution_from_request_productized_form_v1")
        self.assertTrue(model_wide.contract_json["view_orchestration"]["views"]["form"]["semantic_anchors"])
        for action_key, required in self.entries():
            data = self.contract(action_key)
            g = data["formStructureContract"]["sourceAuthority"]["governance_source"]
            self.assertEqual(g["resolvedActionId"], self.ref(action_key).id, action_key)
            self.assertEqual(g["resolvedViewId"], self.ref("view_sc_payment_execution_form").id, action_key)
            self.assertEqual(g["formStructureAuthority"], "native_authority", action_key)
            self.assertEqual(g["formPresentationMode"], "task", action_key)
            self.assertEqual(g["compatibilityDependencies"], [], action_key)
            self.assertEqual(g["configuredSections"], [], action_key)
            names = self.field_names(data)
            for field in required:
                self.assertIn(field, names, (action_key, field))
                self.assertEqual(names.count(field), 1, (action_key, field))

    def test_body_presents_each_fact_once_and_projection_duplicates_are_gone(self):
        """One fact, one node: no duplicated presentation inside the same context."""
        projections = self.retired_projection_fields()
        self.assertTrue(projections, "the retired layer must declare projections to assert against")
        for action_key, _required in self.entries():
            data = self.contract(action_key)
            names = self.field_names(data)
            duplicated = sorted({name for name in names if names.count(name) > 1})
            self.assertEqual(duplicated, [], (action_key, "each business fact must render once"))
            # the statusbar is the single presenter of the workflow state
            self.assertEqual(names.count("state"), 1, action_key)
            for field in self.RECOVERED_FIELDS:
                node = self.field_node(data, field)
                self.assertTrue((node.get("modifiers") or {}).get("readonly"), (action_key, field))
            for field in projections:
                self.assertNotIn(field, names, (action_key, field))

    def test_native_anchors_buttons_and_conditional_section_survive(self):
        """Action carriers and the conditional section keep their native place."""
        from lxml import etree
        arch = etree.fromstring(self.ref("view_sc_payment_execution_form").arch_db.encode())
        anchors = {g.get("data-sc-anchor") for g in arch.xpath(".//group[@data-sc-anchor]")}
        self.assertEqual(anchors, set(self.FORM_ANCHORS))
        # layout wrappers arrange columns only; they must not claim a section
        wrappers = [g for g in arch.xpath("./sheet/group[not(@data-sc-anchor)]")]
        self.assertEqual(len(wrappers), 3, "the column layout containers are not business sections")
        buttons = {b.get("name") for b in arch.xpath(".//header/button")}
        self.assertEqual(buttons, set(self.HEADER_BUTTONS))
        statusbar = arch.xpath('.//header/field[@name="state"]/@widget')
        self.assertEqual(statusbar, ["statusbar"])
        form_fields = [node.get("name") for node in arch.xpath(".//field")]
        self.assertEqual(len(form_fields), len(set(form_fields)),
                         "the form body presents a field more than once")
        # the conditional source-trace section keeps its condition; every other
        # business section is unconditional
        for anchor in self.FORM_ANCHORS:
            group = arch.xpath('.//group[@data-sc-anchor="%s"]' % anchor)[0]
            if anchor in self.CONDITIONAL_ANCHORS:
                self.assertEqual(group.get("invisible"), "state != 'legacy_confirmed'", anchor)
            else:
                self.assertIsNone(group.get("invisible"), anchor)
        # the responsibility summary button keeps its carrier and its condition
        carrier = arch.xpath('.//group[@data-sc-anchor="payment_responsibility"]/button')
        self.assertEqual([b.get("name") for b in carrier],
                         ["action_view_company_contractor_responsibility_summary"])
        self.assertEqual(carrier[0].get("invisible"), "not company_contractor_responsibility_summary_id")
        for action_key, _required in self.entries():
            data = self.contract(action_key)
            for container_id in self.FORM_ANCHORS:
                if container_id in self.CONDITIONAL_ANCHORS:
                    continue
                self.assertNotIn("invisible", self.group_node(data, container_id).get("attributes") or {},
                                 (action_key, container_id))

    def test_retired_projections_keep_their_storage_and_list_duty(self):
        """No field was deleted: only the duplicate body presentation is gone."""
        model = self.env["sc.payment.execution"]
        for field in self.retired_projection_fields():
            self.assertIn(field, model._fields, field)
        list_arch = "".join(self.env["ir.ui.view"].search([
            ("model", "=", "sc.payment.execution"), ("type", "in", ("tree", "search"))]).mapped("arch_db"))
        self.assertTrue(list_arch)
        # the projections that carry list columns keep them
        for field in ("partner_payment_project_name", "partner_payment_writer",
                      "company_finance_note_display", "company_finance_push_result"):
            self.assertIn(field, list_arch, field)
        # the audit pair is recovered into the native body, readonly, once
        for action_key, _required in self.entries():
            names = self.field_names(self.contract(action_key))
            for field in self.RECOVERED_FIELDS:
                self.assertEqual(names.count(field), 1, (action_key, field))

    def test_sibling_entries_keep_their_own_action_and_domain(self):
        """One shared native form, three entries, each with its own query."""
        form_id = self.ref("view_sc_payment_execution_form").id
        expectations = {
            "action_sc_payment_execution_actual_outflow": (
                "[('source_kind', '=', 'actual_outflow')]",
                {"tree": self.ref("view_sc_payment_execution_tree").id, "form": form_id}),
            "action_sc_payment_execution_partner_payment": (
                "[('source_kind', '=', 'actual_outflow'), ('business_category_id.code', '=', 'finance.payment.execution.partner')]",
                {"tree": self.ref("view_sc_payment_execution_partner_formal_tree").id, "form": form_id}),
        }
        for action_key, (domain, views) in expectations.items():
            action = self.ref(action_key)
            self.assertEqual(action.res_model, "sc.payment.execution", action_key)
            self.assertEqual(action.domain, domain, action_key)
            self.assertEqual({row.view_mode: row.view_id.id for row in action.view_ids}, views, action_key)
            self.assertEqual(action.groups_id, self.ref("action_sc_payment_execution_actual_outflow").groups_id,
                             action_key + " must keep the same permission surface")
        expense = self.ref("action_sc_payment_execution_company_finance_expense")
        self.assertEqual(expense.res_model, "sc.payment.execution")
        self.assertIn("business_category_id.code", expense.domain)
        self.assertEqual(expense.view_id.id, self.ref("view_sc_payment_execution_formal_company_finance_expense_tree").id)
        self.assertEqual(expense.view_id.type, "tree")

    def test_each_entry_applies_only_its_own_released_contract(self):
        """Sharing one native form must not merge sibling entry declarations."""
        owned = {
            "action_sc_payment_execution_actual_outflow":
                "payment_execution_actual_outflow_productized_form_v1",
            "action_sc_payment_execution_company_finance_expense":
                "payment_execution_company_finance_expense_productized_form_v1",
            "action_sc_payment_execution_partner_payment":
                "payment_execution_partner_payment_productized_form_v1",
        }
        titles = {}
        for action_key, own_name in owned.items():
            data = self.contract(action_key)
            applied = {row["name"] for row in data["formStructureContract"]["sourceAuthority"]
                       ["governance_source"]["businessConfigContracts"]}
            self.assertIn(own_name, applied, action_key)
            for sibling in set(owned.values()) - {own_name}:
                self.assertNotIn(sibling, applied, (action_key, sibling))
            own = self.env["ui.business.config.contract"].search([("name", "=", own_name)], limit=1)
            self.assertTrue(own, own_name)
            expected_title = own.contract_json["view_orchestration"]["views"]["form"]["title"]
            self.assertEqual(data["formStructureContract"]["navigation"]["title"], expected_title, action_key)
            titles[action_key] = expected_title
        self.assertEqual(len(set(titles.values())), len(titles), "entry titles must stay distinct")

    def test_scoped_lowcode_preview_publish_and_rollback_after_migration(self):
        from odoo.addons.smart_core.handlers.business_config_change_set import (
            BusinessConfigChangeSetOpenHandler, BusinessConfigChangeSetStageHandler,
            BusinessConfigChangeSetPreviewHandler, BusinessConfigChangeSetPublishHandler,
            BusinessConfigChangeSetRollbackHandler,
        )
        from odoo.addons.smart_core.handlers.ui_contract_v2 import authoritative_form_role_key
        role = authoritative_form_role_key(self.env)
        key, outside = "action_sc_payment_execution_actual_outflow", "action_sc_payment_execution_partner_payment"
        baseline, other = self.contract(key), self.contract(outside)
        nodes = self.tree_nodes(baseline)
        labelled = next(n for n in nodes if n.get("name") == "note" and n["type"] == "field")
        hidden = next(n for n in nodes if n.get("name") == "planned_amount" and n["type"] == "field")

        def bind(node, **change):
            return {"target": node["nativeLocator"],
                    "expected": {"type": node["type"], "name": node.get("name"),
                                 "occurrence_index": node.get("occurrenceIndex")}, **change}

        def call(cls, **params):
            result = cls(self.env).handle(payload={"params": {"role_key": role, **params}})
            self.assertTrue(result.get("ok"), result)
            return result["data"]

        self.assertFalse((self.field_node(baseline, "planned_amount").get("modifiers") or {}).get("invisible"))
        before = self.env["sc.payment.execution"].search([]).read(["write_date", "state"])
        opened = call(BusinessConfigChangeSetOpenHandler)
        call(BusinessConfigChangeSetStageHandler, change_set_token=opened["token"], config_type="form",
             target_key="view_orchestration:uc4_g04_transaction", model="sc.payment.execution", view_type="form",
             action_id=self.ref(key).id, view_id=self.ref("view_sc_payment_execution_form").id,
             draft_payload={"view_orchestration": {"views": {"form": {"node_patches": [
                 bind(labelled, set={"label": "受管办理说明"}),
                 bind(hidden, set={"visible": False})]}}}})
        preview = call(BusinessConfigChangeSetPreviewHandler, change_set_token=opened["token"])
        configured = self.contract(key, preview_token=preview["preview"]["token"], preview_role_key=role)
        self.assertTrue((self.field_node(configured, "planned_amount").get("modifiers") or {}).get("invisible"),
                        "preview must hide planned_amount on the final tree")
        published = call(BusinessConfigChangeSetPublishHandler, change_set_token=opened["token"],
                         request_id="uc4-g04-publish")
        self.assertTrue(published["publish_result"]["published_content_verified"])
        published_contract = self.contract(key)
        self.assertTrue((self.field_node(published_contract, "planned_amount").get("modifiers") or {}).get("invisible"),
                        "published contract must hide planned_amount on the final tree")
        self.assertIn("受管办理说明", str(configured["layoutContract"]))
        for part in ("layoutContract", "statusContract", "actionContract"):
            self.assertEqual(published_contract[part], configured[part])
            # the sibling entry of the same native form keeps its own contract
            self.assertEqual(self.contract(outside)[part], other[part])
        call(BusinessConfigChangeSetRollbackHandler, change_set_token=opened["token"], request_id="uc4-g04-rollback")
        rolled_back = self.contract(key)
        self.assertFalse((self.field_node(rolled_back, "planned_amount").get("modifiers") or {}).get("invisible"),
                         "rollback must restore planned_amount visibility")
        for part in ("layoutContract", "statusContract", "actionContract"):
            self.assertEqual(rolled_back[part], baseline[part])
        self.assertEqual(self.env["sc.payment.execution"].search([]).read(["write_date", "state"]), before)
