"""Exercise native action/model missing-record contracts through the real ORM."""
from odoo.tests.common import TransactionCase, tagged
from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler


@tagged('post_install', '-at_install', 'sc_gate')
class TestMissingRecordContract(TransactionCase):
    def test_payment_action_missing_record_is_not_a_configuration_error(self):
        action = self.env.ref('smart_construction_core.action_payment_request_user_payment_apply')
        last = self.env['payment.request'].sudo().search([], order='id desc', limit=1)
        absent_id = (last.id or 0) + 1
        self.assertFalse(self.env['payment.request'].browse(absent_id).exists())
        menu = self.env.ref('smart_construction_core.menu_sc_user_payment_apply')
        for authority in [
            {'op': 'action_open', 'action_id': action.id},
            {'op': 'model', 'model': 'payment.request'},
            {'op': 'menu', 'menu_id': menu.id},
            {'op': 'action_open', 'action_xmlid': 'smart_construction_core.action_payment_request_user_payment_apply'},
        ]:
            with self.subTest(authority=authority):
                params = {
                    **authority, 'record_id': absent_id,
                    'view_type': 'form', 'render_profile': 'readonly', 'contract_surface': 'user',
                    'source_mode': 'backend_internal', 'delivery_profile': 'full', 'client_type': 'web_pc',
                }
                result = UiContractV2Handler(self.env, su_env=self.env).handle(params)
                result = result.to_legacy_dict() if hasattr(result, 'to_legacy_dict') else result
                self.assertEqual(result.get('error', {}).get('reason_code'), 'RECORD_NOT_FOUND', result)
                self.assertEqual(result.get('code'), 404, result)

    def test_action_cannot_validate_a_conflicting_request_model(self):
        action = self.env.ref('smart_construction_core.action_payment_request_user_payment_apply')
        result = UiContractV2Handler(self.env, su_env=self.env).handle({
            'op': 'action_open', 'action_id': action.id, 'model': 'res.partner',
            'record_id': self.env.user.partner_id.id, 'view_type': 'form',
        })
        self.assertEqual(result.code, 400)
