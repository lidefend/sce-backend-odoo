# -*- coding: utf-8 -*-
from lxml import etree

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.core.form_structure_authority import (
    diagnose_structure_ownership,
    resolve_form_structure_governance,
    structural_form_declarations,
)


@tagged("post_install", "-at_install", "uc4_native_lowcode")
class TestUsagePerformanceNativeLowcode(TransactionCase):
    """U-C4 G09: 用量与履约登记整组原生结构迁移.

    Three P1 native forms carry this group and nothing else:

      871 劳务成本登记 / menu 689 / action `action_sc_product_labor_cost_v1`
      562 方单         / menu 504 / action `action_sc_labor_usage_ticket`      -> 同一原生表单
      563 零星用工     / menu 505 / action `action_sc_labor_usage_casual`     -> 同一原生表单
        -> `sc.labor.usage` / `view_sc_labor_usage_form`

      570 机械台班登记 / menus 692+509 / action `action_sc_equipment_usage`
      851 机械台班记录 / menu 510      / action `action_sc_equipment_usage_shift_user_confirmed`
        -> `sc.equipment.usage` / `view_sc_equipment_usage_form`

      575 分包成本登记 / menus 693+518 / action `action_sc_subcontract_register`
        -> `sc.subcontract.register` / `view_sc_subcontract_register_form`

    Before this batch each entry carried its own `entry_semantic_surface` body
    (sections + fields + columns) that duplicated the groups and notebook pages
    its own native form already declares, and the same native tree was projected
    several ways at once: the equipment entry alone exposed 6 entry chapters plus
    5 model-wide chapters.  871 had no entry release at all and consumed the
    model-wide section plane.

    After this batch the native arch owns the structure for the whole group: every
    entry keeps only `title` + `composition_mode: native_semantic_surface`, the
    model-wide section plane is retired, and each reachable entry resolves the SAME
    native body.  No retired declaration referenced a fact that does not exist, and
    the rendered business field set is pinned so the migration cannot silently drop
    a fact.  This batch changes structure only: the model-wide business-fact policy
    carriers stay active, so editability semantics are unchanged.
    """

    # entry contract xmlid -> (action xmlid, model, view xmlid, title)
    ENTRIES = {
        "business_config_contract_labor_usage_register_productized_form_v1": (
            "action_sc_product_labor_cost_v1", "sc.labor.usage",
            "view_sc_labor_usage_form", "劳务成本登记"),
        "business_config_contract_labor_usage_ticket_productized_form_v1": (
            "action_sc_labor_usage_ticket", "sc.labor.usage",
            "view_sc_labor_usage_form", "方单"),
        "business_config_contract_labor_usage_casual_productized_form_v1": (
            "action_sc_labor_usage_casual", "sc.labor.usage",
            "view_sc_labor_usage_form", "零星用工"),
        "business_config_contract_equipment_usage_shift_productized_form_v1": (
            "action_sc_equipment_usage_shift_user_confirmed", "sc.equipment.usage",
            "view_sc_equipment_usage_form", "机械台班记录"),
        "business_config_contract_equipment_usage_register_productized_form_v1": (
            "action_sc_equipment_usage", "sc.equipment.usage",
            "view_sc_equipment_usage_form", "设备使用登记"),
        "business_config_contract_subcontract_register_productized_form_v1": (
            "action_sc_subcontract_register", "sc.subcontract.register",
            "view_sc_subcontract_register_form", "分包登记"),
    }

    # The entries each native form must serve, keyed by view xmlid.
    SHARED_FORMS = {
        "view_sc_labor_usage_form": (
            "action_sc_product_labor_cost_v1",
            "action_sc_labor_usage_ticket",
            "action_sc_labor_usage_casual",
        ),
        "view_sc_equipment_usage_form": (
            "action_sc_equipment_usage",
            "action_sc_equipment_usage_shift_user_confirmed",
        ),
        "view_sc_subcontract_register_form": ("action_sc_subcontract_register",),
    }

    # Model-wide section carriers retired by this batch, and the native view that
    # now owns the section identity.
    RETIRED_SECTION_CARRIERS = {
        "business_config_contract_sc_labor_usage_form_sections_v1": "view_sc_labor_usage_form",
        "business_config_contract_sc_equipment_usage_form_sections_v1": "view_sc_equipment_usage_form",
        "business_config_contract_sc_subcontract_register_form_sections_v1": "view_sc_subcontract_register_form",
    }

    # Model-wide sparse sequence mirrors: retained on purpose (same rule as G05/G06/G07).
    RETAINED_SPARSE_ANNOTATIONS = {
        "business_config_contract_sc_labor_usage_form_structure_generated": "sc.labor.usage",
        "business_config_contract_sc_equipment_usage_form_structure_generated": "sc.equipment.usage",
        "business_config_contract_sc_subcontract_register_form_structure_generated": "sc.subcontract.register",
    }

    # Model-wide business-fact policy carriers retained on purpose: they are the only
    # declaration of the business-fact readonly policy on these three models.
    RETAINED_BUSINESS_FACT_POLICIES = {
        "business_config_contract_sc_labor_usage_p1_form_business_facts_v1": "sc.labor.usage",
        "business_config_contract_sc_equipment_usage_p1_form_business_facts_v1": "sc.equipment.usage",
        "business_config_contract_sc_subcontract_register_p1_form_business_facts_v1": "sc.subcontract.register",
    }

    # Facts declared by the retired entry bodies.  Neither list may reference a
    # name that is not a real model field.
    RETIRED_ENTRY_FACTS = {
        "sc.labor.usage": (
            "state", "name", "usage_type", "usage_date", "project_id", "contractor_id",
            "labor_team", "foreman_name", "construction_part", "work_content",
            "worker_qty", "work_hours", "price_unit", "amount_total", "settlement_state",
            "note", "attachment_ids", "recorder_id", "create_date",
        ),
        "sc.equipment.usage": (
            "state", "name", "usage_date", "project_id", "supplier_id", "request_id",
            "recorder_id", "equipment_name", "equipment_code", "specification", "uom_text",
            "usage_location", "operator_name", "usage_qty", "usage_hours", "price_unit",
            "amount", "currency_id", "note", "attachment_ids", "create_date",
        ),
        "sc.subcontract.register": (
            "state", "name", "project_id", "request_id", "contract_id", "subcontract_scope",
            "subcontractor_id", "responsible_id", "register_date", "sign_date", "start_date",
            "end_date", "registered_amount", "amount_total", "quantity_total",
            "invoice_amount", "paid_amount", "unpaid_amount", "uninvoiced_amount",
            "currency_id", "line_ids", "management_note", "note", "message_attachment_count",
            "legacy_fact_model", "legacy_fact_id", "legacy_fact_type", "source_created_by",
            "source_created_at", "active",
            "subcontract_register_document_no_display", "subcontract_register_title_display",
            "subcontract_register_subcontract_content_display",
            "subcontract_register_amount_display", "subcontract_register_contract_no_display",
        ),
    }

    # Business field set the native arch renders for each form.  Pinned from the
    # pre-migration arch so the batch is provably presentation-neutral.
    RENDERED_FIELDS = {
        "view_sc_labor_usage_form": (
            "state", "name", "project_id", "usage_date", "usage_type", "labor_team",
            "contractor_id", "foreman_name", "recorder_id", "worker_qty", "work_hours",
            "currency_id", "price_unit", "amount_total", "settlement_state", "work_type",
            "construction_part", "work_content", "note", "attachment_ids",
        ),
        "view_sc_equipment_usage_form": (
            "state", "name", "project_id", "request_id", "usage_date", "equipment_name",
            "equipment_code", "specification", "uom_text", "usage_location", "operator_name",
            "usage_qty", "usage_hours", "currency_id", "price_unit", "amount", "supplier_id",
            "recorder_id", "note", "attachment_ids", "processing_advisory",
        ),
        # The editable inline tree of `line_ids` is part of the same arch, so its
        # columns are pinned in document order too.
        "view_sc_subcontract_register_form": (
            "state", "name", "project_id", "request_id", "contract_id", "register_date",
            "start_date", "end_date", "subcontract_scope", "subcontractor_id",
            "responsible_id", "currency_id", "registered_amount", "line_ids",
            "sequence", "work_scope", "work_content", "contract_qty", "unit_name",
            "note", "management_note", "attachment_ids", "processing_advisory",
        ),
    }

    # The anchored native business sections this batch declares.
    NATIVE_SECTIONS = {
        "view_sc_labor_usage_form": (
            ("labor_usage_processing_main", "用工主信息"),
            ("labor_usage_labor_amount", "用工与计价"),
        ),
        "view_sc_equipment_usage_form": (
            ("equipment_usage_identity", "设备与项目"),
            ("equipment_usage_usage_amount", "使用与计价"),
        ),
        "view_sc_subcontract_register_form": (
            ("subcontract_register_main", "登记主信息"),
            ("subcontract_register_parties_amount", "分包单位与金额"),
        ),
    }

    def _contract(self, xmlid):
        return self.env["ui.business.config.contract"].sudo().browse(
            self.ref("smart_construction_core.%s" % xmlid)
        )

    def _entry_contracts(self, model, action_xmlid):
        return self.env["ui.business.config.contract"].sudo()._effective_view_orchestration_contracts(
            model,
            view_type="form",
            action_id=self.ref("smart_construction_core.%s" % action_xmlid),
            view_id=0,
            role_key="",
        )

    def _form_spec(self, record):
        return (
            ((record.contract_json or {}).get("view_orchestration") or {})
            .get("views", {})
            .get("form", {})
        )

    def _arch(self, view_xmlid):
        view = self.env.ref("smart_construction_core.%s" % view_xmlid)
        return etree.fromstring(view.arch.encode("utf-8"))

    def _arch_fields(self, view_xmlid):
        arch = self._arch(view_xmlid)
        seen, ordered = set(), []
        for node in arch.iter("field"):
            name = node.get("name")
            if name and name not in seen:
                seen.add(name)
                ordered.append(name)
        return tuple(ordered)

    def _arch_sections(self, view_xmlid):
        """Anchored native business groups, excluding notebook descendants."""
        arch = self._arch(view_xmlid)
        sections = []
        for notebook in arch.iter("notebook"):
            notebook.getparent().remove(notebook)
        for group in arch.iter("group"):
            anchor = group.get("data-sc-anchor")
            if anchor:
                sections.append((anchor, group.get("string")))
        return tuple(sections)

    def _arch_field_owners(self, nodes, model, out):
        """Resolve every `<field>` against the model that actually owns it.

        A nested `<tree>`/`<form>` inside an x2many field describes the comodel,
        so the inline columns are checked against their own model instead of the
        form's model.
        """
        for node in nodes:
            if node.tag == "field":
                name = node.get("name")
                if name:
                    out.append((model, name))
                containers = [child for child in node if child.tag in ("tree", "form", "kanban")]
                if containers:
                    field = self.env[model]._fields.get(name) if model in self.env else None
                    relation = getattr(field, "relation", None)
                    if relation:
                        for container in containers:
                            self._arch_field_owners(list(container), relation, out)
            else:
                self._arch_field_owners(list(node), model, out)
        return out

    # -- declaration surface -------------------------------------------------

    def test_every_entry_declares_the_native_semantic_surface(self):
        for contract_xmlid, (action_xmlid, model, _view, title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                record = self._contract(contract_xmlid)
                self.assertTrue(record.active)
                self.assertEqual(record.model, model)
                self.assertEqual(
                    record.action_id.id,
                    self.ref("smart_construction_core.%s" % action_xmlid),
                )
                spec = self._form_spec(record)
                self.assertEqual(spec.get("composition_mode"), "native_semantic_surface")
                self.assertEqual(spec.get("title"), title)
                # A native declaration may not carry a competing structure.
                self.assertEqual(structural_form_declarations(spec), {})

    def test_the_entry_semantics_are_preserved_verbatim(self):
        """The release context stays the entry's semantic declaration."""
        for contract_xmlid in self.ENTRIES:
            with self.subTest(contract=contract_xmlid):
                context = (
                    (self._contract(contract_xmlid).contract_json or {})
                    .get("view_orchestration", {})
                    .get("context", {})
                )
                self.assertEqual(context.get("source"), "smart_construction_core.product_release")
                self.assertEqual(context.get("source_status"), "product_release")

    def test_the_model_wide_section_carriers_are_retired(self):
        for contract_xmlid, view_xmlid in self.RETIRED_SECTION_CARRIERS.items():
            with self.subTest(contract=contract_xmlid):
                record = self._contract(contract_xmlid)
                self.assertFalse(record.active)
                # The retired declaration must not be re-armed with a different
                # structural body; the native form owns the identity.
                self.assertTrue(self.env.ref("smart_construction_core.%s" % view_xmlid))

    def test_the_model_wide_sparse_annotation_keeps_serving_the_model(self):
        """Retained on purpose: the sparse sequence mirror is still the model plane."""
        for contract_xmlid, model in self.RETAINED_SPARSE_ANNOTATIONS.items():
            with self.subTest(contract=contract_xmlid):
                record = self._contract(contract_xmlid)
                self.assertTrue(record.active)
                self.assertFalse(record.action_id)
                self.assertEqual(record.model, model)
                spec = self._form_spec(record)
                self.assertIn("fields", spec)
                self.assertNotIn("sections", spec)
                self.assertNotIn("composition_mode", spec)

    def test_the_business_fact_policy_carriers_are_retained(self):
        """Structure retired, policy retained: editability semantics stay unchanged."""
        for contract_xmlid, model in self.RETAINED_BUSINESS_FACT_POLICIES.items():
            with self.subTest(contract=contract_xmlid):
                record = self._contract(contract_xmlid)
                self.assertTrue(record.active)
                self.assertEqual(record.model, model)
                read_only = {
                    row.get("name")
                    for row in (self._form_spec(record).get("fields") or [])
                    if isinstance(row, dict) and row.get("readonly")
                }
                self.assertTrue(read_only, "the retained carrier must still declare policies")

    # -- resolution surface --------------------------------------------------

    def test_every_entry_resolves_the_native_semantic_surface(self):
        for contract_xmlid, (action_xmlid, model, _view, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                configs = self._entry_contracts(model, action_xmlid)
                native = [
                    config for config in configs
                    if (self._form_spec(config) or {}).get("composition_mode")
                    in {"native_semantic_surface", "semantic_native_surface"}
                ]
                self.assertEqual(
                    [config.name for config in native],
                    [self._contract(contract_xmlid).name],
                )

    def test_every_entry_resolves_native_authority(self):
        """The entry declaration must be the last structure writer for its action.

        This is the assertion that pins the priority decision: the model-wide
        carriers are still active and still declare `entry_semantic_surface`, so a
        native declaration that sorted before them would leave the resolved
        authority pointing back at the legacy plane.
        """
        for contract_xmlid, (action_xmlid, model, _view, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                configs = self._entry_contracts(model, action_xmlid)
                resolved = resolve_form_structure_governance({}, configs, view_type="form")
                self.assertEqual(resolved.get("form_structure_authority"), "native_authority")
                self.assertEqual(resolved.get("form_presentation_mode"), "task")

    def test_the_entry_release_outranks_every_model_wide_carrier(self):
        """50 -> 800: no model-wide carrier may sort after the native declaration."""
        for contract_xmlid, (action_xmlid, model, _view, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                entry = self._contract(contract_xmlid)
                others = [
                    config for config in self._entry_contracts(model, action_xmlid)
                    if config.name != entry.name
                ]
                self.assertTrue(others, "each entry still resolves its model-wide plane")
                self.assertGreater(entry.priority, max(config.priority for config in others))

    def test_the_retained_carriers_are_reported_as_suppressed_not_rejected(self):
        """An unscoped legacy declaration degrades; it never blocks the native owner."""
        for contract_xmlid, (action_xmlid, model, _view, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                configs = self._entry_contracts(model, action_xmlid)
                diagnostics = diagnose_structure_ownership(
                    configs,
                    model=model,
                    action_id=self.ref("smart_construction_core.%s" % action_xmlid),
                )
                codes = {row["code"] for row in diagnostics}
                self.assertNotIn("NATIVE_SEMANTIC_SURFACE_STRUCTURE_CONFLICT", codes)
                for row in diagnostics:
                    self.assertFalse(
                        row["explicit_structure_scope"],
                        "a scoped competing declaration must never survive the native owner",
                    )

    def test_a_scoped_competing_declaration_is_refused(self):
        """Negative control: the mechanism still fails closed on a scoped conflict."""
        model = "sc.labor.usage"

        class _Config:
            def __init__(self, name, contract_json, action_id, view_id=0):
                self.id = 0
                self.name = name
                self.priority = 50
                self.view_type = "form"
                self.contract_json = contract_json
                self.action_id = action_id
                self.view_id = view_id

        native = _Config("native", {"view_orchestration": {"views": {"form": {
            "title": "劳务成本登记", "composition_mode": "native_semantic_surface"}}}}, 999)
        competitor = _Config("competitor", {"view_orchestration": {"views": {"form": {
            "composition_mode": "entry_semantic_surface",
            "sections": [{"title": "旧章节"}]}}}}, 999)
        with self.assertRaises(ValueError):
            diagnose_structure_ownership([native, competitor], model=model, action_id=999)

    # -- native arch ---------------------------------------------------------

    def test_the_native_arch_declares_every_business_section_identity(self):
        for view_xmlid, expected in self.NATIVE_SECTIONS.items():
            with self.subTest(view=view_xmlid):
                self.assertEqual(self._arch_sections(view_xmlid), expected)

    def test_the_native_arch_is_presentation_neutral(self):
        """The batch retires declarations; it must not add or drop a rendered fact."""
        for view_xmlid, expected in self.RENDERED_FIELDS.items():
            with self.subTest(view=view_xmlid):
                self.assertEqual(self._arch_fields(view_xmlid), expected)

    def test_no_retired_declaration_referenced_a_missing_fact(self):
        for model, names in self.RETIRED_ENTRY_FACTS.items():
            fields = set(self.env[model]._fields)
            with self.subTest(model=model):
                self.assertEqual(sorted(set(names) - fields), [])

    def test_every_rendered_fact_belongs_to_its_own_model(self):
        mapping = {
            "view_sc_labor_usage_form": "sc.labor.usage",
            "view_sc_equipment_usage_form": "sc.equipment.usage",
            "view_sc_subcontract_register_form": "sc.subcontract.register",
        }
        for view_xmlid, model in mapping.items():
            owners = self._arch_field_owners(list(self._arch(view_xmlid)), model, [])
            unknown = sorted({
                "%s.%s" % (owner, name)
                for owner, name in owners
                if owner not in self.env or name not in self.env[owner]._fields
            })
            with self.subTest(view=view_xmlid):
                self.assertEqual(unknown, [])

    # -- routing surface -----------------------------------------------------

    def test_the_shared_native_form_serves_every_entry(self):
        for view_xmlid, action_xmlids in self.SHARED_FORMS.items():
            view = self.env.ref("smart_construction_core.%s" % view_xmlid)
            primary = self.env["ir.ui.view"].sudo().search([
                ("model", "=", view.model), ("type", "=", "form"),
                ("inherit_id", "=", False), ("active", "=", True),
            ])
            with self.subTest(view=view_xmlid):
                self.assertEqual(primary.ids, [view.id])
                for action_xmlid in action_xmlids:
                    action = self.env.ref("smart_construction_core.%s" % action_xmlid)
                    self.assertEqual(action.res_model, view.model)
                    self.assertIn("form", action.view_mode)
                    # The action either pins a tree (form falls to the primary
                    # form) or pins nothing at all: both reach the same body.
                    if action.view_id:
                        self.assertNotEqual(action.view_id.type, "form")

    def test_the_entry_titles_and_actions_are_unchanged(self):
        for contract_xmlid, (action_xmlid, _model, _view, title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                record = self._contract(contract_xmlid)
                self.assertEqual(record.name, contract_xmlid.replace(
                    "business_config_contract_", ""))
                self.assertEqual(self._form_spec(record).get("title"), title)
                action = self.env.ref("smart_construction_core.%s" % action_xmlid)
                self.assertTrue(action.name)
                self.assertEqual(action.view_mode, "tree,form")

    def test_the_shared_carriers_reach_the_same_form(self):
        """The action pins a tree or nothing; the form is always the primary one."""
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                action = self.env.ref("smart_construction_core.%s" % action_xmlid)
                pinned = action.view_id
                if pinned and pinned.type == "form":
                    self.assertEqual(pinned.id, self.env.ref(
                        "smart_construction_core.%s" % view_xmlid).id)
                else:
                    primary = self.env["ir.ui.view"].sudo().search([
                        ("model", "=", model), ("type", "=", "form"),
                        ("inherit_id", "=", False), ("active", "=", True),
                    ])
                    self.assertEqual(primary.ids, [
                        self.env.ref("smart_construction_core.%s" % view_xmlid).id
                    ])
