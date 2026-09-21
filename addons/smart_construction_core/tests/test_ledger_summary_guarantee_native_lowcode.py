# -*- coding: utf-8 -*-
from lxml import etree

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.core.form_structure_authority import (
    diagnose_structure_ownership,
    resolve_form_structure_governance,
    structural_form_declarations,
)


@tagged("post_install", "-at_install", "uc4_native_lowcode")
class TestLedgerSummaryGuaranteeNativeLowcode(TransactionCase):
    """U-C4 G14: 台账汇总与保证金 (actions 523 / 522 / 646 / 778).

    Four P1 formal entries, none of which pinned a form view:

      523 `action_project_cost_ledger` / menu 668 成本归集
        -> `project.cost.ledger` / `view_project_cost_ledger_form`
      522 `action_project_profit_compare` / menu 669 项目盈亏分析
        -> `project.profit.compare` / `view_project_profit_compare_form`
      646 `action_project_funding_baseline_summary` / menu 542 资金计划汇总
        -> `project.funding.baseline` / `view_project_funding_baseline_form`
      778 `action_sc_tender_guarantee` / menu 474 投标保证金
        -> `tender.guarantee` / `view_tender_guarantee_form`

    Before this batch none of the four had a release of its own.  A
    repository-wide scan of `data/` found no `ui.business.config.contract`
    bound to any of the four actions, so the only effective carrier of each
    entry was its **model-level generated mirror** (`project_cost_ledger_
    form_structure_generated_v1` at priority 70, `project_funding_baseline_
    form_structure_generated_v1` at 72, `project_profit_compare_form_
    structure_generated_v1` at 75, `tender_guarantee_form_structure_
    generated_v1` at 176).  All four mirrors declare an empty `action_id` and
    nothing but a `fields` list.

    Because `form_structure_authority` is derived from a contract that declares
    `composition_mode`, the resolved value stayed `""` and `ui_contract_v2`
    ran the compatibility regrouping path - the ledger counted the four entries
    even though their native arch already rendered them (measured: 23 / 11 / 21
    / 11 business field nodes, zero `data-sc-anchor`, zero inherited children).

    This batch publishes the entry release for each of the four (title +
    `native_semantic_surface` + `context` only), so each entry becomes the
    structure owner of its own action.  A read-only A/B probe of the delivered
    surface (`sc_dev_demo`, `SAVEPOINT` + `ROLLBACK`, zero writes) measured
    that the candidate keeps the container tree, the widget `readonly` /
    `visible` profile and the anchor set node-for-node identical to the
    baseline and changes nothing but the compatibility projection.  Unlike G13,
    the four mirrors declare **0 read-only rows and 0 `visible: false` rows**,
    so this batch needs no sparse field override at all.

    The model-level mirrors stay active: they serve the action-less model plane
    and their sibling entries (585 / 524 cost ledger, 645 funding plan, 854
    deposit return) keep their own surfaces.  `RENDERED_FIELDS` and
    `DELIVERED_MODIFIERS` pin the delivered surface so a later edit cannot
    silently drop a fact or a read-only口径 the entry carries today.
    """

    # entry contract xmlid -> (action xmlid, model, view xmlid, title)
    ENTRIES = {
        "business_config_contract_project_cost_ledger_form_native_v1": (
            "action_project_cost_ledger", "project.cost.ledger",
            "view_project_cost_ledger_form", "成本归集"),
        "business_config_contract_project_profit_compare_form_native_v1": (
            "action_project_profit_compare", "project.profit.compare",
            "view_project_profit_compare_form", "项目盈亏分析"),
        "business_config_contract_project_funding_baseline_form_native_v1": (
            "action_project_funding_baseline_summary", "project.funding.baseline",
            "view_project_funding_baseline_form", "资金计划汇总"),
        "business_config_contract_tender_guarantee_form_native_v1": (
            "action_sc_tender_guarantee", "tender.guarantee",
            "view_tender_guarantee_form", "投标保证金"),
    }

    # Every entry release outranks the model-level mirror it supersedes; the
    # highest of those is the tender mirror 176.
    ENTRY_PRIORITY = 800

    # Model-level generated mirrors kept active on purpose.  Each one serves the
    # action-less model plane of its own model, so retiring it belongs to
    # another group; this batch only has to outrank it.
    # xmlid -> (name, model, priority, sibling actions that keep depending on it)
    MODEL_MIRRORS = {
        "business_config_contract_project_cost_ledger_form_structure_generated": (
            "project_cost_ledger_form_structure_generated_v1", "project.cost.ledger", 70,
            ("action_project_cost_ledger_quick", "action_project_cost_ledger_my")),
        "business_config_contract_project_profit_compare_form_structure_generated": (
            "project_profit_compare_form_structure_generated_v1", "project.profit.compare", 75,
            ()),
        "business_config_contract_project_funding_baseline_form_structure_generated": (
            "project_funding_baseline_form_structure_generated_v1", "project.funding.baseline", 72,
            ("action_project_funding_baseline",)),
        "business_config_contract_tender_guarantee_form_structure_generated": (
            "tender_guarantee_form_structure_generated_v1", "tender.guarantee", 176,
            ("action_tender_guarantee_formal_payment_deposit_return",)),
    }

    # Sibling entries on the same model and the same native form.  They are
    # other ledger rows, so the release must stay scoped to its own action.
    SIBLING_ACTIONS = {
        "business_config_contract_project_cost_ledger_form_native_v1": (
            "action_project_cost_ledger_quick", "action_project_cost_ledger_my"),
        "business_config_contract_project_profit_compare_form_native_v1": (),
        "business_config_contract_project_funding_baseline_form_native_v1": (
            "action_project_funding_baseline",),
        "business_config_contract_tender_guarantee_form_native_v1": (
            "action_tender_guarantee_formal_payment_deposit_return",),
    }

    # Business field set the delivered container tree carries, in document
    # order.  Pinned so the batch is provably presentation-neutral.
    RENDERED_FIELDS = {
        "view_project_cost_ledger_form": (
            "is_generated", "recognition_state", "recognition_stage",
            "reporting_treatment", "normalization_state", "cost_flow_label",
            "project_id", "date", "period", "period_id", "wbs_id",
            "cost_code_id", "partner_id", "qty", "uom_id", "source_amount",
            "source_currency_id", "amount", "currency_id", "source_model",
            "source_id", "source_line_id", "note",
        ),
        "view_project_profit_compare_form": (
            "project_id", "period", "wbs_id", "currency_id",
            "revenue_budget_amount", "revenue_actual_amount",
            "gross_profit_budget", "cost_budget_amount", "cost_actual_amount",
            "gross_profit_actual", "gross_margin_rate",
        ),
        "view_project_funding_baseline_form": (
            "state", "project_id", "version_no", "version_key",
            "normalization_state", "period_start", "period_end",
            "supersedes_id", "total_amount", "allocated_amount",
            "remaining_amount", "currency_id", "attachment_ids", "line_ids",
            "revision_reason", "superseded_by_id", "activated_at",
            "activated_by_id", "ended_at", "ended_by_id", "end_reason",
        ),
        "view_tender_guarantee_form": (
            "state", "bid_id", "project_id", "type", "date", "amount",
            "currency_id", "receipt_bank_account_id", "bank_account_id",
            "remark", "attachment_ids",
        ),
    }

    # Read-only / hidden structure the delivered page keeps.  The four entry
    # releases declare no field policy at all, so this is the口径 the native
    # arch carries on its own; it is the surface the batch must not shrink.
    # (field name, container `readonly` expression, container `invisible`)
    DELIVERED_MODIFIERS = {
        "view_project_cost_ledger_form": (
            ("is_generated", None, True),
            ("recognition_state", "1", False),
            ("recognition_stage", "1", False),
            ("reporting_treatment", "1", False),
            ("normalization_state", "1", False),
            ("cost_flow_label", "1", False),
            ("project_id", "is_generated", False),
            ("date", "is_generated", False),
            ("period", "1", False),
            ("period_id", "1", False),
            ("wbs_id", "is_generated", False),
            ("cost_code_id", "is_generated", False),
            ("partner_id", "is_generated", False),
            ("qty", "is_generated", False),
            ("uom_id", "is_generated", False),
            ("source_amount", "1", False),
            ("source_currency_id", "1", False),
            ("amount", "is_generated", False),
            ("currency_id", "1", False),
            ("note", "is_generated", False),
        ),
        "view_project_profit_compare_form": (
            ("project_id", "1", False),
            ("period", "1", False),
            ("wbs_id", "1", False),
            ("currency_id", "1", True),
            ("revenue_budget_amount", "1", False),
            ("revenue_actual_amount", "1", False),
            ("gross_profit_budget", "1", False),
            ("cost_budget_amount", "1", False),
            ("cost_actual_amount", "1", False),
            ("gross_profit_actual", "1", False),
            ("gross_margin_rate", "1", False),
        ),
        "view_project_funding_baseline_form": (
            ("project_id", "state != 'draft'", False),
            ("version_no", "1", False),
            ("version_key", "1", False),
            ("normalization_state", "1", False),
            ("period_start", "state != 'draft'", False),
            ("period_end", "state != 'draft'", False),
            ("supersedes_id", "1", False),
            ("total_amount", "state != 'draft'", False),
            ("allocated_amount", "1", False),
            ("remaining_amount", "1", False),
            ("currency_id", "1", True),
            ("attachment_ids", "state != 'draft'", False),
            ("line_ids", "state != 'draft'", False),
            ("revision_reason", "1", False),
            ("superseded_by_id", "1", False),
            ("activated_at", "1", False),
            ("activated_by_id", "1", False),
            ("ended_at", "1", False),
            ("ended_by_id", "1", False),
            ("end_reason", "1", False),
        ),
        "view_tender_guarantee_form": (
            ("project_id", "1", False),
            ("currency_id", None, True),
        ),
    }

    # -- helpers -------------------------------------------------------------

    def _contract(self, xmlid):
        return self.env["ui.business.config.contract"].sudo().browse(
            self.ref("smart_construction_core.%s" % xmlid))

    def _entry_contracts(self, model, action_xmlid, view_xmlid):
        return self.env["ui.business.config.contract"].sudo()\
            ._effective_view_orchestration_contracts(
                model,
                view_type="form",
                action_id=self.ref("smart_construction_core.%s" % action_xmlid),
                view_id=self.env.ref("smart_construction_core.%s" % view_xmlid).id,
                role_key="",
            )

    def _form_spec(self, record):
        return (((record.contract_json or {}).get("view_orchestration") or {})
                .get("views", {}).get("form", {})) or {}

    def _native_contract(self, model, action_xmlid, view_xmlid):
        from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler

        action = self.env.ref("smart_construction_core.%s" % action_xmlid)
        result = UiContractV2Handler(
            self.env, su_env=self.env["ir.model"].sudo().env
        ).handle({
            "op": "model", "model": model, "action_id": action.id,
            "view_id": self.env.ref("smart_construction_core.%s" % view_xmlid).id,
            "view_type": "form", "render_profile": "edit",
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
                    yield from TestLedgerSummaryGuaranteeNativeLowcode._walk([child])

    def _field_nodes(self, data):
        tree = (data.get("layoutContract") or {}).get("containerTree") or []
        seen, ordered = set(), []
        for node in self._walk(tree):
            if node.get("type") != "field":
                continue
            name = node.get("name")
            if name and name not in seen:
                seen.add(name)
                ordered.append(node)
        return ordered

    def _arch(self, view_xmlid):
        view = self.env.ref("smart_construction_core.%s" % view_xmlid)
        return etree.fromstring(view.arch.encode("utf-8"))

    def _arch_field_names(self, view_xmlid):
        """Business fields the form arch declares, in document order.

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
        for contract_xmlid, (action_xmlid, model, view_xmlid, title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                record = self._contract(contract_xmlid)
                self.assertTrue(record.active)
                self.assertEqual(record.status, "published")
                self.assertEqual(record.name, contract_xmlid.rsplit("business_config_contract_", 1)[1])
                self.assertEqual(record.model, model)
                self.assertEqual(
                    record.action_id.id,
                    self.ref("smart_construction_core.%s" % action_xmlid),
                )
                self.assertEqual(
                    record.view_id.id,
                    self.ref("smart_construction_core.%s" % view_xmlid),
                )
                self.assertEqual(record.priority, self.ENTRY_PRIORITY)
                spec = self._form_spec(record)
                self.assertEqual(spec.get("composition_mode"), "native_semantic_surface")
                self.assertEqual(spec.get("title"), title)
                # A native declaration may not carry a competing structure.
                self.assertEqual(structural_form_declarations(spec), {})
                for key in ("sections", "fields", "columns", "layout", "semantic_anchors"):
                    self.assertNotIn(key, spec)

    def test_every_entry_semantics_declare_its_own_fact_authority(self):
        for contract_xmlid, (_action, model, _view, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                context = ((self._contract(contract_xmlid).contract_json or {})
                           .get("view_orchestration", {}).get("context", {}))
                self.assertEqual(context.get("source"), "smart_construction_core.product_release")
                self.assertEqual(context.get("source_status"), "product_release")
                self.assertEqual(context.get("fact_authority"), model)

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

        This is the assertion that closes the compatibility path: while only the
        model-level mirror declares the plane, `form_structure_authority` stays
        `""` and the ledger keeps counting the entry as a compatibility
        consumer, even though the native arch already renders the page.
        """
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                configs = self._entry_contracts(model, action_xmlid, view_xmlid)
                resolved = resolve_form_structure_governance({}, configs, view_type="form")
                self.assertEqual(resolved.get("form_structure_authority"), "native_authority")
                self.assertEqual(resolved.get("form_presentation_mode"), "task")
                self.assertFalse(resolved.get("section_titles"))

    def test_every_entry_release_outranks_its_model_mirror(self):
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                entry = self._contract(contract_xmlid)
                others = [
                    config for config in self._entry_contracts(model, action_xmlid, view_xmlid)
                    if config.name != entry.name
                ]
                self.assertTrue(others, "the model-level mirror must still be in the plane")
                self.assertGreater(
                    entry.priority,
                    max(config.priority for config in others),
                    "the entry release must sort after every carrier it competes with",
                )

    def test_the_model_mirrors_stay_active_and_their_structure_is_suppressed(self):
        """A mirror is a model-wide carrier, not a mirror of one entry alone.

        Each one serves the action-less model plane, so the batch may not retire
        it.  The measurement records what it becomes instead: the native view
        owns the structure and the mirror's `fields` declaration is reported as
        suppressed rather than as a conflict.
        """
        for mirror_xmlid, (name, model, priority, sibling_actions) in self.MODEL_MIRRORS.items():
            with self.subTest(contract=mirror_xmlid):
                mirror = self._contract(mirror_xmlid)
                self.assertTrue(mirror.active)
                self.assertEqual(mirror.name, name)
                self.assertEqual(mirror.model, model)
                self.assertFalse(mirror.action_id)
                self.assertFalse(mirror.view_id)
                self.assertEqual(mirror.priority, priority)
                self.assertLess(mirror.priority, self.ENTRY_PRIORITY)

        mirror_by_model = {
            model: name for name, model, _priority, _siblings in self.MODEL_MIRRORS.values()
        }
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title) in self.ENTRIES.items():
            with self.subTest(entry=contract_xmlid):
                configs = self._entry_contracts(model, action_xmlid, view_xmlid)
                diagnostics = diagnose_structure_ownership(
                    configs,
                    model=model,
                    action_id=self.ref("smart_construction_core.%s" % action_xmlid),
                )
                codes = {row["code"] for row in diagnostics}
                self.assertEqual(codes, {"LEGACY_STRUCTURE_SUPPRESSED_BY_NATIVE_VIEW"})
                self.assertEqual(
                    [row["configuration"]["name"] for row in diagnostics],
                    [mirror_by_model[model]],
                )
                for row in diagnostics:
                    self.assertFalse(
                        row["explicit_structure_scope"],
                        "a model-wide mirror is not a scoped competitor",
                    )

    def test_the_release_does_not_leak_to_a_sibling_action(self):
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title) in self.ENTRIES.items():
            for sibling_xmlid in self.SIBLING_ACTIONS[contract_xmlid]:
                with self.subTest(entry=contract_xmlid, sibling=sibling_xmlid):
                    configs = self._entry_contracts(model, sibling_xmlid, view_xmlid)
                    self.assertNotIn(
                        self._contract(contract_xmlid).name,
                        [config.name for config in configs],
                    )

    def test_every_sibling_action_still_reaches_its_own_form(self):
        for mirror_xmlid, (_name, model, _priority, sibling_actions) in self.MODEL_MIRRORS.items():
            for sibling_xmlid in sibling_actions:
                with self.subTest(mirror=mirror_xmlid, action=sibling_xmlid):
                    action = self.env.ref("smart_construction_core.%s" % sibling_xmlid)
                    self.assertEqual(action.res_model, model)
                    self.assertIn("form", action.view_mode or "")

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

    def test_the_rendered_field_set_is_pinned(self):
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                data = self._native_contract(model, action_xmlid, view_xmlid)
                rendered = tuple(node["name"] for node in self._field_nodes(data))
                self.assertEqual(rendered, self.RENDERED_FIELDS[view_xmlid])

    def test_the_delivered_readonly_and_hidden_structure_is_pinned(self):
        """The entry releases declare no field policy, so pin what the page carries."""
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
                    modifiers.append((node["name"], readonly, invisible))
                self.assertEqual(tuple(modifiers), self.DELIVERED_MODIFIERS[view_xmlid])

    # -- native arch ---------------------------------------------------------

    def test_the_native_arch_is_presentation_neutral(self):
        """The batch publishes declarations; it must not add or drop a fact."""
        for view_xmlid, expected in self.RENDERED_FIELDS.items():
            with self.subTest(view=view_xmlid):
                self.assertEqual(self._arch_field_names(view_xmlid), expected)

    def test_the_arch_declares_every_rendered_business_field(self):
        for contract_xmlid, (_action, model, view_xmlid, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                arch_fields = set(self._arch_field_names(view_xmlid))
                for name in self.RENDERED_FIELDS[view_xmlid]:
                    self.assertIn(name, arch_fields)
                    self.assertIn(name, self.env[model]._fields)

    def test_the_native_views_declare_no_anchor_and_no_inherited_child(self):
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
