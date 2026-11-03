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

    def test_company_switch_and_revocation_recompute_cached_authority(self):
        a, b = self._state(self.company_a), self._state(self.company_b)
        a.set_enabled(True)
        b.set_enabled(True)
        self.assertTrue(self._allowed(self.company_a))
        self.assertTrue(self._allowed(self.company_b))
        a.set_enabled(False)
        self.assertFalse(self._allowed(self.company_a))
        self.assertTrue(self._allowed(self.company_b))
        a.set_enabled(True)
        self.assertTrue(self._allowed(self.company_a))

    def test_missing_state_denies_and_legacy_key_does_not_enable_business(self):
        self._state(self.company_a).unlink()
        self.assertFalse(self._allowed(self.company_a))
        self.states.create({'company_id': self.company_a.id,
                            'scene_key': 'finance.payment_requests', 'enabled': True})
        self.assertFalse(self._allowed(self.company_a))

    def test_finance_cannot_enable_scenes_or_read_another_active_company(self):
        a, b = self._state(self.company_a), self._state(self.company_b)
        actor = self._actor(self.company_a)
        with self.assertRaises(AccessError), self.cr.savepoint():
            a.with_env(actor).set_enabled(not a.enabled)
        self.assertFalse(actor['sc.scene.company.enablement'].search([('id', '=', b.id)]))
