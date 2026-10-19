"""Real HTTP revocation with rollback-only fixtures and existing namespace authority."""
import json
import secrets

from odoo.tests.common import HttpCase, tagged
from odoo.addons.smart_core.security.namespace_resolver import (
    _config, SHARED_SECRET_PARAM, SHARED_SECRET_ENV,
    ROUTE_VERSION_PARAM, ROUTE_VERSION_ENV,
)
from odoo.addons.smart_core.tests.test_intent_smoke import setup_test_entry_namespace
from .business_case import BusinessTransactionCase


@tagged('post_install', '-at_install', 'system_permission_http')
class TestSystemPermissionHttp(BusinessTransactionCase, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.write({'company_ids': [(4, cls.env.company.id)]})
        cls.password = secrets.token_urlsafe(32)
        internal = cls.env.ref('base.group_user')
        cls.role = cls.env.ref('smart_construction_core.group_sc_role_partner_manager')
        cls.subject = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Synthetic HTTP permission subject', 'login': 'auth01_http_subject',
            'password': cls.password,
            'company_id': cls.env.company.id, 'company_ids': [(6, 0, cls.env.company.ids)],
            'groups_id': [(6, 0, (internal | cls.role).ids)],
        })
        cls.manager = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Synthetic HTTP permission manager', 'login': 'auth01_http_manager',
            'company_id': cls.env.company.id, 'company_ids': [(6, 0, cls.env.company.ids)],
            'groups_id': [(6, 0, (internal | cls.env.ref('smart_construction_core.group_sc_cap_business_config_admin')).ids)],
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Synthetic HTTP revoked-role blacklist target', 'company_id': cls.env.company.id,
        })

    def _existing_entry(self):
        # Reuse the registered smoke namespace fixture, only inside the test transaction.
        setup_test_entry_namespace(self.env)
        namespace = self.env['sc.platform.namespace'].sudo().search([
            ('database_name', '=', self.env.cr.dbname), ('lifecycle_state', '=', 'active'),
        ])
        if len(namespace) != 1 or not namespace.primary_alias:
            raise AssertionError('registered active local.dev namespace/alias required')
        self.entry_headers = {
            'X-SC-Namespace': namespace.primary_alias,
            'X-SC-Audience': namespace.audience,
            'X-SC-Entry-Secret': _config(self.env, SHARED_SECRET_PARAM, SHARED_SECRET_ENV),
            'X-SC-Route-Version': _config(self.env, ROUTE_VERSION_PARAM, ROUTE_VERSION_ENV),
        }
        if not all(self.entry_headers.values()):
            raise AssertionError('registered entry configuration required; no test override allowed')

    def _intent(self, intent, params=None, token=None):
        headers = dict(self.entry_headers, **{'Content-Type': 'application/json'})
        if token:
            headers['Authorization'] = 'Bearer ' + token
        else:
            headers['X-Anonymous-Intent'] = 'true'
        response = self.url_open('/api/v1/intent', data=json.dumps({
            'intent': intent, 'params': params or {},
        }), headers=headers)
        return response.status_code, response.json()

    def _login(self):
        self._existing_entry()
        status, result = self._intent('login', {'login': self.subject.login, 'password': self.password})
        self.assertEqual(status, 200, result.get('error'))
        self.assertTrue(result.get('ok'), result.get('error'))
        token = ((result.get('data') or {}).get('session') or {}).get('token')
        self.assertTrue(token, 'real password login must issue a token')
        return token

    def _revoke(self):
        # HttpCase request cursors share the test transaction and its registry lock.
        with self.registry.test_lock:
            self.subject.with_user(self.manager).with_context(sc_runtime_user_management=True).write({
                'sc_user_role_group_ids': [(6, 0, [])],
            })
            self.env.flush_all()
            self.assertNotIn(self.role, self.subject.groups_id)

    def test_old_jwt_is_rejected_after_role_revocation(self):
        token = self._login()
        status, result = self._intent('system.init', token=token)
        self.assertEqual(status, 200, result.get('error'))
        self.assertTrue(result.get('ok'), result.get('error'))
        self._revoke()
        status, result = self._intent('system.init', token=token)
        self.assertEqual(status, 401, result.get('error'))
        self.assertFalse(result.get('ok'))
        self.assertEqual((result.get('error') or {}).get('code'), 'AUTH_REQUIRED')
        fresh = self._login()
        self.assertNotEqual(fresh, token)
        status, result = self._intent('system.init', token=fresh)
        self.assertEqual(status, 200, result.get('error'))
        self.assertTrue(result.get('ok'), result.get('error'))

    def _native_action(self, method):
        response = self.url_open('/web/dataset/call_kw/res.partner/' + method,
            data=json.dumps({'jsonrpc': '2.0', 'method': 'call', 'id': 1, 'params': {
                'model': 'res.partner', 'method': method, 'args': [self.partner.ids],
                'kwargs': {'context': {'allowed_company_ids': self.env.company.ids}},
            }}), headers={'Content-Type': 'application/json'})
        return response.json()

    def test_old_native_session_cannot_execute_revoked_action(self):
        self.authenticate(self.subject.login, self.password)
        result = self._native_action('action_sc_add_blacklist')
        self.assertNotIn('error', result)
        self.partner.invalidate_recordset()
        self.assertTrue(self.partner.sc_blacklisted, 'positive control must perform the HTTP action')
        result = self._native_action('action_sc_remove_blacklist')
        self.assertNotIn('error', result)
        self._revoke()
        result = self._native_action('action_sc_add_blacklist')
        self.assertIn('error', result)
        error_name = ((result['error'].get('data') or {}).get('name') or '').rsplit('.', 1)[-1]
        self.assertIn(error_name, ('UserError', 'AccessError', 'AccessDenied', 'SessionExpiredException'))
        self.partner.invalidate_recordset()
        self.assertFalse(self.partner.sc_blacklisted, 'old session must not perform the revoked action')

    def test_context_cannot_keep_old_jwt_after_role_revocation(self):
        token = self._login()
        status, result = self._intent('system.init', token=token)
        self.assertEqual(status, 200, result.get('error'))
        with self.registry.test_lock:
            self.subject.with_user(self.manager).with_context(
                sc_runtime_user_management=True, sc_skip_token_epoch_bump=True,
            ).write({'sc_user_role_group_ids': [(6, 0, [])]})
            self.env.flush_all()
        status, result = self._intent('system.init', token=token)
        self.assertEqual(status, 401, result.get('error'))
        self.assertEqual((result.get('error') or {}).get('code'), 'AUTH_REQUIRED')

    def test_logout_revokes_existing_jwt(self):
        token = self._login()
        status, result = self._intent('system.init', token=token)
        self.assertEqual(status, 200, result.get('error'))
        status, result = self._intent('auth.logout', token=token)
        self.assertEqual(status, 200, result.get('error'))
        self.assertTrue(result.get('ok'), result.get('error'))
        status, result = self._intent('system.init', token=token)
        self.assertEqual(status, 401, result.get('error'))
        self.assertEqual((result.get('error') or {}).get('code'), 'AUTH_REQUIRED')

    def _assert_group_mutation_rejects_old_token(self, mutation):
        token = self._login()
        status, result = self._intent('system.init', token=token)
        self.assertEqual(status, 200, result.get('error'))
        with self.registry.test_lock:
            mutation()
            self.env.flush_all()
        status, result = self._intent('system.init', token=token)
        self.assertEqual(status, 401, result.get('error'))
        self.assertEqual((result.get('error') or {}).get('code'), 'AUTH_REQUIRED')

    def test_reverse_member_removal_rejects_old_jwt(self):
        self._assert_group_mutation_rejects_old_token(
            lambda: self.role.write({'users': [(3, self.subject.id)]}))

    def test_native_group_field_rejects_old_jwt(self):
        self._assert_group_mutation_rejects_old_token(
            lambda: self.subject.write({'in_group_%s' % self.role.id: False}))

    def test_group_definition_change_rejects_old_jwt(self):
        with self.registry.test_lock:
            group = self.env['res.groups'].create({'name': 'Synthetic AUTH01 definition root'})
            self.subject.write({'groups_id': [(4, group.id)]})
        self._assert_group_mutation_rejects_old_token(lambda: group.write({
            'implied_ids': [(4, self.env.ref('smart_construction_core.group_sc_cap_data_read').id)],
        }))

    def test_group_deletion_rejects_old_jwt(self):
        with self.registry.test_lock:
            group = self.env['res.groups'].create({'name': 'Synthetic AUTH01 lifecycle root'})
            self.subject.write({'groups_id': [(4, group.id)]})
        self._assert_group_mutation_rejects_old_token(group.unlink)

    def test_native_rpc_cannot_call_private_authority_methods(self):
        self.authenticate(self.subject.login, self.password)
        with self.registry.test_lock:
            before_epoch = self.subject.token_version
            before_state = dict(self.subject.sc_group_authority_state)
        calls = (
            ('_sc_store_group_authority', [self.subject.ids, None]),
            ('_sc_bump_token_epoch', [self.subject.ids]),
            ('_sc_lock_group_authority', [self.subject.ids]),
            ('_sc_explicit_group_roots', [self.subject.ids]),
        )
        for method, args in calls:
            with self.subTest(method=method):
                response = self.url_open('/web/dataset/call_kw/res.users/' + method,
                    data=json.dumps({'jsonrpc': '2.0', 'method': 'call', 'id': 1, 'params': {
                        'model': 'res.users', 'method': method, 'args': args,
                        'kwargs': {'context': {'allowed_company_ids': self.env.company.ids}},
                    }}), headers={'Content-Type': 'application/json'})
                result = response.json()
                self.assertIn('error', result)
                self.assertEqual(result['error']['data']['name'], 'odoo.exceptions.AccessError')
                with self.registry.test_lock:
                    self.subject.invalidate_recordset()
                    self.assertEqual(self.subject.token_version, before_epoch)
                    self.assertEqual(self.subject.sc_group_authority_state, before_state)

    def test_native_confirmation_journey_rejects_later_edits(self):
        with self.registry.test_lock:
            admin = self.env['res.users'].with_context(no_reset_password=True).create({
                'name': 'Synthetic HTTP authority admin', 'login': 'auth01_http_authority_admin',
                'password': self.password, 'company_id': self.env.company.id,
                'company_ids': [(6, 0, self.env.company.ids)],
                'groups_id': [(6, 0, (self.env.ref('base.group_user') | self.env.ref('base.group_system')).ids)],
            })
            self.subject._sc_store_group_authority(None, 'synthetic HTTP legacy source')
            original_groups = set(self.subject.groups_id.ids)
            roots = (self.env.ref('base.group_user') | self.role).ids
            self.env.flush_all()
        self.authenticate(admin.login, self.password)

        def rpc(model, method, args, kwargs=None):
            response = self.url_open('/web/dataset/call_kw/' + model + '/' + method,
                data=json.dumps({'jsonrpc': '2.0', 'method': 'call', 'id': 1, 'params': {
                    'model': model, 'method': method, 'args': args,
                    'kwargs': dict(kwargs or {}, context={'allowed_company_ids': self.env.company.ids}),
                }}), headers={'Content-Type': 'application/json'})
            return response.json()

        result = rpc('res.users', 'action_sc_review_group_authority', [self.subject.ids])
        self.assertNotIn('error', result)
        review_id = result['result']['res_id']
        result = rpc('sc.group.authority.reconcile', 'write', [[review_id], {
            'root_group_ids': [(6, 0, roots)], 'note': 'Synthetic explicit source confirmation',
        }])
        self.assertNotIn('error', result)
        result = rpc('sc.group.authority.reconcile', 'action_confirm', [[review_id]])
        self.assertNotIn('error', result)
        self.assertEqual(result['result']['type'], 'ir.actions.act_window_close')
        for values in ({'note': 'Changed after confirmation'}, {'root_group_ids': [(5, 0, 0)]}):
            result = rpc('sc.group.authority.reconcile', 'write', [[review_id], values])
            self.assertIn('error', result)
            self.assertEqual(result['error']['data']['name'], 'odoo.exceptions.AccessError')
            self.assertIn('GROUP_AUTHORITY_REVIEW_IMMUTABLE', result['error']['data']['message'])
        result = rpc('sc.group.authority.confirmation', 'search_read', [[('user_id', '=', self.subject.id)]],
                     {'fields': ['note', 'root_group_ids_json', 'actor_id']})
        self.assertNotIn('error', result)
        self.assertEqual(len(result['result']), 1)
        audit = result['result'][0]
        self.assertEqual(audit['note'], 'Synthetic explicit source confirmation')
        self.assertEqual(set(audit['root_group_ids_json']), set(roots))
        self.assertEqual(audit['actor_id'][0], admin.id)
        with self.registry.test_lock:
            self.subject.invalidate_recordset()
            self.assertEqual(set(self.subject.groups_id.ids), original_groups)
            self.assertEqual(self.subject.sc_group_authority_state['status'], 'tracked')

    def test_business_manager_native_rpc_cannot_bypass_delegation(self):
        with self.registry.test_lock:
            self.manager.write({'password': self.password, 'tz': 'Asia/Shanghai'})
            self.env.flush_all()
            subject_ids = self.subject.ids
            company_ids = self.env.company.ids
            company_name = self.env.company.name
            system_id = self.env.ref('base.group_system').id
            before_groups = set(self.subject.groups_id.ids)
        self.authenticate(self.manager.login, self.password)

        def write(ids, values, context):
            response = self.url_open('/web/dataset/call_kw/res.users/write',
                data=json.dumps({'jsonrpc': '2.0', 'method': 'call', 'id': 1, 'params': {
                    'model': 'res.users', 'method': 'write', 'args': [ids, values],
                    'kwargs': {'context': dict(context, allowed_company_ids=company_ids)},
                }}), headers={'Content-Type': 'application/json'})
            return response.json()

        for context in ({}, {'sc_runtime_user_management': True, 'sc_runtime_user_management_sudo': True}):
            result = write(subject_ids, {'groups_id': [(4, system_id)]}, context)
            self.assertNotIn('error', result)
            with self.registry.test_lock:
                self.subject.invalidate_recordset()
                self.assertEqual(set(self.subject.groups_id.ids), before_groups)
        result = write(subject_ids, {'company_ids': [(1, company_ids[0], {'name': 'Unauthorized synthetic rename'})]}, {})
        self.assertIn('error', result)
        self.assertEqual(result['error']['data']['name'], 'odoo.exceptions.ValidationError')
        result = write(self.manager.ids, {'tz': 'UTC'}, {})
        self.assertNotIn('error', result)
        with self.registry.test_lock:
            self.env.company.invalidate_recordset()
            self.manager.invalidate_recordset()
            self.assertEqual(self.env.company.name, company_name)
            self.assertEqual(self.manager.tz, 'UTC')

    def test_native_create_cannot_inject_sudo_defaults(self):
        with self.registry.test_lock:
            self.manager.write({'password': self.password})
            project = self.env['project.project'].create({
                'name': 'Synthetic AUTH01 default HTTP project', 'company_id': self.env.company.id,
            })
            partner_id = self.subject.partner_id.id
            partner_name = self.subject.partner_id.name
            company_ids = self.env.company.ids
            project_id = project.id
            self.env.flush_all()
        self.authenticate(self.manager.login, self.password)
        response = self.url_open('/web/dataset/call_kw/res.users/create',
            data=json.dumps({'jsonrpc': '2.0', 'method': 'call', 'id': 1, 'params': {
                'model': 'res.users', 'method': 'create', 'args': [{
                    'name': 'Synthetic HTTP defaults', 'login': 'auth01_default_http',
                    'password': secrets.token_urlsafe(24), 'company_id': company_ids[0],
                    'company_ids': [(6, 0, company_ids)],
                }], 'kwargs': {'context': {
                    'allowed_company_ids': company_ids,
                    'sc_runtime_user_management_sudo': True,
                    'default_partner_id': partner_id,
                    'default_sc_project_member_assignment_ids': [(0, 0, {'project_id': project_id, 'source': 'manual'})],
                }},
            }}), headers={'Content-Type': 'application/json'})
        result = response.json()
        self.assertNotIn('error', result)
        self.assertTrue(result.get('result'))
        with self.registry.test_lock:
            created = self.env['res.users'].browse(result['result']).exists()
            self.assertTrue(created)
            self.assertNotEqual(created.partner_id.id, partner_id)
            self.assertFalse(created.sc_project_member_assignment_ids)
            self.subject.partner_id.invalidate_recordset()
            self.assertEqual(self.subject.partner_id.name, partner_name)

    def test_native_delegation_respects_user_record_rules(self):
        with self.registry.test_lock:
            self.manager.write({'password': self.password})
            company_ids = self.env.company.ids
            subject_ids = self.subject.ids
            before_name = self.subject.name
            self.env['ir.rule'].create({
                'name': 'Synthetic AUTH01 HTTP user denial',
                'model_id': self.env['ir.model']._get_id('res.users'),
                'domain_force': "[('id', '!=', %d), ('login', '!=', 'auth01_rule_http_denied')]" % self.subject.id,
                'perm_read': False, 'perm_write': True, 'perm_create': True, 'perm_unlink': False,
            })
            self.env.flush_all()
        self.authenticate(self.manager.login, self.password)
        calls = [('write', [subject_ids, {'name': 'Forbidden rule HTTP edit'}]),
                 ('create', [{'name': 'Synthetic rule HTTP denied', 'login': 'auth01_rule_http_denied',
                              'password': secrets.token_urlsafe(24), 'company_id': company_ids[0],
                              'company_ids': [(6, 0, company_ids)]}])]
        for method, args in calls:
            response = self.url_open('/web/dataset/call_kw/res.users/' + method,
                data=json.dumps({'jsonrpc': '2.0', 'method': 'call', 'id': 1, 'params': {
                    'model': 'res.users', 'method': method, 'args': args,
                    'kwargs': {'context': {'allowed_company_ids': company_ids}},
                }}), headers={'Content-Type': 'application/json'})
            result = response.json()
            self.assertIn('error', result)
            self.assertEqual(result['error']['data']['name'], 'odoo.exceptions.AccessError')
        with self.registry.test_lock:
            self.subject.invalidate_recordset()
            self.assertEqual(self.subject.name, before_name)
            self.assertFalse(self.env['res.users'].search([('login', '=', 'auth01_rule_http_denied')]))
            self.assertFalse(self.env['res.partner'].search([('name', '=', 'Synthetic rule HTTP denied')]))

    def test_native_personnel_relation_respects_read_rule(self):
        with self.registry.test_lock:
            self.manager.write({'password': self.password})
            company_ids = self.env.company.ids
            jobs = self.env['hr.job'].create([
                {'name': 'Synthetic AUTH01 HTTP hidden job', 'company_id': company_ids[0]},
                {'name': 'Synthetic AUTH01 HTTP allowed job', 'company_id': company_ids[0]},
            ])
            self.env['ir.rule'].create({
                'name': 'Synthetic AUTH01 HTTP personnel denial',
                'model_id': self.env['ir.model']._get_id('hr.job'),
                'domain_force': "[('id', '!=', %d)]" % jobs[0].id,
                'perm_read': True, 'perm_write': False, 'perm_create': False, 'perm_unlink': False,
            })
            job_ids = jobs.ids
            subject_ids = self.subject.ids
            self.env.flush_all()
        self.authenticate(self.manager.login, self.password)
        for job_id, denied in zip(job_ids, (True, False)):
            response = self.url_open('/web/dataset/call_kw/res.users/write',
                data=json.dumps({'jsonrpc': '2.0', 'method': 'call', 'id': 1, 'params': {
                    'model': 'res.users', 'method': 'write',
                    'args': [subject_ids, {'sc_personnel_job_id': job_id}],
                    'kwargs': {'context': {'allowed_company_ids': company_ids}},
                }}), headers={'Content-Type': 'application/json'})
            result = response.json()
            with self.registry.test_lock:
                self.subject.invalidate_recordset()
                if denied:
                    self.assertIn('error', result)
                    self.assertEqual(result['error']['data']['name'], 'odoo.exceptions.AccessError')
                    self.assertFalse(self.env['hr.employee'].search([('user_id', 'in', subject_ids)]))
                else:
                    self.assertNotIn('error', result)
                    self.assertEqual(self.subject.employee_id.job_id.id, job_id)

    def test_native_public_profile_action_enforces_targets(self):
        with self.registry.test_lock:
            self.manager.write({'password': self.password})
            company_ids = self.env.company.ids
            denied_ids, allowed_ids = self.subject.ids, self.manager.ids
            self.env['ir.rule'].create({
                'name': 'Synthetic AUTH01 HTTP public profile denial',
                'model_id': self.env['ir.model']._get_id('res.users'),
                'domain_force': "[('id', '!=', %d)]" % self.subject.id,
                'perm_read': False, 'perm_write': True, 'perm_create': False, 'perm_unlink': False,
            })
            self.env.flush_all()
        self.authenticate(self.manager.login, self.password)
        for ids, denied in ((denied_ids, True), (allowed_ids, False), (allowed_ids, False)):
            response = self.url_open('/web/dataset/call_kw/res.users/action_sc_ensure_employee_profile',
                data=json.dumps({'jsonrpc': '2.0', 'method': 'call', 'id': 1, 'params': {
                    'model': 'res.users', 'method': 'action_sc_ensure_employee_profile', 'args': [ids],
                    'kwargs': {'context': {'allowed_company_ids': company_ids}},
                }}), headers={'Content-Type': 'application/json'})
            result = response.json()
            if denied:
                self.assertIn('error', result)
                self.assertEqual(result['error']['data']['name'], 'odoo.exceptions.AccessError')
            else:
                self.assertNotIn('error', result)
                self.assertTrue(result['result'])
        with self.registry.test_lock:
            self.assertFalse(self.env['hr.employee'].search([('user_id', 'in', denied_ids)]))
            self.assertEqual(self.env['hr.employee'].search_count([('user_id', 'in', allowed_ids)]), 1)
