# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_construction_core.services import capability_registry
from .business_case import BusinessTransactionCase


@tagged("post_install", "-at_install", "sc_smoke", "capability_registry")
class TestCapabilityRegistryService(TransactionCase):
    def _project_actor(self):
        return self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Capability project actor', 'login': 'capability-project-actor',
            'email': 'capability-project@invalid.local',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id,
                                  self.env.ref('smart_construction_core.group_sc_role_project_manager').id])],
        })

    def test_registry_lint_passes(self):
        issues = capability_registry.lint_registry(self.env)
        self.assertFalse(issues, f"registry lint issues: {issues}")

    def test_registry_surface_count(self):
        definitions = capability_registry.capability_definitions()
        self.assertGreaterEqual(len(definitions), 30)
        definition_keys = {item.get("key") for item in definitions}
        user = self._project_actor()
        rows = capability_registry.list_capabilities_for_user(user.with_user(user).env, user)
        self.assertTrue(rows)
        self.assertTrue(all(row.get("key") in definition_keys for row in rows))
        self.assertTrue(any((row.get("group_key") == "project_management") for row in rows))

    def test_business_capability_identity_is_declared_by_registry(self):
        definition = capability_registry.capability_definitions()[0]
        self.assertEqual(definition["identity_kind"], "business_capability")
        self.assertTrue(definition["business_capability"])
        self.assertEqual(
            definition["definition_authority"],
            "smart_construction_core.services.capability_registry",
        )
        self.assertEqual(
            definition["qualification_authority"],
            "product_catalog_and_effective_release",
        )
        self.assertFalse(definition["key"].startswith(("construction.menu.", "catalog.menu.")))

    def test_existing_entry_catalog_is_not_implicitly_assignable(self):
        definitions = capability_registry.capability_definitions()
        self.assertTrue(definitions)
        for row in definitions:
            self.assertEqual(row['role_composition']['composable'], row['key'] == 'project.list.open', row['key'])
        from ..services.business_capability_authorization import CapabilityCompositionError
        with self.assertRaises(CapabilityCompositionError):
            capability_registry.resolve_role_capabilities(['contract.settlement.audit'])

    def test_composition_verdict_survives_runtime_projection(self):
        from ..core_extension_capability_rows import normalize_capability_row
        user = self._project_actor()
        rows = capability_registry.list_capabilities_for_user(user.with_user(user).env, user)
        self.assertTrue(rows)
        for row in rows:
            projected = normalize_capability_row(row)
            self.assertEqual(projected['role_composition'], row['role_composition'])
            self.assertNotIn('native_groups', projected['role_composition'])
            projected['role_composition']['operations'].append('tampered')
            self.assertNotIn('tampered', row['role_composition']['operations'])

    def test_capability_matrix_sections(self):
        user = self._project_actor()
        matrix = capability_registry.build_capability_matrix_for_user(user.with_user(user).env, user)
        sections = matrix.get("sections") if isinstance(matrix, dict) else None
        self.assertIsInstance(sections, list)
        self.assertTrue(bool(sections))
        self.assertTrue(all(isinstance(section.get("items"), list) for section in sections if isinstance(section, dict)))

    def test_product_project_manager_role_maps_to_pm(self):
        role_group = self.env.ref("smart_construction_core.group_sc_role_project_manager", raise_if_not_found=False)
        if not role_group:
            self.skipTest("smart_construction_core role data not installed")
        user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "role-map-pm",
                "login": "role_map_pm",
                "email": "role_map_pm@example.com",
                "groups_id": [(6, 0, [role_group.id])],
            }
        )
        roles = capability_registry._resolve_role_codes_for_user(user)
        self.assertIn("pm", roles)

    def test_finance_operator_role_includes_dictionary_read_capability(self):
        role_group = self.env.ref(
            "smart_construction_core.group_sc_role_finance_user",
            raise_if_not_found=False,
        )
        data_read_group = self.env.ref(
            "smart_construction_core.group_sc_cap_data_read",
            raise_if_not_found=False,
        )
        if not role_group or not data_read_group:
            self.skipTest("smart_construction_core finance role data not installed")
        user = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Finance operator role dependency",
            "login": "finance_operator_role_dependency",
            "groups_id": [(6, 0, [
                self.env.ref("base.group_user").id,
                role_group.id,
            ])],
        })
        self.assertIn(data_read_group, user.groups_id)
        dictionary_model = self.env["sc.dictionary"].with_user(user)
        self.assertTrue(dictionary_model.check_access_rights("read", raise_exception=False))

    def test_finance_operator_contract_search_satisfies_native_search_view_dependencies(self):
        from odoo.addons.smart_core.handlers.api_data import ApiDataHandler

        role_group = self.env.ref(
            "smart_construction_core.group_sc_role_finance_user",
            raise_if_not_found=False,
        )
        if not role_group:
            self.skipTest("smart_construction_core finance role data not installed")

        company = self.env["res.company"].create({
            "name": "Finance Role Default Configuration Company",
        })
        BusinessTransactionCase.register_business_company(
            company,
            tenant_key="finance-role-search-default-config",
        )
        company_env = self.env(context={
            **self.env.context,
            "allowed_company_ids": [company.id],
        })
        user = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Finance contract search actor",
            "login": "finance_contract_search_actor",
            "company_id": company.id,
            "company_ids": [(6, 0, [company.id])],
            "groups_id": [(6, 0, [
                self.env.ref("base.group_user").id,
                role_group.id,
            ])],
        })
        user_env = self.env(user=user.id, context={
            **self.env.context,
            "allowed_company_ids": [company.id],
        })
        self.assertEqual(user_env.user._sc_data_company_ids(), [company.id])

        contract_model = user_env["construction.contract"]
        handler = ApiDataHandler(user_env)
        search_view_fields = handler._search_view_field_names(contract_model)
        self.assertIn("category_id", search_view_fields)
        self.assertIn("contract_type_id", search_view_fields)
        relation_models = {
            contract_model._fields[field_name].comodel_name
            for field_name in search_view_fields
            if contract_model._fields.get(field_name)
            and contract_model._fields[field_name].type == "many2one"
        }
        self.assertIn("sc.dictionary", relation_models)
        for model_name in sorted(relation_models):
            self.assertTrue(
                user_env[model_name].check_access_rights("read", raise_exception=False),
                "%s search view relation %s is not readable by the standard finance role"
                % (contract_model._name, model_name),
            )

        category = self.env["sc.dictionary"].create({
            "name": "验收付款合同",
            "code": "finance-search-contract-category",
            "type": "contract_category",
        })
        contract_type = self.env["sc.dictionary"].create({
            "name": "验收付款合同",
            "code": "finance-search-contract-type",
            "type": "contract_type",
        })
        project = company_env["project.project"].create({
            "name": "Finance Search Project",
            "company_id": company.id,
        })
        partner = company_env["res.partner"].create({
            "name": "Finance Search Partner",
            "company_id": company.id,
        })
        contract = company_env["construction.contract"].create({
            "subject": "验收付款合同 CNY",
            "type": "in",
            "project_id": project.id,
            "partner_id": partner.id,
            "category_id": category.id,
            "contract_type_id": contract_type.id,
        })
        self.assertEqual(contract.company_id, company)
        company_env["construction.contract"].create({
            "subject": "无关采购合同",
            "type": "in",
            "project_id": project.id,
            "partner_id": partner.id,
            "category_id": category.id,
            "contract_type_id": contract_type.id,
        })

        result = handler.run({
            "intent": "api.data",
            "op": "list",
            "model": "construction.contract",
            "fields": ["id", "name", "display_name"],
            "search_term": "验收付款合同 CNY",
            "limit": 5,
            "need_total": True,
            "context": {"allowed_company_ids": [company.id]},
        })
        self.assertIsInstance(result, tuple)
        data, meta = result
        self.assertEqual(meta["op"], "list")
        self.assertEqual(data["total"], 1)
        self.assertEqual({row["id"] for row in data["records"]}, {contract.id})
        self.assertFalse(
            user_env["sc.dictionary"].check_access_rights("write", raise_exception=False),
            "satisfying the read dependency must not grant dictionary write access",
        )

    def test_standard_role_action_and_operation_permissions_are_closed(self):
        import json
        from pathlib import Path

        from odoo.tools.safe_eval import safe_eval
        from odoo.addons.smart_core.handlers.api_data import ApiDataHandler

        module_root = Path(__file__).resolve().parents[1]
        rebinding = json.loads(
            (module_root / "data/menu_entry_group_rebinding.json").read_text(
                encoding="utf-8"
            )
        )

        errors = []
        action_entries = {}
        for menu_xmlid in sorted(rebinding):
            menu = self.env.ref(menu_xmlid, raise_if_not_found=False)
            if not menu or not menu.action:
                errors.append("%s: product menu action is missing" % menu_xmlid)
                continue
            action_xmlid = menu.action.get_external_id().get(menu.action.id) or ""
            if action_xmlid:
                action_entries.setdefault(action_xmlid, set()).add(
                    "smart_construction_core.group_sc_%s" % rebinding[menu_xmlid]
                )

        actions = self.env["ir.actions.act_window"].sudo().browse()
        for action_xmlid in sorted(action_entries):
            action = self.env.ref(action_xmlid, raise_if_not_found=False)
            if not action:
                errors.append("%s: declared product action is missing" % action_xmlid)
                continue
            if action._name == "ir.actions.act_window" and action not in actions:
                actions |= action

        role_data = self.env["ir.model.data"].sudo().search([
            ("module", "=", "smart_construction_core"),
            ("model", "=", "res.groups"),
            ("name", "=like", "group_sc_role_%"),
        ])
        role_groups = self.env["res.groups"]
        for row in role_data:
            role_groups |= self.env["res.groups"].sudo().browse(row.res_id).exists()
        role_groups |= self.env.ref("smart_construction_core.group_sc_business_full")
        role_groups |= self.env.ref("smart_construction_core.group_sc_role_experience")

        for role_group in role_groups.sorted("id"):
            role_xmlid = role_group.get_external_id().get(role_group.id) or role_group.name
            login = "role_action_%s" % role_group.id
            user = self.env["res.users"].with_context(no_reset_password=True).create({
                "name": "Role action closure %s" % role_group.name,
                "login": login,
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, self.env.company.ids)],
                "groups_id": [(6, 0, [
                    self.env.ref("base.group_user").id,
                    role_group.id,
                ])],
            })
            closure = self.env["res.groups"]
            pending = role_group
            while pending:
                current = pending[0]
                pending = pending[1:]
                if current in closure:
                    continue
                closure |= current
                pending |= current.implied_ids - closure

            user_env = self.env(user=user.id, context={
                **self.env.context,
                "allowed_company_ids": self.env.company.ids,
            })
            handler = ApiDataHandler(user_env)
            model_checks = {}
            for action in actions:
                action_xmlid = action.get_external_id().get(action.id) or action.name
                if action.groups_id and not (action.groups_id & closure):
                    continue
                if not any(user.has_group(group) for group in action_entries.get(action_xmlid, ())):
                    continue
                if not action.groups_id and action_xmlid.startswith("smart_construction_core."):
                    errors.append("%s: visible product action has no authorization group" % action_xmlid)
                model_name = action.res_model
                if not model_name or model_name not in user_env:
                    errors.append("%s %s: action target model is missing" % (role_xmlid, action_xmlid))
                    continue

                cached = model_checks.get(model_name)
                if cached is None:
                    model = user_env[model_name]
                    search_view_fields = handler._filter_readable_fields(
                        model,
                        handler._search_view_field_names(model),
                    )
                    relation_models = {
                        model._fields[field_name].comodel_name
                        for field_name in search_view_fields
                        if model._fields.get(field_name)
                        and model._fields[field_name].type == "many2one"
                    }
                    cached = {
                        "rights": {
                            operation: model.check_access_rights(
                                operation, raise_exception=False
                            )
                            for operation in ("read", "create", "write", "unlink")
                        },
                        "relations": {
                            relation: user_env[relation].check_access_rights(
                                "read", raise_exception=False
                            )
                            for relation in relation_models
                            if relation in user_env
                        },
                    }
                    model_checks[model_name] = cached

                if not cached["rights"]["read"]:
                    errors.append(
                        "%s %s: action target %s is not readable"
                        % (role_xmlid, action_xmlid, model_name)
                    )
                    continue
                if not all(cached["relations"].values()):
                    denied = sorted(
                        relation for relation, allowed in cached["relations"].items()
                        if not allowed
                    )
                    errors.append(
                        "%s %s: search dependency not readable on %s: %s"
                        % (role_xmlid, action_xmlid, model_name, ", ".join(denied))
                    )

                try:
                    action_context = safe_eval(
                        action.context or "{}",
                        {
                            "context": dict(user_env.context),
                            "uid": user.id,
                            "allowed_company_ids": list(self.env.company.ids),
                        },
                    )
                except Exception:
                    action_context = {}
                if not isinstance(action_context, dict):
                    action_context = {}
                for context_key, operation in (
                    ("create", "create"),
                    ("edit", "write"),
                    ("delete", "unlink"),
                ):
                    if action_context.get(context_key) is True and not cached["rights"][operation]:
                        errors.append(
                            "%s %s: action declares %s=true but target %s lacks %s ACL"
                            % (role_xmlid, action_xmlid, context_key, model_name, operation)
                        )

        self.assertFalse(errors, "\n".join(errors))


