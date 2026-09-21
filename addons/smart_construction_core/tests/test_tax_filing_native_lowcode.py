# -*- coding: utf-8 -*-
from lxml import etree

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.core.form_structure_authority import (
    diagnose_structure_ownership,
    resolve_form_structure_governance,
    structural_form_declarations,
)


@tagged("post_install", "-at_install", "uc4_native_lowcode")
class TestTaxFilingNativeLowcode(TransactionCase):
    """U-C4 G15: 税务申报 (action 880 / menu 702 / view 1659).

    One P1 formal entry:

      880 `action_sc_product_tax_filing_v1` / menu 702 税务申报
        -> `sc.tax.filing` / `view_sc_tax_filing_form`

    Before this batch the entry contract `tax_filing_form_v1` (186) carried an
    `entry_semantic_surface` body - four sections (22 fields), `columns: 2` and
    five declared `actions` - so the delivered surface ran the compatibility
    regrouping path (`overview_then_task_slots`).  The declared sections never
    reached the rendered container tree: the contract says 来源与治理 where the
    native arch says 治理信息, and the contract lists 22 field rows against the
    21 field nodes the arch actually delivers.

    This batch retires the structural body in place (the G13 shape used for
    876): the same record keeps its name, action, `priority=800`, `published`
    status, version and the five `context` keys, and only the structural keys
    are dropped, with `composition_mode` becoming `native_semantic_surface`.  A
    read-only A/B probe of the delivered surface (`sc_dev_demo`, `SAVEPOINT` +
    `ROLLBACK`, zero writes) measured that the two render profiles keep the
    container tree, the field set, every `readonly` / `invisible` modifier and
    the anchor set identical to the baseline; the retired body declared no field
    policy at all, so no sparse override is needed.

    The only remaining difference sits on the **create** route's compatibility
    plane: before retirement that route emitted a legacy per-field semantics
    plane (52 keys) and nine surface policies while hiding twelve fields the
    arch renders; after retirement `create` matches `edit` (only `currency_id`
    hidden) and matches the platform's other native entries (876 / 687 / 522 /
    646 / 778 all measure `fieldSemantics=0` and `surfacePolicies={}`).

    `RENDERED_FIELDS`, `DELIVERED_MODIFIERS` and `CONTAINER_SKELETON` pin the
    delivered surface so a later edit cannot silently drop a fact or a read-only
    口径 the entry carries today.
    """

    # entry contract xmlid -> (action xmlid, model, view xmlid, title)
    ENTRIES = {
        "business_config_contract_tax_filing_form_v1": (
            "action_sc_product_tax_filing_v1", "sc.tax.filing",
            "view_sc_tax_filing_form", "税务申报"),
    }

    ENTRY_PRIORITY = 800

    # The declaration the entry keeps verbatim; retirement must not rewrite it.
    ENTRY_CONTEXT = {
        "source": "smart_construction_core.product_release",
        "source_status": "product_release",
        "filing_authority": "sc.tax.filing",
        "invoice_authority": "sc.invoice.registration",
        "deduction_authority": "sc.tax.deduction.registration",
    }

    # Structural keys the retirement must have removed.  `actions` is included:
    # the five declared buttons were the compatibility body's own list, while the
    # native arch declares six, so keeping them would both contradict the arch
    # and raise NATIVE_SEMANTIC_SURFACE_STRUCTURE_CONFLICT.
    RETIRED_KEYS = ("sections", "columns", "actions", "fields", "layout", "semantic_anchors")

    # Sibling entry on the same model and the same-form family.  It is another
    # ledger row and keeps its own entry surface, so the retirement must stay
    # scoped to action 880.
    SIBLING_CONTRACTS = {
        "business_config_contract_tax_report_list_v1": (
            "tax_report_list_v1", "action_sc_product_tax_report_v1"),
    }

    # Business field set the delivered container tree carries, in document
    # order.  Pinned so the batch is provably presentation-neutral.
    RENDERED_FIELDS = {
        "view_sc_tax_filing_form": (
            "state", "name", "company_id", "period_start", "period_end",
            "handler_id", "declaration_no", "calculated_at", "submitted_at",
            "accepted_at", "currency_id", "output_tax_amount", "input_tax_amount",
            "deductible_tax_amount", "prepaid_tax_amount", "surcharge_amount",
            "vat_payable_amount", "other_tax_adjustment", "declared_payable_amount",
            "note", "attachment_ids",
        ),
    }

    # Fields the native form arch declares, statinfo children of the two
    # `oe_stat_button` buttons and the chatter fields included.
    ARCH_FIELDS = {
        "view_sc_tax_filing_form": (
            "state", "invoice_source_count", "deduction_source_count", "name",
            "company_id", "period_start", "period_end", "handler_id",
            "declaration_no", "calculated_at", "submitted_at", "accepted_at",
            "currency_id", "output_tax_amount", "input_tax_amount",
            "deductible_tax_amount", "prepaid_tax_amount", "surcharge_amount",
            "vat_payable_amount", "other_tax_adjustment", "declared_payable_amount",
            "note", "attachment_ids", "message_follower_ids", "activity_ids",
            "message_ids",
        ),
    }

    # Read-only / hidden structure the delivered page keeps.  The retired entry
    # body declared no field policy at all, so this is the口径 the native arch
    # carries on its own; it is the surface the batch must not shrink.
    # (field name, container `readonly` expression, container `invisible`)
    DELIVERED_MODIFIERS = {
        "view_sc_tax_filing_form": (
            ("name", "1", False),
            ("company_id", "state != 'draft'", False),
            ("period_start", "state != 'draft'", False),
            ("period_end", "state != 'draft'", False),
            ("currency_id", None, True),
            ("other_tax_adjustment", "state in ['submitted', 'accepted', 'cancelled']", False),
        ),
    }

    # Non-field container skeleton, in document order.  The six native buttons
    # are pinned because the retired body declared five of them and the entry
    # must not lose the two statinfo buttons the contract never mentioned.
    CONTAINER_SKELETON = {
        "view_sc_tax_filing_form": (
            ("header", "", None, None),
            ("button", "测算税额", "action_calculate", "state not in ['draft', 'calculated']"),
            ("button", "确认申报", "action_submit", "state != 'calculated'"),
            ("button", "登记受理", "action_accept", "state != 'submitted'"),
            ("button", "取消", "action_cancel", "state in ['accepted', 'cancelled']"),
            ("sheet", "", None, None),
            ("container", "", "button_box", None),
            ("button", "", "action_open_invoices", None),
            ("button", "", "action_open_deductions", None),
            ("group", "", None, None),
            ("group", "申报信息", None, None),
            ("group", "治理信息", None, None),
            ("group", "税额测算", None, None),
            ("group", "说明与附件", None, None),
            ("chatter", "沟通记录", None, None),
        ),
    }

    # -- helpers -------------------------------------------------------------

    def _contracts(self):
        return self.env["ui.business.config.contract"].sudo()

    def _contract(self, xmlid):
        return self._contracts().browse(self.ref("smart_construction_core.%s" % xmlid))

    def _entry_contracts(self, model, action_xmlid, view_xmlid):
        return self._contracts()._effective_view_orchestration_contracts(
            model,
            view_type="form",
            action_id=self.ref("smart_construction_core.%s" % action_xmlid),
            view_id=self.env.ref("smart_construction_core.%s" % view_xmlid).id,
            role_key="",
        )

    def _form_spec(self, record):
        return (((record.contract_json or {}).get("view_orchestration") or {})
                .get("views", {}).get("form", {})) or {}

    def _native_contract(self, model, action_xmlid, view_xmlid, render_profile="edit"):
        from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler

        action = self.env.ref("smart_construction_core.%s" % action_xmlid)
        result = UiContractV2Handler(
            self.env, su_env=self.env["ir.model"].sudo().env
        ).handle({
            "op": "model", "model": model, "action_id": action.id,
            "view_id": self.env.ref("smart_construction_core.%s" % view_xmlid).id,
            "view_type": "form", "render_profile": render_profile,
        })
        result = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
        self.assertTrue(result.get("ok", True), result.get("error"))
        return result["data"]

    @staticmethod
    def _walk(rows):
        for node in rows if isinstance(rows, list) else []:
            if isinstance(node, dict):
                yield node
                for child in node.get("children") or []:
                    yield from TestTaxFilingNativeLowcode._walk([child])

    def _field_nodes(self, data):
        tree = (data.get("layoutContract") or {}).get("containerTree") or []
        seen, ordered = set(), []
        for node in self._walk(tree):
            if node.get("type") != "field":
                continue
            name = (node.get("attributes") or {}).get("name")
            if name and name not in seen:
                seen.add(name)
                ordered.append(node)
        return ordered

    def _container_skeleton(self, data):
        tree = (data.get("layoutContract") or {}).get("containerTree") or []
        rows = []
        for node in self._walk(tree):
            if node.get("type") == "field":
                continue
            attributes = node.get("attributes") or {}
            rows.append((node.get("type"), node.get("title"), attributes.get("name"),
                         attributes.get("invisible")))
        return tuple(rows)

    def _arch(self, view_xmlid):
        view = self.env.ref("smart_construction_core.%s" % view_xmlid)
        return etree.fromstring(view.arch.encode("utf-8"))

    def _arch_field_names(self, view_xmlid):
        """Fields the form arch declares, in document order.

        A one2many field that declares its own inline `tree` carries that
        collection's row layout, not a form fact, so the walk does not descend
        into it - the same rule the compiled container tree applies.
        """
        seen, ordered = set(), []

        def walk(node):
            for child in node:
                if child.tag != "field":
                    walk(child)
                    continue
                name = child.get("name")
                if name and name not in seen:
                    seen.add(name)
                    ordered.append(name)
                for sub in child:
                    if sub.tag in ("tree", "form", "kanban"):
                        continue
                    walk(sub)

        walk(self._arch(view_xmlid))
        return tuple(ordered)

    # -- declaration surface -------------------------------------------------

    def test_every_entry_declares_the_native_semantic_surface(self):
        for contract_xmlid, (action_xmlid, model, _view, title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                record = self._contract(contract_xmlid)
                self.assertTrue(record.active)
                self.assertEqual(record.status, "published")
                self.assertEqual(record.name, contract_xmlid.rsplit("business_config_contract_", 1)[1])
                self.assertEqual(record.model, model)
                self.assertEqual(record.view_type, "form")
                self.assertEqual(
                    record.action_id.id,
                    self.ref("smart_construction_core.%s" % action_xmlid),
                )
                self.assertEqual(record.priority, self.ENTRY_PRIORITY)
                # The XML declares version 1; the contract lifecycle appends an
                # immutable publication snapshot and advances the row whenever a
                # published body changes, so retiring the body in place moves this
                # same single carrier to version 2.  The declaration stays the one
                # and only release for action 880 either way.
                self.assertGreaterEqual(record.version_no, 1)
                spec = self._form_spec(record)
                self.assertEqual(spec.get("composition_mode"), "native_semantic_surface")
                self.assertEqual(spec.get("title"), title)
                # A native declaration may not carry a competing structure.
                self.assertEqual(structural_form_declarations(spec), {})
                for key in self.RETIRED_KEYS:
                    self.assertNotIn(key, spec)

    def test_every_entry_keeps_its_declared_context(self):
        for contract_xmlid, (_action, _model, _view, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                context = ((self._contract(contract_xmlid).contract_json or {})
                           .get("view_orchestration", {}).get("context", {}))
                self.assertEqual(context, self.ENTRY_CONTEXT)

    def test_the_retired_body_leaves_no_structure_owner_conflict(self):
        """The retired keys must be gone, not merely outranked.

        While the entry still carried `sections` / `columns` / `actions` it was
        both the native owner and a scoped structural declarer, which
        `diagnose_structure_ownership` refuses outright.
        """
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                configs = self._entry_contracts(model, action_xmlid, view_xmlid)
                conflicts = diagnose_structure_ownership(
                    configs, model=model,
                    action_id=self.ref("smart_construction_core.%s" % action_xmlid),
                )
                self.assertEqual(conflicts, [])

    # -- resolution surface --------------------------------------------------

    def test_every_entry_resolves_its_own_release_as_the_native_plane(self):
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                configs = self._entry_contracts(model, action_xmlid, view_xmlid)
                native = [
                    config for config in configs
                    if (self._form_spec(config) or {}).get("composition_mode")
                    == "native_semantic_surface"
                ]
                self.assertEqual(
                    [config.name for config in native],
                    [self._contract(contract_xmlid).name],
                )

    def test_every_entry_resolves_native_authority(self):
        """The entry declaration must be the last structure writer for its action.

        This is the assertion that closes the compatibility path: while the entry
        body declared sections, `form_structure_authority` stayed
        `entry_semantic_surface` and the ledger kept counting 880 as a
        compatibility consumer even though the native arch already rendered the
        page.
        """
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                configs = self._entry_contracts(model, action_xmlid, view_xmlid)
                resolved = resolve_form_structure_governance({}, configs, view_type="form")
                self.assertEqual(resolved.get("form_structure_authority"), "native_authority")
                self.assertEqual(resolved.get("form_presentation_mode"), "task")
                self.assertFalse(resolved.get("section_titles"))
                self.assertFalse(resolved.get("configured_sections"))
                self.assertFalse(resolved.get("field_names"))

    def test_the_model_carries_no_generated_mirror(self):
        """`sc.tax.filing` has no model-level generated structure carrier.

        The retirement therefore cannot leave a competing mirror behind; the only
        carriers are the retired entry itself and the sibling entry, which keeps
        its own surface.
        """
        carriers = self._contracts().with_context(active_test=False).search(
            [("model", "=", "sc.tax.filing")])
        self.assertEqual(
            sorted(carriers.mapped("name")),
            sorted(["tax_filing_form_v1"] + [name for name, _action in self.SIBLING_CONTRACTS.values()]),
        )

    def test_the_retirement_does_not_leak_to_the_sibling_action(self):
        for contract_xmlid, (_action, _model, _view, _title) in self.ENTRIES.items():
            entry_name = self._contract(contract_xmlid).name
            for sibling_xmlid, (sibling_name, sibling_action) in self.SIBLING_CONTRACTS.items():
                with self.subTest(entry=contract_xmlid, sibling=sibling_xmlid):
                    sibling = self._contract(sibling_xmlid)
                    self.assertEqual(sibling.name, sibling_name)
                    self.assertTrue(sibling.active)
                    # The sibling keeps its own declaration: the retirement is
                    # scoped to action 880 and never rewrites another entry, so
                    # the sibling body must stay exactly what its own file ships:
                    # no composition mode and no structural key.
                    sibling_spec = self._form_spec(sibling)
                    self.assertIsNone(sibling_spec.get("composition_mode"))
                    self.assertEqual(structural_form_declarations(sibling_spec), {})
                    action = self.env.ref("smart_construction_core.%s" % sibling_action)
                    configs = self._contracts()._effective_view_orchestration_contracts(
                        action.res_model, view_type=sibling.view_type,
                        action_id=action.id, role_key="",
                    )
                    self.assertNotIn(entry_name, [config.name for config in configs])

    def test_the_sibling_entry_stays_published_and_reachable(self):
        """The sibling is a report surface on the same model, not a form entry.

        Action 881 is registered as `pivot,graph,tree` and never rendered the
        primary form of `sc.tax.filing`, so the retirement of the form entry must
        leave both the action and its own entry release untouched.
        """
        for sibling_xmlid, (sibling_name, sibling_action) in self.SIBLING_CONTRACTS.items():
            with self.subTest(contract=sibling_xmlid):
                action = self.env.ref("smart_construction_core.%s" % sibling_action)
                self.assertEqual(action.res_model, "sc.tax.filing")
                self.assertNotIn("form", action.view_mode or "")
                sibling = self._contract(sibling_xmlid)
                self.assertTrue(sibling.active)
                self.assertEqual(sibling.view_type, "list")
                carriers = self._contracts()._effective_view_orchestration_contracts(
                    "sc.tax.filing", view_type="list", action_id=action.id, role_key="")
                self.assertIn(sibling_name, [config.name for config in carriers])

    # -- rendered surface ----------------------------------------------------

    def test_the_rendered_surface_is_the_native_container_tree(self):
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                structure = self._native_contract(model, action_xmlid, view_xmlid)\
                    .get("formStructureContract") or {}
                self.assertEqual(structure.get("layoutPolicy"), "container_tree_authority")
                self.assertEqual(structure.get("mode"), "native_structured_form")
                self.assertEqual(structure.get("presentationMode"), "task")
                self.assertFalse(structure.get("slots"))
                self.assertFalse(structure.get("fieldRoles"))
                self.assertFalse(structure.get("sourceSectionTitles"))

    def test_the_create_profile_delivers_the_same_field_plane_as_edit(self):
        """The retired body was the only reason the create route differed.

        Before retirement the compatibility floorplan hid twelve fields on the
        create route and emitted a legacy per-field semantics plane; the retired
        entry declares no field policy, so both profiles must now agree on the
        **field plane**: the same container field nodes, no per-field semantics
        plane and no compatibility surface policies.  This is what discriminates
        the retirement from the baseline: with the entry_semantic_surface body
        live, `create` measured 52 `runtimeContract.fieldSemantics` keys, nine
        `actionContract.surfacePolicies` keys and twelve hidden field widgets
        while `edit` measured none of them.

        The claim is deliberately limited to the field plane.  The record-scoped
        `button_box` statistics remain a create/edit difference (a new record has
        no source rows to count) and are not asserted here.
        """
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                edit = self._native_contract(model, action_xmlid, view_xmlid, "edit")
                create = self._native_contract(model, action_xmlid, view_xmlid, "create")
                edit_fields = tuple((node.get("attributes") or {}).get("name")
                                    for node in self._field_nodes(edit))
                create_fields = tuple((node.get("attributes") or {}).get("name")
                                      for node in self._field_nodes(create))
                self.assertEqual(create_fields, edit_fields)
                for data in (edit, create):
                    structure = data.get("formStructureContract") or {}
                    self.assertEqual(structure.get("layoutPolicy"), "container_tree_authority")
                    governance = ((data.get("dataContract") or {}).get("dataMeta") or {}) \
                        .get("businessOperationProfile", {}).get("form_structure_governance", {})
                    self.assertFalse(governance.get("structure_diagnostics"))
                    # The compatibility plane the retired body used to emit on
                    # the create profile must stay gone: no legacy per-field
                    # semantics plane and no surface policy overrides.
                    self.assertFalse(
                        (data.get("runtimeContract") or {}).get("fieldSemantics"))
                    self.assertFalse(
                        ((data.get("actionContract") or {}).get("surfacePolicies")) or {})

    def test_the_rendered_field_set_is_pinned(self):
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                data = self._native_contract(model, action_xmlid, view_xmlid)
                rendered = tuple((node.get("attributes") or {}).get("name")
                                 for node in self._field_nodes(data))
                self.assertEqual(rendered, self.RENDERED_FIELDS[view_xmlid])

    def test_the_delivered_readonly_and_hidden_structure_is_pinned(self):
        """The retired body declared no field policy, so pin what the page carries."""
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                data = self._native_contract(model, action_xmlid, view_xmlid)
                modifiers = []
                for node in self._field_nodes(data):
                    attributes = node.get("attributes") or {}
                    readonly = attributes.get("readonly")
                    invisible = bool(attributes.get("invisible"))
                    if readonly is None and not invisible:
                        continue
                    modifiers.append((attributes.get("name"), readonly, invisible))
                self.assertEqual(tuple(modifiers), self.DELIVERED_MODIFIERS[view_xmlid])

    def test_the_delivered_container_keeps_the_native_buttons_and_groups(self):
        """The retired body declared five buttons; the arch declares six."""
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                data = self._native_contract(model, action_xmlid, view_xmlid)
                self.assertEqual(
                    self._container_skeleton(data),
                    self.CONTAINER_SKELETON[view_xmlid],
                )

    # -- native arch ---------------------------------------------------------

    def test_the_native_arch_is_presentation_neutral(self):
        """The batch retires a declaration; it must not add or drop a fact."""
        for view_xmlid, expected in self.ARCH_FIELDS.items():
            with self.subTest(view=view_xmlid):
                self.assertEqual(self._arch_field_names(view_xmlid), expected)

    def test_the_arch_declares_every_rendered_business_field(self):
        for contract_xmlid, (_action, model, view_xmlid, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                arch_fields = set(self._arch_field_names(view_xmlid))
                for name in self.RENDERED_FIELDS[view_xmlid]:
                    self.assertIn(name, arch_fields)
                    self.assertIn(name, self.env[model]._fields)

    def test_the_native_view_declares_no_anchor_and_no_inherited_child(self):
        """Measured facts that keep the browser route off `section_navigation`."""
        for contract_xmlid, (_action, _model, view_xmlid, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                arch = self._arch(view_xmlid)
                self.assertEqual(
                    [node.get("data-sc-anchor") for node in arch.iter()
                     if node.get("data-sc-anchor")],
                    [],
                )
                view = self.env.ref("smart_construction_core.%s" % view_xmlid)
                self.assertFalse(view.inherit_id)
                self.assertFalse(
                    self.env["ir.ui.view"].sudo().search([("inherit_id", "=", view.id)]),
                )
