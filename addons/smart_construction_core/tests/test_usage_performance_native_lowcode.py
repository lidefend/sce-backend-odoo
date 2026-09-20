# -*- coding: utf-8 -*-
from lxml import etree

from odoo.exceptions import UserError
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
      561 劳务用工     / 无独立菜单   / action `action_sc_labor_usage`         -> 同一原生表单
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
    a fact.

    The structure migration itself changes structure only: the model-wide
    business-fact policy carriers stay active.  The create-state correction of
    2026-09-19 then had to correct what those carriers declared.  They marked
    every business fact unconditionally read-only, including `project_id`, while
    the same declaration marked it required, so the create page offered 提交 with
    no legal path to the project (`p1_*_form_business_facts_v1`).  The policy now
    keeps read-only only where the model itself carries the value (a default, a
    compute, the sequence-issued number, the workflow state, a read-only history
    field), the native arch opens the draft window on the facts the user types,
    the model refuses a post-submission fact write instead of only claiming it in
    XML, and the computed 办理提示 no longer owns a business section.
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
        # 561 carries the same native form through the model's product-policy
        # integration action.  It has no menu of its own, so it was left out of
        # the delivered-navigation registration - and that is exactly why it kept
        # consuming the model-wide plane.  It stays in this list so the create
        # surface of every action that renders the form is pinned.
        "business_config_contract_labor_usage_work_productized_form_v1": (
            "action_sc_labor_usage", "sc.labor.usage",
            "view_sc_labor_usage_form", "劳务用工"),
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
            "action_sc_labor_usage",
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

    # Every action that renders one of these shared native forms must own an
    # entry-level release.  An action without one falls back to the model-wide
    # policy plane, and that plane is not the delivered create surface: on 561 the
    # fallback projected 57 policy keys whose `advanced` fields exclude the create
    # profile, so `work_content` (`required=True`, no model default) came out
    # invisible while the page still offered 提交.  The behaviour itself is pinned
    # by the create-contract probe (tmp/uc4-g09-creatability); this assertion pins
    # the declaration state that probe identified as its cause.
    ENTRY_RELEASE_ACTIONS = {
        "sc.labor.usage": (
            "action_sc_product_labor_cost_v1", "action_sc_labor_usage_ticket",
            "action_sc_labor_usage_casual", "action_sc_labor_usage",
        ),
        "sc.equipment.usage": (
            "action_sc_equipment_usage",
            "action_sc_equipment_usage_shift_user_confirmed",
        ),
        "sc.subcontract.register": ("action_sc_subcontract_register",),
    }

    def test_every_family_action_owns_an_entry_release(self):
        """No action of this group may fall back to the model-wide policy plane.

        561 was the observed case: with no entry release of its own, the create
        projection took the model-wide plane and the required fact `work_content`
        was not obtainable through any legal path.  The guard is per action rather
        than per model, because one model can be served by several actions and the
        plane is resolved per action.
        """
        for model, action_xmlids in self.ENTRY_RELEASE_ACTIONS.items():
            for action_xmlid in action_xmlids:
                with self.subTest(model=model, action=action_xmlid):
                    contracts = self._entry_contracts(model, action_xmlid)
                    native = [
                        config for config in contracts
                        if (self._form_spec(config) or {}).get("composition_mode")
                        in {"native_semantic_surface", "semantic_native_surface"}
                    ]
                    self.assertEqual(
                        len(native), 1,
                        "%s must own exactly one entry-level native release" % action_xmlid,
                    )
                    self.assertEqual(
                        native[0].action_id,
                        self.ref("smart_construction_core.%s" % action_xmlid),
                        "the native release must be scoped to its own action",
                    )
                    # A release that answered for every entry could not be the
                    # entry's own surface, and the priority is what makes it the
                    # last structure writer for this action alone.
                    self.assertGreater(
                        native[0].priority,
                        max(
                            config.priority for config in contracts
                            if config.name != native[0].name
                        ),
                        "%s must outrank its model-wide plane" % action_xmlid,
                    )

    # -- create-state usability (U-C4 G09 可办理性修正, 2026-09-19) ------------

    # `user` is the fact set the create surface must let the user enter, so none of
    # it may stay read-only by policy.  A model default does not move a fact out of
    # this set: a default only lowers the cost of entry, while the choice still
    # belongs to the user inside the draft window - `usage_type` is the observed
    # case (871 方单 / 562 零星用工 pick it per entry, the model guard freezes it
    # after submit).  `carried` is the complementary set: facts a legal non-user
    # carrier supplies (a compute, the sequence-issued document number, the
    # workflow state, a model-level read-only history field, or a derived status
    # the business does not let the user choose), which may therefore keep their
    # read-only policy.
    # `test_the_readonly_policy_keeps_only_facts_with_a_legal_carrier` asserts the
    # split against the delivered field definition, so it is not a naming guess.
    USER_SUPPLIED_FACTS = {
        "sc.labor.usage": (
            "project_id", "usage_type", "usage_date", "contractor_id", "labor_team",
            "work_type", "construction_part", "work_content", "worker_qty",
            "work_hours", "price_unit", "note", "attachment_ids",
        ),
        "sc.equipment.usage": (
            "project_id", "usage_date", "supplier_id", "equipment_name",
            "specification", "uom_text", "usage_qty", "usage_hours", "price_unit",
            "note", "attachment_ids",
        ),
        "sc.subcontract.register": ("project_id", "note"),
    }

    # Facts a legal non-user carrier supplies, and the carrier that does.
    FACT_CARRIERS = {
        "sc.labor.usage": {
            "name": "sequence", "create_date": "system",
            "settlement_state": "default", "recorder_id": "default",
            "amount_total": "computed", "state": "workflow",
        },
        "sc.equipment.usage": {
            "name": "sequence", "create_date": "system",
            "recorder_id": "default", "amount": "computed", "state": "workflow",
        },
        "sc.subcontract.register": {
            "subcontract_register_document_no_display": "computed",
            "subcontract_register_title_display": "computed",
            "subcontract_register_subcontract_content_display": "computed",
            "subcontract_register_amount_display": "computed",
            "subcontract_register_contract_no_display": "computed",
            "sign_date": "computed", "quantity_total": "computed",
            "invoice_amount": "computed", "paid_amount": "computed",
            "unpaid_amount": "computed", "uninvoiced_amount": "computed",
            "message_attachment_count": "computed",
            "source_created_by": "history", "source_created_at": "history",
            "state": "workflow",
        },
    }

    # The retained `p1_form_business_facts_v1` carrier is the only declaration of
    # the business-fact read-only policy on these models.  This is the exact set
    # it still declares read-only after the create-state correction.
    EXPECTED_READONLY_POLICY = {
        "sc.labor.usage": (
            "amount_total", "create_date", "name", "recorder_id",
            "settlement_state", "state",
        ),
        "sc.equipment.usage": (
            "amount", "create_date", "name", "recorder_id", "state",
        ),
        "sc.subcontract.register": (
            "invoice_amount", "message_attachment_count", "paid_amount",
            "quantity_total", "sign_date",
            "subcontract_register_amount_display",
            "subcontract_register_contract_no_display",
            "subcontract_register_document_no_display",
            "subcontract_register_subcontract_content_display",
            "subcontract_register_title_display",
            "source_created_at", "source_created_by", "state",
            "uninvoiced_amount", "unpaid_amount",
        ),
    }

    POLICY_CARRIERS = {
        "sc.labor.usage": "business_config_contract_sc_labor_usage_p1_form_business_facts_v1",
        "sc.equipment.usage": "business_config_contract_sc_equipment_usage_p1_form_business_facts_v1",
        "sc.subcontract.register": "business_config_contract_sc_subcontract_register_p1_form_business_facts_v1",
    }

    MODEL_VIEWS = {
        "sc.labor.usage": "view_sc_labor_usage_form",
        "sc.equipment.usage": "view_sc_equipment_usage_form",
        "sc.subcontract.register": "view_sc_subcontract_register_form",
    }

    # The create window the native arch declares for the user-typed facts: the
    # interaction face of the same rule the model guard enforces.  871 and 570
    # own an explicit draft window.  575 owns a different, narrower window -
    # `已登记`(active) stays adjustable and only `已关闭`(closed) freezes - so its
    # expression lives in `FACT_FREEZE_EXPRESSION` and is pinned by
    # `test_the_subcontract_register_freezes_only_after_closing`.
    NATIVE_DRAFT_WINDOW = {
        "view_sc_labor_usage_form": (
            "project_id", "usage_date", "usage_type", "labor_team", "contractor_id",
            "worker_qty", "work_hours", "currency_id", "price_unit", "work_type",
            "construction_part", "work_content",
        ),
        "view_sc_equipment_usage_form": (
            "project_id", "usage_date", "equipment_name", "equipment_code",
            "specification", "uom_text", "usage_location", "operator_name",
            "usage_qty", "usage_hours", "supplier_id", "currency_id", "price_unit",
        ),
    }

    # The arch expression that renders each model's freeze window, i.e. the states
    # in which the delivered model refuses a write to the facts the user enters.
    # 871/570 close the window everywhere outside the create state; 575 freezes
    # only `已关闭`, because `已登记` is still a legal settlement anchor and a
    # correction there is a real adjustment, not a historical rewrite.
    FACT_FREEZE_EXPRESSION = {
        "sc.labor.usage": "state != 'draft'",
        "sc.equipment.usage": "state != 'draft'",
        "sc.subcontract.register": "state == 'closed'",
    }

    # Basis facts stay writable after submission on both guarded models: they are
    # evidence the user completes while the record waits, not the measured fact.
    DRAFT_WINDOW_EXEMPT_FACTS = ("note", "attachment_ids")

    def _policy_fields(self, model):
        return [
            row for row in (self._form_spec(self._contract(self.POLICY_CARRIERS[model])).get("fields") or [])
            if isinstance(row, dict) and row.get("name")
        ]

    def _policy_readonly(self, model):
        return {row["name"] for row in self._policy_fields(model) if row.get("readonly")}

    def _arch_readonly(self, view_xmlid):
        """Direct `<field>` read-only expressions declared by the delivered arch."""
        arch = self._arch(view_xmlid)
        return {
            node.get("name"): node.get("readonly")
            for node in arch.iter("field")
            if node.get("name") and node.get("readonly")
        }

    @staticmethod
    def _legal_carrier(model, name):
        """The delivered definition's own answer to "who supplies this value?".

        Returns a carrier name when the model can supply the fact without the
        user typing it, and `None` when only the user can.
        """
        field = model._fields[name]
        if field.compute:
            return "computed"
        if name in ("create_date", "write_date", "create_uid", "write_uid"):
            return "system"
        if field.default is not None:
            return "sequence" if name == "name" else "default"
        if field.readonly:
            return "history"
        return None

    def test_the_readonly_policy_keeps_only_facts_with_a_legal_carrier(self):
        """The policy may only stay read-only where something else supplies the value.

        The delivered create-state defect was exactly this: the same declaration
        marked `project_id` required and unconditionally read-only, so the create
        page offered 提交 with no legal path to the project.
        """
        for model, _xmlid in self.POLICY_CARRIERS.items():
            declared = {row["name"] for row in self._policy_fields(model)}
            user_facts = set(self.USER_SUPPLIED_FACTS[model])
            carried = set(self.FACT_CARRIERS[model])
            fields = self.env[model]._fields
            with self.subTest(model=model):
                self.assertEqual(user_facts & carried, set(), "a fact belongs to one class only")
                self.assertEqual(user_facts | carried, declared, "every declared fact is classified")
                for name in sorted(user_facts):
                    self.assertFalse(fields[name].readonly, "%s must be writable on the model" % name)
                    self.assertFalse(fields[name].compute, "%s must not be computed" % name)
                    # The value the user must be able to enter may not be locked by the
                    # policy carrier.  A model default is not an exemption here: `default`
                    # makes entry cheaper, it does not replace the control, so a fact in
                    # this set stays out of the read-only policy.
                    self.assertNotIn(
                        name, self._policy_readonly(model),
                        "a fact the user must enter may not stay read-only by policy",
                    )
                for name in sorted(carried):
                    self.assertIsNotNone(
                        self._legal_carrier(self.env[model], name),
                        "%s is declared carried but nothing in the model supplies it" % name,
                    )
                self.assertEqual(
                    self._policy_readonly(model),
                    set(self.EXPECTED_READONLY_POLICY[model]),
                    "the retained carrier must keep exactly the justified read-only facts",
                )
                self.assertEqual(
                    set(self.EXPECTED_READONLY_POLICY[model]) & user_facts, set(),
                    "a user-supplied fact may not stay read-only",
                )

    def test_every_required_create_fact_is_obtainable_by_a_legal_path(self):
        """`必需值是否可通过合法路径取得`, not `必填 ∩ 可填`.

        A required fact is obtainable when the user can type it - the delivered
        create policy and the native arch both leave it authorable - or when a
        legal non-user carrier supplies it.  A required fact supplied by nobody
        is the defect this batch repaired, whether or not it is required at all:
        the read-only policy and the REQUIRED marker came from the same
        declaration, so the two could not both hold.
        """
        for model, view_xmlid in self.MODEL_VIEWS.items():
            arch_readonly = self._arch_readonly(view_xmlid)
            policy_readonly = self._policy_readonly(model)
            declared = {row["name"] for row in self._policy_fields(model)}
            fields = self.env[model]._fields
            # The inline detail tree renders columns owned by the detail model
            # (`line_ids.contract_qty` and friends); only facts this form's own
            # model owns can be judged on its create surface.
            surface = {
                name for name in (declared | set(self.RENDERED_FIELDS[view_xmlid]))
                if name in fields
            }
            for name in sorted(surface):
                if not fields[name].required:
                    continue
                with self.subTest(model=model, fact=name):
                    carrier = self._legal_carrier(self.env[model], name)
                    if carrier is None:
                        self.assertNotIn(
                            name, policy_readonly,
                            "required {0} has no carrier and may not stay read-only by policy".format(name),
                        )
                        self.assertNotEqual(
                            arch_readonly.get(name), "1",
                            "required {0} has no carrier and may not be unconditionally read-only".format(name),
                        )
                    else:
                        self.assertTrue(
                            carrier in ("computed", "default", "sequence", "system", "workflow", "history"),
                            "%s carries an unknown carrier %s" % (name, carrier),
                        )

    def test_the_native_arch_opens_the_draft_window_for_the_user_facts(self):
        """Interaction face and backend guard must declare the same window."""
        for view_xmlid, names in self.NATIVE_DRAFT_WINDOW.items():
            arch_readonly = self._arch_readonly(view_xmlid)
            for name in names:
                with self.subTest(view=view_xmlid, fact=name):
                    self.assertEqual(
                        arch_readonly.get(name), "state != 'draft'",
                        "%s must be editable inside the draft window" % name,
                    )
        for view_xmlid, names in self.NATIVE_DRAFT_WINDOW.items():
            arch_readonly = self._arch_readonly(view_xmlid)
            for name in self.DRAFT_WINDOW_EXEMPT_FACTS:
                with self.subTest(view=view_xmlid, fact=name):
                    self.assertNotIn(name, arch_readonly, "basis facts stay writable after submission")
        # 575: `已登记` is not automatically `不可修改` - the delivered rule locks the
        # register's facts and its detail lines in `已关闭` only.  The arch may
        # therefore render exactly one conditional window, it must be
        # `state == 'closed'`, and it must name the model's own frozen facts; the
        # basis facts stay outside it.  The runtime behaviour is pinned by
        # test_the_subcontract_register_freezes_only_after_closing.
        register_window = self._arch_readonly("view_sc_subcontract_register_form")
        with self.subTest(view="view_sc_subcontract_register_form", surface="window"):
            self.assertEqual(
                {
                    name: expr for name, expr in register_window.items()
                    if expr and expr != "1" and expr != "state == 'closed'"
                },
                {},
                "575 may lock facts only in 已关闭; 已登记 stays adjustable",
            )
            self.assertEqual(
                {name for name, expr in register_window.items() if expr == "1"},
                {"processing_advisory"},
                "no user fact stays unconditionally read-only on the delivered arch",
            )
            self.assertEqual(
                {name for name, expr in register_window.items() if expr == "state == 'closed'"},
                set(self.env["sc.subcontract.register"]._FACT_IMMUTABLE_FIELDS),
                "the arch window and the model freeze must name the same facts",
            )
        for name in self.DRAFT_WINDOW_EXEMPT_FACTS + ("management_note", "name"):
            with self.subTest(view="view_sc_subcontract_register_form", fact=name):
                self.assertNotIn(
                    "state", register_window.get(name, ""),
                    "%s is a basis fact and stays writable after closing" % name,
                )

    def test_the_policy_never_locks_a_fact_the_model_treats_as_user_entered(self):
        """`配置策略` may not contradict `模型约束` about who enters the fact.

        The observed defect chain is 原生声明 -> 模型约束 -> 配置策略 -> 最终契约
        -> 控件.  `_FACT_IMMUTABLE_FIELDS` is the model's own definition of the
        facts the user enters and the backend then freezes, and the native arch
        declares the same window (`readonly="state != 'draft'"` on 871/570,
        `readonly="state == 'closed'"` on 575 - see `FACT_FREEZE_EXPRESSION`).  A
        read-only policy on a fact inside that window is therefore the first
        divergence, and it survived because the two declarations were never
        compared.  `usage_type` was the observed case: the older p1 carrier locked
        it unconditionally while the model guard and the arch both treated it as a
        draft-window fact, so the create page rendered it read-only while the
        delivered status contract still called it authorable - the internal
        contradiction the user measured.
        """
        compared = 0
        for model, view_xmlid in self.MODEL_VIEWS.items():
            guard = getattr(self.env[model], "_FACT_IMMUTABLE_FIELDS", None)
            if guard is None:
                continue
            compared += 1
            expression = self.FACT_FREEZE_EXPRESSION[model]
            arch_readonly = self._arch_readonly(view_xmlid)
            window = {name for name, expr in arch_readonly.items() if expr == expression}
            with self.subTest(model=model):
                self.assertEqual(
                    self._policy_readonly(model) & set(guard), set(),
                    "a fact the model treats as user-entered may not stay read-only by policy",
                )
                self.assertEqual(
                    set(guard) - window, set(),
                    "every fact the model freezes must render the same window in the native arch",
                )
                self.assertEqual(
                    set(self.USER_SUPPLIED_FACTS[model]) - set(guard),
                    set(self.DRAFT_WINDOW_EXEMPT_FACTS) & set(self.USER_SUPPLIED_FACTS[model]),
                    "only the basis facts stay outside the model's own freeze window",
                )
        self.assertEqual(
            compared, 3, "871, 570 and 575 each declare a fact freeze with its window",
        )
        self.assertEqual(
            set(self.FACT_FREEZE_EXPRESSION) - set(self.MODEL_VIEWS), set(),
            "every declared freeze window names a governed create surface",
        )
        # Closed by the window alignment: the residual used to be `request_id`,
        # which 570's arch locked inside the draft window while the guard did not
        # freeze it.  The comparison stays so the two declarations cannot drift
        # apart again silently.
        residual = {name for name, expr in self._arch_readonly("view_sc_equipment_usage_form").items()
                    if expr == "state != 'draft'"} - set(self.env["sc.equipment.usage"]._FACT_IMMUTABLE_FIELDS)
        self.assertEqual(residual, set())

    def test_the_prompt_is_feedback_not_a_section(self):
        """The computed 办理提示 is auxiliary feedback, never a business section.

        A `<page>`/`<group>` host promotes it to a section with its own
        navigation entry, and an empty compute then renders as a placeholder
        "—" inside a business section.  The feedback surface is not a group, so
        it can never become a section, and it hides itself while the compute has
        nothing to act on.  Convention and positive examples:
        `test_context_workspace_native_lowcode.py::test_the_prompt_is_feedback_not_a_section`,
        `views/support/current_account_workspace_views.xml`.
        """
        def assert_feedback_surface(root, label):
            self.assertFalse(root.xpath(".//group[field[@name='processing_advisory']]"), label)
            self.assertFalse(root.xpath(".//page[field[@name='processing_advisory']]"), label)
            hosts = root.xpath(".//div[field[@name='processing_advisory']]")
            self.assertEqual(len(hosts), 1, label)
            host = hosts[0]
            classes = set((host.get("class") or "").split())
            self.assertIn("alert", classes, label)
            self.assertIn("alert-info", classes, label)
            self.assertEqual(host.get("role"), "status", label)
            self.assertEqual(host.get("invisible"), "not processing_advisory", label)
            node = host.xpath("./field[@name='processing_advisory']")[0]
            self.assertEqual(node.get("readonly"), "1", label)
            self.assertEqual(node.get("nolabel"), "1", label)

        for view_xmlid in ("view_sc_equipment_usage_form", "view_sc_subcontract_register_form"):
            with self.subTest(view=view_xmlid):
                assert_feedback_surface(self._arch(view_xmlid), view_xmlid)
        inherited = self.env.ref(
            "smart_construction_core.view_sc_labor_usage_product_advisory_form"
        )
        with self.subTest(view="view_sc_labor_usage_product_advisory_form"):
            assert_feedback_surface(
                etree.fromstring(inherited.arch.encode("utf-8")),
                "view_sc_labor_usage_product_advisory_form",
            )

    def test_no_empty_notebook_page_is_declared(self):
        """An empty 来源追溯 page owned a navigation entry with nothing behind it."""
        for view_xmlid in self.MODEL_VIEWS.values():
            root = self._arch(view_xmlid)
            empty = [
                page.get("string") for page in root.xpath(".//page")
                if not page.xpath(".//field")
            ]
            with self.subTest(view=view_xmlid):
                self.assertEqual(empty, [])
                self.assertFalse(root.xpath(".//page[@string='来源追溯']"))

    def test_the_labor_usage_guard_matches_the_declared_draft_window(self):
        """The read-only window is only real if the backend refuses the write."""
        project = self.env["project.project"].search([], limit=1)
        self.assertTrue(project, "the governed database must carry a project")
        usage = self.env["sc.labor.usage"].create({
            "project_id": project.id,
            "labor_team": "G09 可办理性班组",
            "work_content": "G09 可办理性验证",
            "worker_qty": 2.0,
            "work_hours": 4.0,
        })
        self.assertEqual(
            usage._FACT_IMMUTABLE_FIELDS,
            {"project_id", "usage_type", "usage_date", "labor_team", "contractor_id",
             "work_type", "construction_part", "work_content", "worker_qty",
             "work_hours", "price_unit", "currency_id"},
        )
        # The draft window is open: the record may be corrected before it is sent.
        usage.write({"worker_qty": 3.0, "work_hours": 6.0})
        usage.write({"note": "草稿修正说明"})
        self.assertEqual(usage.worker_qty, 3.0)
        usage.action_submit()
        self.assertEqual(usage.state, "submitted")
        with self.assertRaises(UserError):
            usage.write({"worker_qty": 4.0})
        with self.assertRaises(UserError):
            usage.write({"work_content": "提交后改写"})
        with self.assertRaises(UserError):
            usage.unlink()
        # Basis facts are not measured facts: the user completes them while the
        # record waits for confirmation.
        usage.write({"note": "提交后补充依据", "attachment_ids": [(6, 0, [])]})
        # The 退回 leg of the delivered flow: a submitted record may be cancelled,
        # but it gives up its window with it - the arch renders `state != 'draft'`
        # read-only and the backend must refuse the same write instead of leaving
        # an API-only gap behind the page.
        usage.action_cancel()
        self.assertEqual(usage.state, "cancel")
        with self.assertRaises(UserError):
            usage.write({"work_content": "取消后改写"})
        with self.assertRaises(UserError):
            usage.unlink()
        # The sanctioned way back to the window is the business action, not a write.
        usage.action_reset_draft()
        self.assertEqual(usage.state, "draft")
        usage.write({"work_content": "退回草稿后修正"})
        self.assertEqual(usage.work_content, "退回草稿后修正")
        usage.action_submit()
        usage.action_confirm()
        self.assertEqual(usage.state, "confirmed")
        with self.assertRaises(UserError):
            usage.write({"price_unit": 12.0})
        # `cancel` is only reachable from draft/submitted, so a confirmed record
        # keeps that refusal too (the delivered flow rule, not a new lock).
        with self.assertRaises(UserError):
            usage.action_cancel()

    def test_the_labor_usage_state_is_only_advanced_by_a_business_action(self):
        """A fact guard with an unguarded `state` is not a guard.

        `state` is not a business fact, so the fact set cannot cover it.  Without
        a transition guard, one `write({"state": "draft"})` re-opens the window a
        submitted or confirmed record had already left, and the fact guard becomes
        decorative.  570 `sc.equipment.usage` refuses the same write through the
        shared cost-source token; this entry now shares that mechanism.
        """
        project = self.env["project.project"].search([], limit=1)
        self.assertTrue(project, "the governed database must carry a project")
        usage = self.env["sc.labor.usage"].create({
            "project_id": project.id,
            "labor_team": "G09 状态守卫班组",
            "work_content": "G09 状态守卫验证",
            "worker_qty": 1.0,
            "work_hours": 1.0,
        })
        # A raw state write is refused in every state, including the reopening one.
        with self.assertRaises(UserError):
            usage.write({"state": "submitted"})
        usage.action_submit()
        self.assertEqual(usage.state, "submitted")
        with self.assertRaises(UserError):
            usage.write({"state": "draft"})
        self.assertEqual(usage.state, "submitted")
        with self.assertRaises(UserError):
            usage.write({"state": "draft", "worker_qty": 9.0})
        usage.invalidate_recordset()
        self.assertEqual(usage.state, "submitted")
        self.assertEqual(usage.worker_qty, 1.0)
        # The business actions still move the state through the sanctioned path,
        # and they keep their own flow rules (`已确认` may not be cancelled late).
        usage.action_confirm()
        self.assertEqual(usage.state, "confirmed")
        with self.assertRaises(UserError):
            usage.action_cancel()
        self.assertEqual(usage.state, "confirmed")

    def test_the_labor_usage_guard_covers_the_record_creation_entry(self):
        """The transition guard has to hold on `create()`, not only on `write()`.

        Fact writes go through `write()`, but a record can also enter the table
        already outside the draft window: `create({"state": "confirmed", ...})`
        plants one without ever passing the fact guard or a business action.  570
        `sc.equipment.usage` refuses the same values through the shared
        cost-source token, so the two entries share the mechanism.

        `copy()` is the other creation entry and is deliberately not part of the
        hole: `state.copy` is `False` on the delivered model, so a copy of a
        confirmed record lands as a new `draft` (facts copied, state defaulted)
        instead of resurrecting the moved-on record.  That is platform behaviour
        and is pinned here so a later reader does not mistake `copy()` for a
        second bypass.
        """
        project = self.env["project.project"].search([], limit=1)
        self.assertTrue(project, "the governed database must carry a project")
        model = self.env["sc.labor.usage"]
        self.assertFalse(model._fields["state"].copy)
        vals = {
            "project_id": project.id,
            "labor_team": "G09 建单守卫班组",
            "work_content": "G09 建单守卫验证",
            "worker_qty": 1.0,
            "work_hours": 1.0,
        }
        # No state means the declared default, and the draft window is open.
        draft = model.create(dict(vals))
        self.assertEqual(draft.state, "draft")
        # Planting a moved-on record is refused at every off-default state.
        with self.assertRaises(UserError):
            model.create(dict(vals, state="submitted"))
        with self.assertRaises(UserError):
            model.create(dict(vals, state="confirmed"))
        self.assertEqual(model.search_count([("labor_team", "=", vals["labor_team"])]), 1)
        # `copy()` cannot land a non-draft state, and it does not touch the source.
        draft.action_submit()
        self.assertEqual(draft.state, "submitted")
        copied = draft.copy()
        self.assertEqual(copied.state, "draft")
        self.assertEqual(copied.work_content, draft.work_content)
        self.assertEqual(draft.state, "submitted")
        with self.assertRaises(UserError):
            copied.write({"state": "confirmed"})

    def test_the_equipment_usage_window_matches_the_native_arch(self):
        """Interaction face and backend guard declare the same window.

        570's arch locks every delivered fact on `state != 'draft'`, but the model
        guard refused a fact write only in `submitted`/`confirmed`, so a `cancel`
        record stayed writable behind a page that rendered it read-only - the same
        divergence 871 carried before it was aligned.  570 now enforces the arch's
        own window, so the former residual is asserted closed rather than pinned
        open.
        """
        guard = self.env["sc.equipment.usage"]._FACT_IMMUTABLE_FIELDS
        arch = self._arch_readonly("view_sc_equipment_usage_form")
        window = {name for name, expr in arch.items() if expr == "state != 'draft'"}
        self.assertTrue(window, "570's arch must open a draft window")
        self.assertEqual(set(guard), window, "the backend window is the arch's window")

    def test_the_equipment_usage_guard_is_retained(self):
        """570's guard keeps acting, on the window its own arch declares.

        The correction does not add a rule the page does not declare: it makes the
        backend refuse exactly what the arch already renders read-only, so the
        window survives the state that used to stay writable behind it.
        """
        project = self.env["project.project"].search([], limit=1)
        self.assertTrue(project, "the governed database must carry a project")
        usage = self.env["sc.equipment.usage"].create({
            "project_id": project.id,
            "equipment_name": "G09 可办理性机械",
            "usage_location": "G09 现场",
            "operator_name": "G09 操作人员",
            "usage_hours": 4.0,
        })
        self.assertEqual(
            usage._FACT_IMMUTABLE_FIELDS,
            {"project_id", "request_id", "usage_date", "equipment_name", "equipment_code",
             "specification", "uom_text", "usage_location", "operator_name",
             "usage_qty", "usage_hours", "supplier_id", "currency_id", "price_unit"},
        )
        usage.write({"usage_hours": 5.0})
        usage.action_submit()
        self.assertEqual(usage.state, "submitted")
        with self.assertRaises(UserError):
            usage.write({"usage_hours": 9.0})
        # Basis facts are not measured facts: the user completes them while the
        # record waits for confirmation.
        usage.write({"note": "提交后补充依据"})
        # The refusal now follows the arch's window, so cancelling does not reopen
        # it; the sanctioned way back is the business action, not a write.
        usage.action_cancel()
        self.assertEqual(usage.state, "cancel")
        with self.assertRaises(UserError):
            usage.write({"usage_hours": 6.0})
        with self.assertRaises(UserError):
            usage.write({"request_id": False})
        with self.assertRaises(UserError):
            usage.unlink()
        usage.action_reset_draft()
        self.assertEqual(usage.state, "draft")
        usage.write({"usage_hours": 6.0})
        self.assertEqual(usage.usage_hours, 6.0)

    def test_the_subcontract_register_freezes_only_after_closing(self):
        """`已登记` is not automatically `不可修改`; `已关闭` is, until `重新打开`.

        This replaces the pin that recorded an absence ("no guard, no state lock,
        rule undecided").  The delivered rule is now defined: the register's facts
        and its detail lines stay writable in `草稿` and `已登记`.  `已登记` keeps
        the window open on purpose - it is still a legal settlement anchor
        (`ScSubcontractSettlement._check_business_anchor` accepts `active` and
        `closed`), so a correction there is a real adjustment, and the cumulative
        registered amount and settlement authority checks are what bound it.
        `已关闭` freezes those facts on both surfaces (model guard + arch window),
        and the only legal way back to an adjustable record is the controlled
        `重新打开` (closed -> active) action, which the model refuses once a
        settlement references the register's detail lines - the same shape as the
        delivered detail-line `unlink()` protection.  The run is exercised with
        rollback-safe throwaway records; nothing is published, and no delivered
        record is touched.
        """
        model = self.env["sc.subcontract.register"]
        self.assertEqual(tuple(model._FACT_IMMUTABLE_STATES), ("closed",))
        self.assertEqual(
            set(model._FACT_IMMUTABLE_FIELDS) & set(self.DRAFT_WINDOW_EXEMPT_FACTS), set(),
            "basis facts are not facts the register freezes",
        )
        project = self.env["project.project"].search([], limit=1)
        self.assertTrue(project, "the governed database must carry a project")
        subcontractor = self.env["res.partner"].create({"name": "G09 已关闭规则分包单位"})
        # 结算关系要求登记单落在正式分包合同上（`_sc_validate_register_pair`）。
        contract = self.env["construction.contract"].create({
            "subject": "G09 已关闭规则分包合同",
            "type": "in",
            "project_id": project.id,
            "partner_id": subcontractor.id,
        })
        register = model.create({
            "project_id": project.id,
            "subcontractor_id": subcontractor.id,
            "contract_id": contract.id,
            "subcontract_scope": "G09 已关闭规则分包范围",
            "line_ids": [(0, 0, {
                "work_scope": "G09 已关闭规则工作范围",
                "contract_qty": 1.0,
                "unit_name": "项",
                "registered_amount": 1000.0,
            })],
        })

        # 状态不是可写字段：与 871／570／材料验收同一条口径，`create()` 与 `write()`
        # 都不能绕过受控动作（否则「已关闭」窗口可被 `write({"state": ...})` 直接掀开）。
        with self.assertRaises(UserError):
            model.create({
                "project_id": project.id,
                "subcontractor_id": subcontractor.id,
                "contract_id": contract.id,
                "subcontract_scope": "G09 非法植入状态",
                "state": "active",
            })
        with self.assertRaises(UserError):
            register.write({"state": "active"})
        self.assertEqual(register.state, "draft")

        # 草稿与已登记都可调整：冻结不是「非草稿」。
        register.write({"subcontract_scope": "G09 草稿可调整范围"})
        register.action_register()
        self.assertEqual(register.state, "active")
        register.write({"subcontract_scope": "G09 已登记可调整范围"})
        line = register.line_ids
        line.write({"work_scope": "G09 已登记可调整工作范围"})
        self.assertEqual(register.subcontract_scope, "G09 已登记可调整范围")
        self.assertEqual(line.work_scope, "G09 已登记可调整工作范围")

        # 已关闭：事实与明细都拒绝写入，记录依据仍可补充。
        register.action_close()
        self.assertEqual(register.state, "closed")
        with self.assertRaises(UserError):
            register.write({"subcontract_scope": "G09 已关闭不可改写"})
        with self.assertRaises(UserError):
            register.write({"line_ids": [(1, line.id, {"work_scope": "G09 已关闭不可改写"})]})
        # 冻结不能只在单头生效：明细模型自身的 create／write／unlink 也是写入路径，
        # 否则「已关闭」窗口可被 `line.write()` 直接绕开（实测旁路，见
        # `tmp/uc4-g09-creatability/575-line-freeze-probe.py`）。
        with self.assertRaises(UserError):
            line.write({"work_scope": "G09 已关闭明细不可改写"})
        with self.assertRaises(UserError):
            line.write({"registered_amount": 999.0})
        with self.assertRaises(UserError):
            self.env["sc.subcontract.register.line"].create({
                "register_id": register.id,
                "work_scope": "G09 已关闭不可补明细",
                "contract_qty": 1.0,
                "registered_amount": 10.0,
            })
        with self.assertRaises(UserError):
            line.unlink()
        self.assertTrue(line.exists(), "冻结的登记明细不得被删除")
        self.assertEqual(line.registered_amount, 1000.0)
        register.write({"note": "G09 已关闭仍可补充依据"})
        self.assertEqual(register.note, "G09 已关闭仍可补充依据")

        # 受控动作回到可调整状态，重开后同一事实再次可写。
        register.action_reopen()
        self.assertEqual(register.state, "active")
        register.write({"subcontract_scope": "G09 重开后仍可调整"})
        self.assertEqual(register.subcontract_scope, "G09 重开后仍可调整")

        # 方法的前置条件：非 `已关闭` 拒绝重开，避免把它当成通用解锁开关。
        with self.assertRaises(UserError):
            register.action_reopen()
        self.assertEqual(register.state, "active")

        # 已被结算引用的登记不可重开：冻结之后不能改写结算依据。
        settlement = self.env["sc.subcontract.settlement"].create({
            "project_id": project.id,
            "subcontractor_id": subcontractor.id,
            "register_id": register.id,
            "line_ids": [(0, 0, {
                "work_scope": "G09 已关闭规则结算范围",
                "register_line_id": line.id,
                "qty": 1.0,
                "unit_price": 100.0,
            })],
        })
        register.action_close()
        self.assertEqual(register.state, "closed")
        with self.assertRaises(UserError):
            register.action_reopen()
        self.assertEqual(register.state, "closed")
        # 受控动作之外的写入路径同样不能把冻结窗口掀开。
        with self.assertRaises(UserError):
            register.write({"state": "active"})
        with self.assertRaises(UserError):
            register.with_context(sc_skip_subcontract_contract_authority=True).write(
                {"state": "active"}
            )
        self.assertEqual(register.state, "closed")
        self.assertTrue(settlement.exists(), "the throwaway settlement is the settlement authority")

    # The delivered `退回草稿` rule names the state each entry accepts the action
    # in: `action_reset_draft` is refused outside `已取消` on every model below, and
    # the native arch header of the same entry renders that same action.  The
    # workflow contract is the second surface - the Vue form reads it through
    # `describe_record()` - so both have to name the same state.
    RESET_TO_DRAFT_ENTRIES = {
        "view_sc_labor_usage_form": "sc.labor.usage",
        "view_sc_equipment_usage_form": "sc.equipment.usage",
        "view_sc_subcontract_register_form": "sc.subcontract.register",
    }

    def test_the_reset_to_draft_action_is_declared_where_it_runs(self):
        """A control the model refuses is not an available action.

        The delivered way back to the draft window is `取消` (`draft`/`submitted`
        -> `cancel`) followed by `退回草稿` (`cancel` -> `draft`).  A contract that
        offers `reopen` in `已提交`/`已登记` ships a button that can only fail, and
        one that omits it in `已取消` hides the only legal return.  The arch header
        and the declared `state_actions` are therefore compared to the model's own
        precondition, and the declared action is then actually run.
        """
        service = self.env["sc.workflow.contract.service"]
        project = self.env["project.project"].search([], limit=1)
        self.assertTrue(project, "the governed database must carry a project")

        labor = self.env["sc.labor.usage"].create({
            "project_id": project.id,
            "labor_team": "G09 回退路径班组",
            "work_content": "G09 回退路径验证",
            "worker_qty": 1.0,
            "work_hours": 1.0,
        })
        equipment = self.env["sc.equipment.usage"].create({
            "project_id": project.id,
            "equipment_name": "G09 回退路径机械",
            "usage_location": "G09 现场",
            "operator_name": "G09 操作人员",
            "usage_hours": 2.0,
        })
        # 575 needs its own business anchor before it can be registered: the
        # delivered `action_register` refuses a register without 分包单位 and 明细.
        subcontractor = self.env["res.partner"].create({"name": "G09 回退路径分包单位"})
        register = self.env["sc.subcontract.register"].create({
            "project_id": project.id,
            "subcontractor_id": subcontractor.id,
            "subcontract_scope": "G09 回退路径分包范围",
            "line_ids": [(0, 0, {"work_scope": "G09 回退路径工作范围"})],
        })

        cases = (
            (labor, labor.action_submit, labor.action_cancel),
            (equipment, equipment.action_submit, equipment.action_cancel),
            (register, register.action_register, register.action_cancel),
        )
        for record, submit, cancel in cases:
            view_xmlid = next(
                key for key, value in self.RESET_TO_DRAFT_ENTRIES.items() if value == record._name
            )
            with self.subTest(model=record._name, surface="arch"):
                buttons = self._arch(view_xmlid).xpath(".//button[@name='action_reset_draft']")
                self.assertEqual(len(buttons), 1, "the 退回草稿 button is declared once")
                self.assertEqual(buttons[0].get("invisible"), "state != 'cancel'")

            with self.subTest(model=record._name, surface="contract"):
                submit()
                record.invalidate_recordset()
                rows = {row["key"]: row for row in service.describe_record(record)["availableActions"]}
                self.assertNotIn(
                    "reopen", rows,
                    "已提交/已登记 may not declare the action the model refuses",
                )
                cancel()
                record.invalidate_recordset()
                self.assertEqual(record.state, "cancel")
                rows = {row["key"]: row for row in service.describe_record(record)["availableActions"]}
                self.assertIn("reopen", rows, "已取消 must declare the only legal return")
                self.assertTrue(rows["reopen"]["enabled"], "the declared action must be enabled")
                self.assertEqual(rows["reopen"]["method"], "action_reset_draft")
                # Declared, and actually runnable: the same record goes back.
                record.action_reset_draft()
                self.assertEqual(record.state, "draft")

    # G09: 871／570／575 是同一族的成本登记入口，办理动作的角色门禁必须同口径。
    # `只读 ⊂ 经办 ⊂ 审批` 是严格蕴含，经办与审批都持 `write` ⇒ 审批分离无法由
    # ACL 或行级规则表达，只能落在方法级门禁与按钮 `groups` 上。任一入口漏掉门禁，
    # 经办即可自审自批，且只读角色会看到「点了必然失败」的按钮。
    OPERATOR_AND_MANAGER = (
        "smart_construction_core.group_sc_cap_project_user",
        "smart_construction_core.group_sc_cap_project_manager",
    )
    MANAGER_ONLY = (
        "smart_construction_core.group_sc_cap_project_manager",
    )
    CAPABILITY_GATED_BUTTONS = {
        "view_sc_labor_usage_form": {
            "action_submit": OPERATOR_AND_MANAGER,
            "action_confirm": MANAGER_ONLY,
            "action_reset_draft": MANAGER_ONLY,
            "action_cancel": OPERATOR_AND_MANAGER,
        },
        "view_sc_equipment_usage_form": {
            "action_submit": OPERATOR_AND_MANAGER,
            "action_confirm": MANAGER_ONLY,
            "action_reset_draft": MANAGER_ONLY,
            "action_cancel": OPERATOR_AND_MANAGER,
        },
        "view_sc_subcontract_register_form": {
            "action_register": MANAGER_ONLY,
            "action_close": MANAGER_ONLY,
            "action_reopen": MANAGER_ONLY,
            "action_reset_draft": MANAGER_ONLY,
            "action_cancel": OPERATOR_AND_MANAGER,
        },
    }

    def test_every_workflow_button_declares_its_capability_gate(self):
        """An ungated header ships the approval to whoever can write the record.

        The three entries of this family share the same capability ladder and the
        same separation of 经办 and 审批, so each header must declare the gate that
        matches the model method it calls.  This pins the buttons to the model's
        own refusals: `action_confirm`／`action_register`／`action_close`／
        `action_reopen`／`action_reset_draft` are manager-only on the model, so they
        are manager-only in the arch as well; `action_submit` and `action_cancel`
        stay available to 经办.
        """
        for view_xmlid, expected in self.CAPABILITY_GATED_BUTTONS.items():
            with self.subTest(view=view_xmlid):
                declared = {}
                for node in self._arch(view_xmlid).xpath(".//button[@type='object']"):
                    name = node.get("name")
                    if name in expected:
                        declared[name] = tuple(
                            group
                            for group in (node.get("groups") or "").split(",")
                            if group
                        )
                self.assertEqual(
                    sorted(declared),
                    sorted(expected),
                    "every workflow button of %s must be declared exactly once" % view_xmlid,
                )
                for name, groups in expected.items():
                    self.assertEqual(
                        sorted(declared[name]),
                        sorted(groups),
                        "%s on %s must declare the same gate as the model method it calls"
                        % (name, view_xmlid),
                    )