@tagged("post_install", "-at_install", "capability_verdict_projection")
class TestCapabilityVerdictProjection(TransactionCase):
    def test_verdict_and_entry_parameters_survive_industry_projection(self):
        from ..core_extension_capability_rows import normalize_capability_row
        from odoo.addons.smart_core.core.capability_provider import build_capability_groups
        for state in ("allow", "readonly", "deny", "pending", "coming_soon"):
            with self.subTest(state=state):
                source = {
                    "key": "test.entry", "state": "LOCKED" if state == "deny" else "PREVIEW",
                    "capability_state": state, "capability_state_reason": "authority-verdict",
                    "reason_code": "AUTHORITY_REASON", "reason": "权限服务的说明",
                    "default_payload": {"model": "project.project", "view_type": "list"},
                }
                row = normalize_capability_row(source)
                for key in source:
                    self.assertEqual(row[key], source[key])
                group = build_capability_groups([row])[0]
                self.assertEqual(group["capability_state_counts"][state], 1)
                self.assertEqual(group["capabilities"][0]["reason"], source["reason"])
                row["default_payload"]["model"] = "changed"
                self.assertEqual(source["default_payload"]["model"], "project.project")

    def test_missing_verdict_is_not_invented_by_normalization(self):
        from ..core_extension_capability_rows import normalize_capability_row
        row = normalize_capability_row({"key": "test.entry"})
        self.assertNotIn("capability_state", row)
        self.assertNotIn("reason_code", row)

    def test_explicit_empty_capability_result_does_not_query_fallback(self):
        from unittest.mock import patch, MagicMock
        from odoo.addons.smart_core.core import capability_provider
        env = MagicMock()
        with patch.object(
            capability_provider,
            "call_extension_hook_first_compatible",
            return_value=[],
        ) as hook:
            self.assertEqual(capability_provider.load_capabilities_for_user(env, self.env.user), [])
        hook.assert_called_once()
        env.__getitem__.assert_not_called()

    def test_absent_provider_keeps_standalone_capability_source(self):
        from unittest.mock import patch, MagicMock
        from odoo.addons.smart_core.core import capability_provider
        env = MagicMock()
        record = MagicMock()
        record._user_visible.return_value = True
        record.to_public_dict.return_value = {"key": "standalone", "capability_state": "deny"}
        env.__getitem__.return_value.sudo.return_value.search.return_value = [record]
        with patch.object(
            capability_provider,
            "call_extension_hook_first_compatible",
            return_value=None,
        ), patch.object(
            capability_provider,
            "call_extension_hook_first",
            return_value=None,
        ):
            rows = capability_provider.load_capabilities_for_user(env, self.env.user)
        self.assertEqual(rows[0]["capability_state"], "deny")
        self.assertEqual(rows[0]["key"], "standalone")

    def test_real_user_registry_verdict_reaches_startup_provider(self):
        from odoo.addons.smart_core.core.capability_provider import load_capabilities_for_user
        user = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Projection actor", "login": "capability-projection-actor",
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id,
                self.env.ref("smart_construction_core.group_sc_role_project_manager").id])],
        })
        env = user.with_user(user).env
        expected = {row["key"]: row for row in capability_registry.list_capabilities_for_user(env, user)}
        actual = {row["key"]: row for row in load_capabilities_for_user(env, user)}
        self.assertTrue(expected)
        self.assertEqual(set(actual), set(expected))
        for key in expected:
            for field in ("state", "capability_state", "capability_state_reason", "reason_code", "reason", "default_payload"):
                self.assertEqual(actual[key][field], expected[key][field], (key, field))

    def test_personal_catalog_handler_uses_actual_user_verdicts(self):
        from ..handlers.product_configuration_capability import ProductConfigurationCapabilityCatalogHandler
        user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Personal catalog actor', 'login': 'personal-catalog-actor',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id,
                self.env.ref('smart_construction_core.group_sc_role_finance_user').id])],
        })
        env = user.with_user(user).env
        expected = capability_registry.list_capabilities_for_user(env, user)
        data = ProductConfigurationCapabilityCatalogHandler(env).handle()['data']
        actual = data['user_capabilities']['items']
        self.assertTrue(expected)
        self.assertEqual({r['key']: r['status'] for r in actual},
                         {r['key']: r['capability_state'] for r in expected})
        self.assertEqual(data['configuration_cards'], [])
        self.assertEqual(data['capabilities'], [])


