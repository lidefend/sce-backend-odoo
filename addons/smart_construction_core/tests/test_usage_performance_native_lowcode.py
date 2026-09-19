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
            "source_created_at", "source_created_by",
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
    # own an explicit draft window.  575's post-registration rule is still
    # undecided, so this batch declares no state lock there and the pin below
    # records that absence instead of inventing a rule.
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
        # 575: `已登记` is not automatically `不可修改`; the rule is pending, so no
        # state lock is declared here.
        pending = self._arch_readonly("view_sc_subcontract_register_form")
        for name in ("project_id", "note", "subcontract_scope"):
            with self.subTest(view="view_sc_subcontract_register_form", fact=name):
                self.assertNotIn("state", pending.get(name, ""))

    def test_the_policy_never_locks_a_fact_the_model_treats_as_user_entered(self):
        """`配置策略` may not contradict `模型约束` about who enters the fact.

        The observed defect chain is 原生声明 -> 模型约束 -> 配置策略 -> 最终契约
        -> 控件.  `_FACT_IMMUTABLE_FIELDS` is the model's own definition of the
        facts the user enters inside the draft window and the backend then
        freezes; the native arch declares the same window with
        `readonly="state != 'draft'"`.  A read-only policy on a fact inside that
        window is therefore the first divergence, and it survived because the two
        declarations were never compared.  `usage_type` was the observed case: the
        older p1 carrier locked it unconditionally while the model guard and the
        arch both treated it as a draft-window fact, so the create page rendered
        it read-only while the delivered status contract still called it
        authorable - the internal contradiction the user measured.
        """
        compared = 0
        for model, view_xmlid in self.MODEL_VIEWS.items():
            guard = getattr(self.env[model], "_FACT_IMMUTABLE_FIELDS", None)
            if guard is None:
                # 575's post-registration rule is undecided, so there is no guard to
                # contradict.  Pinned by
                # test_the_subcontract_register_post_registration_rule_stays_pending.
                continue
            compared += 1
            arch_readonly = self._arch_readonly(view_xmlid)
            window = {name for name, expr in arch_readonly.items() if expr == "state != 'draft'"}
            with self.subTest(model=model):
                self.assertEqual(
                    self._policy_readonly(model) & set(guard), set(),
                    "a fact the model treats as user-entered may not stay read-only by policy",
                )
                self.assertEqual(
                    set(guard) - window, set(),
                    "every draft-window fact the model freezes must open on the native create surface",
                )
                self.assertEqual(
                    set(self.USER_SUPPLIED_FACTS[model]) - set(guard),
                    set(self.DRAFT_WINDOW_EXEMPT_FACTS),
                    "only the basis facts stay outside the model's own draft window",
                )
        self.assertEqual(compared, 2, "871 and 570 carry the draft-window guard")
        # Recorded, not authorized: 570's arch keeps `request_id` inside the draft
        # window while its retained guard does not freeze it.  This batch reuses
        # 570's guard unchanged (the registered rule for that entry), so the
        # residual is pinned here for the follow-up schedule instead of being
        # silently widened or silently dropped.
        residual = {name for name, expr in self._arch_readonly("view_sc_equipment_usage_form").items()
                    if expr == "state != 'draft'"} - set(self.env["sc.equipment.usage"]._FACT_IMMUTABLE_FIELDS)
        self.assertEqual(residual, {"request_id"})

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

    def test_the_equipment_usage_window_stays_narrower_and_is_pinned(self):
        """570's guard is retained unchanged, so its narrower window is recorded.

        `sc.equipment.usage` refuses a post-submission fact write only in
        `submitted`/`confirmed`, while its arch locks on the wider
        `state != 'draft'`.  This batch is not authorized to add a lock to 570, so
        the divergence is pinned here for the follow-up schedule instead of being
        silently widened or silently dropped.
        """
        guard = self.env["sc.equipment.usage"]._FACT_IMMUTABLE_FIELDS
        arch = self._arch_readonly("view_sc_equipment_usage_form")
        window = {name for name, expr in arch.items() if expr == "state != 'draft'"}
        self.assertTrue(window, "570's arch must open a draft window")
        # 570's backend window is the narrower one and this batch does not widen it.
        self.assertIn("request_id", window - set(guard))

    def test_the_equipment_usage_guard_is_retained(self):
        """570's delivered guard is untouched: the correction adds no new lock."""
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
            {"project_id", "usage_date", "equipment_name", "equipment_code",
             "specification", "uom_text", "usage_location", "operator_name",
             "usage_qty", "usage_hours", "supplier_id", "currency_id", "price_unit"},
        )
        usage.write({"usage_hours": 5.0})
        usage.action_submit()
        self.assertEqual(usage.state, "submitted")
        with self.assertRaises(UserError):
            usage.write({"usage_hours": 9.0})
        usage.write({"note": "提交后补充依据"})

    def test_the_subcontract_register_post_registration_rule_stays_pending(self):
        """`已登记` is not automatically `不可修改`.

        The delivered `sc.subcontract.register.write()` enforces contract
        authority, the cumulative registered amount and the settlement
        authorization; it carries no fact-immutability guard.  The
        `draft/active/closed` edit rule for the register and its detail lines is
        still undecided, so this batch adds no guard and no state lock.  Pinning
        the absence keeps a later batch from reading this file as if the rule had
        been settled here.
        """
        model = self.env["sc.subcontract.register"]
        self.assertFalse(hasattr(model, "_FACT_IMMUTABLE_FIELDS"))
        project = self.env["project.project"].search([], limit=1)
        self.assertTrue(project, "the governed database must carry a project")
        register = model.create({
            "project_id": project.id,
            "subcontract_scope": "G09 可办理性分包范围",
        })
        # No unconditional lock exists: a fact write is not refused by an
        # immutability rule on the delivered model.
        register.write({"note": "G09 可办理性备注"})
        self.assertEqual(register.note, "G09 可办理性备注")
