# -*- coding: utf-8 -*-
import re

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "uc4_native_lowcode")
class TestTaxDeductionNativeLowcode(TransactionCase):
    """U-C4 G06: 抵扣登记 (790) / 项目专项抵扣 (879) native semantic surface migration.

    Formal entries 790 (抵扣登记 / menu 538) and 879 (项目专项抵扣 / menu 701)
    share model ``sc.tax.deduction.registration`` and the single native primary
    form ``smart_construction_core.view_sc_tax_deduction_registration_form``.
    Neither action fixes ``view_id``/``view_ids``, so both entries resolve the
    model primary form, and action 852 (扣款单) fixes only a tree view, so its
    records fall back to the same primary form as well: one body serves three
    stored entries of which two are ledger consumers, plus one derived surface
    (税务申报 → 申报期抵扣来源, ``sc.tax.filing.action_open_deductions()``) that
    returns an unstored action dict, so its form resolves with no action scope at
    all.  A model-wide contract has no action/view/role/company narrowing, which
    is why retiring one of them changes every one of those surfaces and why the
    derived surface is part of the declared scope instead of an afterthought.

    The rebuilt native arch owns the structure.  Entries 790 and 879 declare
    ``native_semantic_surface`` and drop their own section/field/column bodies,
    so body and section navigation consume one structure.  The entries keep
    their titles and their semantic context (the ``project_special`` scope
    authority of 879 is what separates the two entries, not a second body).

    Every fact those retired bodies rendered still renders exactly once.  The
    arch gained the facts only they declared and the native body did not carry
    (``company_id``, ``partner_name`` and the migrated provenance facts on a
    迁移来源 page), the arch now states the read-only restrictions the retired
    bodies declared, and the one fact the authority body presented twice
    (``withholding_amount``) is presented once, where the retired body had it.

    The retired bodies also declared ``deduction_bill_attachment_text`` and
    ``message_attachment_count``.  Those are not recovered here: the native
    arch renders the attachment fact once through ``attachment_ids`` and both
    of them expressed that same fact inside the same context, so recovering
    them would be an in-context duplicate.  Each keeps its own scenario outside
    the body (list summary, chatter count) and both are asserted below.

    The model-wide contracts
    ``sc_tax_deduction_registration_form_sections_v1`` and
    ``sc_tax_deduction_registration_form_structure_generated_v1`` have no
    action scope and keep serving action 852 (扣款单); they are neither deleted
    nor rewritten, and they are not re-projected on top of a native-authority
    entry either.  The third member of that trio,
    ``sc_tax_deduction_registration_p1_form_business_facts_v1``, is retired by
    this batch exactly as G02 / G03 / G04 retired the equivalent body: the
    rebuilt native body owns its structure, and its unconditional read-only
    fact annotations otherwise merged onto the nodes of the released entries
    and contradicted both the native arch and the delivered field policy.
    """

    NATIVE_VIEW = "view_sc_tax_deduction_registration_form"
    GENERAL_ENTRY = ("action_sc_tax_deduction_registration_user", NATIVE_VIEW, "抵扣登记")
    SPECIAL_ENTRY = ("action_sc_product_project_tax_deduction_v1", NATIVE_VIEW, "项目专项抵扣")
    FORMAL_ENTRIES = (GENERAL_ENTRY, SPECIAL_ENTRY)
    BYPASS_ENTRY = ("action_sc_tax_deduction_registration_deduction_bill_acceptance", NATIVE_VIEW, "扣款单")
    ENTRY_CONTRACTS = {
        "action_sc_tax_deduction_registration_user":
            "business_config_contract_tax_deduction_registration_productized_form_v1",
        "action_sc_product_project_tax_deduction_v1":
            "business_config_contract_project_special_tax_deduction_form_v1",
    }
    RETIRED_ENTRY_CONTRACTS = (
        "business_config_contract_tax_deduction_registration_productized_form_v1",
        "business_config_contract_project_special_tax_deduction_form_v1",
    )
    # The model-wide contracts that are still active: both keep serving action
    # 852 (扣款单), which has no release of its own.
    MODEL_WIDE_CONTRACTS = (
        "business_config_contract_sc_tax_deduction_registration_form_sections_v1",
        "business_config_contract_sc_tax_deduction_registration_form_structure_generated",
    )
    # The third member of that trio is retired by this batch, the same way G02 /
    # G03 / G04 retired the equivalent body.  Its `sections` were already
    # reported as suppressed on both released entries, but its unconditional
    # `readonly` field annotations still merged onto the nodes and contradicted
    # the native arch and the delivered policy, so a required create fact
    # (发票号码 / 抵扣税额) rendered without a control the user could fill.
    RETIRED_MODEL_WIDE_CONTRACTS = (
        "business_config_contract_sc_tax_deduction_registration_p1_form_business_facts_v1",
    )
    # Facts the retired model-wide P1 body declared read-only that the rebuilt
    # native body declares editable until `state == 'legacy_confirmed'`.  The
    # delivered policy already resolved them to `auth=edit`; the tree node used
    # to keep the retired body's unconditional read-only on top of it.
    UNFROZEN_FACTS = (
        "invoice_no", "deduction_amount", "deduction_tax_amount",
        "deduction_surcharge_amount", "note",
    )
    # The 扣款单 list scenario the retired body projected its display mirrors
    # onto.  A mirror that keeps this scenario has not lost its presentation.
    BILL_DISPLAY_VIEW = "view_sc_tax_deduction_registration_formal_deduction_bill_tree"

    # Facts the retired bodies rendered, as declared by their own field lists.
    # `deduction_bill_attachment_text` and `message_attachment_count` are
    # excluded on purpose: they repeat the attachment fact the native body
    # already renders through `attachment_ids`, in that same context, so
    # recovering them would be an in-context duplicate rather than a second
    # scenario.  They keep a list-scope and a chatter-scope expression of their
    # own and are asserted below.
    GENERAL_DECLARED = (
        "state", "name", "deduction_flow_label", "business_category_id", "source_origin", "project_id",
        "company_id", "partner_id", "partner_name", "deduction_unit_name", "document_no", "document_date",
        "invoice_no", "invoice_code", "invoice_date", "tax_rate_text", "invoice_amount_untaxed",
        "invoice_tax_amount", "invoice_amount_total", "withholding_amount", "deduction_amount",
        "deduction_tax_amount", "deduction_surcharge_amount", "currency_id", "deduction_confirm_date",
        "deduction_reason", "note", "attachment_ids",
        "legacy_source_model", "legacy_source_table", "legacy_record_id",
        "legacy_document_state", "creator_name", "created_time", "source_created_by", "source_created_at",
        "active",
    )
    SPECIAL_DECLARED = (
        "state", "name", "deduction_flow_label", "deduction_scope", "business_category_id", "source_origin",
        "project_id", "company_id", "operation_strategy", "partner_id", "partner_name", "document_no",
        "document_date", "invoice_no", "invoice_code", "invoice_date", "deduction_confirm_date",
        "tax_rate_text", "invoice_amount_untaxed", "invoice_tax_amount", "invoice_amount_total",
        "deduction_amount", "deduction_tax_amount", "deduction_surcharge_amount", "currency_id",
        "deduction_reason", "note", "attachment_ids",
    )
    # Facts the retired bodies declared that the native arch did not carry.
    RECOVERED_FACTS = (
        "company_id", "partner_name",
        "legacy_source_model", "legacy_source_table", "legacy_record_id", "legacy_document_state",
        "source_created_by", "source_created_at",
    )
    # Facts the retired bodies declared read-only that the model does not make
    # read-only on its own, so the arch has to carry the declaration.
    DECLARED_READONLY_FACTS = (
        "state", "deduction_flow_label", "company_id", "partner_name", "tax_rate_text",
        "legacy_source_model",
        "legacy_source_table", "legacy_record_id", "legacy_document_state", "creator_name",
        "created_time", "source_created_by", "source_created_at",
    )
    # 879 additionally declared these read-only, and 790 declared
    # business_category_id authorable: the arch has to keep both entries right
    # although they share one body.
    SPECIAL_DECLARED_READONLY_FACTS = (
        "deduction_scope", "business_category_id", "source_origin", "operation_strategy", "currency_id",
    )
    GENERAL_AUTHORABLE_FACTS = ("business_category_id",)

    ANCHORS = (
        "deduction_business_direction", "deduction_project_partner", "deduction_invoice_info",
        "deduction_amount_tax", "deduction_handling", "deduction_note_attachment",
        "contractor_responsibility", "deduction_source_trace",
    )
    HEADER_BUTTONS = ("action_confirm", "action_deduct", "action_cancel")
    # The responsibility summary action is not a header action: it keeps its
    # carrier inside the responsibility section, next to the record it explains.
    CARRIER_BUTTON = "action_view_company_contractor_responsibility_summary"
    # The retired bodies rendered the band between 抵扣金额与税额 and 扣款办理
    # once; the authority body presented it twice.
    SINGLE_PRESENTATION_FACTS = ("withholding_amount",)

    def setUp(self):
        super().setUp()
        from odoo.tools.convert import convert_file
        for source in (
            "views/core/tax_deduction_registration_views.xml",
            "data/tax_deduction_certificate_form_productization_contract.xml",
            "data/project_special_tax_deduction_contract.xml",
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
            "view_id": self.view_ref_id(view_id),
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
                    yield from TestTaxDeductionNativeLowcode.walk([child], node)

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

    def arch_invisible_condition(self, node):
        """Nearest declared invisible condition on a node or a container above it.

        Returns the raw attribute value: ``"1"`` for an unconditional hide, a
        Python expression for a record-dependent one (the 迁移来源 page is
        conditional on ``source_origin``), or ``None`` when nothing hides the
        node.  The expression is deliberately not evaluated here; the exact
        conditions are pinned by
        ``test_native_anchors_wrappers_and_conditional_sections``, and this test
        only establishes that hiding is always traceable to a declared
        condition instead of being a silent removal by the mechanism.
        """
        while node is not None:
            value = node.get("invisible")
            if value:
                return value
            node = node.getparent()
        return None

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
            self.assertTrue(self.tree_field_names(data), "%s must consume a native body" % action_key)

        # the two entries are distinct entries of one shared body
        self.assertEqual(len({action for action, _view, _title in self.FORMAL_ENTRIES}), 2)

    def test_legacy_structure_cannot_re_project_over_a_native_authority_entry(self):
        """The shared mechanism suppresses the model-wide chapters on both entries."""
        model_wide_names = {self.ref(key).name for key in self.MODEL_WIDE_CONTRACTS}
        for action_key, view_id, _title in self.FORMAL_ENTRIES:
            data = self.contract(action_key, view_id)
            contract = data["formStructureContract"]
            governance = contract["sourceAuthority"]["governance_source"]
            own = self.ref(self.ENTRY_CONTRACTS[action_key]).name
            applied = [row["name"] for row in governance["businessConfigContracts"]]
            self.assertIn(own, applied, action_key)
            for name in applied:
                self.assertTrue(name == own or name in model_wide_names,
                                (action_key, name, "an unexpected configuration reached this entry"))
            conflicts = [row for row in governance["structureDiagnostics"]
                         if row["code"] == "LEGACY_STRUCTURE_SUPPRESSED_BY_NATIVE_VIEW"]
            self.assertTrue(conflicts, (action_key, "the model-wide legacy structure must be reported"))
            suppressed = {row["configuration"]["name"] for row in conflicts}
            # a model-wide contract may still be listed as consulted, but its
            # body must be reported as suppressed rather than projected
            self.assertEqual(suppressed, model_wide_names,
                             (action_key, "every model-wide body must be suppressed"))
            for row in conflicts:
                self.assertFalse(row["explicit_structure_scope"], action_key)
                self.assertEqual({owner["name"] for owner in row["competing_owners"]}, {own}, action_key)
            # the suppression is a real compatibility dependency, not a silent drop
            self.assertEqual(
                governance["compatibilityDependencies"], ["legacy_configuration_structure_suppression"],
                action_key,
            )
            self.assertEqual(governance["configuredSections"], [], action_key)
            # and the native tree really is the only structure that renders
            self.assertEqual(contract["layoutPolicy"], "container_tree_authority", action_key)
            self.assertFalse(contract["slots"], action_key)

    def test_every_declared_fact_still_renders_exactly_once(self):
        """Retiring a body cannot drop or double a fact it used to render."""
        arch_fields = {node.get("name"): node for node in self.arch(self.NATIVE_VIEW).xpath(".//field")}
        for (action_key, view_id, _title), declared in (
            (self.GENERAL_ENTRY, self.GENERAL_DECLARED),
            (self.SPECIAL_ENTRY, self.SPECIAL_DECLARED),
        ):
            data = self.contract(action_key, view_id)
            rendered = self.tree_field_names(data)
            for name in declared:
                # one fact, one presentation: the authority body must not drop
                # a declared fact, nor present it twice in the same context
                self.assertEqual(rendered.count(name), 1, (action_key, name))
                # an arch declaration to hide a fact must survive as the
                # visibility policy the renderer consumes, i.e. hiding is a
                # modifier on the single occurrence and never a silent removal.
                # The lxml element is tested for None explicitly: a childless
                # element is falsy, so `element or {}` would read a hidden
                # childless field as visible.
                arch_node = arch_fields.get(name)
                self.assertIsNotNone(arch_node, (action_key, name, "declared fact is absent from the arch"))
                condition = self.arch_invisible_condition(arch_node)
                policy = self.widget_status(data).get(name)
                self.assertIsNotNone(policy, (action_key, name, "rendered fact has no consumption policy"))
                if policy.get("visible") is False:
                    # a fact may only disappear behind a condition the arch declares
                    self.assertIsNotNone(
                        condition,
                        (action_key, name, "fact was hidden without any declared arch condition"),
                    )
                if condition == "1":
                    # an unconditional hide must be consumed as hidden, never dropped
                    self.assertEqual(policy.get("visible"), False, (action_key, name))
                    self.assertEqual(policy.get("reasonCode"), "NATIVE_MODIFIER_INVISIBLE",
                                     (action_key, name))

        # the recovered facts occupy the group that owns their business meaning
        data = self.contract(*self.GENERAL_ENTRY[:2])
        for name in ("company_id", "partner_name"):
            self.assertIn(self.field_node(data, name),
                          self.group_node(data, "deduction_project_partner")["children"])
        # the attachment fact renders once in its group, through the carrier
        attachment_group = self.group_node(data, "deduction_note_attachment")["children"]
        self.assertIn(self.field_node(data, "attachment_ids"), attachment_group)
        group_field_names = [node.get("name") for node in attachment_group
                             if node.get("type") == "field"]
        for duplicate in ("deduction_bill_attachment_text", "message_attachment_count"):
            self.assertNotIn(
                duplicate, group_field_names,
                (duplicate, "same-context duplicate of the attachment carrier"),
            )
        for name in ("legacy_source_model", "legacy_source_table", "legacy_record_id",
                     "legacy_document_state", "source_created_by", "source_created_at"):
            self.assertIn(self.field_node(data, name),
                          self.group_node(data, "deduction_source_trace")["children"])

    def test_attachment_expressions_keep_their_own_scenario(self):
        """Each attachment expression survives in the scenario that owns it.

        The business body carries the attachment fact once.  The retired
        bodies' text summary keeps its list-scope expression and the chatter
        count keeps its collaboration-scope expression, so removing the
        in-context duplicate did not delete either fact from the product.
        """
        data = self.contract(*self.GENERAL_ENTRY[:2])
        body_fields = self.tree_field_names(data)
        for name in ("deduction_bill_attachment_text", "message_attachment_count"):
            self.assertEqual(
                body_fields.count(name), 0,
                (name, "attachment fact must render once in the body, not twice"),
            )
        model_fields = self.env["sc.tax.deduction.registration"]._fields
        for name in ("deduction_bill_attachment_text", "message_attachment_count"):
            self.assertIn(name, model_fields, name)
            self.assertTrue(model_fields[name].readonly, name)
        # the list scope keeps the summary expression on its own tree
        list_arch = self.arch(
            "view_sc_tax_deduction_registration_formal_deduction_bill_tree"
        )
        list_fields = {node.get("name") for node in list_arch.xpath(".//field")}
        self.assertIn("deduction_bill_attachment_text", list_fields)

    def test_recovered_facts_are_real_fields_not_copied_names(self):
        """A recovered fact must be a real field the mechanism can render."""
        model_fields = self.env["sc.tax.deduction.registration"]._fields
        arch = self.arch(self.NATIVE_VIEW)
        arch_fields = {node.get("name") for node in arch.xpath(".//field")}
        for name in self.RECOVERED_FACTS:
            self.assertIn(name, model_fields, name)
            self.assertIn(name, arch_fields, name)
        # every recovered fact is read-only on the model or on the arch, which is
        # why the arch states the restriction instead of leaving it open
        for name in ("source_created_by", "source_created_at"):
            self.assertTrue(model_fields[name].readonly, name)
        # this model also defines a prefixed provenance pair of its own; the
        # recovered provenance facts are not merged into it
        prefixed = {"deduction_bill_source_created_by", "deduction_bill_source_created_at"}
        self.assertTrue(prefixed <= set(model_fields))
        self.assertEqual(prefixed & set(self.RECOVERED_FACTS), set())

    def test_recovered_facts_keep_their_declared_readonly_behaviour(self):
        """A fact recovered from the retired body keeps the read-only declaration it had."""
        for action_key, view_id, _title in self.FORMAL_ENTRIES:
            data = self.contract(action_key, view_id)
            status = self.widget_status(data)
            for name in self.DECLARED_READONLY_FACTS:
                node = self.field_node(data, name)
                self.assertTrue((node.get("modifiers") or {}).get("readonly"), (action_key, name))
                # the declaration must survive into the policy the renderer consumes,
                # not only into the compiled arch string
                self.assertTrue((status.get(name) or {}).get("readonly"),
                                (action_key, name, "declared read-only fact is editable in the contract"))
        # 879 declared these read-only; the shared body must keep that scope read-only
        special = self.contract(*self.SPECIAL_ENTRY[:2])
        special_status = self.widget_status(special)
        for name in self.SPECIAL_DECLARED_READONLY_FACTS:
            node = self.field_node(special, name)
            self.assertTrue((node.get("modifiers") or {}).get("readonly"),
                            (self.SPECIAL_ENTRY[0], name))
            self.assertTrue((special_status.get(name) or {}).get("readonly"),
                            (self.SPECIAL_ENTRY[0], name, "declared read-only fact is editable"))
        # ... while 790 keeps the category authorable in its own scope.  The
        # shared body states the restriction as the scope condition the two
        # retired bodies implied (879 declared it read-only, 790 did not), not
        # as an unconditional read-only that would take the category away
        # from 抵扣登记.
        general = self.contract(*self.GENERAL_ENTRY[:2])
        for name in self.GENERAL_AUTHORABLE_FACTS:
            # the arch still has to state the scope condition ...
            self.assertTrue(
                (self.field_node(general, name).get("modifiers") or {}).get("readonly"),
                (self.GENERAL_ENTRY[0], name, "the arch dropped the scope condition"),
            )
            # ... and the renderer has to resolve it to an editable fact for the
            # entry that declared it authorable.  Asserting the resolved policy
            # rather than the modifier expression keeps this a behaviour check.
            policy = self.widget_status(general).get(name) or {}
            self.assertIs(policy.get("readonly"), False,
                          (self.GENERAL_ENTRY[0], name, "a fact 790 declared authorable became read-only"))
            self.assertEqual(policy.get("auth"), "edit", (self.GENERAL_ENTRY[0], name))

    def test_declared_facts_keep_a_visible_business_label(self):
        """A fact the user is asked to read or fill keeps a visible label.

        G06 验收: `deduction_reason` lost its label in the compiled body (the
        retired body declared ``nolabel="1"``), so the field showed its default
        text with nothing naming it.  The arch now states no suppression and the
        label reaches the renderer as the business label, not as the field name.
        """
        model_fields = self.env["sc.tax.deduction.registration"]._fields
        self.assertEqual(model_fields["deduction_reason"].string, "扣款事由")
        # the structure authority must not suppress the label it inherited
        arch = self.arch(self.NATIVE_VIEW)
        declarations = arch.xpath('.//field[@name="deduction_reason"]')
        self.assertTrue(declarations, "the native body dropped the fact entirely")
        for node in declarations:
            self.assertFalse(
                node.get("nolabel") in ("1", "true", "True"),
                "the body suppresses the label the business needs to read",
            )
        # the label must reach the compiled contract as a visible business label
        for action_key, view_id, _title in self.FORMAL_ENTRIES:
            data = self.contract(action_key, view_id)
            node = self.field_node(data, "deduction_reason")
            self.assertEqual(node.get("label"), "扣款事由", (action_key, "label"))
            self.assertFalse(node.get("nolabel"), (action_key, "label suppressed"))

    def test_native_anchors_wrappers_and_conditional_sections(self):
        """Action carriers, layout wrappers and the conditional sections keep their place."""
        view_key = self.NATIVE_VIEW
        arch = self.arch(view_key)
        found = {node.get("data-sc-anchor") for node in arch.xpath(".//group[@data-sc-anchor]")}
        self.assertEqual(found, set(self.ANCHORS), view_key)
        # the untitled layout wrapper is not a section and must not claim one
        wrappers = [node for node in arch.xpath(".//group")
                    if not node.get("data-sc-anchor") and not node.get("string")]
        self.assertEqual(len(wrappers), 1, view_key)
        buttons = {node.get("name") for node in arch.xpath(".//header/button")}
        self.assertEqual(buttons, set(self.HEADER_BUTTONS), view_key)
        form_fields = [node.get("name") for node in arch.xpath(".//field")
                       if not node.xpath("ancestor::field")]
        self.assertEqual(len(form_fields), len(set(form_fields)),
                         "%s presents a fact more than once" % view_key)
        for name in self.SINGLE_PRESENTATION_FACTS:
            self.assertEqual(form_fields.count(name), 1, (view_key, name))
        # the responsibility action keeps its carrier and its condition
        carrier = arch.xpath('.//group[@data-sc-anchor="contractor_responsibility"]//button')
        self.assertEqual([node.get("name") for node in carrier], [self.CARRIER_BUTTON], view_key)
        self.assertEqual(carrier[0].get("invisible"),
                         "not company_contractor_responsibility_summary_id", view_key)
        # the migrated provenance page is conditional on the record own origin
        pages = {page.get("string"): page for page in arch.xpath(".//page")}
        self.assertEqual(pages["迁移来源"].get("invisible"), "source_origin != 'legacy'", view_key)
        # the responsibility page stays conditional on the summary it explains
        self.assertEqual(pages["责任余额"].get("invisible"),
                         "not company_contractor_responsibility_summary_id", view_key)
        # the read-only restriction the retired bodies declared is stated on the arch
        self.assertEqual(arch.xpath('.//header/field[@name="state"]/@readonly'), ["1"], view_key)
        self.assertEqual(
            arch.xpath('.//field[@name="business_category_id"]/@readonly'),
            ["deduction_scope == 'project_special' or state == 'legacy_confirmed'"], view_key,
        )
        # no business section became conditional by accident
        for anchor in self.ANCHORS:
            if anchor in ("contractor_responsibility", "deduction_source_trace"):
                continue
            self.assertFalse(
                arch.xpath('.//group[@data-sc-anchor="%s"]/@invisible' % anchor),
                "an unconditional section must not become conditional: %s" % anchor,
            )

        # the released tree keeps exactly the declared sections and the carriers
        for action_key, view_id, _title in self.FORMAL_ENTRIES:
            data = self.contract(action_key, view_id)
            self.assertEqual(sorted(self.rendered_anchors(data)), sorted(self.ANCHORS), action_key)
            self.assertEqual(
                sorted({node.get("name") for node in self.tree_nodes(data) if node.get("type") == "button"}),
                sorted(self.HEADER_BUTTONS + (self.CARRIER_BUTTON,)), action_key,
            )
            page_owned = ("contractor_responsibility", "deduction_source_trace")
            kinds = {node.get("containerId"): node.get("containerType") for node in self.tree_nodes(data)}
            for anchor in page_owned:
                chain = self.container_chain(data, anchor)
                self.assertTrue(
                    any(kinds.get(container) == "page" for container in chain[:-1]),
                    (action_key, anchor, "a tab-owned section must stay under its page"),
                )

    def test_model_wide_configurations_keep_serving_the_bypass_entry(self):
        """Action 852 (扣款单) has no release of its own and keeps the model-wide floor."""
        # This batch retired the model-wide P1 fact body the same way G02 / G03 /
        # G04 retired theirs: it owned structure that view 1654 now owns, and its
        # field annotations contradicted the rebuilt body.
        for contract_key in self.RETIRED_MODEL_WIDE_CONTRACTS:
            record = self.ref(contract_key)
            self.assertFalse(record.active, (contract_key, "the retired body must stay retired"))
            self.assertFalse(record.action_id, contract_key)
            self.assertEqual(record.model, "sc.tax.deduction.registration", contract_key)
        # The remaining model-wide contracts are the ones that still serve 852.
        for contract_key in self.MODEL_WIDE_CONTRACTS:
            record = self.ref(contract_key)
            self.assertTrue(record.active, contract_key)
            self.assertFalse(record.action_id, contract_key)
            self.assertEqual(record.model, "sc.tax.deduction.registration", contract_key)
        bypass = self.ref(self.BYPASS_ENTRY[0])
        self.assertEqual(bypass.res_model, "sc.tax.deduction.registration")
        # the bypass entry fixes only a tree view, so its records resolve the
        # same primary form the two ledger entries rebuild
        self.assertFalse([row for row in (bypass.view_ids or []) if row.view_mode == "form"])
        data = self.contract(*self.BYPASS_ENTRY[:2])
        governance = data["formStructureContract"]["sourceAuthority"]["governance_source"]
        self.assertEqual(governance["resolvedViewId"], self.view_ref_id(self.NATIVE_VIEW))
        self.assertEqual(governance["resolvedActionId"], bypass.id)
        # it is a shared consumer of the rebuilt body, not a ledger entry
        self.assertNotIn(bypass.id, [self.ref(action_key).id for action_key, _v, _t in self.FORMAL_ENTRIES])
        self.assertFalse(
            self.env["ui.business.config.contract"].search([("action_id", "=", bypass.id)]),
            "扣款单 must stay an entry without a release of its own",
        )
        # and it must never consume a configuration scoped to one of the two
        # ledger entries of this model
        applied = [row["name"] for row in governance["businessConfigContracts"]]
        for contract_key in self.RETIRED_ENTRY_CONTRACTS:
            self.assertNotIn(self.ref(contract_key).name, applied)
        # 852 renders the same native body, so retiring a redundant second
        # structure may not cost it a single fact that body declared.
        self._assert_declared_facts_survive(self.BYPASS_ENTRY[0], data)

    def test_a_derived_surface_without_an_action_scope_keeps_the_declared_facts(self):
        """A surface opened by an unstored action consumes the model-wide floor.

        税务申报 → 申报期抵扣来源 is reached from the 税务申报 form's 抵扣来源
        stat button, which returns an action dict built in code
        (``sc.tax.filing._source_action``) with no stored
        ``ir.actions.act_window``.  The record page takes ``action_id`` and
        ``view_id`` from the route query, and a derived action dict carries
        neither, so this form resolves with no action scope and no view scope.

        The retired model-wide P1 body carried the same un-narrowed scope
        (``action_id`` / ``view_id`` / ``role_key`` / ``company_id`` all empty),
        so it applied to this surface exactly as it applied to 790 / 879 / 852.
        Declaring the retirement for "three entries" therefore understated it:
        this surface is inside the changed scope too and has to be proven here
        instead of being called an afterthought.
        """
        from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler

        # 1. provenance: the surface is derived from a released entry, not a
        #    stored action of its own, and it stays reachable from that entry.
        filing = self.env["sc.tax.filing"].new({})
        derived = filing.action_open_deductions()
        self.assertNotIn("id", derived, "the derived entry must not be a stored action")
        self.assertEqual(derived["res_model"], "sc.tax.deduction.registration")
        self.assertEqual(derived["view_mode"], "tree,form")
        self.assertEqual(derived["context"], {"create": False})
        filing_action = self.ref("action_sc_product_tax_filing_v1")
        filing_menu = self.env.ref("smart_construction_core.menu_sc_product_tax_filing_v1")
        self.assertEqual(filing_menu.action.res_model, "sc.tax.filing")
        self.assertEqual(
            filing_menu.action.id, filing_action.id,
            "the entry that opens this surface must stay a formal menu entry",
        )
        self.assertTrue(
            self.arch("view_sc_tax_filing_form").xpath("//button[@name='action_open_deductions']"),
            "the 税务申报 body must keep the button that opens this surface",
        )

        # 2. the request a record page issues for it: model + form, with no
        #    action scope and no view scope.  An unscoped form request resolves
        #    the model primary form, which is the same rebuilt native body the
        #    two released entries render.
        result = UiContractV2Handler(self.env, su_env=self.env["ir.model"].sudo().env).handle({
            "op": "model", "model": "sc.tax.deduction.registration",
            "view_type": "form", "render_profile": "create",
        })
        result = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
        self.assertTrue(result.get("ok", True), result.get("error"))
        data = result["data"]
        governance = data["formStructureContract"]["sourceAuthority"]["governance_source"]
        self.assertEqual(governance["resolvedActionId"], 0)
        self.assertEqual(governance["resolvedViewId"], self.view_ref_id(self.NATIVE_VIEW))

        # 3. with no entry-scoped declaration applicable, this surface consumes
        #    the model-wide floor in task mode, exactly like the tree-only 852
        #    does.  The retired body declared that same mode, so retiring it can
        #    drop the section titles and field annotations it merged in but can
        #    never flip this surface into the native authority that 790 / 879
        #    declare for themselves.
        self.assertEqual(governance["formStructureAuthority"], "entry_semantic_surface")
        retired_form_spec = self.ref(
            self.RETIRED_MODEL_WIDE_CONTRACTS[0]
        ).contract_json["view_orchestration"]["views"]["form"]
        self.assertEqual(
            retired_form_spec.get("composition_mode"), "entry_semantic_surface",
            "the retired body declared the mode this surface resolves, so the "
            "retirement cannot change the authority of any model-wide surface",
        )

        # 4. the retirement really reaches this surface: neither the retired
        #    body nor its section projection survives here, while the model-wide
        #    contract that still serves it is applied and keeps declaring the
        #    facts it carries.
        applied = [row["name"] for row in governance["businessConfigContracts"]]
        for contract_key in self.RETIRED_MODEL_WIDE_CONTRACTS:
            self.assertNotIn(
                self.ref(contract_key).name, applied,
                (contract_key, "the retired model-wide body must not reach this surface"),
            )
        self.assertIn(
            self.ref(self.MODEL_WIDE_CONTRACTS[0]).name, applied,
            "the model-wide floor must keep serving this surface",
        )
        retired_titles = [
            row.get("title") for row in retired_form_spec.get("sections") or [] if row.get("title")
        ]
        self.assertTrue(retired_titles, "the retired body must still declare the sections it merged in")
        for title in retired_titles:
            self.assertNotIn(title, governance.get("sectionTitles") or [], title)
        rendered = self.tree_field_names(data)
        generated_form_spec = self.ref(
            self.MODEL_WIDE_CONTRACTS[1]
        ).contract_json["view_orchestration"]["views"]["form"]
        for row in generated_form_spec.get("fields") or []:
            self.assertIn(
                row["name"], rendered,
                (row["name"], "the model-wide floor must keep declaring this fact here"),
            )

        # 5. and losing the retired body may not cost this surface a single
        #    fact that body declared.
        self._assert_declared_facts_survive("sc.tax.filing.action_open_deductions", data)

    def _assert_declared_facts_survive(self, action_key, data):
        """Retiring a body may not cost the product a fact that body declared.

        A fact the rebuilt native body carries must render there exactly once.
        A fact it does not carry has to be a computed, read-only display
        projection that keeps a scenario of its own - the 扣款单 list it was
        projected onto, or the display-copy mapping the business layer declares
        for it - instead of being unioned into the body as a second presentation
        of the same fact in the same context.
        """
        rendered = self.tree_field_names(data)
        model_fields = self.env["sc.tax.deduction.registration"]._fields
        bill_scenario = {
            node.get("name")
            for node in self.arch(self.BILL_DISPLAY_VIEW).xpath(".//field")
        }
        for name in self._retired_p1_declared_facts():
            if name in rendered:
                self.assertEqual(rendered.count(name), 1, (action_key, name, "presented twice"))
                continue
            field = model_fields.get(name)
            self.assertTrue(field, (action_key, name, "fact lost by retiring the P1 body"))
            self.assertTrue(field.compute, (action_key, name, "a fact the body dropped must be a projection"))
            self.assertTrue(field.readonly, (action_key, name, "a projection is not authorable"))
            self.assertTrue(
                name in bill_scenario or name in self._declared_display_copy_sources(),
                (action_key, name, "the projection lost the scenario that presented it"),
            )

    def _declared_display_copy_sources(self):
        """Display projections the business layer declares a source for.

        Consumed from the declaration rather than guessed from a name: the
        mapping is what tells the product which canonical fact a projection
        mirrors, so a projection whose canonical fact a body carries is not a
        lost presentation.
        """
        from odoo.addons.smart_construction_core.models.core.formal_config_contract_fields import (
            _TAXDEDUCTION_FORMAL_CONFIG_FIELDS,
        )
        declared = set()
        for name, (_label, sources) in _TAXDEDUCTION_FORMAL_CONFIG_FIELDS.items():
            native = self.tree_field_names(self.contract(*self.GENERAL_ENTRY[:2]))
            if any(source in native for source in sources):
                declared.add(name)
        return declared

    def _retired_p1_declared_facts(self):
        """Facts the retired model-wide P1 body declared.

        Read from the retired record itself, so the assertion states what the
        product used to present instead of a hard-coded list that could drift
        away from the retired body it claims to preserve.
        """
        retired = self.ref(self.RETIRED_MODEL_WIDE_CONTRACTS[0])
        form = retired.contract_json["view_orchestration"]["views"]["form"]
        return tuple(row["name"] for row in form["fields"])

    def test_entry_category_is_presented_on_the_create_surface(self):
        """The entry category must be visible on the form, not only persisted.

        Both entries declare 业务分类 through their action context
        (``default_business_category_code``) and narrow their list domain to the
        same code.  ``create()`` already resolves that declaration, so the saved
        record carries the entry category; a create surface that leaves the
        relation empty cannot tell the operator which entry the record will
        belong to, and 879 renders the fact read-only, so it could never be
        filled by hand either.  The declaration has to reach the surface that
        collects the fact.
        """
        model = "sc.tax.deduction.registration"
        for action_key, _view_id, _title in self.FORMAL_ENTRIES:
            with self.subTest(action=action_key):
                context = self._entry_context(action_key)
                code = context["default_business_category_code"]
                category = self._entry_category(model, code)
                defaults = self.env[model].with_context(**context).default_get(
                    ["business_category_id", "deduction_scope"]
                )
                self.assertEqual(
                    defaults.get("business_category_id"),
                    category.id,
                    "the create surface must present the category its entry declares",
                )
                self.assertEqual(defaults.get("deduction_scope"), context["default_deduction_scope"])

    def test_create_surface_presents_the_fact_the_save_persists(self):
        """Preview and persisted fact must be the same entry category.

        Behaviour, not implementation: whatever the create surface presents for
        业务分类 is what ``create()`` writes for the same entry context.  This
        also exercises the entry that declares no context code, where the
        category follows the record's own scope in both steps.
        """
        model = self.env["sc.tax.deduction.registration"]
        project = self.env["project.project"].create({
            "name": "抵扣登记入口一致性项目",
            "company_id": self.env.company.id,
            "operation_strategy": "direct",
        })
        cases = [
            (self._entry_context(self.GENERAL_ENTRY[0]), {}),
            (self._entry_context(self.SPECIAL_ENTRY[0]), {}),
            ({}, {"default_deduction_scope": "general"}),
        ]
        for index, (context, extra) in enumerate(cases):
            with self.subTest(case=index):
                context = {**context, **extra}
                presented = model.with_context(**context).default_get(["business_category_id"])
                record = model.with_context(**context).create({
                    "project_id": project.id,
                    "invoice_no": "ENTRY-PREVIEW-%d" % index,
                })
                self.assertEqual(
                    record.business_category_id.id,
                    presented.get("business_category_id"),
                    "the create surface and the save disagree about the entry category",
                )

    def test_auxiliary_derived_fact_is_presented_only_when_a_value_is_returned(self):
        """办理事项 is an auxiliary derived label, so absence must not become a row.

        The create response does not provide a value for this non-stored
        computed fact, and the arch declares ``invisible="not
        deduction_flow_label"`` on it.  The shared modifier engine consumes that
        declaration, so an auxiliary row without a fact is not presented; once
        the backend returns a value for the very same declaration the row is
        presented again.  Both directions matter: an entry that is hidden by the
        mechanism regardless of its value, or one that is filled by the client
        with a default the backend never returned, would both be wrong.  The
        declaration is what is asserted - not a client-side model special case.
        """
        model_name = "sc.tax.deduction.registration"
        model = self.env[model_name]
        project = self.env["project.project"].create({
            "name": "抵扣登记办理事项反例项目",
            "company_id": self.env.company.id,
            "operation_strategy": "direct",
        })
        for action_key, view_id, _title in self.FORMAL_ENTRIES:
            with self.subTest(action=action_key):
                context = self._entry_context(action_key)
                data = self.contract(action_key, view_id)
                node = self.field_node(data, "deduction_flow_label")
                self.assertEqual(
                    (node.get("modifiers") or {}).get("invisible"),
                    {
                        "kind": "not",
                        "expr": {"kind": "field_truthy", "field": "deduction_flow_label"},
                        "raw": "not deduction_flow_label",
                    },
                    "the native visibility declaration must reach the contract as a consumable modifier",
                )
                main_data = (data.get("dataContract") or {}).get("mainData") or {}
                self.assertFalse(
                    main_data.get("deduction_flow_label"),
                    (action_key, "the create response must not carry a value for this derived fact"),
                )
                create_policy = self.widget_status(data).get("deduction_flow_label")
                self.assertIsNotNone(create_policy, (action_key, "the rendered fact has no consumption policy"))
                self.assertIs(
                    create_policy.get("visible"), False,
                    (action_key, "an auxiliary row without a returned value must not be presented"),
                )

                record = model.with_context(**context).create({
                    "project_id": project.id,
                    "invoice_no": "FLOW-LABEL-%s" % action_key,
                })
                self.assertTrue(
                    record.deduction_flow_label,
                    "a persisted record owns the derived fact this row presents",
                )
                data = self.contract(action_key, view_id, record_id=record.id, render_profile="edit")
                record_main_data = (data.get("dataContract") or {}).get("mainData") or {}
                self.assertTrue(
                    record_main_data.get("deduction_flow_label"),
                    (action_key, "the record response returns the derived fact"),
                )
                record_policy = self.widget_status(data).get("deduction_flow_label")
                self.assertIs(
                    record_policy.get("visible"), True,
                    (action_key, "a returned value must present the auxiliary row"),
                )

    def test_an_unresolvable_entry_category_is_not_replaced_by_a_guess(self):
        """A declared code with no matching category must not be substituted.

        The entry declares the category it creates; when that declaration cannot
        be resolved the surface and the save both leave the fact unset instead
        of inventing the other entry's category.
        """
        model = self.env["sc.tax.deduction.registration"]
        context = {"default_business_category_code": "tax.deduction.absent"}
        self.assertFalse(
            self.env["sc.business.category"].sudo().search(
                [("code", "=", "tax.deduction.absent")], limit=1
            ),
            "the fixture must not define this code",
        )
        defaults = model.with_context(**context).default_get(["business_category_id"])
        self.assertFalse(defaults.get("business_category_id"))
        self.assertFalse(model.with_context(**context)._resolve_business_category_id({"deduction_scope": "general"}))

    def test_entry_candidate_scope_is_the_entry_category(self):
        """The selectable candidates are the entry's own category, not the model's.

        The entry narrows ``business_category_id`` to one code.  If the contract
        only carried the model-wide domain
        (``target_model = sc.tax.deduction.registration``) the operator could
        pick the other entry's category, and a record saved under the wrong
        entry could not be found again from the entry it was created in.
        """
        model = self.env["sc.tax.deduction.registration"]
        for action_key, view_id, _title in self.FORMAL_ENTRIES:
            with self.subTest(action=action_key):
                context = self._entry_context(action_key)
                code = context["default_business_category_code"]
                data = self.contract(action_key, view_id, record_id="new")
                entry = ((self.field_node(data, "business_category_id").get("fieldInfo") or {})
                         .get("relation_entry") or {})
                domain = [tuple(row) for row in entry.get("domain") or []]
                self.assertIn(("code", "in", [code]), domain)
                self.assertIn(("target_model", "=", model._name), domain)
                codes = [row[2] for row in domain if row[0] == "code" and row[1] == "in"]
                self.assertEqual(codes, [[code]], "the entry must offer exactly its own category")

    def test_an_out_of_entry_category_is_not_silently_saved(self):
        """A save may not place the record outside the entry that created it.

        The candidate surface already offers only the entry's own category.  A
        client that posts a category from the other entry anyway must be told,
        not silently filed under a scope the originating entry filters out:
        the record would then be invisible from the entry the operator used.
        Nothing may be persisted by the rejected attempt.
        """
        model_name = "sc.tax.deduction.registration"
        model = self.env[model_name]
        project = self.env["project.project"].create({
            "name": "抵扣登记入口越界反例项目",
            "company_id": self.env.company.id,
            "operation_strategy": "direct",
        })
        other_entry = self._entry_category(model_name, "tax.deduction.project_special")
        context = self._entry_context(self.GENERAL_ENTRY[0])
        self.assertEqual(context["default_deduction_scope"], "general")
        with self.assertRaises(ValidationError):
            model.with_context(**context).create({
                "project_id": project.id,
                "business_category_id": other_entry.id,
                "invoice_no": "ENTRY-SCOPE-REJECTED",
            })
        self.assertFalse(
            model.sudo().search([("invoice_no", "=", "ENTRY-SCOPE-REJECTED")]),
            "the rejected save must not persist a record outside the entry scope",
        )

    def _entry_context(self, action_key):
        import ast
        raw = self.ref(action_key).context
        return dict(ast.literal_eval(raw)) if isinstance(raw, str) else dict(raw or {})

    def _entry_category(self, model, code):
        category = self.env["sc.business.category"].sudo().search(
            [("code", "=", code), ("target_model", "=", model)], limit=1
        )
        self.assertTrue(category, "the entry category %s must exist" % code)
        return category

    def test_retiring_the_redundant_p1_body_keeps_its_facts_and_frees_the_create_surface(self):
        """The retired P1 body neither drops a fact nor freezes a fillable one.

        Business behaviour under test: a fact the delivered create profile
        requires must expose a control the user can fill.  The retired body's
        unconditional read-only annotations used to contradict both the native
        arch (`readonly="state == 'legacy_confirmed'"`) and the delivered field
        policy (`auth=edit`) on exactly those facts.
        """
        declared = self._retired_p1_declared_facts()
        self.assertTrue(declared, "the retired P1 body must still be readable for this comparison")
        # 1. no fact the retired body declared is lost anywhere it was presented
        for action_key, view_id, _title in (self.FORMAL_ENTRIES + (self.BYPASS_ENTRY,)):
            self._assert_declared_facts_survive(action_key, self.contract(action_key, view_id))
        # 2. a fact the delivered policy leaves authorable is not frozen on the node
        for action_key, view_id, _title in self.FORMAL_ENTRIES:
            data = self.contract(action_key, view_id)
            status = self.widget_status(data)
            for name in self.UNFROZEN_FACTS:
                self.assertIs((status.get(name) or {}).get("readonly"), False,
                              (action_key, name, "the delivered profile must leave this fact authorable"))
                node = self.field_node(data, name)
                self.assertIsNot(node.get("readonly"), True,
                                 (action_key, name, "the node keeps a read-only the profile contradicts"))
                self.assertIsNot((node.get("fieldInfo") or {}).get("readonly"), True,
                                 (action_key, name, "fieldInfo keeps a read-only the profile contradicts"))
            # ... and at least one of them really is required, so the rule
            # above is exercised by a fact the user has to fill rather than by
            # an optional fact that could be left empty.
            required_unfrozen = []
            for name in self.UNFROZEN_FACTS:
                if (self.field_node(data, name).get("fieldInfo") or {}).get("required") is True:
                    required_unfrozen.append(name)
            self.assertTrue(required_unfrozen, (action_key, "no required fact exercised the rule"))