@tagged("post_install", "-at_install", "query_capability_native_acl")
class TestQueryCapabilityNativeAcl(TransactionCase):
    def _actor(self, groups, login="native-query-actor"):
        return self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Query actor', 'login': login,
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id] +
                [self.env.ref(group).id for group in groups])],
        })

    def test_read_principal_sees_project_entry_without_pm_role_or_write_grant(self):
        from unittest.mock import patch

        user = self._actor(['smart_construction_core.group_sc_cap_project_read'])
        model = self.env['project.project'].with_user(user)
        self.assertTrue(model.check_access_rights('read', raise_exception=False))
        self.assertFalse(model.check_access_rights('write', raise_exception=False))
        roles = capability_registry._resolve_role_codes_for_user(user)
        self.assertNotIn('pm', roles)
        action = self.env.ref('smart_construction_core.action_sc_project_list')
        menu = self.env.ref('smart_construction_core.menu_sc_project_project')
        published = {action.id: (menu.id, action.id)}
        with patch.object(
            capability_registry,
            '_published_query_pairs_by_action_id',
            return_value=published,
        ):
            decision = capability_registry.capability_authorization_for_user(
                user, 'project.list.open'
            )
            rows = capability_registry.list_capabilities_for_user(
                user.with_user(user).env, user
            )
        self.assertEqual(decision['state'], 'allow')
        self.assertIn('project.list.open', {row['key'] for row in rows})
        self.assertFalse(model.check_access_rights('write', raise_exception=False))

    def test_each_query_verdict_equals_native_action_and_experience_marker_does_not_grant(self):
        user = self._actor([])
        keys = {'project.list.open': 'project.project', 'contract.center.open': 'construction.contract',
                'contract.income.track': 'construction.contract.income', 'contract.expense.track': 'construction.contract.expense'}
        before = {}
        for key, model in keys.items():
            definition = next(row for row in capability_registry.capability_definitions() if row['key'] == key)
            action = self.env.ref(definition['access_action'])
            self.assertEqual(action.res_model, model)
            allowed = bool((not action.groups_id or action.groups_id & user.groups_id)
                and self.env[model].with_user(user).check_access_rights('read', raise_exception=False))
            allowed = allowed and bool(capability_registry._published_query_pair(user, action.id))
            decision = capability_registry.capability_authorization_for_user(user, key)
            self.assertEqual(decision['state'], 'allow' if allowed else 'deny')
            before[key] = decision
        user.groups_id = [(4, self.env.ref('smart_construction_core.group_sc_role_experience').id)]
        for key in keys:
            self.assertEqual(capability_registry.capability_authorization_for_user(user, key), before[key])

    def test_admitted_entry_still_enforces_live_record_and_write_checks(self):
        from odoo.exceptions import AccessError
        from unittest.mock import patch
        user = self._actor(['smart_construction_core.group_sc_cap_project_read'])
        project = self.env['project.project'].create({'name': 'Execution boundary', 'code': 'EFFECTIVE-BOUNDARY'})
        action = self.env.ref('smart_construction_core.action_sc_project_list')
        menu = self.env.ref('smart_construction_core.menu_sc_project_project')
        with patch.object(capability_registry, '_published_query_pairs_by_action_id',
                          return_value={action.id: (menu.id, action.id)}):
            self.assertEqual(capability_registry.capability_authorization_for_user(user, 'project.list.open')['state'], 'allow')
        with self.assertRaises(AccessError):
            project.with_user(user).write({'name': 'Forbidden write'})
        self.env['ir.rule'].create({
            'name': 'Effective delivery test record exclusion',
            'model_id': self.env['ir.model']._get_id('project.project'),
            'domain_force': str([('id', '!=', project.id)]),
        })
        with self.assertRaises(AccessError):
            project.with_user(user).read(['name'])

    def test_record_rules_still_bound_project_queries(self):
        user = self._actor(['smart_construction_core.group_sc_cap_project_read'])
        model = self.env['project.project'].with_user(user)
        before_ids = model.search([]).ids
        capability_registry.list_capabilities_for_user(user.with_user(user).env, user)
        self.assertEqual(model.search([]).ids, before_ids)
        self.assertFalse(model.env.su)


    def test_standard_and_preview_publication_share_released_entries_but_not_principal_access(self):
        from odoo.addons.smart_core.delivery.delivery_engine import DeliveryEngine
        from odoo.addons.smart_core.delivery.menu_fact_service import MenuFactService
        from odoo.addons.smart_core.delivery.runtime_route_authority import published_pairs
        from odoo.addons.smart_core.identity.identity_resolver import IdentityResolver
        from ..core_extension_policy_maps import ROLE_SURFACE_OVERRIDES
        menus = [self.env.ref('smart_construction_core.' + key) for key in
                 ('menu_payment_ledger', 'menu_sc_treasury_ledger', 'menu_sc_settlement_order')]
        expected_pairs = {(menu.id, menu.action.id) for menu in menus}
        full = self._actor(['smart_construction_core.group_sc_business_full'], login='edition-full')
        restricted = self._actor([], login='edition-restricted')
        for user in (full, restricted):
            user_env = user.with_user(user).env
            facts = MenuFactService(user_env).export_visible_menu_facts()
            resolver = IdentityResolver(user_env)
            surface = resolver.build_role_surface(resolver.user_group_xmlids(user), facts.tree,
                                                  {'workspace.home'}, ROLE_SURFACE_OVERRIDES)
            engine = DeliveryEngine(user_env)
            for edition in ('standard', 'preview'):
                with self.subTest(user=user.login, edition=edition):
                    policy = engine.product_policy_service.get_policy(
                        product_key='construction.' + edition, edition_key=edition,
                        base_product_key='construction', enforce_release=True, enforce_access=True)
                    declared = {row['menu_xmlid'] for group in policy['menu_groups'] for row in group['menus']}
                    for menu in menus:
                        xmlid = menu.get_external_id()[menu.id]
                        self.assertIn(xmlid, declared)
                    delivery = engine.build(data={'role_surface': surface, 'scenes': [], 'capabilities': []},
                                            product_key='construction.' + edition, edition_key=edition,
                                            base_product_key='construction', native_nav=facts.tree)
                    pairs = published_pairs(delivery['route_authority'])
                    if user == full:
                        self.assertTrue(expected_pairs <= pairs, expected_pairs - pairs)
                    else:
                        self.assertFalse(expected_pairs & pairs)

    def test_all_query_bindings_follow_native_action_model_and_groups(self):
        user = self._actor([])
        definitions = [row for row in capability_registry.capability_definitions() if row.get('access_action')]
        self.assertEqual(len(definitions), 10)
        actors = [user, self._actor(['smart_construction_core.group_sc_cap_finance_read'], login='query-finance-reader'),
                  self._actor(['smart_construction_core.group_sc_cap_cost_read'], login='query-cost-reader')]
        for user in actors:
            for row in definitions:
                action = self.env.ref(row['access_action'])
                self.assertEqual(action._name, 'ir.actions.act_window')
                expected = bool((not action.groups_id or action.groups_id & user.groups_id)
                    and self.env[action.res_model].with_user(user).check_access_rights('read', raise_exception=False))
                expected = expected and bool(capability_registry._published_query_pair(user, action.id))
                verdict = capability_registry.capability_authorization_for_user(user, row['key'])
                self.assertEqual(verdict['state'], 'allow' if expected else 'deny', row['key'])
                self.assertFalse(row.get('required_roles'))
                self.assertFalse(row.get('access_model'))

    def test_reachable_scene_targets_replace_false_navigation_denials(self):
        from unittest.mock import patch

        user = self._actor(
            [
                'smart_construction_core.group_sc_cap_project_read',
                'smart_construction_core.group_sc_cap_finance_read',
                'smart_construction_core.group_sc_cap_contract_read',
            ],
            login='reachable-capability-targets',
        )
        env = user.with_user(user).env
        payment_action = env.ref(
            'smart_construction_core.action_payment_request_user_payment_apply'
        )
        payment_menu = env.ref('smart_construction_core.menu_sc_user_payment_apply')
        income_action = env.ref(
            'smart_construction_core.action_construction_contract_income'
        )
        income_menu = env.ref(
            'smart_construction_core.menu_sc_p1_income_contract'
        )
        expense_action = env.ref(
            'smart_construction_core.action_construction_contract_expense'
        )
        expense_menu = env.ref(
            'smart_construction_core.menu_sc_p1_expense_contract'
        )
        published_pairs = {
            payment_action.id: (payment_menu.id, payment_action.id),
            income_action.id: (income_menu.id, income_action.id),
            expense_action.id: (expense_menu.id, expense_action.id),
        }
        with patch.object(
            capability_registry,
            '_published_query_pairs_by_action_id',
            return_value=published_pairs,
        ):
            rows = {
                row['key']: row
                for row in capability_registry.list_capabilities_for_user(env, user)
            }
        self.assertEqual(rows['project.task.list']['state'], 'READY')
        self.assertEqual(
            rows['project.task.list']['default_payload']['scene_key'],
            'task.center',
        )
        self.assertEqual(rows['finance.payment_request.list']['state'], 'READY')
        self.assertEqual(
            rows['finance.payment_request.list']['default_payload']['route'],
            '/a/%s?menu_id=%s' % (
                env.ref('smart_construction_core.action_payment_request_user_payment_apply').id,
                env.ref('smart_construction_core.menu_sc_user_payment_apply').id,
            ),
        )
        self.assertNotIn('contract.center.open', rows)
        self.assertEqual(rows['contract.income.track']['state'], 'READY')
        self.assertEqual(rows['contract.expense.track']['state'], 'READY')

    def test_action_model_change_is_not_hidden_by_copied_model_binding(self):
        from unittest.mock import patch
        from odoo.addons.smart_core.delivery.menu_service import MenuService

        user = self._actor(['smart_construction_core.group_sc_cap_project_read'])
        action = self.env.ref('smart_construction_core.action_sc_project_list')
        menu = self.env.ref('smart_construction_core.menu_sc_project_project')
        with patch.object(
            capability_registry,
            '_published_query_pairs_by_action_id',
            side_effect=lambda actor: ({action.id: (menu.id, action.id)}
                if MenuService(actor.with_user(actor).env)._action_is_runtime_allowed(action.with_user(actor), "read") else {}),
        ):
            self.assertEqual(capability_registry.capability_authorization_for_user(user, 'project.list.open')['state'], 'allow')
            # Transactional test change is rolled back by TransactionCase.
            action.res_model = 'ir.config_parameter'
            self.assertFalse(self.env['ir.config_parameter'].with_user(user).check_access_rights('read', raise_exception=False))
            self.assertEqual(capability_registry.capability_authorization_for_user(user, 'project.list.open')['state'], 'deny')

    def test_native_action_group_change_is_honored_without_role_inference(self):
        user = self._actor(['smart_construction_core.group_sc_cap_project_read'])
        action = self.env.ref('smart_construction_core.action_sc_project_list')
        action.groups_id = [(6, 0, [self.env.ref('smart_core.group_smart_core_admin').id])]
        self.assertTrue(self.env['project.project'].with_user(user).check_access_rights('read', raise_exception=False))
        self.assertEqual(capability_registry.capability_authorization_for_user(user, 'project.list.open')['state'], 'deny')


    def test_query_navigation_and_authorization_use_same_native_action(self):
        from ..core_extension_capability_rows import normalize_capability_rows
        from odoo.addons.smart_construction_scene.services.capability_scene_targets import CAPABILITY_ENTRY_SCENE_MAP
        user = self._actor(['smart_construction_core.group_sc_cap_project_read'])
        env = user.with_user(user).env
        rows = {row['key']: row for row in normalize_capability_rows(capability_registry.list_capabilities_for_user(env, user))}
        matrix = capability_registry.build_capability_matrix_for_user(env, user)
        links = {row['key']: row for section in matrix['sections'] for row in section['items']}
        for definition in capability_registry.capability_definitions():
            if not definition.get('access_action') or not definition.get('visible', True):
                continue
            key = definition['key']
            action = env.ref(definition['access_action'])
            self.assertNotIn(key, CAPABILITY_ENTRY_SCENE_MAP)
            expected = {'target_mode': 'action', 'action_id': action.id, 'model': action.res_model}
            pair = capability_registry._published_query_pair(user, action.id)
            if pair:
                expected.update(menu_id=pair[0], route='/a/%s' % action.id + ('?menu_id=%s' % pair[0] if pair[0] else ''))
            self.assertEqual(rows[key]['entry_target'], expected)
            self.assertEqual(rows[key]['default_payload'], expected)
            self.assertEqual(links[key]['target_url'], expected.get('route'))
            self.assertFalse(links[key]['scene_key'])
        self.assertEqual(rows['contract.income.track']['default_payload']['model'], 'construction.contract.income')
        self.assertEqual(rows['contract.expense.track']['default_payload']['model'], 'construction.contract.expense')


    def test_unpublished_native_action_is_denied_and_has_no_route(self):
        from unittest.mock import patch
        from odoo.addons.smart_core.delivery import runtime_route_authority
        user = self._actor(['smart_construction_core.group_sc_cap_project_read'])
        self.assertTrue(self.env['project.project'].with_user(user).check_access_rights('read', raise_exception=False))
        with patch.object(runtime_route_authority, 'published_route_authority', return_value={}):
            decision = capability_registry.capability_authorization_for_user(user, 'project.list.open')
            self.assertEqual(decision['state'], 'deny')
            self.assertEqual(decision['reason_code'], 'NAVIGATION_AUTHORITY_DENIED')
            rows = capability_registry.list_capabilities_for_user(user.with_user(user).env, user)
            project = next(row for row in rows if row['key'] == 'project.list.open')
            self.assertNotIn('route', project['default_payload'])

    def test_registry_timing_hook_reaches_startup_provider(self):
        from odoo.addons.smart_core.core.capability_provider import (
            load_capabilities_for_user_with_timings,
        )

        user = self._actor(
            ['smart_construction_core.group_sc_role_project_manager'],
            login='timed-capability-registry',
        )
        env = user.with_user(user).env
        expected = {
            row["key"]: row
            for row in capability_registry.list_capabilities_for_user(env, user)
        }
        actual_rows, timings = load_capabilities_for_user_with_timings(env, user)
        actual = {row["key"]: row for row in actual_rows}
        self.assertEqual(set(actual), set(expected))
        for key in expected:
            for field in (
                "state",
                "capability_state",
                "capability_state_reason",
                "reason_code",
                "reason",
                "default_payload",
            ):
                self.assertEqual(actual[key][field], expected[key][field], (key, field))
        self.assertIn("published_route_authority", timings)
        self.assertIn("loop_resolve_capability_entry_target_payload", timings)
        self.assertIn("load_capabilities_for_user_total", timings)

    def test_capability_list_resolves_published_route_authority_once(self):
        from unittest.mock import patch
        from odoo.addons.smart_core.delivery.effective_delivery_service import EffectiveDeliveryService
        from odoo.addons.smart_core.delivery import runtime_route_authority

        user = self._actor(
            ['smart_construction_core.group_sc_cap_project_read'],
            login='single-route-authority-resolution',
        )
        env = user.with_user(user).env
        authority = runtime_route_authority.published_route_authority(env)
        with patch.object(
            EffectiveDeliveryService,
            'resolve',
            wraps=EffectiveDeliveryService.resolve,
        ) as resolver:
            rows = capability_registry.list_capabilities_for_user(
                env,
                user,
                published_authority=authority,
            )
        self.assertTrue(rows)
        resolver.assert_not_called()

    def test_capability_list_reuses_same_scope_published_authority(self):
        from unittest.mock import patch
        from odoo.addons.smart_core.delivery import runtime_route_authority

        user = self._actor(
            ['smart_construction_core.group_sc_cap_project_read'],
            login='same-scope-route-authority-reuse',
        )
        env = user.with_user(user).env
        authority = runtime_route_authority.published_route_authority(env)
        with patch.object(
            capability_registry,
            '_published_query_pairs_by_action_id',
            wraps=capability_registry._published_query_pairs_by_action_id,
        ) as pair_builder:
            rows = capability_registry.list_capabilities_for_user(
                env,
                user,
                published_authority=authority,
            )
        self.assertTrue(rows)
        pair_builder.assert_called_once()
        self.assertIs(
            pair_builder.call_args.kwargs.get('published_authority'),
            authority,
        )

    def test_capability_entry_targets_do_not_consume_request_route_authority(self):
        from unittest.mock import patch
        from odoo.addons.smart_core.delivery import runtime_route_authority
        from odoo.addons.smart_core.core.system_init_request_context import SystemInitRequestContext

        user = self._actor(
            ['smart_construction_core.group_sc_cap_project_read'],
            login='entry-target-route-authority-reuse',
        )
        env = user.with_user(user).env
        authority = runtime_route_authority.published_route_authority(env)
        request_context = SystemInitRequestContext(env)
        with patch.object(
            capability_registry,
            'build_capability_entry_target',
            wraps=capability_registry.build_capability_entry_target,
        ) as build_target, patch.object(
            capability_registry,
            'resolve_capability_entry_target_payload_with_timings',
            wraps=capability_registry.resolve_capability_entry_target_payload_with_timings,
        ) as resolve_payload:
            rows = capability_registry.list_capabilities_for_user(
                env,
                user,
                published_authority=authority,
                request_context=request_context,
            )

        self.assertTrue(rows)
        self.assertTrue(build_target.call_args_list)
        self.assertTrue(resolve_payload.call_args_list)
        for call in build_target.call_args_list:
            self.assertNotIn('published_authority', call.kwargs)
            self.assertIs(call.kwargs.get('request_context'), request_context)
        for call in resolve_payload.call_args_list:
            self.assertNotIn('published_authority', call.kwargs)
            self.assertIs(call.kwargs.get('request_context'), request_context)

    def test_cached_published_query_pairs_match_legacy_first_match(self):
        from odoo.addons.smart_core.delivery.runtime_route_authority import (
            iter_published_pairs,
            published_route_authority,
        )

        user = self._actor(
            ['smart_construction_core.group_sc_cap_project_read'],
            login='cached-published-pairs',
        )
        authority = published_route_authority(user.with_user(user).env)
        published_pairs = list(iter_published_pairs(authority))
        cached_pairs = capability_registry._published_query_pairs_by_action_id(user)
        for _menu_id, action_id in published_pairs:
            if action_id <= 0:
                continue
            legacy = next((pair for pair in published_pairs if pair[1] == action_id), None)
            self.assertEqual(cached_pairs.get(action_id), legacy)

@tagged("post_install", "-at_install", "formal_role_hint")
class TestFormalRoleHint(TransactionCase):
    def test_hints_match_declared_identity_bindings(self):
        from odoo.addons.smart_core.identity.identity_resolver import IdentityResolver
        resolver = IdentityResolver(self.env)
        groups = ('smart_construction_core.group_sc_cap_finance_user',
                  'smart_construction_core.group_sc_cap_finance_manager',
                  'smart_construction_core.group_sc_cap_cost_user',
                  'smart_construction_core.group_sc_role_experience')
        for group in groups:
            declared = resolver.assigned_role_codes({group})
            self.assertTrue(declared)
            self.assertEqual(capability_registry.role_code_for_group(group, env=self.env), declared[0])
        self.assertEqual(capability_registry.role_code_for_group(groups[0], env=self.env), 'finance')

    def test_undeclared_groups_never_gain_role_hint_from_spelling(self):
        for group in ('smart_construction_core.group_sc_role_invented',
                      'smart_construction_core.group_sc_cap_contract_user', ''):
            self.assertEqual(capability_registry.role_code_for_group(group, env=self.env), '')
