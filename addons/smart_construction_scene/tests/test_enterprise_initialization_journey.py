"""Real company initialization, including Scene-owned activation authority."""
from odoo.tests.common import tagged
from odoo.exceptions import AccessError
from odoo.addons.smart_construction_core.tests.business_case import BusinessTransactionCase


@tagged("post_install", "-at_install", "enterprise_initialization_journey")
class TestEnterpriseInitializationJourney(BusinessTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sc.core.extension_modules", "smart_construction_core,smart_construction_scene"
        )
        cls.env.user.write({'company_ids': [(4, cls.env.company.id)]})
        cls.internal = cls.env.ref('base.group_user')
        cls.manager = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Synthetic role maintainer', 'login': 'auth01_role_maintainer',
            'company_id': cls.env.company.id, 'company_ids': [(6, 0, cls.env.company.ids)],
            'groups_id': [(6, 0, (cls.internal | cls.env.ref('smart_construction_core.group_sc_cap_business_config_admin')).ids)],
        })
        cls.job_a = cls.env['hr.job'].create({'name': 'Synthetic position A', 'company_id': cls.env.company.id})
        cls.job_b = cls.env['hr.job'].create({'name': 'Synthetic position B', 'company_id': cls.env.company.id})

    def _group(self, suffix):
        return self.env.ref('smart_construction_core.group_sc_role_' + suffix)

    def _subject(self, suffix, extra=None):
        group = self._group(suffix)
        self.assertTrue(group.sc_assignable_user_permission)
        groups = self.internal | group
        if extra:
            groups |= self._group(extra)
        return self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Synthetic separation ' + suffix, 'login': 'auth01_separation_' + suffix,
            'company_id': self.env.company.id, 'company_ids': [(6, 0, self.env.company.ids)],
            'groups_id': [(6, 0, groups.ids)],
        })

    def _managed(self, user):
        return user.with_user(self.manager).with_context(sc_runtime_user_management=True)

    def test_enterprise_initialization_configuration_journey(self):
        import secrets
        from odoo.addons.smart_construction_scene.handlers.enterprise_readiness import EnterpriseReadinessDiagnosisGetHandler
        from odoo.addons.smart_construction_scene.handlers.scenario_activation import ScenarioActivationSetHandler
        company = self.env.company
        self.env["ir.config_parameter"].sudo().set_param("smart_core.platform_release_db", self.env.cr.dbname)
        self.env["project.project"].create({"name": "Synthetic initialization project", "company_id": company.id})
        actor = self.env['res.company'].with_user(self.manager).with_context(allowed_company_ids=company.ids).env
        from odoo.addons.smart_core.delivery.native_config_menu_projection import native_config_delivery_groups
        menu_xmlid = 'smart_construction_core.menu_sc_enterprise_initialization'
        menu = self.env.ref(menu_xmlid)
        self.assertIn(menu.id, actor['ir.ui.menu']._visible_menu_ids())
        projected = [row for group in native_config_delivery_groups(actor) for row in group['menus']
                     if row['menu_xmlid'] == menu_xmlid]
        self.assertEqual(len(projected), 1)
        target = projected[0]['entry_target']
        self.assertEqual(target['route'], f'/a/{menu.action.id}?menu_id={menu.id}')
        self.assertEqual(target['subject'], 'action')
        self.assertEqual(target['action_id'], menu.action.id)
        self.assertEqual(target['model'], menu.action.res_model)
        from odoo.addons.smart_core.delivery.runtime_route_authority import published_route_authority, menu_publication_decision
        self.assertTrue(menu_publication_decision(published_route_authority(actor), menu.id, menu.action.id))
        ordinary_actor = actor(user=self._subject('general_user').id)
        self.assertNotIn(menu.id, ordinary_actor['ir.ui.menu']._visible_menu_ids())
        diagnose = EnterpriseReadinessDiagnosisGetHandler(actor)
        def rules():
            result = diagnose.run(payload={'intent': 'enterprise.readiness.diagnosis.get', 'params': {'company_id': company.id}})
            self.assertTrue(result['ok'], result)
            self.assertEqual(result['data']['contract_version'], 'enterprise_readiness.v2')
            self.assertEqual(result['data']['company_id'], company.id)
            self.assertEqual(len(result['data']['rules']), 12)
            return {row['rule_key']: row for row in result['data']['rules']}
        before = rules()
        department = actor['hr.department'].create({'name': 'Synthetic initialization department', 'company_id': company.id})
        job = actor['hr.job'].create({'name': 'Synthetic initialization position', 'company_id': company.id})
        user = actor['res.users'].with_context(sc_runtime_user_management=True, no_reset_password=True).create({
            'name': 'Synthetic initialization employee', 'login': 'initialization_journey_employee',
            'password': secrets.token_urlsafe(24),
            'company_id': company.id, 'company_ids': [(6, 0, company.ids)],
            'sc_personnel_department_id': department.id, 'sc_personnel_job_id': job.id,
        })
        self.assertEqual(user.employee_id.department_id, department)
        self.assertEqual(user.employee_id.job_id, job)
        self.assertFalse(self._group('general_user') in user.groups_id)
        self._managed(user).write({'sc_user_role_group_ids': [(6, 0, self._group('general_user').ids)]})
        self.assertIn(self._group('general_user'), user.groups_id)
        self.assertEqual(user.employee_id.job_id, job)
        after = rules()
        for key, count in [('organization', 'department_count'), ('positions', 'job_count'),
                           ('user_employee_link', 'linked_employee_count'), ('user_org_position', 'positioned_employee_count')]:
            self.assertEqual(after['enterprise.' + key]['evidence'][count], before['enterprise.' + key]['evidence'][count] + 1)
        self.assertEqual(after['enterprise.roles']['remediation']['key'], 'smart_construction_core.action_sc_product_data_permission_v1')
        self.assertEqual(after['enterprise.employees']['remediation']['key'], 'smart_construction_core.action_sc_runtime_user_management')
        self.env['sc.scene.company.enablement'].create({'company_id': company.id, 'scene_key': 'enterprise.setup', 'enabled': True})
        self.assertEqual(rules()['enterprise.scenario_enablement']['evidence']['enabled_scene_count'], 0)
        from odoo.addons.smart_core.delivery.edition_release_snapshot_service import EditionReleaseSnapshotService
        EditionReleaseSnapshotService(self.env).freeze_release_surface(
            product_key="construction.standard", version="synthetic-initialization-journey",
            note="Rolled-back initialization journey fixture", replace_active=True,
        )
        activation = ScenarioActivationSetHandler(actor)
        from odoo.addons.smart_core.security.intent_authorization import authorize_intent
        self.assertTrue(authorize_intent(actor, 'scenario.activation.set', {})['allowed'])
        with self.assertRaises(AccessError):
            authorize_intent(actor(user=user.id), 'scenario.activation.set', {})
        params = {'company_id': company.id, 'scene_key': 'project.initiation', 'enablement_scope': 'business.v1'}
        self.assertTrue(activation.run(payload={'intent': 'scenario.activation.set', 'params': {**params, 'enabled': True}})['ok'])
        enabled = rules()
        self.assertEqual(enabled['enterprise.scenario_enablement']['evidence']['enabled_scene_count'], 1)
        self.assertTrue(enabled['enterprise.project_responsibility']['applicability'])
        self.assertEqual(enabled['enterprise.project_responsibility']['remediation']['key'], 'smart_construction_core.action_sc_product_data_permission_v1')
        self.assertEqual(enabled['enterprise.scenario_dependencies']['status'], 'NOT_EVALUATED')
        self.assertEqual(enabled['enterprise.role_delivery']['status'], 'NOT_EVALUATED')
        self.assertTrue(activation.run(payload={'intent': 'scenario.activation.set', 'params': {**params, 'enabled': False}})['ok'])
        self.assertFalse(rules()['enterprise.project_responsibility']['applicability'])
        self.assertEqual(rules()['enterprise.scenario_enablement']['evidence']['enabled_scene_count'], 0)
        ordinary = EnterpriseReadinessDiagnosisGetHandler(actor(user=user.id))
        self.assertEqual(ordinary.handle({'company_id': company.id})['error']['code'], 403)
        self.assertEqual(diagnose.handle({'company_id': True})['error']['code'], 400)
