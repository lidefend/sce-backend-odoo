# -*- coding: utf-8 -*-
"""Shared form-structure consumption mechanism.

These tests prove behaviour, not implementation strings:

* the display-copy registry is declaration-driven and every declaration is
  backed by a co-present canonical carrier in the same form arch;
* registered copies never enter the form body union, while an unregistered
  same-shape projection is untouched (the shared layer must not guess copies
  from a model name or a field suffix);
* anchors may declare the canonical business fact only.
"""

import ast

from odoo.tests.common import TransactionCase

from odoo.addons.smart_construction_core.models.core.formal_config_contract_fields import (
    FORMAL_DISPLAY_COPY_SOURCES,
    _display_value,
)


class TestFormStructureConsumption(TransactionCase):
    def _walk_field_names(self, nodes):
        names = set()
        for node in nodes if isinstance(nodes, list) else []:
            if not isinstance(node, dict):
                continue
            if str(node.get("type") or "").strip().lower() == "field":
                name = str(node.get("name") or "").strip()
                if name:
                    names.add(name)
            for key in ("children", "pages", "tabs", "nodes", "items"):
                names.update(self._walk_field_names(node.get(key)))
        return names

    def _form_arch_field_names(self, model_name):
        views = self.env["ir.ui.view"].sudo().search([("model", "=", model_name), ("type", "=", "form")])
        names = set()
        for view in views:
            arch = view.arch or ""
            if "<form" not in arch:
                continue
            for field_name in self.env[model_name]._fields:
                if 'name="%s"' % field_name in arch:
                    names.add(field_name)
        return names

    # Entries that declare the same premise: a list domain on
    # ``business_category_id.code`` plus a ``default_business_category_code``
    # context default.  ``create()`` resolves that declaration for every one of
    # them; the create surface must present the same fact.
    BUSINESS_CATEGORY_ENTRIES = (
        ("action_sc_settlement_order_income", "sc.settlement.order"),
        ("action_sc_settlement_order_expense", "sc.settlement.order"),
        ("action_sc_tax_deduction_registration_user", "sc.tax.deduction.registration"),
        ("action_sc_product_project_tax_deduction_v1", "sc.tax.deduction.registration"),
    )

    @staticmethod
    def _action_context(action):
        raw = action.context
        return dict(ast.literal_eval(raw)) if isinstance(raw, str) else dict(raw or {})

    @staticmethod
    def _action_domain(action):
        raw = action.domain
        return list(ast.literal_eval(raw)) if isinstance(raw, str) else list(raw or [])

    def test_a_declared_entry_category_reaches_the_create_surface(self):
        """A declared entry category is a shared premise, not a per-model extra.

        Four entries of two models declare the same premise.  ``create()``
        resolves it for all of them, so a create surface that leaves the
        relation empty is not a model quirk but a missing step of the shared
        declaration.  Proved behaviourally: the entry context resolves, through
        the model's own declaration, to the category the entry domain already
        names.
        """
        for action_key, model_name in self.BUSINESS_CATEGORY_ENTRIES:
            with self.subTest(action=action_key):
                action = self.env.ref("smart_construction_core." + action_key)
                context = self._action_context(action)
                self.assertEqual(action.res_model, model_name)
                code = context.get("default_business_category_code")
                self.assertTrue(code, (action_key, "the entry declares no category"))
                self.assertIn(
                    ("business_category_id.code", "=", code),
                    [tuple(row) for row in self._action_domain(action)],
                    (action_key, "the entry domain does not name the same category"),
                )
                category = self.env["sc.business.category"].sudo().search(
                    [("code", "=", code), ("target_model", "=", model_name)], limit=1
                )
                self.assertTrue(category, (action_key, code, "the declared category must exist"))
                defaults = self.env[model_name].with_context(**context).default_get(
                    ["business_category_id"]
                )
                self.assertEqual(
                    defaults.get("business_category_id"), category.id,
                    (action_key, "the declared entry category never reaches the create surface"),
                )

    def test_an_entry_category_that_cannot_be_resolved_is_not_substituted(self):
        """No declaration means no value: the shared layer must not guess.

        A code the entry declares but the data does not define resolves to
        nothing on both steps.  Substituting another category (for example the
        scope-derived sibling) would create a record under an entry the user did
        not choose.
        """
        model = "sc.tax.deduction.registration"
        context = {"default_business_category_code": "tax.deduction.absent"}
        self.assertFalse(
            self.env["sc.business.category"].sudo().search(
                [("code", "=", "tax.deduction.absent")], limit=1
            )
        )
        defaults = self.env[model].with_context(**context).default_get(["business_category_id"])
        self.assertFalse(defaults.get("business_category_id"))

    def test_every_declaration_is_backed_by_a_co_present_canonical(self):
        """A declaration is valid only if the fact stays visible without the copy."""
        self.assertTrue(FORMAL_DISPLAY_COPY_SOURCES, "the registry must declare at least one group")
        for model_name, copies in FORMAL_DISPLAY_COPY_SOURCES.items():
            self.assertIn(model_name, self.env, "%s must be an installed model" % model_name)
            model_fields = self.env[model_name]._fields
            arch_fields = self._form_arch_field_names(model_name)
            for copy_name, canonical_name in copies.items():
                self.assertIn(copy_name, model_fields, "%s.%s must stay a real field" % (model_name, copy_name))
                self.assertIn(canonical_name, model_fields, "%s.%s must be a real canonical field" % (model_name, canonical_name))
                self.assertIn(
                    canonical_name,
                    arch_fields,
                    "%s.%s is not carried by the model form arch, so excluding %s would hide the fact"
                    % (model_name, canonical_name, copy_name),
                )

    def test_declared_copy_value_is_the_projection_of_its_canonical(self):
        """The declared source relation is the live projection, not a snapshot."""
        for model_name, copies in FORMAL_DISPLAY_COPY_SOURCES.items():
            model = self.env[model_name]
            field_info = model.fields_get(list(copies.keys()) + list(copies.values()))
            for copy_name, canonical_name in copies.items():
                field_type = field_info.get(canonical_name, {}).get("type")
                sample = {
                    "char": "样例",
                    "text": "样例",
                    "selection": None,
                    "datetime": "2026-09-17 08:00:00",
                    "date": "2026-09-17",
                }.get(field_type)
                if sample is None:
                    # relation/other types are covered by the arch co-presence test
                    continue
                record = model.new({canonical_name: sample})
                self.assertEqual(
                    str(record[copy_name] or ""),
                    str(_display_value(record, canonical_name) or ""),
                    "%s.%s must mirror %s" % (model_name, copy_name, canonical_name),
                )
                other = model.new({canonical_name: sample})
                self.assertEqual(str(other[copy_name] or ""), str(_display_value(other, canonical_name) or ""))

    def test_registered_copies_never_enter_the_form_union(self):
        from copy import deepcopy

        from odoo.addons.smart_core.core.view_orchestrator import ViewOrchestrator

        orchestrator = ViewOrchestrator(self.env)
        for model_name, copies in FORMAL_DISPLAY_COPY_SOURCES.items():
            self.assertEqual(
                orchestrator._display_copy_field_names(model_name),
                set(copies.keys()),
                "%s must expose exactly its declared copies" % model_name,
            )
            canonical_names = sorted(set(copies.values()))
            spec_fields = [{"name": name, "visible": True} for name in canonical_names + sorted(copies.keys())]
            contract = {"layout": [{"type": "group", "children": [{"type": "field", "name": name} for name in canonical_names]}]}
            out = orchestrator._apply_form_spec(deepcopy(contract), {"fields": spec_fields}, model_name)
            names = self._walk_field_names(out.get("layout"))
            for canonical_name in canonical_names:
                self.assertIn(canonical_name, names, "%s.%s must stay in the form" % (model_name, canonical_name))
            for copy_name in copies:
                self.assertNotIn(copy_name, names, "%s.%s must not be unioned into the form" % (model_name, copy_name))

    def test_unregistered_same_shape_projection_is_not_excluded(self):
        """The shared layer follows declarations only, never a suffix guess."""
        from copy import deepcopy

        from odoo.addons.smart_core.core.view_orchestrator import ViewOrchestrator

        orchestrator = ViewOrchestrator(self.env)
        # payment.request registers its attachment summary only.  Another
        # same-shape projection on the same model stays untouched.
        self.assertIn("payment_request_attachment_text_display", FORMAL_DISPLAY_COPY_SOURCES["payment.request"])
        self.assertNotIn("payment_request_account_no_display", FORMAL_DISPLAY_COPY_SOURCES["payment.request"])
        contract = {"layout": [{"type": "group", "children": [{"type": "field", "name": "name"}]}]}
        spec = {"fields": [
            {"name": "name", "visible": True},
            {"name": "payment_request_attachment_text_display", "visible": True},
            {"name": "payment_request_account_no_display", "visible": True},
        ]}
        out = orchestrator._apply_form_spec(deepcopy(contract), spec, "payment.request")
        names = self._walk_field_names(out.get("layout"))
        self.assertNotIn("payment_request_attachment_text_display", names)
        self.assertIn("payment_request_account_no_display", names)

    def test_platform_declared_plumbing_field_is_not_unioned_into_the_body(self):
        """A configuration may not promote declared plumbing into the body.

        The platform declares the non-presentable names once, in the core.  The
        union consumes that declaration instead of guessing from a name or a
        suffix, which matters because the plumbing field and the canonical
        attachment carrier have the same shape: ``message_attachment_count``
        counts the collaboration attachments while ``attachment_ids`` carries
        the bill attachments, and both are named like a counter/relation.  A
        suffix rule would drop the carrier too.
        """
        from copy import deepcopy

        from odoo.addons.smart_core.core.lowcode_presentable_fields import (
            LOWCODE_NON_PRESENTABLE_FIELD_NAMES,
        )
        from odoo.addons.smart_core.core.view_orchestrator import ViewOrchestrator

        model_name = "sc.tax.deduction.registration"
        plumbing = "message_attachment_count"
        carrier = "attachment_ids"
        self.assertIn(plumbing, LOWCODE_NON_PRESENTABLE_FIELD_NAMES)
        self.assertNotIn(
            carrier, LOWCODE_NON_PRESENTABLE_FIELD_NAMES,
            "a canonical business carrier must never be declared non-presentable",
        )
        orchestrator = ViewOrchestrator(self.env)
        contract = {"layout": [{"type": "group", "children": [{"type": "field", "name": "name"}]}]}
        spec = {"fields": [
            {"name": "name", "visible": True},
            {"name": plumbing, "visible": True},
            {"name": carrier, "visible": True},
        ]}
        names = self._walk_field_names(
            orchestrator._apply_form_spec(deepcopy(contract), spec, model_name).get("layout")
        )
        self.assertNotIn(plumbing, names, "declared plumbing must not be unioned into the business body")
        self.assertIn(carrier, names, "the canonical attachment carrier keeps its entry")

    def test_anchor_rejects_a_declared_copy(self):
        from types import SimpleNamespace

        from odoo.addons.smart_core.core.view_orchestrator import ViewOrchestrator

        orchestrator = ViewOrchestrator(self.env)
        for model_name, copies in FORMAL_DISPLAY_COPY_SOURCES.items():
            copy_name = sorted(copies)[0]
            canonical_name = copies[copy_name]
            config = SimpleNamespace(contract_json={"view_orchestration": {"views": {"form": {
                "composition_mode": "native_semantic_surface",
                "semantic_anchors": [{"anchor": "section", "fields": [canonical_name, copy_name]}],
            }}}})
            with self.assertRaises(ValueError, msg="%s.%s anchor must be rejected" % (model_name, copy_name)):
                orchestrator._config_declares_native_semantic_surface(config, "form", model_name)
            clean = SimpleNamespace(contract_json={"view_orchestration": {"views": {"form": {
                "composition_mode": "native_semantic_surface",
                "semantic_anchors": [{"anchor": "section", "fields": [canonical_name]}],
            }}}})
            self.assertTrue(
                orchestrator._config_declares_native_semantic_surface(clean, "form", model_name),
                "%s: canonical-only anchors must keep passing" % model_name,
            )
