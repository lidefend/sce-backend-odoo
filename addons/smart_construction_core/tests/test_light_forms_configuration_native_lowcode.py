# -*- coding: utf-8 -*-
from lxml import etree

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.core.form_structure_authority import (
    diagnose_structure_ownership,
    resolve_form_structure_governance,
    structural_form_declarations,
)


@tagged("post_install", "-at_install", "uc4_native_lowcode")
class TestLightFormsConfigurationNativeLowcode(TransactionCase):
    """U-C4 G11: 轻表单与管理配置整组原生结构迁移.

    Six P1 native forms carry this group, and each one sits behind its own
    capability boundary (collaboration inbox / HR organisation / office asset /
    approval policy / system parameters / numbering rules):

      860 消息通知 / menu 675 / action `action_sc_product_message_notification_v1`
        -> `mail.notification` / `view_sc_product_mail_notification_form`
      883 岗位管理 / menu 705 / action `action_sc_product_job_management_v1`
        -> `hr.job` / `view_sc_product_job_form_v1`
      885 办公资产 / menu 707 / action `action_sc_product_office_asset_v1`
        -> `sc.office.asset` / `view_sc_office_asset_form`
      727 流程审批配置 / menu 424 / action `action_sc_approval_policy`
        -> `sc.approval.policy` / `view_sc_approval_policy_form`
      887 系统参数 / menu 710 / action `action_sc_product_system_parameter_v1`
        -> `sc.product.system.settings` / `view_sc_product_system_settings_form_v1`
      888 编码规则 / menu 711 / action `action_sc_product_numbering_rule_v1`
        -> `ir.sequence` / `view_sc_product_numbering_rule_form_v1`

    The group reaches the compatibility floorplan two different ways, and the
    batch closes both:

      * 860 / 883 / 885 / 887 / 888 carried an entry-level
        `entry_semantic_surface` body (sections + fields + columns) that
        duplicated the groups their own native forms already declare.  Those
        bodies are retired: each entry keeps only `title` +
        `composition_mode: native_semantic_surface`, and the native arch owns
        the structure.  Three of them (860 / 885 / 888) keep a SPARSE
        read-only overlay - `fields` rows carrying `name` + `readonly` only -
        for the exact fields whose read-only policy the arch does not restate.
      * 727 had NO entry release at all.  It consumed only the model-wide
        generated mirror 52
        (`sc_approval_policy_form_structure_generated_v1`, priority 84), so
        `form_structure_authority` stayed `""` and `ui_contract_v2` ran the
        generic governance projection.  This batch publishes the same native
        shape on that action at priority 800.

    In both cases the entry declaration becomes the LAST structure writer for
    its own action, so `form_structure_authority` resolves to
    `native_authority` and `layoutPolicy` resolves to
    `container_tree_authority`: the compatibility regrouping path stops
    applying.

    The regression rule this batch must not break (same rule as G10): a
    model-wide carrier may only be retired when it is not the last remaining
    structure writer for any OTHER action on the same model.  Mirror 52 has no
    action binding, so it stays active and unscoped - it is still the structure
    plane of `sc.approval.policy` on any surface resolved without an action
    context.  Every other model in this group holds exactly one active carrier,
    this batch's own entry release.

    The batch is presentation-neutral: the native arch is the ground truth and
    `RENDERED_FIELDS` pins it, so a retired declaration cannot silently drop a
    fact.
    """

    # entry contract xmlid -> (action xmlid, model, view xmlid, title, kind)
    # kind: "body_retired" keeps the release and drops its structural body;
    #       "release_added" publishes a release where the entry had none.
    ENTRIES = {
        "business_config_contract_mail_notification_form_v1": (
            "action_sc_product_message_notification_v1", "mail.notification",
            "view_sc_product_mail_notification_form", "消息通知", "body_retired"),
        "business_config_contract_product_job_form_v1": (
            "action_sc_product_job_management_v1", "hr.job",
            "view_sc_product_job_form_v1", "岗位管理", "body_retired"),
        "business_config_contract_office_asset_form_v1": (
            "action_sc_product_office_asset_v1", "sc.office.asset",
            "view_sc_office_asset_form", "办公资产", "body_retired"),
        "business_config_contract_sc_approval_policy_productized_form_v1": (
            "action_sc_approval_policy", "sc.approval.policy",
            "view_sc_approval_policy_form", "流程审批配置", "release_added"),
        "business_config_contract_product_system_settings_form_v1": (
            "action_sc_product_system_parameter_v1", "sc.product.system.settings",
            "view_sc_product_system_settings_form_v1", "系统参数", "body_retired"),
        "business_config_contract_product_numbering_rule_form_v1": (
            "action_sc_product_numbering_rule_v1", "ir.sequence",
            "view_sc_product_numbering_rule_form_v1", "编码规则", "body_retired"),
    }

    # Deliberate release priorities.  Every entry release must outrank the
    # model-wide carriers still active on its own model; the highest of those is
    # the approval-policy mirror 52 at 84.
    ENTRY_PRIORITIES = {
        "mail_notification_form_v1": 800,
        "product_job_form_v1": 800,
        "office_asset_form_v1": 800,
        "sc_approval_policy_productized_form_v1": 800,
        "product_system_settings_form_v1": 800,
        "product_numbering_rule_form_v1": 800,
    }

    # Model-wide carriers retained on purpose.  Mirror 52 is still the only
    # structure carrier of `sc.approval.policy` when no action scopes the
    # resolution, so retiring it belongs to another group.
    # xmlid -> (model, the sibling actions that keep depending on it)
    RETAINED_MODEL_WIDE_CARRIERS = {
        "business_config_contract_sc_approval_policy_form_structure_generated": (
            "sc.approval.policy", ()),
    }

    # Facts declared by the retired entry bodies.  No name may be missing from
    # the model, and every fact must still be reachable from the native arch -
    # which is exactly what makes the retirement presentation-neutral.
    RETIRED_ENTRY_FACTS = {
        "mail.notification": (
            "sc_subject", "author_id", "sc_message_date", "is_read", "read_date",
            "sc_record_name", "sc_body",
        ),
        "hr.job": (
            "sc_job_code", "name", "department_id", "company_id", "active",
            "expected_employees", "no_of_employee", "sc_responsibility",
            "sc_qualification",
        ),
        "sc.office.asset": (
            "status", "asset_code", "name", "category", "specification", "serial_no",
            "company_id", "department_id", "custodian_id", "location", "active",
            "purchase_date", "purchase_value", "currency_id", "note", "attachment_ids",
        ),
        "sc.product.system.settings": (
            "parameter_scope", "cost_ledger_source", "operation_notice",
        ),
        "ir.sequence": (
            "name", "code", "company_id", "prefix", "suffix", "padding",
            "number_increment", "number_next_actual",
        ),
    }

    # Technical traces that stay in the native arch as `invisible="1"` and are
    # deliberately NOT part of any anchored business section.  The
    # `mail.notification` entry carries two provenance markers
    # (`sc_source_model` / `sc_source_res_id`) that the retired entry body never
    # declared; they stay invisible so the "打开关联单据" button keeps resolving
    # while the surface keeps showing business facts only.
    TECHNICAL_TRACE_FIELDS = {
        "mail.notification": ("sc_source_model", "sc_source_res_id"),
    }

    # The retired entry bodies also pinned a field-level read-only policy.  The
    # native arch does not restate it for every field node, so three entries keep
    # a SPARSE semantic overlay: `fields` rows carrying `name` + `readonly` only.
    # Such a row holds no structure key, so `structural_form_declarations()`
    # still reads the entry as declaring nothing and the native authority stands.
    # Only the fields that really regress are re-pinned; a field the model
    # already reports read-only is left to the model and never restated here.
    # contract xmlid -> the re-pinned field names
    SPARSE_READONLY_OVERLAY = {
        "business_config_contract_mail_notification_form_v1": (
            "author_id", "is_read", "read_date"),
        "business_config_contract_office_asset_form_v1": ("status",),
        "business_config_contract_product_numbering_rule_form_v1": (
            "name", "code", "company_id"),
    }

    # The full read-only set L0 declared for those entries.  The sparse overlay
    # only restates part of it, so the surface has to resolve every one of them
    # read-only once the retirement is done - the model covers the rest.
    RETIRED_READONLY_FIELDS = {
        "business_config_contract_mail_notification_form_v1": (
            "sc_subject", "author_id", "sc_message_date", "is_read", "read_date",
            "sc_record_name", "sc_body"),
        "business_config_contract_office_asset_form_v1": ("status",),
        "business_config_contract_product_numbering_rule_form_v1": (
            "name", "code", "company_id"),
    }

    # Business field set the native arch renders for each form, in document
    # order and de-duplicated across embedded list/form containers.  Pinned so
    # the batch is provably presentation-neutral.
    RENDERED_FIELDS = {
        "view_sc_product_mail_notification_form": (
            "sc_source_model", "sc_source_res_id", "sc_subject", "author_id",
            "sc_message_date", "is_read", "read_date", "sc_record_name", "sc_body",
        ),
        "view_sc_product_job_form_v1": (
            "sc_job_code", "name", "department_id", "company_id", "active",
            "expected_employees", "no_of_employee", "sc_responsibility",
            "sc_qualification",
        ),
        "view_sc_office_asset_form": (
            "status", "asset_code", "name", "category", "specification", "serial_no",
            "company_id", "department_id", "custodian_id", "location", "active",
            "purchase_date", "purchase_value", "currency_id", "note", "attachment_ids",
        ),
        "view_sc_approval_policy_form": (
            "name", "target_model", "approval_required", "trigger", "mode",
            "manager_scope_key", "step_count", "runtime_state", "active",
            "company_id", "manager_group_id", "step_ids", "sequence",
            "approval_scope_key", "approve_group_id", "amount_min", "amount_max",
            "condition_note", "note",
        ),
        "view_sc_product_system_settings_form_v1": (
            "parameter_scope", "cost_ledger_source", "operation_notice",
        ),
        "view_sc_product_numbering_rule_form_v1": (
            "name", "code", "company_id", "prefix", "suffix", "padding",
            "number_increment", "number_next_actual",
        ),
    }

    # The anchored native business sections this batch declares.  Notebook
    # descendants are excluded by the helper, and layout-only column groups plus
    # the embedded one2many step list/form carry no anchor because they are not
    # entry-level business sections.
    NATIVE_SECTIONS = {
        "view_sc_product_mail_notification_form": (
            ("mail_notification_info", "消息信息"),
            ("mail_notification_content", "消息内容"),
        ),
        "view_sc_product_job_form_v1": (
            ("sc_product_job_identity", "岗位信息"),
            ("sc_product_job_headcount", "编制信息"),
            ("sc_product_job_duty", "岗位职责"),
            ("sc_product_job_qualification", "任职要求"),
        ),
        "view_sc_office_asset_form": (
            ("sc_office_asset_identity", "资产信息"),
            ("sc_office_asset_usage", "使用信息"),
            ("sc_office_asset_purchase", "购置信息"),
        ),
        "view_sc_approval_policy_form": (
            ("sc_approval_policy_rules", "业务规则"),
            ("sc_approval_policy_runtime", "系统承载"),
        ),
        "view_sc_product_system_settings_form_v1": (
            ("sc_product_system_settings_scope", "参数范围"),
            ("sc_product_system_settings_cost_ledger", "成本台账"),
            ("sc_product_system_settings_operation", "运行说明"),
        ),
        "view_sc_product_numbering_rule_form_v1": (
            ("sc_product_numbering_rule_identity", "规则标识"),
            ("sc_product_numbering_rule_format", "编号格式"),
        ),
    }

    # -- helpers -------------------------------------------------------------

    def _contract(self, xmlid):
        return self.env["ui.business.config.contract"].sudo().browse(
            self.ref("smart_construction_core.%s" % xmlid)
        )

    def _entry_contracts(self, model, action_xmlid, view_xmlid):
        """Resolve the contracts the runtime would use for this exact entry."""
        return self.env["ui.business.config.contract"].sudo()._effective_view_orchestration_contracts(
            model,
            view_type="form",
            action_id=self.ref("smart_construction_core.%s" % action_xmlid),
            view_id=self.env.ref("smart_construction_core.%s" % view_xmlid).id,
            role_key="",
        )

    def _form_spec(self, record):
        return (
            ((record.contract_json or {}).get("view_orchestration") or {})
            .get("views", {})
            .get("form", {})
        )

    def _native_contract(self, action_xmlid, view_xmlid, model):
        """Render this exact entry the way the runtime would render it.

        The static checks above read the declarations; the read-only policy can
        only be observed on the rendered surface, so this drives the real
        handler instead of trusting the declaration text.
        """
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
    def _walk(rows, parent=None):
        for node in rows if isinstance(rows, list) else []:
            if isinstance(node, dict):
                yield node, parent
                for child in node.get("children") or []:
                    yield from TestLightFormsConfigurationNativeLowcode._walk([child], node)

    def _rendered_readonly(self, data, names):
        """Map each field name to the read-only flags its rendered nodes carry."""
        seen: dict[str, list] = {}
        tree = (data.get("layoutContract") or {}).get("containerTree") or []
        for node, _parent in self._walk(tree):
            name = node.get("name")
            if node.get("type") == "field" and name in names:
                seen.setdefault(name, []).append(bool(node.get("readonly")))
        return seen

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
        """Resolve every `<field>` against the model that actually owns it."""
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
        for contract_xmlid, (action_xmlid, model, _view, title, _kind) in self.ENTRIES.items():
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
                self.assertEqual(record.priority, self.ENTRY_PRIORITIES[record.name])

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

    def test_the_retired_bodies_are_the_only_structural_bodies_removed(self):
        """`body_retired` keeps no structure; `release_added` never had one.

        A `fields` row may survive the retirement only as the sparse read-only
        overlay - `name` + `readonly`, nothing else.  Any other row would be a
        competing structural declaration wearing a semantic coat.
        """
        for contract_xmlid, (_action, _model, _view, _title, kind) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                self.assertIn(kind, {"body_retired", "release_added"})
                spec = self._form_spec(self._contract(contract_xmlid))
                for key in ("sections", "columns", "layout"):
                    self.assertNotIn(key, spec)
                rows = spec.get("fields")
                if rows is None:
                    continue
                self.assertEqual(
                    sorted(row["name"] for row in rows),
                    sorted(self.SPARSE_READONLY_OVERLAY.get(contract_xmlid, ())),
                )
                for row in rows:
                    self.assertEqual(set(row), {"name", "readonly"})
                    self.assertTrue(row["readonly"])

    def test_no_retired_body_left_a_competing_structure_key(self):
        """The mechanism only works because the retired body declares nothing."""
        for contract_xmlid, (_action, _model, _view, _title, kind) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                spec = self._form_spec(self._contract(contract_xmlid))
                # Not the retired body and not the sparse overlay declares structure.
                self.assertEqual(structural_form_declarations(spec), {})
                self.assertFalse(spec.get("sections"))

    # -- resolution surface --------------------------------------------------

    def test_every_entry_resolves_the_native_semantic_surface(self):
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title, _kind) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                configs = self._entry_contracts(model, action_xmlid, view_xmlid)
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

        This is the assertion that closes the compatibility path: while a
        model-wide carrier still declares its own structure (mirror 52 on
        `sc.approval.policy`), a native declaration that sorted before it would
        leave the resolved authority pointing back at the legacy plane and
        `layoutPolicy` back at the compatibility floorplan.
        """
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title, _kind) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                configs = self._entry_contracts(model, action_xmlid, view_xmlid)
                resolved = resolve_form_structure_governance({}, configs, view_type="form")
                self.assertEqual(resolved.get("form_structure_authority"), "native_authority")
                self.assertEqual(resolved.get("form_presentation_mode"), "task")

    def test_the_entry_release_outranks_every_model_wide_carrier(self):
        """The entry priority is the whole mechanism, so it is pinned."""
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title, _kind) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                entry = self._contract(contract_xmlid)
                others = [
                    config for config in self._entry_contracts(model, action_xmlid, view_xmlid)
                    if config.name != entry.name
                ]
                self.assertGreater(
                    entry.priority,
                    max((config.priority for config in others), default=0),
                    "the entry release must sort after every carrier it competes with",
                )

    def test_the_retained_carriers_are_reported_as_suppressed_not_rejected(self):
        """An unscoped legacy declaration degrades; it never blocks the native owner."""
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title, _kind) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                configs = self._entry_contracts(model, action_xmlid, view_xmlid)
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
        model = "sc.approval.policy"

        class _Config:
            def __init__(self, name, contract_json, action_id, view_id=0):
                self.id = 0
                self.name = name
                self.priority = 50
                self.action_id = action_id
                self.view_id = view_id
                self.contract_json = contract_json

        native = _Config("native", {"view_orchestration": {"views": {"form": {
            "title": "流程审批配置", "composition_mode": "native_semantic_surface"}}}}, 999)
        competitor = _Config("competitor", {"view_orchestration": {"views": {"form": {
            "composition_mode": "entry_semantic_surface",
            "sections": [{"title": "旧章节"}]}}}}, 999)
        with self.assertRaises(ValueError):
            diagnose_structure_ownership([native, competitor], model=model, action_id=999)

    # -- retention surface ---------------------------------------------------

    def test_the_model_wide_carriers_stay_active_for_their_unscoped_surface(self):
        """The regression rule: a shared mirror is never retired by this group.

        Mirror 52 has no action binding, so it is still the structure plane of
        `sc.approval.policy` on any surface resolved without an action context.
        Retiring it here would change those surfaces, so it stays active and
        stays unscoped.
        """
        for contract_xmlid, (model, sibling_actions) in self.RETAINED_MODEL_WIDE_CARRIERS.items():
            with self.subTest(contract=contract_xmlid):
                record = self._contract(contract_xmlid)
                self.assertTrue(record.active)
                self.assertFalse(record.action_id)
                self.assertFalse(record.view_id)
                self.assertEqual(record.model, model)
                for action_xmlid in sibling_actions:
                    action = self.env.ref("smart_construction_core.%s" % action_xmlid)
                    self.assertEqual(action.res_model, model)

    def test_the_retained_mirror_still_scopes_in_without_an_action(self):
        """Mirror 52 keeps answering when no action narrows the resolution."""
        mirror = self._contract(
            "business_config_contract_sc_approval_policy_form_structure_generated")
        configs = self.env["ui.business.config.contract"].sudo()._effective_view_orchestration_contracts(
            "sc.approval.policy", view_type="form", action_id=0, view_id=0, role_key="")
        self.assertIn(mirror.name, [config.name for config in configs])

    def test_the_entry_release_does_not_leak_to_other_actions_on_the_model(self):
        """Each entry release is scoped to its own action, so siblings are untouched.

        Resolved by domain instead of hard-coded ids: core also ships
        `mail.notification`, `hr.job` and `ir.sequence` actions that must keep
        rendering whatever they rendered before this batch.
        """
        action_model = self.env["ir.actions.act_window"]
        for _contract_xmlid, (action_xmlid, model, _view, _title, _kind) in self.ENTRIES.items():
            entry = self._contract(_contract_xmlid)
            own_action_id = self.ref("smart_construction_core.%s" % action_xmlid)
            siblings = action_model.sudo().search([
                ("res_model", "=", model),
                ("id", "!=", own_action_id),
            ])
            for sibling in siblings:
                with self.subTest(model=model, action=sibling.id):
                    configs = self.env["ui.business.config.contract"].sudo()\
                        ._effective_view_orchestration_contracts(
                            model, view_type="form", action_id=sibling.id,
                            view_id=0, role_key="")
                    self.assertNotIn(entry.name, [config.name for config in configs])

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

    def test_the_retired_readonly_policy_survives_on_the_native_surface(self):
        """A retired declaration may not relax a fact it used to pin read-only.

        860 / 885 / 888 declared a field-level read-only policy that the native
        arch does not restate for every node, so the entry keeps the sparse
        overlay.  The check runs against the rendered container tree, not the
        declaration text, because that is where the regression would show.
        """
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title, _kind) in self.ENTRIES.items():
            pinned = self.RETIRED_READONLY_FIELDS.get(contract_xmlid)
            if not pinned:
                continue
            data = self._native_contract(action_xmlid, view_xmlid, model)
            rendered = self._rendered_readonly(data, set(pinned))
            contract = data.get("formStructureContract") or {}
            with self.subTest(contract=contract_xmlid):
                self.assertEqual(contract.get("layoutPolicy"), "container_tree_authority")
                self.assertEqual(contract.get("presentationMode"), "task")
                for name in pinned:
                    self.assertTrue(rendered.get(name), "%s must stay on the surface" % name)
                    self.assertTrue(
                        all(rendered[name]), "%s must stay read-only" % name)

    def test_the_sparse_overlay_is_a_subset_of_the_retired_readonly_policy(self):
        """The overlay re-pins only a part; it may never invent a field."""
        for contract_xmlid, names in self.SPARSE_READONLY_OVERLAY.items():
            with self.subTest(contract=contract_xmlid):
                self.assertIn(contract_xmlid, self.ENTRIES)
                declared = self.RETIRED_READONLY_FIELDS[contract_xmlid]
                self.assertEqual(sorted(set(names) - set(declared)), [])
                self.assertEqual(sorted(set(names) - self._arch_pinned(contract_xmlid)), [])

    def _arch_pinned(self, contract_xmlid):
        return {
            row["name"]
            for row in (self._form_spec(self._contract(contract_xmlid)).get("fields") or [])
        }

    def test_every_retired_fact_is_still_reachable_from_the_native_arch(self):
        """Every retired business fact stays on the surface, one way or the other.

        A fact a retired body declared must be rendered by the native arch that
        now owns the structure.  Nothing may vanish silently.
        """
        view_by_model = {
            model: view_xmlid
            for _contract_xmlid, (_action, model, view_xmlid, _title, kind) in self.ENTRIES.items()
            if kind == "body_retired"
        }
        for model, names in self.RETIRED_ENTRY_FACTS.items():
            with self.subTest(model=model):
                rendered = set(self._arch_fields(view_by_model[model]))
                self.assertEqual(
                    sorted(name for name in names if name not in rendered),
                    [],
                    "a retired declaration may not hold a fact nobody accounts for",
                )

    def test_the_technical_traces_stay_invisible_and_outside_every_section(self):
        """A trace field is a trace field: hidden, and never a business section."""
        view_by_model = {
            model: view_xmlid
            for _contract_xmlid, (_action, model, view_xmlid, _title, kind) in self.ENTRIES.items()
            if kind == "body_retired"
        }
        for model, names in self.TECHNICAL_TRACE_FIELDS.items():
            arch = self._arch(view_by_model[model])
            anchored_fields = {
                node.get("name")
                for group in arch.iter("group") if group.get("data-sc-anchor")
                for node in group.iter("field")
            }
            for name in names:
                nodes = [node for node in arch.iter("field") if node.get("name") == name]
                with self.subTest(model=model, field=name):
                    self.assertTrue(nodes, "a registered trace field must exist in the arch")
                    self.assertEqual([node.get("invisible") for node in nodes], ["1"])
                    self.assertNotIn(name, anchored_fields)

    def test_the_released_mirror_declared_nothing_the_arch_dropped(self):
        """727 is the reverse direction: the native arch must not lose a fact.

        The retired-shaped mirror 52 declared eleven `fields` entries.  Switching
        the entry to native authority hands structure to the arch, so the arch
        has to render at least what the mirror rendered.
        """
        mirror = self._contract(
            "business_config_contract_sc_approval_policy_form_structure_generated")
        declared = {
            str(row.get("name") or row.get("field") or "").strip()
            for row in self._form_spec(mirror).get("fields") or []
            if isinstance(row, dict)
        }
        declared.discard("")
        rendered = set(self._arch_fields("view_sc_approval_policy_form"))
        self.assertEqual(sorted(declared - rendered), [])

    def test_no_retired_declaration_referenced_a_missing_fact(self):
        for model, names in self.RETIRED_ENTRY_FACTS.items():
            fields = set(self.env[model]._fields)
            with self.subTest(model=model):
                self.assertEqual(sorted(set(names) - fields), [])

    def test_every_rendered_fact_belongs_to_its_own_model(self):
        mapping = {
            view_xmlid: model
            for _contract_xmlid, (_action, model, view_xmlid, _title, _kind) in self.ENTRIES.items()
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

    def test_the_native_arch_keeps_no_empty_business_page(self):
        """Same rule as G09/G10: an empty page holds no fact, so it goes."""
        for view_xmlid in {entry[2] for entry in self.ENTRIES.values()}:
            arch = self._arch(view_xmlid)
            empty = []
            for page in arch.iter("page"):
                if not page.xpath(".//field"):
                    empty.append(page.get("string"))
            with self.subTest(view=view_xmlid):
                self.assertEqual(empty, [])

    def test_every_anchored_section_carries_a_readable_business_title(self):
        """The consumer needs anchor AND label; an anchor alone renders nothing."""
        for view_xmlid in self.NATIVE_SECTIONS:
            for anchor, label in self._arch_sections(view_xmlid):
                with self.subTest(view=view_xmlid, anchor=anchor):
                    self.assertTrue(anchor)
                    self.assertTrue((label or "").strip())
