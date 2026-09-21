# -*- coding: utf-8 -*-
from lxml import etree

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.core.form_structure_authority import (
    diagnose_structure_ownership,
    resolve_form_structure_governance,
    structural_form_declarations,
)


@tagged("post_install", "-at_install", "uc4_native_lowcode")
class TestDataPermissionNativeLowcode(TransactionCase):
    """U-C4 G16: 数据权限 (action 886 / menu 709 / view 1904).

    One P1 formal entry:

      886 `action_sc_product_data_permission_v1` / menu 709 数据权限
        -> `res.users` / `view_sc_data_permission_user_form`

    Before this batch the entry contract `data_permission_form_v1` (181) carried
    an `entry_semantic_surface` body - four sections (7 fields), `columns: 2` and
    seven declared `fields` rows, three of them `readonly: True` - so the
    delivered surface ran the compatibility regrouping path.  The declared
    structure never added a fact: the native arch 1904 already renders the same
    four business groups (人员身份 / 主公司与允许公司 / 业务权限角色 / 项目数据范围)
    and already carries the same read-only口径 (`name` / `login` / `active`
    `readonly="1"`).

    This batch retires the structural body in place (the G13 shape used for 876
    and G15 for 880): the same record keeps its name, action, `priority=800`,
    `published` status, version and the five `context` keys, and only the
    structural keys are dropped, with `composition_mode` becoming
    `native_semantic_surface`.  A read-only A/B probe of the delivered surface
    (`sc_dev_demo`, `SAVEPOINT` + `ROLLBACK`, zero writes) measured that the two
    render profiles keep the container tree, the field set, every `readonly` /
    `invisible` modifier and the anchor set identical to the baseline; the
    retired body declared no policy the native arch does not already carry, so no
    sparse override is needed.

    The same probe registered one measured fact of this entry: before retirement
    the **create** route could not be assembled at all - the compatibility
    plane's own layout tripped `validate_occurrences` in
    `unified_page_contract_v2_assembler._assemble_native_form_projection`
    (`field='name'` with an empty `native_locator` and no `occurrence_index`) and
    the route raised `ValueError` instead of returning a page.  After retirement
    `create` assembles like `edit` and like the platform's other native entries.
    The read-only entry declares `create="0"` on the arch and `'create': False` in
    the action context, so the browser never requested that profile; the
    assertion below pins that the route now assembles and stops there.

    `RENDERED_FIELDS`, `DELIVERED_MODIFIERS` and `CONTAINER_SKELETON` pin the
    delivered surface so a later edit cannot silently drop a fact or a read-only
    口径 the entry carries today.
    """

    # entry contract xmlid -> (action xmlid, model, view xmlid, title)
    ENTRIES = {
        "business_config_contract_data_permission_form_v1": (
            "action_sc_product_data_permission_v1", "res.users",
            "view_sc_data_permission_user_form", "数据权限"),
    }

    ENTRY_PRIORITY = 800

    # The declaration the entry keeps verbatim; retirement must not rewrite it.
    ENTRY_CONTEXT = {
        "source": "smart_construction_core.product_release",
        "source_status": "product_release",
        "identity_authority": "res.users",
        "role_authority": "res.groups",
        "project_scope_authority": "sc.project.member.assignment",
    }

    # Structural keys the retirement must have removed.
    RETIRED_KEYS = ("sections", "columns", "actions", "fields", "layout", "semantic_anchors")

    # The four native business groups the arch declares, in document order.
    DECLARED_GROUPS = (
        "sc_permission_identity",
        "sc_permission_company_scope",
        "sc_permission_business_roles",
        "sc_permission_project_scope",
    )

    # Sibling entry on the same model: 人员档案 keeps its own route and its own
    # view, and owns no business config contract at all, so the retirement of
    # action 886 must not reach it.
    SIBLING = {
        "action_xmlid": "action_sc_runtime_user_management",
        "action_name": "人员档案",
        "view_xmlid": "view_sc_runtime_user_form",
    }

    # Business field set the delivered container tree carries, in document
    # order.  Pinned so the batch is provably presentation-neutral.
    RENDERED_FIELDS = {
        "view_sc_data_permission_user_form": (
            "name", "login", "active", "company_id", "company_ids",
            "sc_user_permission_group_ids", "sc_project_member_assignment_ids",
        ),
    }

    # Fields the native form arch declares, in document order.  The one2many
    # `sc_project_member_assignment_ids` declares an inline `tree` for its own
    # collection rows; those row fields are not form facts, so the walk does not
    # descend into them - the same rule the compiled container tree applies.
    ARCH_FIELDS = {
        "view_sc_data_permission_user_form": (
            "name", "login", "active", "company_id", "company_ids",
            "sc_user_permission_group_ids", "sc_project_member_assignment_ids",
        ),
    }

    # Read-only / hidden structure the delivered page keeps.  The retired entry
    # body declared no field policy the native arch does not already carry, so
    # this is the口径 the arch carries on its own; it is the surface the batch
    # must not shrink.
    # (field name, container `readonly` expression, container `invisible`)
    DELIVERED_MODIFIERS = {
        "view_sc_data_permission_user_form": (
            ("name", "1", False),
            ("login", "1", False),
            ("active", "1", False),
            ("sc_project_member_assignment_ids", "not id", False),
        ),
    }

    # Non-field container skeleton, in document order.  The retired body declared
    # four sections and no button, and the arch declares four groups and no
    # button either, so the delivered page must carry neither a button nor a
    # `data-sc-anchor`.
    CONTAINER_SKELETON = {
        "view_sc_data_permission_user_form": (
            ("sheet", "", None, None),
            ("group", "", None, None),
            ("group", "人员身份", "sc_permission_identity", None),
            ("group", "主公司与允许公司", "sc_permission_company_scope", None),
            ("group", "业务权限角色", "sc_permission_business_roles", None),
            ("group", "项目数据范围", "sc_permission_project_scope", None),
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
                    yield from TestDataPermissionNativeLowcode._walk([child])

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
                # same single carrier past version 1.  The declaration stays the
                # one and only release for action 886 either way.
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

        While the entry still carried `sections` / `columns` / `fields` it was
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
        `entry_semantic_surface` and the ledger kept counting 886 as a
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
        """`res.users` has no model-level generated structure carrier.

        The retirement therefore cannot leave a competing mirror behind: the
        single carrier on the model is the retired entry itself.
        """
        carriers = self._contracts().with_context(active_test=False).search(
            [("model", "=", "res.users")])
        self.assertEqual(
            sorted(carriers.mapped("name")),
            sorted([self._contract(xmlid).name for xmlid in self.ENTRIES]),
        )

    def test_the_retirement_does_not_leak_to_the_sibling_action(self):
        """人员档案 (736) shares the model but owns its own route and view."""
        for contract_xmlid, (_action, _model, _view, _title) in self.ENTRIES.items():
            entry_name = self._contract(contract_xmlid).name
            sibling = self.env.ref(
                "smart_construction_core.%s" % self.SIBLING["action_xmlid"])
            with self.subTest(entry=contract_xmlid, sibling=self.SIBLING["action_xmlid"]):
                self.assertEqual(sibling.name, self.SIBLING["action_name"])
                self.assertEqual(sibling.res_model, "res.users")
                sibling_views = {row.view_mode: row.view_id.id for row in sibling.view_ids}
                self.assertEqual(
                    sibling_views.get("form"),
                    self.env.ref("smart_construction_core.%s" % self.SIBLING["view_xmlid"]).id,
                )
                # 人员档案 owns no business config contract on this model, so the
                # retired entry must never be resolved as its structure writer.
                configs = self._contracts()._effective_view_orchestration_contracts(
                    sibling.res_model, view_type="form",
                    action_id=sibling.id, role_key="")
                self.assertNotIn(entry_name, [config.name for config in configs])
                self.assertEqual(list(configs), [])
                self.assertEqual(
                    resolve_form_structure_governance({}, configs, view_type="form"), {})

    def test_the_entry_route_identity_is_unchanged(self):
        """The retirement touches the declaration, never the route."""
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                action = self.env.ref("smart_construction_core.%s" % action_xmlid)
                view = self.env.ref("smart_construction_core.%s" % view_xmlid)
                menu = self.env.ref(
                    "smart_construction_core.menu_sc_product_data_permission_v1")
                self.assertEqual(menu.action, action)
                self.assertEqual(action.res_model, model)
                self.assertEqual(view.model, model)
                self.assertIn(view.id, action.view_ids.mapped("view_id").ids)
                # A read-only entry: the arch and the action context both refuse
                # create and delete, which is why the create route below is a
                # contract-assembly fact and not a browser journey.
                arch_root = self._arch(view_xmlid)
                self.assertEqual(arch_root.get("create"), "0")
                self.assertEqual(arch_root.get("delete"), "0")

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

        This is the discriminating assertion of the batch, and it is measured
        both ways: with the `entry_semantic_surface` body live the create route
        did not merely differ - it could not be assembled, because the body's own
        layout tripped `validate_occurrences` and raised `ValueError`; after
        retirement both profiles assemble the native container tree.  The retired
        entry declares no field policy, so both profiles must agree on the
        **field plane**: the same container field nodes, the same read-only
        modifiers, no per-field semantics plane and no compatibility surface
        policies.
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
                self.assertEqual(create_fields, self.RENDERED_FIELDS[view_xmlid])
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

    def test_the_delivered_container_keeps_the_native_groups_and_no_button(self):
        """The retired body declared four sections; the arch declares four groups."""
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                data = self._native_contract(model, action_xmlid, view_xmlid)
                self.assertEqual(
                    self._container_skeleton(data),
                    self.CONTAINER_SKELETON[view_xmlid],
                )
                self.assertEqual(
                    [node for node in self._walk(
                        (data.get("layoutContract") or {}).get("containerTree") or [])
                     if node.get("type") == "button"],
                    [],
                )

    # -- native arch ---------------------------------------------------------

    def test_the_native_arch_is_presentation_neutral(self):
        """The batch retires a declaration; it must not add or drop a fact."""
        for view_xmlid, expected in self.ARCH_FIELDS.items():
            with self.subTest(view=view_xmlid):
                self.assertEqual(self._arch_field_names(view_xmlid), expected)
                arch = self._arch(view_xmlid)
                groups = [node.get("name") for node in arch.iter("group") if node.get("name")]
                self.assertEqual(tuple(groups), self.DECLARED_GROUPS)
                self.assertEqual(list(arch.iter("button")), [])

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
