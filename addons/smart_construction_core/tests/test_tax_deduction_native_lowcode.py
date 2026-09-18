# -*- coding: utf-8 -*-
import re

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
    entries of which two are ledger consumers.

    The rebuilt native arch owns the structure.  Entries 790 and 879 declare
    ``native_semantic_surface`` and drop their own section/field/column bodies,
    so body and section navigation consume one structure.  The entries keep
    their titles and their semantic context (the ``project_special`` scope
    authority of 879 is what separates the two entries, not a second body).

    Every fact those retired bodies rendered still renders exactly once.  The
    arch gained the facts only they declared and the native body did not carry
    (``company_id``, ``partner_name``, ``deduction_bill_attachment_text``,
    ``message_attachment_count`` and the migrated provenance facts on a
    迁移来源 page), the arch now states the read-only restrictions the retired
    bodies declared, and the one fact the authority body presented twice
    (``withholding_amount``) is presented once, where the retired body had it.

    The model-wide contracts
    ``sc_tax_deduction_registration_form_sections_v1``,
    ``sc_tax_deduction_registration_p1_form_business_facts_v1`` and
    ``sc_tax_deduction_registration_form_structure_generated_v1`` have no
    action scope and keep serving action 852 (扣款单); they are neither deleted
    nor rewritten, and they are not re-projected on top of a native-authority
    entry either.
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
    MODEL_WIDE_CONTRACTS = (
        "business_config_contract_sc_tax_deduction_registration_form_sections_v1",
        "business_config_contract_sc_tax_deduction_registration_p1_form_business_facts_v1",
        "business_config_contract_sc_tax_deduction_registration_form_structure_generated",
    )

    # Facts the retired bodies rendered, as declared by their own field lists.
    GENERAL_DECLARED = (
        "state", "name", "deduction_flow_label", "business_category_id", "source_origin", "project_id",
        "company_id", "partner_id", "partner_name", "deduction_unit_name", "document_no", "document_date",
        "invoice_no", "invoice_code", "invoice_date", "tax_rate_text", "invoice_amount_untaxed",
        "invoice_tax_amount", "invoice_amount_total", "withholding_amount", "deduction_amount",
        "deduction_tax_amount", "deduction_surcharge_amount", "currency_id", "deduction_confirm_date",
        "deduction_reason", "note", "attachment_ids", "deduction_bill_attachment_text",
        "message_attachment_count", "legacy_source_model", "legacy_source_table", "legacy_record_id",
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
        "company_id", "partner_name", "deduction_bill_attachment_text", "message_attachment_count",
        "legacy_source_model", "legacy_source_table", "legacy_record_id", "legacy_document_state",
        "source_created_by", "source_created_at",
    )
    # Facts the retired bodies declared read-only that the model does not make
    # read-only on its own, so the arch has to carry the declaration.
    DECLARED_READONLY_FACTS = (
        "state", "deduction_flow_label", "company_id", "partner_name", "tax_rate_text",
        "deduction_bill_attachment_text", "message_attachment_count", "legacy_source_model",
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
        self.assertIn(self.field_node(data, "deduction_bill_attachment_text"),
                      self.group_node(data, "deduction_note_attachment")["children"])
        for name in ("legacy_source_model", "legacy_source_table", "legacy_record_id",
                     "legacy_document_state", "source_created_by", "source_created_at"):
            self.assertIn(self.field_node(data, name),
                          self.group_node(data, "deduction_source_trace")["children"])

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
        self.assertTrue(model_fields["message_attachment_count"].readonly)
        self.assertFalse(model_fields["message_attachment_count"].store)
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
