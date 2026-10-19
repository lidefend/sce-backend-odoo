"""Offline safety tests for the read-only personnel contract probe."""
from types import SimpleNamespace as NS
from unittest import TestCase, mock
from scripts.verify import user_permission_view_contract_boundary_guard as guard


class ReadOnlyPrincipalTests(TestCase):
    def setUp(self):
        self.env = mock.MagicMock()
        self.env.ref.return_value = NS(id=42)
        self.users = self.env.__getitem__.return_value.sudo.return_value.with_context.return_value
        self.patch = mock.patch.object(guard, '_env', return_value=self.env)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_preferred_account_must_satisfy_role_and_active_scope(self):
        self.users.search.return_value = NS(login='maintainer')
        self.assertEqual(guard._contract_login('maintainer'), 'maintainer')
        domain = self.users.search.call_args.args[0]
        for condition in [('groups_id', 'in', [42]), ('active', '=', True), ('share', '=', False), ('login', '=', 'maintainer')]:
            self.assertIn(condition, domain)
        self.users.create.assert_not_called()

    def test_invalid_preferred_uses_existing_qualified_account(self):
        self.users.search.side_effect = [False, NS(login='qualified')]
        self.assertEqual(guard._contract_login('disabled'), 'qualified')
        self.assertEqual(self.users.search.call_count, 2)
        self.assertIn(('active', '=', True), self.users.search.call_args.args[0])
        self.users.create.assert_not_called()

    def test_missing_account_fails_without_writing(self):
        self.users.search.return_value = False
        with self.assertRaisesRegex(AssertionError, 'no account was created'):
            guard._contract_login()
        self.users.create.assert_not_called()
        self.users.write.assert_not_called()
        self.env.cr.rollback.assert_not_called()

    def test_missing_group_fails_without_writing(self):
        self.env.ref.return_value = False
        with self.assertRaisesRegex(AssertionError, 'missing prerequisites'):
            guard._contract_login()
        self.users.search.assert_not_called()
        self.users.create.assert_not_called()


class PersonnelEligibilityTests(TestCase):
    def check_user(self, **changes):
        values = dict(id=10, login='demo_pm', name='测试演示人员', active=False,
                      share=False, company_id=NS(id=1), groups_id=NS(ids=[2]))
        values.update(changes)
        return guard._maintainable_user_errors(
            [NS(**values)], company_ids={1}, privileged_ids={3}, internal_id=2, template_id=9)

    def test_empty_personnel_result_cannot_pass_acceptance(self):
        self.assertTrue(guard._maintainable_user_errors(
            [], company_ids={1}, privileged_ids={3}, internal_id=2, template_id=9))

    def test_inactive_and_demo_named_internal_person_is_not_inferred_invalid(self):
        self.assertEqual(self.check_user(), [])

    def test_template_account_rejected_by_identity_not_login(self):
        self.assertTrue(self.check_user(id=9, login='renamed-template'))
        self.assertEqual(self.check_user(login='default'), [])

    def test_privileged_user_rejected(self):
        self.assertTrue(self.check_user(groups_id=NS(ids=[2, 3])))

    def test_other_company_user_rejected(self):
        self.assertTrue(self.check_user(company_id=NS(id=7)))

    def test_portal_and_noninternal_and_missing_login_rejected(self):
        for changes in [dict(share=True), dict(groups_id=NS(ids=[])), dict(login=False)]:
            with self.subTest(changes=changes):
                self.assertTrue(self.check_user(**changes))
