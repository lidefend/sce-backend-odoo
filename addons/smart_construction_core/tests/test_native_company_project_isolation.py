"""Real native ORM witnesses for AUTH-02; no mocked ACL/rule executor."""
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged
from odoo.addons.smart_core.tests.platform_company_test_support import license_multi_company
from .business_case import BusinessTransactionCase


@tagged('post_install', '-at_install', 'auth02_native_isolation')
class TestNativeCompanyProjectIsolation(BusinessTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.env.user.company_id = cls.company_a
        cls.company_b = cls.env['res.company'].create({'name': 'AUTH02 group subsidiary B', 'parent_id': cls.company_a.id})
        cls.register_business_company(cls.company_b)
        cls.actor = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Native scope actor', 'login': 'auth02-native-scope',
            'company_id': cls.company_a.id, 'company_ids': [(6, 0, (cls.company_a | cls.company_b).ids)],
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id, cls.env.ref('project.group_project_user').id])],
        })
        cls.project_a = cls.env['project.project'].create({
            'name': 'Private A', 'company_id': cls.company_a.id,
            'user_id': cls.env.uid, 'privacy_visibility': 'followers',
        })
        cls.project_b = cls.env['project.project'].create({
            'name': 'Private B', 'company_id': cls.company_b.id,
            'user_id': cls.env.uid, 'privacy_visibility': 'followers',
        })

    def _projects(self, companies):
        return self.env['project.project'].with_user(self.actor).with_context(allowed_company_ids=companies.ids)

    def _membership(self, project):
        return self.env['sc.project.member.assignment'].create({'project_id': project.id, 'user_id': self.actor.id})

    def test_native_company_context_cannot_select_an_unassigned_company(self):
        other = self.env['res.company'].create({'name': 'Not assigned'})
        with self.assertRaises(AccessError):
            self._projects(other).env.companies

    def test_native_membership_does_not_bypass_platform_license(self):
        self._membership(self.project_b)
        with self.assertRaises(AccessError):
            self._projects(self.company_b).browse(self.project_b.id).read(['name'])

    def test_private_project_requires_native_membership(self):
        projects = self._projects(self.company_a)
        self.assertFalse(projects.search([('id', '=', self.project_a.id)]))
        membership = self._membership(self.project_a)
        self.assertEqual(projects.browse(self.project_a.id).read(['name'])[0]['name'], 'Private A')
        membership.write({'active': False})
        self.assertFalse(projects.search([('id', '=', self.project_a.id)]))

    def test_project_membership_never_crosses_company_ceiling(self):
        license_multi_company(self.env, self.company_a)
        self._membership(self.project_a)
        self._membership(self.project_b)
        self.assertFalse(self._projects(self.company_a).search([('id', '=', self.project_b.id)]))
        with self.assertRaises(AccessError):
            self._projects(self.company_a).browse(self.project_b.id).read(['name'])
        self.assertEqual(self._projects(self.company_b).browse(self.project_b.id).read(['name'])[0]['name'], 'Private B')

    def test_native_manager_group_cannot_override_global_company_rule(self):
        license_multi_company(self.env, self.company_a)
        self.actor.write({'groups_id': [(4, self.env.ref('project.group_project_manager').id)]})
        self.assertTrue(self._projects(self.company_a).search([('id', '=', self.project_a.id)]))
        self.assertFalse(self._projects(self.company_a).search([('id', '=', self.project_b.id)]))

    def test_group_rules_union_but_global_company_rule_intersects(self):
        license_multi_company(self.env, self.company_a)
        group = self.env['res.groups'].create({'name': 'Synthetic permissive project rule'})
        self.env['ir.rule'].create({
            'name': 'Synthetic group rule OR witness',
            'model_id': self.env['ir.model']._get_id('project.project'),
            'groups': [(6, 0, group.ids)], 'domain_force': '[(1, "=", 1)]',
        })
        self.actor.write({'groups_id': [(4, group.id)]})
        self.assertTrue(self._projects(self.company_a).search([('id', '=', self.project_a.id)]))
        self.assertFalse(self._projects(self.company_a).search([('id', '=', self.project_b.id)]))

    def test_native_group_membership_is_not_company_dependent(self):
        license_multi_company(self.env, self.company_a)
        for company in (self.company_a, self.company_b):
            user = self.actor.with_user(self.actor).with_context(allowed_company_ids=company.ids)
            self.assertTrue(user.has_group('project.group_project_user'))

    def test_native_relation_consistency_rejects_cross_company_task(self):
        license_multi_company(self.env, self.company_a)
        self._membership(self.project_b)
        tasks = self.env['project.task'].with_user(self.actor).with_context(allowed_company_ids=(self.company_a | self.company_b).ids)
        with self.assertRaises(UserError) as caught, self.env.cr.savepoint():
            tasks.create({'name': 'Invalid cross-company task', 'company_id': self.company_a.id, 'project_id': self.project_b.id})
        self.assertIs(type(caught.exception), UserError)

    def test_industry_task_enables_native_consistency_and_accepts_same_company(self):
        self._membership(self.project_a)
        tasks = self.env['project.task'].with_user(self.actor).with_context(allowed_company_ids=self.company_a.ids)
        self.assertTrue(tasks._check_company_auto)
        self.assertTrue(tasks._fields['project_id'].check_company)
        task = tasks.create({'name': 'Valid company task', 'company_id': self.company_a.id, 'project_id': self.project_a.id})
        self.assertEqual(task.company_id, self.company_a)
        self.assertEqual(task.project_id, self.project_a)

    def test_group_parent_company_does_not_implicitly_grant_subsidiary(self):
        self.actor.write({'company_ids': [(6, 0, self.company_a.ids)]})
        license_multi_company(self.env, self.company_a)
        self.assertEqual(self.company_b.parent_id, self.company_a)
        with self.assertRaises(AccessError):
            self._projects(self.company_b).env.companies
