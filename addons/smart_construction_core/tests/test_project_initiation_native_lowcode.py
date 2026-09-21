# -*- coding: utf-8 -*-
from lxml import etree

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.core.form_structure_authority import (
    diagnose_structure_ownership,
    resolve_form_structure_governance,
    structural_form_declarations,
)


@tagged("post_install", "-at_install", "uc4_native_lowcode")
class TestProjectInitiationNativeLowcode(TransactionCase):
    """U-C4 G12: 项目立项 原生结构迁移 (action 724 / menu 379 / view 1503).

    The entry `新项目立项` (menu 379) resolves action
    `smart_construction_core.action_project_initiation` on `project.project`,
    which fixes view `project.project.form.sc.create`
    (`smart_construction_core.view_project_create_form`, db id 1503).

    Before this batch the entry resolved `entry_semantic_surface` through
    `project_project_form_structure_v1` (contract 139): 11 section titles, 54
    field rows (25 of them `visible: false`) and two `semantic_anchors`, with
    `layoutPolicy = business_config_sections` and `mode = business_task_form`.
    A read-only probe of the delivered surface (sc_dev_demo, SAVEPOINT +
    ROLLBACK) showed the rendered container tree and field set came entirely
    from the native view - 12 fields in 3 titled business groups, with 3
    untitled nested groups under two of them.  Nine of the eleven declared
    sections carried no field at all and the 25 hidden fields were not in the
    tree, so the declaration never reached the page.

    This batch therefore moves the entry's own section identities
    (`current_task` / `intake_risk`) and the field label it declared
    (`manager_id` = 项目负责人) into the native arch, and retires the
    structural body: the entry keeps `title` + `composition_mode:
    native_semantic_surface` at priority 800.

    The declared mirror `project_project_form_structure_generated_v1`
    (contract 46) is the reason the retirement cannot be partial: it is bound
    to the SAME action and view, so leaving it active makes it the last
    structure writer for this surface, which the ownership diagnosis refuses as
    a scoped conflict (measured: the rendered payload stops resolving
    altogether).  It is a mirror of this one entry, not the sole carrier of any
    action-less surface, so it is retired with it through the existing
    `<function model="ui.business.config.contract" name="write">` pattern.

    The rendered field set is unchanged by this batch (the same 12 rows, none
    added or removed); what changes is the grouping - untitled nested groups are
    promoted to anchored business sections.  The native arch is the ground truth
    and `RENDERED_FIELDS` pins it, so a retired declaration cannot silently drop
    a fact.
    """

    ENTRY_CONTRACT = "business_config_contract_project_project_form_structure_v1"
    ENTRY_CONTRACT_NAME = "project_project_form_structure_v1"
    MIRROR_CONTRACT = "business_config_contract_project_project_form_structure_generated"
    MIRROR_CONTRACT_NAME = "project_project_form_structure_generated_v1"
    ACTION = "action_project_initiation"
    ACTION_ID = 724
    VIEW = "view_project_create_form"
    VIEW_ID = 1503
    MODEL = "project.project"
    TITLE = "项目立项"
    ENTRY_PRIORITY = 800
    MIRROR_PRIORITY = 77

    # Sibling entries on the same model that must keep rendering whatever they
    # rendered before this batch.  725 is the 「快速创建项目」 dispatch that
    # is not part of the ledger scope; it renders its own native view and is
    # checked explicitly below.
    QUICK_SIBLING_ACTION = "action_project_initiation_quick"
    QUICK_SIBLING_VIEW = "view_project_create_form_quick"
    QUICK_SIBLING_FIELDS = (
        "intake_next_action_display", "intake_blocking_reason_display", "name",
        "initiation_date", "manager_id", "operation_strategy", "owner_id",
    )

    # Business field set the native arch renders for the create form, in
    # document order.  Pinned so the batch provably keeps the rendered field
    # set unchanged (same 12 rows, none added or removed).
    RENDERED_FIELDS = (
        "intake_next_action_display", "intake_blocking_reason_display", "name",
        "initiation_date", "manager_id", "operation_strategy", "owner_id",
        "project_type_id", "project_category_id", "location", "start_date",
        "end_date",
    )

    # Anchored native business sections this batch declares.  The two keyed
    # ones carry the section identity the retired entry declared.
    NATIVE_SECTIONS = (
        ("current_task", "当前任务"),
        ("intake_risk", "立项条件"),
        ("project_create_required", "项目创建（必填）"),
        ("project_create_optional", "项目标识（可选）"),
    )

    # Read-only policy the retired declaration pinned and the native arch has
    # to restate, because the model itself does not report these fields
    # read-only.
    RETIRED_READONLY_FIELDS = ("intake_next_action_display", "intake_blocking_reason_display")

    # Labels the retired declaration pinned.  A label is a rendered fact: if the
    # arch does not restate one, the page silently falls back to the model's own
    # string.
    RETIRED_FIELD_LABELS = {"manager_id": "项目负责人"}

    # Declared facts that were NEVER rendered before the batch, proved by the
    # L0 probe of the delivered surface: nine sections carry no field and every
    # one of these names is absent from the rendered container tree.  They are
    # recorded rather than migrated, because putting them on the page now would
    # be a new surface, not a preserved one.
    DECLARED_NOT_RENDERED_SECTIONS = (
        "项目基本信息", "业务关系与类型", "参建单位与联系人", "合同与工期",
        "财税与账户", "成本与进度", "补充资料", "来源核对", "驾驶舱",
    )
    DECLARED_HIDDEN_FIELDS = (
        "company_id", "contract_amount", "contract_count", "contract_expense_total",
        "contract_ids", "contract_income_total", "dashboard_cost_actual",
        "dashboard_document_completion", "dashboard_invoice_amount",
        "dashboard_payment_in", "dashboard_payment_out", "dashboard_profit_actual",
        "dashboard_progress_rate", "dashboard_revenue_actual", "display_name",
        "document_count", "document_ids", "document_missing_count",
        "document_required_count", "label_tasks", "message_needaction",
        "subcontract_amount", "tag_ids", "task_ids", "tender_bid_ids",
    )

    # -- helpers -------------------------------------------------------------

    def _contract(self, xmlid):
        return self.env["ui.business.config.contract"].sudo().browse(
            self.ref("smart_construction_core.%s" % xmlid))

    def _entry_contracts(self, action_id=None, view_id=None):
        return self.env["ui.business.config.contract"].sudo()._effective_view_orchestration_contracts(
            self.MODEL,
            view_type="form",
            action_id=self.ACTION_ID if action_id is None else action_id,
            view_id=self.VIEW_ID if view_id is None else view_id,
            role_key="",
        )

    def _form_spec(self, record):
        return (((record.contract_json or {}).get("view_orchestration") or {})
                .get("views", {}).get("form", {})) or {}

    def _native_contract(self, action_xmlid, view_xmlid, model):
        """Render this exact entry the way the runtime would render it."""
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
                    yield from TestProjectInitiationNativeLowcode._walk([child])

    def _rendered_fields(self, data):
        """Rendered business field names, in document order, de-duplicated."""
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

    def _rendered_labels(self, data, names):
        labels = {}
        tree = (data.get("layoutContract") or {}).get("containerTree") or []
        for node in self._walk(tree):
            if node.get("type") == "field" and node.get("name") in names:
                labels[node["name"]] = node.get("label") or node.get("title")
        return labels

    def _arch(self, view_xmlid=None):
        view = self.env.ref("smart_construction_core.%s" % (view_xmlid or self.VIEW))
        return etree.fromstring(view.arch.encode("utf-8"))

    def _arch_fields(self):
        seen, ordered = set(), []
        for node in self._arch().iter("field"):
            name = node.get("name")
            if name and name not in seen:
                seen.add(name)
                ordered.append(name)
        return tuple(ordered)

    def _arch_sections(self):
        return tuple((group.get("data-sc-anchor"), group.get("string"))
                     for group in self._arch().iter("group") if group.get("data-sc-anchor"))

    # -- declaration surface -------------------------------------------------

    def test_the_entry_declares_the_native_semantic_surface(self):
        record = self._contract(self.ENTRY_CONTRACT)
        self.assertTrue(record.active)
        self.assertEqual(record.name, self.ENTRY_CONTRACT_NAME)
        self.assertEqual(record.model, self.MODEL)
        self.assertEqual(record.action_id.id, self.ref("smart_construction_core.%s" % self.ACTION))
        self.assertEqual(record.view_id.id, self.VIEW_ID)
        self.assertEqual(record.priority, self.ENTRY_PRIORITY)
        self.assertGreater(record.priority, self.MIRROR_PRIORITY)
        spec = self._form_spec(record)
        self.assertEqual(spec.get("composition_mode"), "native_semantic_surface")
        self.assertEqual(spec.get("title"), self.TITLE)
        # A native declaration may not carry a competing structure.
        self.assertEqual(structural_form_declarations(spec), {})
        for key in ("sections", "fields", "semantic_anchors", "columns", "layout"):
            self.assertNotIn(key, spec)

    def test_the_entry_semantics_are_preserved_verbatim(self):
        """The retired body's context survives the retirement unchanged."""
        context = ((self._contract(self.ENTRY_CONTRACT).contract_json or {})
                   .get("view_orchestration", {}).get("context", {}))
        self.assertEqual(context.get("source"), "smart_construction_core.product_release")
        self.assertEqual(context.get("source_status"), "product_release")

    def test_the_mirror_is_retired_with_the_entry(self):
        """Mirror 46 is action-bound, so the retirement is all-or-nothing.

        Leaving it active makes it the last structure writer for this action and
        the ownership diagnosis refuses the surface.  The record stays declared
        (explicitly retired) rather than being dropped from the data file.
        """
        mirror = self._contract(self.MIRROR_CONTRACT)
        self.assertEqual(mirror.name, self.MIRROR_CONTRACT_NAME)
        self.assertFalse(mirror.active)
        self.assertEqual(mirror.model, self.MODEL)
        # It is a mirror of THIS entry: it never served an action-less surface,
        # which is what would forbid retiring it.
        self.assertEqual(mirror.action_id.id, self.ACTION_ID)
        self.assertEqual(mirror.view_id.id, self.VIEW_ID)
        configs = self._entry_contracts()
        self.assertNotIn(mirror.name, [config.name for config in configs])

    # -- resolution surface --------------------------------------------------

    def test_the_entry_resolves_the_native_semantic_surface(self):
        configs = self._entry_contracts()
        native = [config for config in configs
                  if (self._form_spec(config) or {}).get("composition_mode")
                  in {"native_semantic_surface", "semantic_native_surface"}]
        self.assertEqual([config.name for config in native], [self.ENTRY_CONTRACT_NAME])

    def test_the_entry_resolves_native_authority(self):
        configs = self._entry_contracts()
        resolved = resolve_form_structure_governance({}, configs, view_type="form")
        self.assertEqual(resolved.get("form_structure_authority"), "native_authority")
        self.assertFalse(structural_form_declarations(self._form_spec(self._contract(self.ENTRY_CONTRACT))))
        diagnostics = diagnose_structure_ownership(
            configs, model=self.MODEL, action_id=self.ACTION_ID)
        codes = {row["code"] for row in diagnostics}
        self.assertNotIn("LEGACY_STRUCTURE_KEY_OVERRIDE", codes)
        self.assertNotIn("NATIVE_SEMANTIC_SURFACE_STRUCTURE_CONFLICT", codes)
        for row in diagnostics:
            self.assertFalse(
                row["explicit_structure_scope"],
                "a scoped competing declaration must never survive the native owner",
            )

    def test_the_rendered_surface_is_the_native_container_tree(self):
        data = self._native_contract(self.ACTION, self.VIEW, self.MODEL)
        structure = data.get("formStructureContract") or {}
        self.assertEqual(structure.get("layoutPolicy"), "container_tree_authority")
        self.assertEqual(structure.get("mode"), "native_structured_form")
        self.assertFalse(structure.get("slots"))
        self.assertFalse(structure.get("sourceSectionTitles"))
        self.assertFalse(structure.get("fieldRoles"))

    def test_the_entry_release_does_not_leak_to_other_actions_on_the_model(self):
        """The release is scoped to action 724, so sibling entries are untouched."""
        action_model = self.env["ir.actions.act_window"]
        entry = self._contract(self.ENTRY_CONTRACT)
        siblings = action_model.sudo().search([
            ("res_model", "=", self.MODEL), ("id", "!=", self.ACTION_ID)])
        self.assertTrue(siblings)
        for sibling in siblings:
            with self.subTest(action=sibling.id):
                configs = self.env["ui.business.config.contract"].sudo()\
                    ._effective_view_orchestration_contracts(
                        self.MODEL, view_type="form", action_id=sibling.id,
                        view_id=0, role_key="")
                self.assertNotIn(entry.name, [config.name for config in configs])

    def test_the_quick_sibling_keeps_its_rendered_facts(self):
        """`快速创建项目` renders its own native view; the batch may not shrink it.

        The dispatch is not a ledger consumer, so it is checked as a neighbour:
        it must keep rendering the same fields with the same editability.
        """
        data = self._native_contract(
            self.QUICK_SIBLING_ACTION, self.QUICK_SIBLING_VIEW, self.MODEL)
        self.assertEqual(self._rendered_fields(data), self.QUICK_SIBLING_FIELDS)
        readonly = self._rendered_readonly(data, self.RETIRED_READONLY_FIELDS)
        for name in self.RETIRED_READONLY_FIELDS:
            self.assertEqual(readonly.get(name), [True] * len(readonly[name]))

    # -- native arch ---------------------------------------------------------

    def test_the_native_arch_declares_every_business_section_identity(self):
        self.assertEqual(self._arch_sections(), self.NATIVE_SECTIONS)

    def test_the_native_arch_is_presentation_neutral(self):
        """The provenance of the rendered field set is the arch, not the contract."""
        self.assertEqual(self._arch_fields(), self.RENDERED_FIELDS)
        data = self._native_contract(self.ACTION, self.VIEW, self.MODEL)
        self.assertEqual(self._rendered_fields(data), self.RENDERED_FIELDS)

    def test_the_retired_readonly_policy_survives_on_the_native_surface(self):
        data = self._native_contract(self.ACTION, self.VIEW, self.MODEL)
        readonly = self._rendered_readonly(data, self.RETIRED_READONLY_FIELDS)
        self.assertEqual(sorted(readonly), sorted(self.RETIRED_READONLY_FIELDS))
        for name, flags in readonly.items():
            with self.subTest(field=name):
                self.assertTrue(flags and all(flags))

    def test_the_retired_field_labels_survive_on_the_native_surface(self):
        """A pinned label is a rendered fact: the arch has to restate it."""
        data = self._native_contract(self.ACTION, self.VIEW, self.MODEL)
        labels = self._rendered_labels(data, tuple(self.RETIRED_FIELD_LABELS))
        self.assertEqual(labels, self.RETIRED_FIELD_LABELS)

    def test_the_unrendered_declaration_never_reaches_the_page(self):
        """Facts the retired body declared but never rendered stay off the page.

        Migrating them now would create a surface the batch has no evidence for,
        so the check pins the honest boundary instead of glossing over it.
        """
        data = self._native_contract(self.ACTION, self.VIEW, self.MODEL)
        rendered = set(self._rendered_fields(data))
        self.assertFalse(rendered & set(self.DECLARED_HIDDEN_FIELDS))
        arch = self._arch()
        # A retired section identity would surface as an element attribute - a
        # container's own `string`, or a `field`'s `name`.  Reading those off the
        # parsed arch is robust against attribute quoting/whitespace variants
        # that a text substring match would miss, while still ignoring helper
        # copy that legitimately mentions a title as element text (项目驾驶舱).
        arch_strings = {
            node.get("string") for node in arch.iter() if node.get("string")
        }
        self.assertFalse(arch_strings & set(self.DECLARED_NOT_RENDERED_SECTIONS))
        arch_field_names = {
            node.get("name") for node in arch.iter() if node.tag == "field"
        }
        self.assertFalse(arch_field_names & set(self.DECLARED_HIDDEN_FIELDS))

    def test_every_rendered_fact_belongs_to_its_own_model(self):
        for name in self.RENDERED_FIELDS:
            with self.subTest(field=name):
                self.assertIn(name, self.env[self.MODEL]._fields)

    def test_every_anchored_section_carries_a_readable_business_title(self):
        for anchor, label in self._arch_sections():
            with self.subTest(anchor=anchor):
                self.assertTrue(anchor)
                self.assertTrue((label or "").strip())
