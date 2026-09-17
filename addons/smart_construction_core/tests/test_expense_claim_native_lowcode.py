# -*- coding: utf-8 -*-
import re

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "uc4_native_lowcode")
class TestExpenseClaimNativeLowcode(TransactionCase):
    """U-C4 G05: 报销申请 / 扣款登记 / 备用金 native semantic surface migration.

    Formal entries 792 (报销申请 / menu 578), 798 (扣款登记 / menu 563) and 793
    (备用金 / menu 575) share model ``sc.expense.claim`` and the two native form
    views ``view_sc_expense_claim_form`` and
    ``view_sc_expense_claim_deduction_registration_form``.  Menu 543
    (费用与保证金) bypasses the reimbursement action and therefore consumes the
    same ``view_sc_expense_claim_form`` surface.

    The rebuilt native arch owns the structure: entries 792 and 798 declare
    ``native_semantic_surface`` and drop their own section/field/column bodies,
    so the body and the section navigation consume one structure.  Every fact
    those retired bodies declared still renders exactly once because the native
    arch gained the facts only the configuration declared.  The other fourteen
    productized configurations of the same model keep their own entry structure
    and are the shared blast radius: they must not be rewritten, and they must
    not be re-projected on top of a native-authority entry either.

    793 (备用金) shares the same body but had no entry-scoped release, so it
    resolved through the model wide generated configuration
    ``sc_expense_claim_form_structure_generated_v1``: ``native_authority`` with
    independent slots, which makes the entry consume the compatibility
    presentation.  That presentation prunes every create-mode read-only fact
    without a value, which emptied the whole entry body on a read-mostly entry.
    Its own entry release restores the native structure for this entry; the
    model wide configuration stays untouched for its other consumers.
    """

    # Views are addressed by xmlid, never by a database id: a clean install or a
    # tenant database assigns different ids to the same native form views.
    RECLAIM_VIEW = "view_sc_expense_claim_form"
    DEDUCTION_VIEW = "view_sc_expense_claim_deduction_registration_form"
    RECLAIM_ENTRY = ("action_sc_expense_claim_reimbursement_request", RECLAIM_VIEW, "报销申请")
    DEDUCTION_ENTRY = ("action_sc_expense_claim_deduction_bill", DEDUCTION_VIEW, "扣款登记")
    ADVANCE_FUND_ENTRY = ("action_sc_expense_claim_advance_fund", DEDUCTION_VIEW, "备用金")
    SIBLING_ENTRIES = (
        ("action_sc_expense_claim_expense", RECLAIM_VIEW, "费用报销单", 8),
        ("action_sc_expense_claim_project", RECLAIM_VIEW, "项目费用报销单", 7),
    )
    FORMAL_ENTRIES = (RECLAIM_ENTRY, DEDUCTION_ENTRY, ADVANCE_FUND_ENTRY)
    # The model wide generated configuration sc.expense.claim fell back to before
    # 793 declared an entry release of its own.
    MODEL_WIDE_GENERATED_CONTRACT = "sc_expense_claim_form_structure_generated_v1"

    CLAIM_DECLARED = (
        "state", "validation_status", "name", "claim_flow_label", "claim_type", "direction",
        "business_category_id", "source_origin", "project_id", "operation_strategy", "company_id",
        "company_name_text", "partner_id", "payment_request_id", "applicant_name", "department_name",
        "expense_type", "summary", "date_claim", "fill_date", "handling_kind", "business_axis",
        "amount", "approved_amount", "paid_amount", "unpaid_amount", "currency_id", "payment_state",
        "payment_method", "payment_anchor_policy", "payee", "receipt_account_name", "payee_account",
        "payee_bank", "payment_account_name", "payer_account", "payer_bank", "note", "attachment_ids",
        "reject_reason", "return_reason", "legacy_source_model", "legacy_source_table",
        "legacy_record_id", "legacy_document_no", "legacy_document_state", "creator_name",
        "created_time", "active",
    )
    DEDUCTION_DECLARED = (
        "state", "validation_status", "name", "claim_flow_label", "claim_type", "direction",
        "business_category_id", "source_origin", "project_id", "operation_strategy", "company_id",
        "company_name_text", "partner_id", "payment_request_id", "expense_type", "summary",
        "date_claim", "fill_date", "handling_kind", "business_axis", "deduction_line_ids",
        "deduction_line_amount_total", "amount", "approved_amount", "paid_amount", "unpaid_amount",
        "currency_id", "payment_state", "company_contractor_responsibility_state",
        "company_contractor_arrival_unprocessed_amount",
        "company_contractor_arrival_over_processed_amount",
        "company_contractor_self_funding_balance", "company_contractor_responsibility_notice",
        "payee", "receipt_account_name", "payee_account", "payee_bank", "payment_account_name",
        "payer_account", "payer_bank", "payment_method", "note", "attachment_ids", "reject_reason",
        "return_reason", "legacy_source_model", "legacy_source_table", "legacy_record_id",
        "legacy_document_no", "legacy_document_state", "creator_name", "created_time", "active",
    )

    CLAIM_ANCHORS = (
        "claim_business_direction", "claim_amount_status", "claim_project_partner",
        "claim_applicant_payee", "claim_payment_account", "claim_deposit_handling",
        "claim_matter_note", "claim_note_attachment", "contractor_responsibility",
        "claim_source_trace",
    )
    DEDUCTION_ANCHORS = (
        "deduction_basic", "deduction_responsible_party", "deduction_description",
        "deduction_lines", "deduction_amount_summary", "deduction_note_attachment",
        "deduction_payment_account", "contractor_responsibility", "deduction_source_trace",
    )
    HEADER_BUTTONS = (
        "action_submit", "validate_tier", "reject_tier", "action_approve", "action_done",
        "action_cancel",
    )
    # The responsibility summary action is not a header action: it keeps its
    # carrier inside the responsibility section, next to the record it explains.
    CARRIER_BUTTON = "action_view_company_contractor_responsibility_summary"
    # Facts the retired entry bodies declared that the native arch did not carry.
    # They are recovered on the arch so that retiring the configuration body
    # cannot make a business fact disappear.
    RECOVERED_CLAIM_FACTS = (
        "company_id", "reject_reason", "legacy_source_model", "legacy_source_table",
        "legacy_record_id", "legacy_document_no", "legacy_document_state", "creator_name",
        "created_time",
    )
    RECOVERED_DEDUCTION_FACTS = (
        "claim_flow_label", "company_id", "company_name_text", "payment_request_id",
        "paid_amount", "unpaid_amount", "payment_state", "payee", "receipt_account_name",
        "payee_account", "payee_bank", "payment_account_name", "payer_account", "payer_bank",
        "payment_method", "reject_reason", "return_reason", "legacy_source_model",
        "legacy_source_table", "legacy_record_id", "legacy_document_no", "legacy_document_state",
        "creator_name", "created_time",
    )
    # Facts the recalled bodies declared read-only that the model does not make
    # read-only on its own, so the arch has to carry the declaration.
    DECLARED_READONLY_CLAIM_FACTS = (
        "reject_reason", "legacy_source_model", "legacy_source_table", "legacy_record_id",
        "legacy_document_no", "legacy_document_state", "creator_name", "created_time",
        # 217 declared these three unconditionally read-only.  The native arch already
        # carried a *conditional* read-only for the two payment facts, so retiring the
        # configuration body silently made them editable while the entry is still a
        # draft; company_name_text carried no restriction at all.  The arch now states
        # the same restriction the retired body declared.
        "company_name_text", "paid_amount", "payment_state",
    )
    DECLARED_READONLY_DEDUCTION_FACTS = (
        "claim_flow_label", "company_id", "company_name_text", "paid_amount", "unpaid_amount",
        "payment_state", "reject_reason", "legacy_source_model", "legacy_source_table",
        "legacy_record_id", "legacy_document_no", "legacy_document_state", "creator_name",
        "created_time",
    )
    # The draft-period handling facts keep their authoring behaviour.
    AUTHORABLE_DEDUCTION_FACTS = (
        "payee", "receipt_account_name", "payee_account", "payee_bank", "payment_account_name",
        "payer_account", "payer_bank", "payment_method", "payment_request_id", "return_reason",
    )
    RETIRED_ENTRY_CONTRACTS = (
        "business_config_contract_expense_claim_reimbursement_request_productized_form_v1",
        "business_config_contract_expense_claim_deduction_bill_productized_form_v1",
    )
    # Entry-scoped release each formal entry must resolve through.  793 has no
    # retired body (it never declared one), so it is tracked separately from the
    # two contracts whose bodies were retired by this batch.
    ENTRY_CONTRACTS = {
        RECLAIM_ENTRY[0]: RETIRED_ENTRY_CONTRACTS[0],
        DEDUCTION_ENTRY[0]: RETIRED_ENTRY_CONTRACTS[1],
        ADVANCE_FUND_ENTRY[0]: "business_config_contract_expense_claim_advance_fund_productized_form_v1",
    }
    SIBLING_CONTRACTS = (
        "business_config_contract_expense_claim_expense_productized_form_v1",
        "business_config_contract_payment_deposit_refund_productized_form_v1",
        "business_config_contract_expense_claim_bid_deposit_pay_productized_form_v1",
        "business_config_contract_expense_claim_bid_deposit_return_productized_form_v1",
        "business_config_contract_expense_claim_contract_deposit_pay_productized_form_v1",
        "business_config_contract_expense_claim_contract_deposit_return_productized_form_v1",
        "business_config_contract_expense_claim_project_expense_productized_form_v1",
        "business_config_contract_expense_claim_repayment_registration_productized_form_v1",
        "business_config_contract_expense_claim_contractor_project_repay_productized_form_v1",
        "business_config_contract_expense_claim_project_repay_company_productized_form_v1",
        "business_config_contract_expense_claim_deduction_paid_productized_form_v1",
        "business_config_contract_expense_claim_deduction_paid_refund_productized_form_v1",
        "business_config_contract_expense_claim_payment_deposit_return_productized_form_v1",
        "business_config_contract_expense_claim_payment_deposit_return_refund_productized_form_v1",
    )

    def setUp(self):
        super().setUp()
        from odoo.tools.convert import convert_file
        for source in (
            "views/core/expense_claim_views.xml",
            "data/expense_claim_form_productization_contract.xml",
            "data/view_orchestration_form_section_contract_data.xml",
            "data/view_orchestration_contract_generated_data.xml",
        ):
            convert_file(self.env, "smart_construction_core", source, {}, mode="update", noupdate=False)

    def ref(self, key):
        return self.env.ref("smart_construction_core." + key)

    def view_ref_id(self, key):
        if isinstance(key, int):
            return key
        return self.env.ref("smart_construction_core." + key).id

    def contract(self, action_key, view_id, **extra):
        from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler
        action = self.ref(action_key)
        result = UiContractV2Handler(self.env, su_env=self.env["ir.model"].sudo().env).handle({
            "op": "model", "model": action.res_model, "action_id": action.id,
            "view_id": self.ref(view_id).id if isinstance(view_id, str) else view_id,
            "view_type": "form", "render_profile": "create", **extra,
        })
        result = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
        self.assertTrue(result.get("ok", True), result.get("error"))
        return result["data"]

    def governance(self, action_key, view_id):
        data = self.contract(action_key, view_id)
        return data["formStructureContract"]["sourceAuthority"]["governance_source"]

    @staticmethod
    def walk(rows, parent=None):
        for node in rows if isinstance(rows, list) else []:
            if isinstance(node, dict):
                yield node, parent
                for child in node.get("children", []) or []:
                    yield from TestExpenseClaimNativeLowcode.walk([child], node)

    def tree_nodes(self, data):
        return [n for n, _parent in self.walk(data["layoutContract"]["containerTree"])]

    def tree_field_names(self, data):
        return [n.get("name") for n in self.tree_nodes(data) if n.get("type") == "field"]

    def field_node(self, data, name):
        nodes = [n for n in self.tree_nodes(data) if n.get("type") == "field" and n.get("name") == name]
        self.assertEqual(len(nodes), 1, "expected single occurrence of %s" % name)
        return nodes[0]

    def widget_status(self, data):
        """Per-field policy the compiled contract hands to the renderer."""
        rows = {}
        for row in (data.get("statusContract") or {}).get("widgetStatus") or []:
            match = re.match(r"^field\.([^.]+)\.occ\.", str(row.get("widgetId") or ""))
            if match:
                rows.setdefault(match.group(1), row)
        return rows

    def group_node(self, data, container_id):
        groups = [n for n in self.tree_nodes(data)
                  if n.get("containerType") == "group" and n.get("containerId") == container_id]
        self.assertEqual(len(groups), 1, "expected single rendered group %s" % container_id)
        return groups[0]

    def rendered_anchors(self, data):
        return [n.get("containerId") for n in self.tree_nodes(data)
                if (n.get("attributes") or {}).get("data-sc-anchor")]

    def arch(self, view_key):
        from lxml import etree
        return etree.fromstring(self.ref(view_key).arch_db.encode())

    def container_chain(self, data, container_id):
        """Ancestor container ids from the sheet down to the requested container."""
        found = []

        def visit(rows, chain):
            for node in rows if isinstance(rows, list) else []:
                if not isinstance(node, dict):
                    continue
                node_chain = chain + [node.get("containerId")]
                if node.get("containerId") == container_id:
                    found.append(node_chain)
                visit(node.get("children", []) or [], node_chain)

        visit(data["layoutContract"]["containerTree"], [])
        self.assertEqual(len(found), 1, "expected one chain for %s" % container_id)
        return found[0]

    def test_entry_contracts_spend_one_native_structure(self):
        """Two released configurations, one native authority, no second root."""
        for contract_key in self.RETIRED_ENTRY_CONTRACTS:
            record = self.ref(contract_key)
            self.assertTrue(record.active, contract_key)
            self.assertEqual(record.contract_json["view_orchestration"]["context"]["source_status"],
                             "product_release", contract_key)
            form_spec = record.contract_json["view_orchestration"]["views"]["form"]
            self.assertEqual(form_spec["composition_mode"], "native_semantic_surface", contract_key)
            self.assertNotIn("sections", form_spec, contract_key)
            self.assertNotIn("fields", form_spec, contract_key)
            self.assertNotIn("columns", form_spec, contract_key)

        for action_key, view_id, title in self.FORMAL_ENTRIES:
            data = self.contract(action_key, view_id)
            contract = data["formStructureContract"]
            governance = contract["sourceAuthority"]["governance_source"]
            self.assertEqual(governance["resolvedActionId"], self.ref(action_key).id, action_key)
            self.assertEqual(governance["resolvedViewId"], self.view_ref_id(view_id), action_key)
            self.assertEqual(governance["formStructureAuthority"], "native_authority", action_key)
            self.assertEqual(governance["formPresentationMode"], "task", action_key)
            self.assertEqual(governance["configuredSections"], [], action_key)
            self.assertEqual(contract["layoutPolicy"], "container_tree_authority", action_key)
            self.assertEqual(contract["navigation"]["title"], title, action_key)
            # the released configuration keeps its title without projecting a body
            self.assertFalse(contract["slots"], action_key)

        # 备用金 declares its own entry release instead of resolving through the
        # model-wide generated configuration.  The structure it consumes is the
        # same native tree its two siblings consume, so the entry cannot fall back
        # to the compatibility presentation that emptied its whole body.
        action_key, view_id, title = self.ADVANCE_FUND_ENTRY
        entry_record = self.ref(self.ENTRY_CONTRACTS[action_key])
        self.assertTrue(entry_record.active)
        self.assertEqual(entry_record.action_id.id, self.ref(action_key).id)
        entry_spec = entry_record.contract_json["view_orchestration"]["views"]["form"]
        self.assertEqual(entry_spec["composition_mode"], "native_semantic_surface")
        for absent in ("sections", "fields", "columns"):
            self.assertNotIn(absent, entry_spec, "the entry release must not project its own body")
        data = self.contract(action_key, view_id)
        contract = data["formStructureContract"]
        governance = contract["sourceAuthority"]["governance_source"]
        self.assertEqual(governance["resolvedActionId"], self.ref(action_key).id)
        self.assertEqual(governance["resolvedViewId"], self.view_ref_id(view_id))
        self.assertEqual(governance["formStructureAuthority"], "native_authority")
        self.assertEqual(governance["formPresentationMode"], "task")
        self.assertEqual(governance["configuredSections"], [])
        self.assertEqual([row["name"] for row in governance["businessConfigContracts"]], [entry_record.name])
        self.assertEqual(contract["layoutPolicy"], "container_tree_authority")
        self.assertEqual(contract["navigation"]["title"], title)
        self.assertFalse(contract["slots"])
        self.assertFalse(contract["fieldRoles"])
        # the structure the entry renders is the native body, not the sparse
        # model-wide annotation the entry used to fall back to
        self.assertTrue(self.tree_field_names(data), "备用金 must consume a native body")
        # the fallback configuration keeps serving its other consumers untouched
        generated = self.env["ui.business.config.contract"].search(
            [("name", "=", self.MODEL_WIDE_GENERATED_CONTRACT)])
        self.assertEqual(len(generated), 1, "the model-wide configuration must not be deleted")
        self.assertTrue(generated.active)
        self.assertFalse(generated.action_id)
        self.assertNotIn(generated.name, [row["name"] for row in governance["businessConfigContracts"]])
        # the three entries are distinct entries of one shared body
        self.assertEqual(len({action for action, _view, _title in self.FORMAL_ENTRIES}), 3)

    def test_legacy_structure_cannot_re_project_over_a_native_authority_entry(self):
        """The shared mechanism suppresses the legacy chapters on all three entries."""
        model_wide = self.MODEL_WIDE_GENERATED_CONTRACT
        for action_key, view_id, _title in self.FORMAL_ENTRIES:
            governance = self.governance(action_key, view_id)
            applied = [row["name"] for row in governance["businessConfigContracts"]]
            own = self.ref(self.ENTRY_CONTRACTS[action_key]).name
            self.assertEqual(applied, [own], action_key)
            conflicts = [row for row in governance["structureDiagnostics"]
                         if row["code"] == "LEGACY_STRUCTURE_SUPPRESSED_BY_NATIVE_VIEW"]
            self.assertTrue(conflicts, (action_key, "the model-wide legacy structure must be reported"))
            suppressed = {row["configuration"]["name"] for row in conflicts}
            self.assertIn(model_wide, suppressed, action_key)
            for row in conflicts:
                self.assertFalse(row["explicit_structure_scope"], action_key)
                self.assertEqual({owner["name"] for owner in row["competing_owners"]}, {own}, action_key)
            # the suppression is a real compatibility dependency, not a silent drop
            self.assertEqual(
                governance["compatibilityDependencies"], ["legacy_configuration_structure_suppression"],
                action_key,
            )
            self.assertEqual(governance["configuredSections"], [], action_key)

    def test_sibling_entries_keep_their_own_configuration_structure(self):
        """Fourteen sibling configurations of the same model are shared surface, not scope."""
        for contract_key in self.SIBLING_CONTRACTS:
            record = self.ref(contract_key)
            self.assertTrue(record.active, contract_key)
            form_spec = record.contract_json["view_orchestration"]["views"]["form"]
            self.assertEqual(form_spec["composition_mode"], "entry_semantic_surface", contract_key)
            self.assertTrue(form_spec["sections"], contract_key)
            self.assertTrue(form_spec["fields"], contract_key)
        for action_key, view_id, title, section_count in self.SIBLING_ENTRIES:
            governance = self.governance(action_key, view_id)
            self.assertEqual(governance["formStructureAuthority"], "entry_semantic_surface", action_key)
            self.assertEqual(governance["formPresentationMode"], "task", action_key)
            self.assertEqual(len(governance["configuredSections"]), section_count, action_key)
            self.assertNotIn(
                [row["name"] for row in governance["businessConfigContracts"]],
                [[self.ref(key).name] for key in self.RETIRED_ENTRY_CONTRACTS],
                "a sibling entry must not consume a retired entry configuration",
            )
            data = self.contract(action_key, view_id)
            self.assertEqual(data["formStructureContract"]["layoutPolicy"], "business_config_sections", action_key)
            self.assertEqual(data["formStructureContract"]["navigation"]["title"], title, action_key)

    def test_every_declared_fact_still_renders_exactly_once(self):
        """Retiring the configuration body must not drop or duplicate a business fact."""
        for (action_key, view_id, _title), declared in (
            (self.RECLAIM_ENTRY, self.CLAIM_DECLARED),
            (self.DEDUCTION_ENTRY, self.DEDUCTION_DECLARED),
        ):
            data = self.contract(action_key, view_id)
            names = self.tree_field_names(data)
            duplicated = sorted({name for name in names if names.count(name) > 1})
            self.assertEqual(duplicated, [], (action_key, "each fact must render once"))
            missing = [name for name in declared if name not in names]
            self.assertEqual(missing, [], (action_key, "the retired body declared facts that no longer render"))
            unexpected = [name for name in names if name not in declared and name not in (
                "can_review", "clearing_method", "financial_flow", "guarantee_project_name",
                "guarantee_type", "is_returned", "company_contractor_responsibility_summary_id",
                "company_contractor_responsibility_state",
                "company_contractor_arrival_unprocessed_amount",
                "company_contractor_arrival_over_processed_amount",
                "company_contractor_self_funding_balance",
                "company_contractor_responsibility_notice", "payment_anchor_policy",
            )]
            self.assertEqual(unexpected, [], (action_key, "the native body gained a fact the entry never presented"))

    def test_recovered_facts_keep_their_declared_readonly_behaviour(self):
        """A fact recovered from the retired body keeps the read-only declaration it had."""
        for (action_key, view_id, _title), readonly_facts, authorable in (
            (self.RECLAIM_ENTRY, self.DECLARED_READONLY_CLAIM_FACTS, ()),
            (self.DEDUCTION_ENTRY, self.DECLARED_READONLY_DEDUCTION_FACTS, self.AUTHORABLE_DEDUCTION_FACTS),
        ):
            data = self.contract(action_key, view_id)
            status = self.widget_status(data)
            for name in readonly_facts:
                node = self.field_node(data, name)
                self.assertTrue((node.get("modifiers") or {}).get("readonly"), (action_key, name))
                # the declaration must survive into the policy the renderer consumes,
                # not only into the compiled arch string
                self.assertTrue((status.get(name) or {}).get("readonly"),
                                (action_key, name, "declared read-only fact is editable in the contract"))
            for name in authorable:
                node = self.field_node(data, name)
                self.assertFalse((node.get("modifiers") or {}).get("readonly"), (action_key, name))
        # the recovered facts occupy the group that owns their business meaning
        data = self.contract(*self.RECLAIM_ENTRY[:2])
        for name in self.RECOVERED_CLAIM_FACTS[:2]:
            self.assertIn(self.field_node(data, name), self.group_node(data, "claim_project_partner")["children"]
                          + self.group_node(data, "claim_note_attachment")["children"])
        deduction = self.contract(*self.DEDUCTION_ENTRY[:2])
        self.assertIn(self.field_node(deduction, "company_name_text"),
                      self.group_node(deduction, "deduction_responsible_party")["children"])
        for name in ("payee", "receipt_account_name", "payee_account", "payee_bank",
                     "payment_account_name", "payer_account", "payer_bank", "payment_method"):
            self.assertIn(self.field_node(deduction, name),
                          self.group_node(deduction, "deduction_payment_account")["children"])
        self.assertIn(self.field_node(deduction, "claim_flow_label"),
                      self.group_node(deduction, "deduction_basic")["children"])
        for name in ("paid_amount", "unpaid_amount", "payment_state"):
            self.assertIn(self.field_node(deduction, name),
                          self.group_node(deduction, "deduction_amount_summary")["children"])
        for name in ("reject_reason", "return_reason"):
            self.assertIn(self.field_node(deduction, name),
                          self.group_node(deduction, "deduction_note_attachment")["children"])

    def test_native_anchors_wrappers_and_conditional_sections(self):
        """Action carriers, layout wrappers and the conditional sections keep their place."""
        for view_key, anchors, untitled in (
            ("view_sc_expense_claim_form", self.CLAIM_ANCHORS, 3),
            ("view_sc_expense_claim_deduction_registration_form", self.DEDUCTION_ANCHORS, 1),
        ):
            arch = self.arch(view_key)
            found = {node.get("data-sc-anchor") for node in arch.xpath(".//group[@data-sc-anchor]")}
            self.assertEqual(found, set(anchors), view_key)
            wrappers = [node for node in arch.xpath(".//group")
                        if not node.get("data-sc-anchor") and not node.get("string")]
            self.assertEqual(len(wrappers), untitled, view_key)
            buttons = {node.get("name") for node in arch.xpath(".//header/button")}
            self.assertEqual(buttons, set(self.HEADER_BUTTONS), view_key)
            # only the record's own body is asserted here: a nested one2many
             # row layout belongs to its own model and owns its row fields.
            form_fields = [node.get("name") for node in arch.xpath(".//field")
                           if not node.xpath("ancestor::field")]
            self.assertEqual(len(form_fields), len(set(form_fields)),
                             "%s presents a fact more than once" % view_key)
            # the responsibility action keeps its carrier and its condition
            carrier = arch.xpath('.//group[@data-sc-anchor="contractor_responsibility"]//button')
            self.assertEqual([node.get("name") for node in carrier],
                             ["action_view_company_contractor_responsibility_summary"], view_key)
            self.assertEqual(carrier[0].get("invisible"), "not company_contractor_responsibility_summary_id", view_key)
            # the migrated provenance page is conditional on the record own origin
            pages = {page.get("string"): page for page in arch.xpath(".//page")}
            self.assertEqual(pages["迁移来源"].get("invisible"), "source_origin != 'legacy'", view_key)

        # 保证金办理 is the only claim-side business section with its own condition
        claim_arch = self.arch("view_sc_expense_claim_form")
        self.assertEqual(
            claim_arch.xpath('.//group[@data-sc-anchor="claim_deposit_handling"]/@invisible'),
            ["claim_type not in ['deposit_pay', 'deposit_refund', 'deposit_receive']"],
        )
        for anchor in self.CLAIM_ANCHORS:
            if anchor == "claim_deposit_handling":
                continue
            self.assertFalse(
                claim_arch.xpath('.//group[@data-sc-anchor="%s"]/@invisible' % anchor),
                "an unconditional claim section must not become conditional: %s" % anchor,
            )
        for anchor in self.DEDUCTION_ANCHORS:
            self.assertFalse(
                self.arch("view_sc_expense_claim_deduction_registration_form")
                .xpath('.//group[@data-sc-anchor="%s"]/@invisible' % anchor),
                "an unconditional deduction section must not become conditional: %s" % anchor,
            )

        # the released tree keeps exactly the declared sections and the carriers
        for (action_key, view_id, _title), anchors in (
            (self.RECLAIM_ENTRY, self.CLAIM_ANCHORS),
            (self.DEDUCTION_ENTRY, self.DEDUCTION_ANCHORS),
        ):
            data = self.contract(action_key, view_id)
            self.assertEqual(sorted(self.rendered_anchors(data)), sorted(anchors), action_key)
            self.assertEqual(
                sorted({node.get("name") for node in self.tree_nodes(data) if node.get("type") == "button"}),
                sorted(self.HEADER_BUTTONS + (self.CARRIER_BUTTON,)), action_key,
            )

    def test_deduction_detail_collection_keeps_its_own_presenter(self):
        """The one2many明细 is not swallowed and its row model keeps its own fields."""
        arch = self.arch("view_sc_expense_claim_deduction_registration_form")
        detail = arch.xpath('.//field[@name="deduction_line_ids"]')
        self.assertEqual(len(detail), 1)
        self.assertIn("one2many", str(self.env["sc.expense.claim"]._fields["deduction_line_ids"].type))
        self.assertEqual(
            self.env["sc.expense.claim"]._fields["deduction_line_ids"].comodel_name,
            "sc.expense.claim.deduction.line",
        )
        self.assertEqual(len(detail[0].xpath("./tree")), 1, "the detail must keep its own row layout")

        data = self.contract(*self.DEDUCTION_ENTRY[:2])
        container = self.group_node(data, "deduction_lines")
        widgets = container.get("widgetList") or []
        self.assertEqual([widget.get("fieldCode") for widget in widgets], ["deduction_line_ids"])
        self.assertEqual([widget.get("widgetType") for widget in widgets], ["table"])
        names = self.tree_field_names(data)
        for row_only in ("item_name", "deduction_category", "sequence"):
            self.assertNotIn(row_only, names,
                             "a deduction row field must not be claimed as a claim-level fact")
        self.assertIn("deduction_line_amount_total", names)
        # the aggregate the retired body declared still renders once
        self.assertEqual(names.count("deduction_line_amount_total"), 1)

    def test_tab_owned_anchors_do_not_claim_the_page_level(self):
        """Notebook pages own their sections and the layout wrappers own none."""
        for (action_key, view_id, _title), page_owned, wrapped in (
            (self.DEDUCTION_ENTRY, ("contractor_responsibility", "deduction_source_trace"), ("deduction_basic",)),
            (self.RECLAIM_ENTRY, ("contractor_responsibility", "claim_source_trace"), ("claim_business_direction",)),
        ):
            data = self.contract(action_key, view_id)
            kinds = {node.get("containerId"): node.get("containerType") for node in self.tree_nodes(data)}
            for anchor in page_owned:
                chain = self.container_chain(data, anchor)
                self.assertTrue(
                    any(kinds.get(container) == "page" for container in chain[:-1]),
                    (action_key, anchor, "a tab-owned section must stay under its page"),
                )
            for anchor in wrapped:
                parent = self.container_chain(data, anchor)[-2]
                self.assertIsNone(
                    (next(node for node in self.tree_nodes(data)
                          if node.get("containerId") == parent).get("attributes") or {}).get("data-sc-anchor"),
                    (action_key, anchor, "a layout wrapper must not claim a section of its own"),
                )

    def test_scoped_lowcode_preview_publish_and_rollback_after_migration(self):
        """A scoped configuration write still round-trips on the rebuilt native tree."""
        from odoo.addons.smart_core.handlers.business_config_change_set import (
            BusinessConfigChangeSetOpenHandler, BusinessConfigChangeSetStageHandler,
            BusinessConfigChangeSetPreviewHandler, BusinessConfigChangeSetPublishHandler,
            BusinessConfigChangeSetRollbackHandler,
        )
        from odoo.addons.smart_core.handlers.ui_contract_v2 import authoritative_form_role_key
        role = authoritative_form_role_key(self.env)
        action_key, view_id, _title = self.RECLAIM_ENTRY
        sibling_key, sibling_view, _sibling_title, _sibling_sections = self.SIBLING_ENTRIES[0]
        baseline = self.contract(action_key, view_id)
        sibling = self.contract(sibling_key, sibling_view)
        labelled = self.field_node(baseline, "note")
        hidden = self.field_node(baseline, "department_name")

        def bind(node, **change):
            return {"target": node["nativeLocator"],
                    "expected": {"type": node["type"], "name": node.get("name"),
                                 "occurrence_index": node.get("occurrenceIndex")}, **change}

        def call(handler, **params):
            result = handler(self.env).handle(payload={"params": {"role_key": role, **params}})
            self.assertTrue(result.get("ok"), result)
            return result["data"]

        self.assertFalse((hidden.get("modifiers") or {}).get("invisible"))
        before = self.env["sc.expense.claim"].search([]).read(["write_date", "state"])
        opened = call(BusinessConfigChangeSetOpenHandler)
        call(BusinessConfigChangeSetStageHandler, change_set_token=opened["token"], config_type="form",
             target_key="view_orchestration:uc4_g05_transaction", model="sc.expense.claim",
             view_type="form", action_id=self.ref(action_key).id, view_id=self.view_ref_id(view_id),
             draft_payload={"view_orchestration": {"views": {"form": {"node_patches": [
                 bind(labelled, set={"label": "受管办理说明"}),
                 bind(hidden, set={"visible": False})]}}}})
        preview = call(BusinessConfigChangeSetPreviewHandler, change_set_token=opened["token"])
        configured = self.contract(action_key, view_id, preview_token=preview["preview"]["token"],
                                   preview_role_key=role)
        self.assertTrue((self.field_node(configured, "department_name").get("modifiers") or {}).get("invisible"),
                        "preview must hide department_name on the final tree")
        self.assertIn("受管办理说明", str(configured["layoutContract"]))
        published = call(BusinessConfigChangeSetPublishHandler, change_set_token=opened["token"],
                         request_id="uc4-g05-publish")
        self.assertTrue(published["publish_result"]["published_content_verified"])
        published_contract = self.contract(action_key, view_id)
        self.assertTrue(
            (self.field_node(published_contract, "department_name").get("modifiers") or {}).get("invisible"),
            "the published contract must hide department_name on the final tree",
        )
        for part in ("layoutContract", "statusContract", "actionContract"):
            self.assertEqual(published_contract[part], configured[part])
            # the sibling entry of the same native view keeps its own structure
            self.assertEqual(self.contract(sibling_key, sibling_view)[part], sibling[part])
        call(BusinessConfigChangeSetRollbackHandler, change_set_token=opened["token"],
             request_id="uc4-g05-rollback")
        rolled_back = self.contract(action_key, view_id)
        self.assertFalse(
            (self.field_node(rolled_back, "department_name").get("modifiers") or {}).get("invisible"),
            "rollback must restore department_name visibility",
        )
        for part in ("layoutContract", "statusContract", "actionContract"):
            self.assertEqual(rolled_back[part], baseline[part])
        self.assertEqual(self.env["sc.expense.claim"].search([]).read(["write_date", "state"]), before)
