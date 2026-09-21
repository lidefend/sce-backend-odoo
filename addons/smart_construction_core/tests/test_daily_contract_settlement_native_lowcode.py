# -*- coding: utf-8 -*-
from lxml import etree

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.core.form_structure_authority import (
    diagnose_structure_ownership,
    resolve_form_structure_governance,
    structural_form_declarations,
)


@tagged("post_install", "-at_install", "uc4_native_lowcode")
class TestDailyContractNativeLowcode(TransactionCase):
    """U-C4 G13: 日常合同 (action 687 / menu 663 / view 1757).

    `日常合同` (menu `menu_sc_p1_daily_contract`, list id 663) resolves
    `smart_construction_core.action_sc_general_contract` on `sc.general.contract`.
    The action pins no form view, so it resolves the model primary form
    `view_sc_general_contract_form` (db id 1757).

    Before this batch the entry had **no release of its own**: a repository-wide
    scan of `action_sc_general_contract` in `data/` found no
    `ui.business.config.contract` bound to it, so the only effective carrier was
    the model-level generated mirror 77
    (`sc_general_contract_company_handling_form_v2`, priority 1000, empty
    `action_id`).  Because `form_structure_authority` is derived from a contract
    that declares `composition_mode`, the resolved value stayed `""` and the
    frontend took the compatibility floorplan path - the ledger counted the
    entry even though the native arch already rendered it (measured: 31 business
    fields, no anchors, container tree node-for-node equal to the arch).

    This batch publishes the entry release (title + `native_semantic_surface`
    only) so the entry itself becomes the structure owner of its own action.
    """

    ENTRY_CONTRACT = "business_config_contract_daily_contract_form_native_v1"
    ENTRY_CONTRACT_NAME = "daily_contract_form_native_v1"
    MIRROR_CONTRACT = "business_config_contract_sc_general_contract_form_structure_generated"
    MIRROR_CONTRACT_NAME = "sc_general_contract_company_handling_form_v2"
    ACTION = "action_sc_general_contract"
    ACTION_ID = 687
    VIEW = "view_sc_general_contract_form"
    VIEW_ID = 1757
    MODEL = "sc.general.contract"
    TITLE = "日常合同"
    ENTRY_PRIORITY = 800
    MIRROR_PRIORITY = 1000

    # Sibling entry on the same model and the same native view.  It is not part
    # of the G13 ledger row, so the release must stay scoped to 687.
    SIBLING_ACTION = "action_sc_tier_review_my_general_contract"

    # Business field set the native arch renders, in document order.  Pinned so
    # the batch provably keeps the delivered surface unchanged.
    RENDERED_FIELDS = (
        "contract_name", "contract_no", "contract_type", "contract_direction",
        "project_id", "partner_id", "partner_name_text", "credit_code",
        "contact_name", "contact_phone", "engineering_address", "bank_name",
        "bank_account", "signing_place", "amount_total", "tax_id",
        "amount_untaxed", "currency_id", "payment_terms", "special_condition",
        "contract_date", "expected_sign_date", "completion_date", "pricing_mode",
        "union_mode", "subcontract_mode", "applicant_name", "applicant_department",
        "handler_id", "purchase_engineer", "note",
    )

    # -- helpers -------------------------------------------------------------

    def _contract(self, xmlid):
        return self.env["ui.business.config.contract"].sudo().browse(
            self.ref("smart_construction_core.%s" % xmlid))

    def _entry_contracts(self):
        return self.env["ui.business.config.contract"].sudo()._effective_view_orchestration_contracts(
            self.MODEL, view_type="form", action_id=self.ACTION_ID,
            view_id=self.VIEW_ID, role_key="",
        )

    def _form_spec(self, record):
        return (((record.contract_json or {}).get("view_orchestration") or {})
                .get("views", {}).get("form", {})) or {}

    def _native_contract(self):
        from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler

        action = self.env.ref("smart_construction_core.%s" % self.ACTION)
        result = UiContractV2Handler(
            self.env, su_env=self.env["ir.model"].sudo().env
        ).handle({
            "op": "model", "model": self.MODEL, "action_id": action.id,
            "view_id": self.env.ref("smart_construction_core.%s" % self.VIEW).id,
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
                    yield from TestDailyContractNativeLowcode._walk([child])

    def _rendered_fields(self, data):
        tree = (data.get("layoutContract") or {}).get("containerTree") or []
        seen, ordered = set(), []
        for node in self._walk(tree):
            if node.get("type") != "field":
                continue
            name = node.get("name")
            if name and name not in seen:
                seen.add(name)
                ordered.append(name)
        return tuple(ordered)

    def _arch(self):
        view = self.env.ref("smart_construction_core.%s" % self.VIEW)
        return etree.fromstring(view.arch.encode("utf-8"))

    def _arch_field_names(self):
        seen, ordered = set(), []
        for node in self._arch().iter("field"):
            name = node.get("name")
            if name and name not in seen:
                seen.add(name)
                ordered.append(name)
        return tuple(ordered)

    # -- declaration surface -------------------------------------------------

    def test_the_entry_publishes_the_native_semantic_surface(self):
        record = self._contract(self.ENTRY_CONTRACT)
        self.assertTrue(record.active)
        self.assertEqual(record.status, "published")
        self.assertEqual(record.name, self.ENTRY_CONTRACT_NAME)
        self.assertEqual(record.model, self.MODEL)
        self.assertEqual(record.action_id.id, self.ref("smart_construction_core.%s" % self.ACTION))
        self.assertEqual(record.view_id.id, self.VIEW_ID)
        self.assertEqual(record.priority, self.ENTRY_PRIORITY)
        spec = self._form_spec(record)
        self.assertEqual(spec.get("composition_mode"), "native_semantic_surface")
        self.assertEqual(spec.get("title"), self.TITLE)
        # A native declaration may not carry a competing structure.
        self.assertEqual(structural_form_declarations(spec), {})
        for key in ("sections", "fields", "semantic_anchors", "columns", "layout"):
            self.assertNotIn(key, spec)

    def test_the_entry_semantics_declare_the_fact_authority(self):
        context = ((self._contract(self.ENTRY_CONTRACT).contract_json or {})
                   .get("view_orchestration", {}).get("context", {}))
        self.assertEqual(context.get("source"), "smart_construction_core.product_release")
        self.assertEqual(context.get("source_status"), "product_release")
        self.assertEqual(context.get("fact_authority"), self.MODEL)

    # -- resolution surface --------------------------------------------------

    def test_the_entry_resolves_native_authority(self):
        configs = self._entry_contracts()
        self.assertIn(self.ENTRY_CONTRACT_NAME, [config.name for config in configs])
        resolved = resolve_form_structure_governance({}, configs, view_type="form")
        self.assertEqual(resolved.get("form_structure_authority"), "native_authority")
        self.assertEqual(resolved.get("form_presentation_mode"), "task")
        self.assertFalse(resolved.get("section_titles"))

    def test_the_model_mirror_stays_active_and_its_structure_is_suppressed(self):
        """Mirror 77 is a model-wide carrier, not a mirror of this entry alone.

        It serves the action-less model plane, so the batch may not retire it.
        The measurement records what it becomes instead: the native view owns the
        structure and the mirror's `fields` declaration is reported as
        suppressed rather than as a conflict.
        """
        mirror = self._contract(self.MIRROR_CONTRACT)
        self.assertTrue(mirror.active)
        self.assertEqual(mirror.name, self.MIRROR_CONTRACT_NAME)
        self.assertEqual(mirror.model, self.MODEL)
        self.assertFalse(mirror.action_id)
        self.assertEqual(mirror.priority, self.MIRROR_PRIORITY)
        diagnostics = diagnose_structure_ownership(
            self._entry_contracts(), model=self.MODEL, action_id=self.ACTION_ID)
        codes = {row["code"] for row in diagnostics}
        self.assertEqual(codes, {"LEGACY_STRUCTURE_SUPPRESSED_BY_NATIVE_VIEW"})
        for row in diagnostics:
            with self.subTest(key=row["key"]):
                self.assertEqual(row["configuration"]["name"], self.MIRROR_CONTRACT_NAME)
                self.assertFalse(
                    row["explicit_structure_scope"],
                    "a model-wide mirror is not a scoped competitor",
                )

    def test_the_release_does_not_leak_to_the_sibling_action(self):
        sibling = self.env.ref("smart_construction_core.%s" % self.SIBLING_ACTION)
        configs = self.env["ui.business.config.contract"].sudo()\
            ._effective_view_orchestration_contracts(
                self.MODEL, view_type="form", action_id=sibling.id,
                view_id=self.VIEW_ID, role_key="")
        self.assertNotIn(self.ENTRY_CONTRACT_NAME, [config.name for config in configs])

    # -- rendered surface ----------------------------------------------------

    def test_the_rendered_surface_is_the_native_container_tree(self):
        structure = self._native_contract().get("formStructureContract") or {}
        self.assertEqual(structure.get("layoutPolicy"), "container_tree_authority")
        self.assertEqual(structure.get("mode"), "native_structured_form")
        self.assertFalse(structure.get("slots"))
        self.assertFalse(structure.get("fieldRoles"))
        self.assertFalse(structure.get("sourceSectionTitles"))

    def test_the_rendered_field_set_is_pinned(self):
        data = self._native_contract()
        self.assertEqual(self._rendered_fields(data), self.RENDERED_FIELDS)

    def test_the_arch_declares_every_rendered_business_field(self):
        arch_fields = set(self._arch_field_names())
        for name in self.RENDERED_FIELDS:
            with self.subTest(field=name):
                self.assertIn(name, arch_fields)
                self.assertIn(name, self.env[self.MODEL]._fields)


@tagged("post_install", "-at_install", "uc4_native_lowcode")
class TestDailyContractSettlementNativeLowcode(TransactionCase):
    """U-C4 G13: 日常合同结算 (action 876 / menu 698 / view 1764).

    `日常合同结算` (menu `menu_sc_product_general_contract_settlement_v1`) resolves
    `action_sc_product_general_contract_settlement_v1` on `sc.settlement.order`; the
    action pins no form view, so the entry renders the model primary form
    `view_sc_settlement_order_form` (db id 1764).

    Before this batch the entry resolved `entry_semantic_surface` through
    `daily_contract_settlement_form_v1` (contract 174): 4 declared sections, 30
    field rows (17 of them read-only) and `columns`, with
    `layoutPolicy = business_config_sections` and `mode = business_task_form`.
    A read-only A/B probe of the delivered surface (sc_dev_demo, SAVEPOINT +
    ROLLBACK) showed the rendered container tree came entirely from the native
    view - 10 `data-sc-anchor` business groups and the same field nodes with the
    same conditional read-only/invisible attributes - while the four declared
    section titles only ever entered `sourceSectionTitles`, never the tree.

    This batch therefore retires the structural body and keeps the entry's title,
    its action binding and its `view_orchestration.context` verbatim.  The two
    read-only fields the retirement measured as real regressions
    (`currency_id`, `state`) are restored with a sparse semantic override; of the
    other declared read-only rows, fourteen are already carried by the delivered
    widget profile and the last one (`attachment_count`) never reaches the
    rendered surface at all, so it is recorded as declared-not-rendered rather
    than being asserted as a policy the page carries.
    """

    ENTRY_CONTRACT = "business_config_contract_daily_contract_settlement_form_v1"
    ENTRY_CONTRACT_NAME = "daily_contract_settlement_form_v1"
    RETIRED_MIRROR_CONTRACT = "business_config_contract_sc_settlement_order_form_structure_generated"
    RETIRED_MIRROR_NAME = "sc_settlement_order_form_structure_generated_v1"
    ACTION = "action_sc_product_general_contract_settlement_v1"
    ACTION_ID = 876
    VIEW = "view_sc_settlement_order_form"
    VIEW_ID = 1764
    MODEL = "sc.settlement.order"
    TITLE = "日常合同结算"
    ENTRY_PRIORITY = 800

    # Sibling entry on the same model and the same native view, with its own
    # released compatibility surface (contract 195, 9 sections).  It is a
    # different ledger row, so this batch must leave it alone.
    SIBLING_ACTION = "action_sc_settlement_order"
    SIBLING_CONTRACT_NAME = "settlement_order_productized_form_v1"
    SIBLING_SECTION_COUNT = 9

    # Section titles the retired body declared.  The probe showed they never
    # reached the rendered container tree, so they are recorded as declared but
    # not rendered instead of being migrated into the arch.
    DECLARED_NOT_RENDERED_SECTIONS = (
        "办理主信息", "项目与日常合同", "结算金额与明细", "办理依据",
    )

    # Read-only policy the retired body declared that the delivered widget
    # profile already carries on its own; the sparse override must not repeat
    # these.  `attachment_count` is deliberately absent: the native arch never
    # renders that field, so it is pinned as declared-not-rendered below.
    NATIVE_READONLY_FIELDS = (
        "validation_status", "name", "settlement_flow_label", "settlement_type",
        "operation_strategy", "contract_source_kind", "source_contract_name",
        "source_contract_no", "company_id", "amount_total", "amount_paid",
        "amount_payable", "compliance_state", "compliance_message",
    )
    # Declared read-only by the retired body but absent from the native surface.
    DECLARED_NOT_RENDERED_FIELDS = ("attachment_count",)
    # The measured regressions the sparse semantic override restores.
    SPARSE_READONLY_FIELDS = ("currency_id", "state")

    # Anchored native business sections of the shared settlement form.
    NATIVE_SECTIONS = (
        ("settlement-business-object", "项目与合同相对方"),
        ("settlement-basis", "结算依据"),
        ("settlement-detail-amount", "结算明细与金额"),
        ("settlement-handling", "办理说明"),
        ("settlement-execution", "执行与匹配"),
        ("settlement-invoice", "发票信息"),
        ("settlement-payment-requests", "付款申请"),
        ("settlement-adjustments", "扣款调整"),
        ("settlement-purchase-orders", "采购订单"),
        ("settlement-system-identity", "系统办理信息"),
    )

    # Rendered business field set, in document order, de-duplicated.
    RENDERED_FIELDS = (
        "validation_status", "can_review", "state", "currency_id",
        "settlement_stage", "compliance_state", "business_category_id",
        "project_id", "contract_source_kind", "contract_id",
        "general_contract_id", "source_contract_name", "source_contract_no",
        "partner_id", "settlement_unit_id", "operation_strategy", "company_id",
        "title", "settlement_category_id", "settlement_stage_id",
        "document_date", "date_settlement", "settlement_period_start",
        "settlement_period_end", "planned_settlement_date", "declared_date",
        "final_approved_date", "approved_date", "line_ids", "settlement_amount",
        "amount_total", "submitted_amount", "approved_amount", "deduction_amount",
        "settlement_description", "note", "attachment_ids", "compliance_message",
        "requested_fund_amount", "amount_paid", "unpaid_amount", "amount_payable",
        "invoice_amount", "adjustment_total", "amount_after_adjustment",
        "invoice_ref", "invoice_date", "payment_request_ids",
        "payment_request_line_ids", "adjustment_ids", "purchase_order_ids",
        "name", "settlement_flow_label", "settlement_type",
    )

    # -- helpers -------------------------------------------------------------

    def _contract(self, xmlid):
        return self.env["ui.business.config.contract"].sudo().browse(
            self.ref("smart_construction_core.%s" % xmlid))

    def _entry_contracts(self, action_id=None, view_id=None):
        return self.env["ui.business.config.contract"].sudo()._effective_view_orchestration_contracts(
            self.MODEL, view_type="form",
            action_id=self.ACTION_ID if action_id is None else action_id,
            view_id=self.VIEW_ID if view_id is None else view_id, role_key="",
        )

    def _form_spec(self, record):
        return (((record.contract_json or {}).get("view_orchestration") or {})
                .get("views", {}).get("form", {})) or {}

    def _native_contract(self, action_id=None, view_id=None):
        from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler

        action_id = self.ACTION_ID if action_id is None else action_id
        view_id = self.VIEW_ID if view_id is None else view_id
        result = UiContractV2Handler(
            self.env, su_env=self.env["ir.model"].sudo().env
        ).handle({
            "op": "model", "model": self.MODEL, "action_id": action_id,
            "view_id": view_id, "view_type": "form", "render_profile": "edit",
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
                    yield from TestDailyContractSettlementNativeLowcode._walk([child])

    def _rendered_fields(self, data):
        tree = (data.get("layoutContract") or {}).get("containerTree") or []
        seen, ordered = set(), []
        for node in self._walk(tree):
            if node.get("type") != "field":
                continue
            name = node.get("name")
            if name and name not in seen:
                seen.add(name)
                ordered.append(name)
        return tuple(ordered)

    def _rendered_readonly(self, data, names):
        seen = {}
        tree = (data.get("layoutContract") or {}).get("containerTree") or []
        for node in self._walk(tree):
            name = node.get("name")
            if node.get("type") == "field" and name in names:
                seen.setdefault(name, []).append(bool(node.get("readonly")))
        return seen

    def _widget_readonly(self, data):
        """Delivered readonly decision per business field.

        The frontend resolves a field's readonly state from this profile first
        and only falls back to the container node flag, so this is the carrier
        the reader observes for a policy the native arch already owns.  The
        container node flag is reserved here for the sparse semantic override.
        """
        rows = (data.get("statusContract") or {}).get("widgetStatus") or []
        profile = {}
        for row in rows:
            widget_id = str(row.get("widgetId") or "")
            if widget_id.startswith("field."):
                profile.setdefault(widget_id.split(".")[1], bool(row.get("readonly")))
        return profile

    def _arch(self):
        view = self.env.ref("smart_construction_core.%s" % self.VIEW)
        return etree.fromstring(view.arch.encode("utf-8"))

    def _arch_sections(self):
        return tuple((group.get("data-sc-anchor"), group.get("string"))
                     for group in self._arch().iter("group") if group.get("data-sc-anchor"))

    # -- declaration surface -------------------------------------------------

    def test_the_entry_retires_the_legacy_structure_body(self):
        record = self._contract(self.ENTRY_CONTRACT)
        self.assertTrue(record.active)
        self.assertEqual(record.status, "published")
        self.assertEqual(record.name, self.ENTRY_CONTRACT_NAME)
        self.assertEqual(record.model, self.MODEL)
        self.assertEqual(record.priority, self.ENTRY_PRIORITY)
        spec = self._form_spec(record)
        self.assertEqual(spec.get("composition_mode"), "native_semantic_surface")
        self.assertEqual(spec.get("title"), self.TITLE)
        for key in ("sections", "columns", "cols", "layout", "semantic_anchors"):
            self.assertNotIn(key, spec)
        # A sparse field override is a semantic annotation, not a structure.
        self.assertEqual(structural_form_declarations(spec), {})

    def test_the_entry_keeps_its_action_binding_and_context(self):
        record = self._contract(self.ENTRY_CONTRACT)
        self.assertEqual(record.action_id.id, self.ref("smart_construction_core.%s" % self.ACTION))
        context = ((record.contract_json or {})
                   .get("view_orchestration", {}).get("context", {}))
        self.assertEqual(context.get("source"), "smart_construction_core.product_release")
        self.assertEqual(context.get("source_status"), "product_release")
        self.assertEqual(context.get("fact_authority"), self.MODEL)
        self.assertEqual(context.get("contract_source_authority"), "sc.general.contract")

    def test_the_sparse_override_lists_only_the_measured_regressions(self):
        spec = self._form_spec(self._contract(self.ENTRY_CONTRACT))
        rows = spec.get("fields") or []
        self.assertEqual([row.get("name") for row in rows], list(self.SPARSE_READONLY_FIELDS))
        for row in rows:
            with self.subTest(field=row.get("name")):
                self.assertTrue(row.get("readonly"))
                self.assertLessEqual(set(row), {"name", "readonly"})

    # -- resolution surface --------------------------------------------------

    def test_the_entry_resolves_native_authority(self):
        configs = self._entry_contracts()
        resolved = resolve_form_structure_governance({}, configs, view_type="form")
        self.assertEqual(resolved.get("form_structure_authority"), "native_authority")
        self.assertEqual(resolved.get("form_presentation_mode"), "task")
        self.assertFalse(resolved.get("section_titles"))
        diagnostics = diagnose_structure_ownership(
            configs, model=self.MODEL, action_id=self.ACTION_ID)
        self.assertFalse(diagnostics)

    def test_the_pre_retired_generated_mirror_is_not_an_owner_again(self):
        """Mirror 122 was retired before this batch and must stay retired.

        The ledger row still names it as a competing owner; the runtime shows the
        retirement is already in place, so this batch measures it instead of
        re-retiring it.
        """
        mirror = self._contract(self.RETIRED_MIRROR_CONTRACT)
        self.assertEqual(mirror.name, self.RETIRED_MIRROR_NAME)
        self.assertEqual(mirror.model, self.MODEL)
        self.assertFalse(mirror.active)
        self.assertNotIn(mirror.name, [config.name for config in self._entry_contracts()])

    def test_the_sibling_settlement_entry_keeps_its_own_compatibility_surface(self):
        sibling = self.env.ref("smart_construction_core.%s" % self.SIBLING_ACTION)
        configs = self._entry_contracts(action_id=sibling.id)
        names = [config.name for config in configs]
        self.assertEqual(names, [self.SIBLING_CONTRACT_NAME])
        spec = self._form_spec(self._contract("business_config_contract_settlement_order_productized_form_v1"))
        self.assertEqual(spec.get("composition_mode"), "entry_semantic_surface")
        self.assertEqual(len(spec.get("sections") or []), self.SIBLING_SECTION_COUNT)
        self.assertNotIn(self.ENTRY_CONTRACT_NAME, names)

    # -- rendered surface ----------------------------------------------------

    def test_the_rendered_surface_is_the_native_container_tree(self):
        structure = self._native_contract().get("formStructureContract") or {}
        self.assertEqual(structure.get("layoutPolicy"), "container_tree_authority")
        self.assertEqual(structure.get("mode"), "native_structured_form")
        self.assertFalse(structure.get("slots"))
        self.assertFalse(structure.get("sourceSectionTitles"))
        self.assertFalse(structure.get("fieldRoles"))

    def test_the_rendered_field_set_is_pinned(self):
        self.assertEqual(self._rendered_fields(self._native_contract()), self.RENDERED_FIELDS)

    def test_the_native_arch_declares_every_business_section_identity(self):
        self.assertEqual(self._arch_sections(), self.NATIVE_SECTIONS)

    def test_the_declared_sections_never_reach_the_page(self):
        data = self._native_contract()
        structure = data.get("formStructureContract") or {}
        self.assertFalse(structure.get("sourceSectionTitles"))
        arch_strings = {node.get("string") for node in self._arch().iter()
                        if node.get("string")}
        self.assertFalse(arch_strings & set(self.DECLARED_NOT_RENDERED_SECTIONS))

    def test_the_retired_readonly_policy_survives_on_the_native_surface(self):
        data = self._native_contract()
        readonly = self._rendered_readonly(data, self.SPARSE_READONLY_FIELDS)
        self.assertEqual(sorted(readonly), sorted(self.SPARSE_READONLY_FIELDS))
        for name, flags in readonly.items():
            with self.subTest(field=name):
                self.assertTrue(flags and all(flags))
        # The arch carries the rest of the retired read-only policy on its own.
        self.assertFalse(set(self.NATIVE_READONLY_FIELDS) & set(self.SPARSE_READONLY_FIELDS))
        profile = self._widget_readonly(data)
        for name in self.NATIVE_READONLY_FIELDS:
            with self.subTest(field=name):
                self.assertIn(name, profile)
                self.assertTrue(profile[name])
        for name in self.DECLARED_NOT_RENDERED_FIELDS:
            with self.subTest(field=name):
                self.assertNotIn(name, profile)
                self.assertNotIn(name, self._rendered_fields(data))

    def test_the_sparse_override_does_not_become_a_second_structure_owner(self):
        """The override restores policy without reopening the compatibility path."""
        data = self._native_contract()
        structure = data.get("formStructureContract") or {}
        self.assertEqual(structure.get("layoutPolicy"), "container_tree_authority")
        provenance = structure.get("sourceAuthority", {}).get("governance_source", {})
        self.assertEqual(provenance.get("configuredSections"), [])
        self.assertFalse(provenance.get("legacyFieldPolicyOverlay"))
        self.assertFalse(provenance.get("formLayoutOverlay"))
