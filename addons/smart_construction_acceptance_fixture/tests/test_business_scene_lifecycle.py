from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.delivery.runtime_route_authority import (
    menu_publication_decision, published_route_authority,
)


@tagged("post_install", "-at_install", "acceptance_business_scene_lifecycle")
class TestBusinessSceneLifecycle(TransactionCase):
    """Native company/permission behavior; TransactionCase rolls back all toggles."""

    def setUp(self):
        super().setUp()
        self.finance = self.env.ref('smart_construction_acceptance_fixture.fe_user_finance')
        self.company_a = self.env.ref('smart_construction_acceptance_fixture.fe_company_a')
        self.company_b = self.env.ref('smart_construction_acceptance_fixture.fe_company_b')
        self.menu = self.env.ref('smart_construction_core.menu_sc_user_payment_apply')
        self.states = self.env['sc.scene.company.enablement'].sudo()
        # These cases verify company revocation against a released policy.
        # Build that prerequisite inside TransactionCase, independently of
        # maintained policy rows or a full product release snapshot.
        policy = self.env['sc.product.policy'].sudo()
        policy.search([('product_key', 'in', [
            'construction.standard', 'construction.preview',
        ])]).unlink()
        policy.sync_construction_menu_product_policies()

    def _state(self, company):
        row = self.states.search([('company_id', '=', company.id),
                                  ('scene_key', '=', 'business.v1:payment.capital')])
        self.assertEqual(len(row), 1, 'run the governed fixture before lifecycle acceptance')
        return row

    def _actor(self, company):
        return self.env(user=self.finance.id, context=dict(
            self.env.context, allowed_company_ids=[company.id]))

    def _allowed(self, company):
        authority = published_route_authority(self._actor(company))
        self.assertTrue(authority, 'authority construction must succeed')
        return menu_publication_decision(authority, self.menu.id, self.menu.action.id)

    def test_company_scene_state_does_not_replace_role_navigation_authority(self):
        a, b = self._state(self.company_a), self._state(self.company_b)
        a.set_enabled(True)
        b.set_enabled(True)
        self.assertTrue(self._allowed(self.company_a))
        self.assertTrue(self._allowed(self.company_b))
        a.set_enabled(False)
        self.assertTrue(self._allowed(self.company_a))
        self.assertTrue(self._allowed(self.company_b))
        a.set_enabled(True)
        self.assertTrue(self._allowed(self.company_a))

    def test_project_kanban_fixture_binding_is_released_for_all_business_roles(self):
        menu = self.env.ref("smart_construction_core.menu_sc_project_kanban")
        entry = self.env["sc.product.scenario.entry"].sudo().search(
            [("menu_id", "=", menu.id)],
            limit=1,
        )
        self.assertTrue(entry, "project Kanban must have an acceptance scenario binding")
        self.assertEqual(entry.scenario_id.code, "project.management")

        for login in (
            "fixture_role_config_admin",
            "fixture_role_pm",
            "fixture_role_project_a_member",
        ):
            user = self.env["res.users"].sudo().search([("login", "=", login)], limit=1)
            self.assertTrue(user, login)
            actor = self.env(
                user=user.id,
                context=dict(
                    self.env.context,
                    allowed_company_ids=[self.company_a.id],
                    company_id=self.company_a.id,
                ),
            )
            authority = published_route_authority(actor)
            self.assertTrue(
                menu_publication_decision(authority, menu.id, menu.action.id),
                "%s must receive the released project Kanban route" % login,
            )
            self.assertTrue(
                actor["project.project"].check_access_rights("read", raise_exception=False),
                "%s must retain project read ACL" % login,
            )
            self.assertGreater(
                actor["project.project"].search_count([
                    ("company_id", "=", self.company_a.id),
                ]),
                0,
                "%s must receive the fixture company's project data" % login,
            )

    def test_payment_approval_fixture_assigns_a_real_current_reviewer(self):
        request = self.env.ref(
            "smart_construction_acceptance_fixture.fe_journey_payment_request_approval_a"
        )
        reviewer = self.env.ref(
            "smart_construction_acceptance_fixture.fe_user_finance_reviewer"
        )
        pending = request.review_ids.filtered(
            lambda review: review.status in ("waiting", "pending")
        )
        self.assertTrue(pending, "the approval fixture must contain a live review instance")
        self.assertIn(reviewer, pending.mapped("reviewer_ids"))
        self.assertTrue(
            request.with_user(reviewer).with_context(
                allowed_company_ids=[self.company_a.id],
                company_id=self.company_a.id,
            ).can_review,
            "the assigned finance reviewer must own the current approval step",
        )
        member = self.env.ref(
            "smart_construction_acceptance_fixture.fe_user_project_a_member"
        )
        self.assertFalse(request.with_user(member).can_review)

    def test_missing_scenario_state_does_not_remove_role_authority(self):
        self._state(self.company_a).unlink()
        self.assertTrue(self._allowed(self.company_a))
        self.states.create({'company_id': self.company_a.id,
                            'scene_key': 'finance.payment_requests', 'enabled': True})
        self.assertTrue(self._allowed(self.company_a))

    def test_finance_cannot_enable_scenes_or_read_another_active_company(self):
        a, b = self._state(self.company_a), self._state(self.company_b)
        actor = self._actor(self.company_a)
        with self.assertRaises(AccessError), self.cr.savepoint():
            a.with_env(actor).set_enabled(not a.enabled)
        self.assertFalse(actor['sc.scene.company.enablement'].search([('id', '=', b.id)]))

    def test_maintained_membership_drives_scenario_catalog_without_seed_file(self):
        from unittest.mock import patch
        from odoo.addons.smart_construction_core.services import scenario_surface_projection
        from odoo.addons.smart_construction_scene.services.tenant_scene_activation import write_tenant_enablement
        from odoo.addons.smart_construction_scene.handlers.scenario_activation import _catalog
        entry = self.env['sc.product.scenario.entry'].sudo().search([('menu_id', '=', self.menu.id)])
        self.assertEqual(len(entry), 1)
        replacement = self.env['sc.product.scenario'].sudo().create({
            'code': 'test.maintained.payment', 'name': 'Maintained payment',
        })
        entry.scenario_id = replacement
        with patch.object(scenario_surface_projection, 'load_surface', side_effect=AssertionError('runtime read seed')):
            write_tenant_enablement(self.env, self.company_a.id, 'business.v1:test.maintained.payment', True)
            self.assertTrue(self._allowed(self.company_b))
            replacement.name = 'Renamed payment'
            rows = _catalog(self.env, self.company_a.id)['business_scenarios']
            row = next(row for row in rows if row['scene_key'] == replacement.code)
            self.assertEqual(row['name'], 'Renamed payment')
            self.assertTrue(row['tenant_enabled'])
            replacement.active = False
            row = next(row for row in _catalog(self.env, self.company_a.id)['business_scenarios']
                       if row['scene_key'] == replacement.code)
            self.assertFalse(row['product_released'])
            replacement.active = True
            row = next(row for row in _catalog(self.env, self.company_a.id)['business_scenarios']
                       if row['scene_key'] == replacement.code)
            self.assertTrue(row['tenant_enabled'])
            entry.unlink()
            row = next(row for row in _catalog(self.env, self.company_a.id)['business_scenarios']
                       if row['scene_key'] == replacement.code)
            self.assertFalse(row['product_released'])
            self.menu.sc_scenario_exempt = True
            self.assertTrue(self._allowed(self.company_a))
            self.menu.sc_scenario_exempt = False
            self.assertTrue(self._allowed(self.company_a))

    def test_binding_clears_old_exemption_and_identity_cannot_be_renamed(self):
        from odoo.exceptions import ValidationError
        for code in (' test.ambiguous ', '   '):
            with self.assertRaises(ValidationError), self.cr.savepoint():
                self.env['sc.product.scenario'].sudo().create({'code': code, 'name': 'Invalid identity'})
        entry = self.env['sc.product.scenario.entry'].sudo().search([('menu_id', '=', self.menu.id)])
        scenario = entry.scenario_id
        with self.assertRaises(ValidationError), self.cr.savepoint():
            scenario.code = 'test.reassigned.identity'
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.menu.sc_scenario_exempt = True
        entry.unlink()
        self.menu.sc_scenario_exempt = True
        rebound = self.env['sc.product.scenario.entry'].sudo().create({
            'menu_id': self.menu.id, 'scenario_id': scenario.id,
        })
        self.assertFalse(self.menu.sc_scenario_exempt)
        rebound.unlink()
        self.assertTrue(self._allowed(self.company_a))

    def test_exemption_migration_does_not_revive_deleted_business_binding(self):
        scenario = self.env['sc.product.scenario'].sudo()
        params = self.env['ir.config_parameter'].sudo()
        marker = 'smart_construction_core.scenario_entry_scope.v1'
        entry = self.env['sc.product.scenario.entry'].sudo().search([('menu_id', '=', self.menu.id)])
        entry.unlink()
        direct = self.env['ir.ui.menu'].sudo().create({
            'name': 'Explicit direct test entry', 'sc_scenario_exempt': True, 'action': 'ir.actions.act_window,%s' % self.menu.action.id,
        })
        params.set_param(marker, False)
        scenario.initialize_direct_entry_exemptions()
        self.assertTrue(direct.sc_scenario_exempt)
        self.assertFalse(self.menu.sc_scenario_exempt)
        direct.sc_scenario_exempt = False
        scenario.initialize_direct_entry_exemptions()
        self.assertFalse(direct.sc_scenario_exempt)

    def test_custom_binding_deleted_before_upgrade_stays_unconfigured(self):
        Scenario = self.env['sc.product.scenario'].sudo()
        Entry = self.env['sc.product.scenario.entry'].sudo()
        Menu = self.env['ir.ui.menu'].sudo()
        params = self.env['ir.config_parameter'].sudo()
        marker = 'smart_construction_core.scenario_entry_scope.v1'
        custom = Scenario.create({'code': 'test.custom.deleted', 'name': 'Custom'})
        action = 'ir.actions.act_window,%s' % self.menu.action.id
        for vals in ({'name': 'Custom action', 'action': action},
                     {'name': 'Custom actionless leaf'}):
            menu = Menu.create(vals)
            # Previously explicit direct entries also lose their exemption
            # when bound. Deletion must not resurrect the prior declaration.
            menu.sc_scenario_exempt = True
            entry = Entry.create({'scenario_id': custom.id, 'menu_id': menu.id})
            self.assertFalse(menu.sc_scenario_exempt)
            entry.unlink()
            params.set_param(marker, False)
            Scenario.initialize_direct_entry_exemptions()
            self.assertFalse(menu.sc_scenario_exempt)
            self.assertTrue(params.get_param(marker))
            Scenario.initialize_direct_entry_exemptions()
            self.assertFalse(menu.sc_scenario_exempt)
        unknown = Menu.create({'name': 'Unknown history', 'action': action})
        params.set_param(marker, False)
        Scenario.initialize_direct_entry_exemptions()
        self.assertFalse(unknown.sc_scenario_exempt)
        # Missing history can only be resolved by an explicit maintenance act.
        unknown.sc_scenario_exempt = True
        Scenario.initialize_direct_entry_exemptions()
        self.assertTrue(unknown.sc_scenario_exempt)

    def test_business_diagnosis_consumes_same_catalog_without_composition_record(self):
        from odoo.addons.smart_construction_scene.handlers.scenario_activation import _catalog
        from odoo.addons.smart_construction_scene.services.scenario_dependency_diagnosis import diagnose_scenario_dependencies
        entry = self.env['sc.product.scenario.entry'].sudo().search([('menu_id', '=', self.menu.id)])
        scenario = entry.scenario_id
        for active in (True, False):
            scenario.active = active
            row = next(row for row in _catalog(self.env, self.company_a.id)['business_scenarios']
                       if row['scene_key'] == scenario.code)
            diagnosis = diagnose_scenario_dependencies(self.env,
                scene_key='business.v1:' + scenario.code, company_id=self.company_a.id)
            self.assertEqual(diagnosis['enable_allowed'], row['product_released'])
            self.assertFalse(diagnosis['publication']['scene_composition']['applicable'])

    def test_native_entry_does_not_require_composition_release(self):
        from odoo.addons.smart_construction_scene.services.scenario_dependency_diagnosis import diagnose_scenario_dependencies
        Scene = self.env['sc.scene'].sudo()
        scene = Scene.search([('code', '=', 'enterprise.setup')], limit=1)
        if not scene:
            scene = Scene.create({'code': 'enterprise.setup', 'name': 'Native entry diagnosis test'})
        scene.state = 'draft'
        diagnosis = diagnose_scenario_dependencies(self.env, scene_key='enterprise.setup', company_id=self.company_a.id)
        self.assertEqual(diagnosis['dependencies'][0]['evidence']['readiness_kind'], 'native_action', diagnosis)
        self.assertTrue(diagnosis['dependencies'][0]['evidence']['structure_ready'])
        self.assertEqual(diagnosis['enable_allowed'], diagnosis['publication']['native_capability']['entry_qualified'])
        self.assertFalse(diagnosis['publication']['scene_composition']['applicable'])
        menu = self.env.ref('smart_construction_core.menu_sc_enterprise_initialization')
        menu.action = False
        invalid = diagnose_scenario_dependencies(self.env, scene_key='enterprise.setup', company_id=self.company_a.id)
        self.assertFalse(invalid['dependencies'][0]['evidence']['structure_ready'])
        self.assertFalse(invalid['enable_allowed'])

    def test_composition_has_its_own_version_and_edition_release(self):
        from odoo.addons.smart_construction_scene.services.scenario_dependency_diagnosis import diagnose_scenario_dependencies
        Scene = self.env['sc.scene'].sudo()
        scene = Scene.search([('code', '=', 'projects.detail')], limit=1)
        if not scene:
            scene = Scene.create({'code': 'projects.detail', 'name': 'Composition diagnosis test'})
        version = self.env['sc.scene.version'].sudo().create({
            'scene_id': scene.id, 'version': 'test-diagnosis', 'payload_json': {'scene_key': scene.code},
            'product_release_state': 'PREVIEW', 'product_edition': 'construction.standard',
        })
        scene.write({'state': 'published', 'active_version_id': version.id})
        def diagnose():
            return diagnose_scenario_dependencies(self.env, scene_key=scene.code, company_id=self.company_a.id)
        result = diagnose()
        self.assertTrue(result['publication']['native_capability']['entry_qualified'])
        self.assertTrue(result['publication']['scene_composition']['snapshot_published'])
        self.assertFalse(result['enable_allowed'])
        version.product_release_state = 'STANDARD_RELEASE'
        self.assertTrue(diagnose()['enable_allowed'])
        version.product_edition = 'construction.preview'
        self.assertFalse(diagnose()['enable_allowed'])
        version.product_edition = 'construction.standard'
        other = Scene.create({'code': 'test.other.composition', 'name': 'Other composition'})
        version.scene_id = other
        self.assertFalse(diagnose()['enable_allowed'])

    def test_direct_handoff_does_not_erase_published_composition_content(self):
        from odoo.addons.smart_construction_scene.services.scenario_dependency_diagnosis import diagnose_scenario_dependencies
        Scene = self.env['sc.scene'].sudo()
        scene = Scene.search([('code', '=', 'projects.list')], limit=1)
        if not scene:
            scene = Scene.create({'code': 'projects.list', 'name': 'Composed list test'})
        version = self.env['sc.scene.version'].sudo().create({
            'scene_id': scene.id, 'version': 'test-hidden-composition',
            'payload_json': {'tiles': [{'key': 'restricted', 'groups_xmlids': ['base.group_system']}]},
            'product_release_state': 'PREVIEW',
        })
        scene.write({'state': 'published', 'active_version_id': version.id})
        result = diagnose_scenario_dependencies(self._actor(self.company_a),
            scene_key='projects.list', company_id=self.company_a.id)
        self.assertEqual(result['dependencies'][0]['evidence']['readiness_kind'], 'orchestration')
        self.assertTrue(result['publication']['scene_composition']['applicable'])
        self.assertFalse(result['enable_allowed'])
