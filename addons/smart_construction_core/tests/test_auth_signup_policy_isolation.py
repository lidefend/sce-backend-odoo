# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged
from werkzeug.wrappers import Response

from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.addons.smart_construction_core.controllers import auth_signup as controller_module
from odoo.addons.smart_construction_core.controllers.auth_signup import ScAuthSignup


@tagged("post_install", "-at_install", "smart_construction_core", "auth_signup")
class TestAuthSignupPolicyIsolation(TransactionCase):
    def test_shared_qcontext_does_not_apply_invite_signup_gate_to_reset(self):
        controller = ScAuthSignup()
        fake_request = SimpleNamespace(params={})
        with (
            patch.object(controller_module, "request", fake_request),
            patch.object(AuthSignupHome, "get_auth_signup_qcontext", return_value={"reset_password_enabled": True}),
            patch.object(controller, "_get_signup_mode", return_value="invite"),
            patch.object(controller, "_assert_open_allowed", side_effect=AssertionError("signup gate leaked")) as gate,
        ):
            result = controller.get_auth_signup_qcontext()
        self.assertTrue(result["reset_password_enabled"])
        gate.assert_not_called()

    def test_existing_user_reset_never_applies_creation_defaults(self):
        controller = ScAuthSignup()
        existing_user = SimpleNamespace(id=42)
        partner = SimpleNamespace(user_ids=[existing_user])
        partner.with_context = lambda **_kwargs: partner
        user_model = SimpleNamespace(
            sudo=lambda: user_model,
            search=lambda *args, **kwargs: existing_user,
        )
        partner_model = SimpleNamespace(
            sudo=lambda: partner_model,
            _signup_retrieve_partner=lambda *args, **kwargs: partner,
        )
        fake_env = {"res.partner": partner_model, "res.users": user_model}
        fake_request = SimpleNamespace(env=fake_env)
        with (
            patch.object(controller_module, "request", fake_request),
            patch.object(controller, "_assert_open_allowed"),
            patch.object(controller, "_assert_rate_limit"),
            patch.object(controller, "_assert_password_strength"),
            patch.object(controller, "_assert_email_allowed"),
            patch.object(controller, "_require_email_verify", return_value=True),
            patch.object(AuthSignupHome, "do_signup", return_value=True),
            patch.object(controller, "_apply_user_defaults") as defaults,
        ):
            controller.do_signup(
                {"token": "opaque-test-token", "login": "existing-user", "password": "Password2026"}
            )
        defaults.assert_not_called()

    def test_disabled_self_service_recovery_redirects_without_enumerating_login(self):
        controller = ScAuthSignup()
        native_response = Response(status=200)
        fake_request = SimpleNamespace(
            params={},
            redirect=lambda location, code=302: Response(status=code, headers={"Location": location}),
        )
        with (
            patch.object(controller_module, "request", fake_request),
            patch.object(controller, "_password_recovery_self_service_enabled", return_value=False),
            patch.object(AuthSignupHome, "web_auth_reset_password", return_value=native_response) as native_reset,
        ):
            result = controller.web_auth_reset_password()
        self.assertEqual(result.status_code, 303)
        self.assertEqual(result.headers["Location"], "/password-recovery")
        native_reset.assert_not_called()
