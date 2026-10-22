# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_construction_core.services import capability_registry


@tagged("sc_smoke", "capability_registry")
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
        with patch.object(capability_provider, "call_extension_hook_first", return_value=[]) as hook:
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
        with patch.object(capability_provider, "call_extension_hook_first", return_value=None):
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
        user = self._actor(['smart_construction_core.group_sc_cap_project_read'])
        model = self.env['project.project'].with_user(user)
        self.assertTrue(model.check_access_rights('read', raise_exception=False))
        self.assertFalse(model.check_access_rights('write', raise_exception=False))
        roles = capability_registry._resolve_role_codes_for_user(user)
        self.assertNotIn('pm', roles)
        decision = capability_registry.capability_authorization_for_user(user, 'project.list.open')
        self.assertEqual(decision['state'], 'allow')
        rows = capability_registry.list_capabilities_for_user(user.with_user(user).env, user)
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

    def test_record_rules_still_bound_project_queries(self):
        user = self._actor(['smart_construction_core.group_sc_cap_project_read'])
        model = self.env['project.project'].with_user(user)
        before_ids = model.search([]).ids
        capability_registry.list_capabilities_for_user(user.with_user(user).env, user)
        self.assertEqual(model.search([]).ids, before_ids)
        self.assertFalse(model.env.su)


    def test_preview_publication_and_principal_access_are_independent(self):
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
                        self.assertEqual(xmlid in declared, edition == 'preview')
                    delivery = engine.build(data={'role_surface': surface, 'scenes': [], 'capabilities': []},
                                            product_key='construction.' + edition, edition_key=edition,
                                            base_product_key='construction', native_nav=facts.tree)
                    pairs = published_pairs(delivery['route_authority'])
                    if user == full and edition == 'preview':
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
            '_published_query_pair',
            side_effect=lambda _user, action_id: published_pairs.get(action_id),
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
        user = self._actor(['smart_construction_core.group_sc_cap_project_read'])
        action = self.env.ref('smart_construction_core.action_sc_project_list')
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
