# -*- coding: utf-8 -*-
import json
from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import HttpCase, TransactionCase, tagged

from odoo.addons.smart_core.models.user_activation import (
    PURPOSE_ENTERPRISE_ACTIVATION,
    PURPOSE_PASSWORD_RECOVERY,
)


@tagged("post_install", "-at_install", "smart_core", "user_activation")
class TestUserActivation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.internal = cls.env.ref("base.group_user")
        cls.activation_admin = cls.env.ref("smart_core.group_smart_core_user_activation_admin")
        cls.admin = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Activation administrator",
                "login": "activation-admin-test",
                "company_id": cls.env.company.id,
                "company_ids": [Command.set([cls.env.company.id])],
                "groups_id": [Command.set([cls.internal.id, cls.activation_admin.id])],
            }
        )
        cls.user = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Activation target",
                "login": "activation-target-test",
                "lang": "en_US",
                "tz": "UTC",
                "company_id": cls.env.company.id,
                "company_ids": [Command.set([cls.env.company.id])],
                "groups_id": [Command.set([cls.internal.id])],
            }
        )
        cls.Service = cls.env["sc.user.activation.credential"].with_user(cls.admin)
        parameters = cls.env["ir.config_parameter"].sudo()
        parameters.set_param("sc.runtime.tenant_key", "test-tenant")
        parameters.set_param("sc.runtime.environment_type", "acceptance")

    def _batch(self, suffix="default"):
        return self.Service._create_batch(
            batch_key=f"activation-test-{suffix}",
            tenant_key="test-tenant",
            environment_type="acceptance",
            purpose=PURPOSE_ENTERPRISE_ACTIVATION,
        )

    def _issue(self, suffix="default"):
        batch = self._batch(suffix)
        issued = self.Service._issue_once(
            user=self.user,
            immutable_user_id="test:user:activation-target",
            target_login=self.user.login,
            tenant_key="test-tenant",
            environment_type="acceptance",
            batch=batch,
            purpose=PURPOSE_ENTERPRISE_ACTIVATION,
        )
        credential = self.env["sc.user.activation.credential"].sudo().search(
            [("credential_id", "=", issued["credential_id"])]
        )
        return batch, issued, credential

    def test_digest_only_single_use_and_native_password_authority(self):
        _batch, issued, credential = self._issue("single-use")
        raw_token = issued["activation_token"]
        self.assertNotEqual(credential.token_digest, raw_token)
        self.assertNotIn(raw_token, str(credential.read()[0]))
        before_groups = set(self.user.groups_id.ids)
        before_companies = set(self.user.company_ids.ids)
        before_profile = (self.user.name, self.user.email, self.user.lang, self.user.tz)

        started = self.env["sc.user.activation.credential"].sudo()._begin_activation(
            raw_token,
            expected_purpose=PURPOSE_ENTERPRISE_ACTIVATION,
        )
        context = started["activation_context"]
        self.assertNotEqual(context, credential.challenge_digest)
        credential.invalidate_recordset()
        self.assertTrue(credential.challenge_digest)
        self.assertGreater(credential.challenge_expires_at, fields.Datetime.now())
        self.assertGreater(credential.expires_at, fields.Datetime.now())
        self.assertEqual(credential.state, "pending")
        self.assertEqual(credential.batch_id.state, "active")
        self.assertTrue(credential._binding_is_current())
        self.env["sc.user.activation.credential"].sudo()._complete_activation(
            context,
            "StrongPassword2026",
            expected_purpose=PURPOSE_ENTERPRISE_ACTIVATION,
        )
        credential.invalidate_recordset()
        self.assertEqual(credential.state, "used")
        authenticated_user = self.user.with_user(self.user)
        authenticated_user._check_credentials("StrongPassword2026", authenticated_user.env)
        self.assertEqual(set(self.user.groups_id.ids), before_groups)
        self.assertEqual(set(self.user.company_ids.ids), before_companies)
        self.assertEqual((self.user.name, self.user.email, self.user.lang, self.user.tz), before_profile)
        with self.assertRaisesRegex(UserError, "ACTIVATION_REQUEST_REJECTED"):
            self.env["sc.user.activation.credential"].sudo()._complete_activation(
                context,
                "OtherPassword2026",
                expected_purpose=PURPOSE_ENTERPRISE_ACTIVATION,
            )

    def test_cross_purpose_token_use_is_rejected(self):
        _batch, issued, _credential = self._issue("cross-purpose")
        with self.assertRaisesRegex(UserError, "ACTIVATION_REQUEST_REJECTED"):
            self.env["sc.user.activation.credential"].sudo()._begin_activation(
                issued["activation_token"],
                expected_purpose=PURPOSE_PASSWORD_RECOVERY,
            )

    def test_expired_revoked_and_paused_credentials_are_rejected(self):
        batch, issued, credential = self._issue("state-boundaries")
        credential.with_context(sc_activation_service=True).write(
            {"expires_at": fields.Datetime.now() - timedelta(seconds=1)}
        )
        with self.assertRaisesRegex(UserError, "ACTIVATION_REQUEST_REJECTED"):
            self.env["sc.user.activation.credential"].sudo()._begin_activation(
                issued["activation_token"], expected_purpose=PURPOSE_ENTERPRISE_ACTIVATION
            )
        credential.with_context(sc_activation_service=True).write(
            {"expires_at": fields.Datetime.now() + timedelta(hours=1), "state": "pending"}
        )
        credential.with_user(self.admin)._revoke()
        with self.assertRaisesRegex(UserError, "ACTIVATION_REQUEST_REJECTED"):
            self.env["sc.user.activation.credential"].sudo()._begin_activation(
                issued["activation_token"], expected_purpose=PURPOSE_ENTERPRISE_ACTIVATION
            )
        batch.with_context(sc_activation_service=True).write({"state": "paused"})

    def test_binding_drift_blocks_without_repairing_user(self):
        _batch, issued, _credential = self._issue("binding-drift")
        extra_group = self.env["res.groups"].create({"name": "Activation drift group"})
        self.user.write({"groups_id": [Command.link(extra_group.id)]})
        with self.assertRaisesRegex(UserError, "ACTIVATION_REQUEST_REJECTED"):
            self.env["sc.user.activation.credential"].sudo()._begin_activation(
                issued["activation_token"], expected_purpose=PURPOSE_ENTERPRISE_ACTIVATION
            )
        self.assertIn(extra_group, self.user.groups_id)

    def test_runtime_tenant_binding_and_reissue_are_fail_closed(self):
        batch, issued, first = self._issue("tenant-and-reissue")
        self.env["ir.config_parameter"].sudo().set_param("sc.runtime.tenant_key", "other-tenant")
        with self.assertRaisesRegex(UserError, "ACTIVATION_REQUEST_REJECTED"):
            self.env["sc.user.activation.credential"].sudo()._begin_activation(
                issued["activation_token"], expected_purpose=PURPOSE_ENTERPRISE_ACTIVATION
            )
        self.env["ir.config_parameter"].sudo().set_param("sc.runtime.tenant_key", "test-tenant")
        replacement = self.Service._reissue_once(
            user=self.user,
            immutable_user_id="test:user:activation-target",
            target_login=self.user.login,
            tenant_key="test-tenant",
            environment_type="acceptance",
            batch=batch,
            purpose=PURPOSE_ENTERPRISE_ACTIVATION,
        )
        first.invalidate_recordset()
        self.assertEqual(first.state, "revoked")
        self.assertNotEqual(issued["activation_token"], replacement["activation_token"])
        with self.assertRaisesRegex(UserError, "ACTIVATION_REQUEST_REJECTED"):
            self.env["sc.user.activation.credential"].sudo()._begin_activation(
                issued["activation_token"], expected_purpose=PURPOSE_ENTERPRISE_ACTIVATION
            )

    def test_delivery_audit_contains_fingerprint_not_secret(self):
        _batch, issued, credential = self._issue("delivery-audit")
        audit = credential.with_user(self.admin)._record_delivery(
            operator_identity="test:delivery-operator",
            channel_type="verified-enterprise-messaging",
            verification_method="test-identity-check",
        )
        self.assertEqual(audit.token_fingerprint, issued["token_fingerprint"])
        self.assertNotIn(issued["activation_token"], str(audit.read()[0]))

    def test_activation_admin_is_minimal_and_isolated(self):
        forbidden_groups = (
            "base.group_system",
            "smart_core.group_smart_core_admin",
            "smart_core.group_smart_core_tenant_payload_importer",
            "smart_core.group_smart_core_data_operator",
        )
        for xmlid in forbidden_groups:
            self.assertFalse(self.admin.has_group(xmlid), xmlid)
        self.assertEqual(self.admin.company_ids, self.env.company)
        self.assertFalse(self.activation_admin.implied_ids)

        _batch, issued, credential = self._issue("minimal-isolation")
        status = credential.with_user(self.admin).read(
            ["credential_id", "state", "token_fingerprint"]
        )[0]
        self.assertEqual(status["state"], "pending")
        self.assertNotIn("activation_token", credential._fields)
        self.assertNotIn("raw_token", credential._fields)
        self.assertNotIn(issued["activation_token"], str(status))
        credential.with_user(self.admin)._revoke()
        self.assertEqual(credential.state, "revoked")

        with self.assertRaises(AccessError):
            self.user.with_user(self.admin).write(
                {"groups_id": [Command.link(self.activation_admin.id)]}
            )
        with self.assertRaises(AccessError):
            self.user.with_user(self.admin).write({"company_id": self.env.company.id})

    def test_unsupported_public_saas_purpose_is_disabled(self):
        with self.assertRaisesRegex(UserError, "ACTIVATION_PURPOSE_NOT_ENABLED"):
            self.Service._create_batch(
                batch_key="activation-test-saas-disabled",
                tenant_key="practice-test",
                environment_type="practice",
                purpose="saas_registration_verification",
            )


@tagged("post_install", "-at_install", "smart_core", "user_activation_http")
class TestUserActivationHttpContract(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        internal = cls.env.ref("base.group_user")
        activation_admin = cls.env.ref("smart_core.group_smart_core_user_activation_admin")
        cls.admin = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Activation HTTP administrator",
                "login": "activation-http-admin-test",
                "company_id": cls.env.company.id,
                "company_ids": [Command.set([cls.env.company.id])],
                "groups_id": [Command.set([internal.id, activation_admin.id])],
            }
        )
        cls.user = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Activation HTTP target",
                "login": "activation-http-target-test",
                "company_id": cls.env.company.id,
                "company_ids": [Command.set([cls.env.company.id])],
                "groups_id": [Command.set([internal.id])],
            }
        )
        parameters = cls.env["ir.config_parameter"].sudo()
        parameters.set_param("sc.runtime.tenant_key", "http-test-tenant")
        parameters.set_param("sc.runtime.environment_type", "acceptance")
        service = cls.env["sc.user.activation.credential"].with_user(cls.admin)
        batch = service._create_batch(
            batch_key="activation-http-test",
            tenant_key="http-test-tenant",
            environment_type="acceptance",
            purpose=PURPOSE_ENTERPRISE_ACTIVATION,
        )
        cls.issued = service._issue_once(
            user=cls.user,
            immutable_user_id="test:user:activation-http-target",
            target_login=cls.user.login,
            tenant_key="http-test-tenant",
            environment_type="acceptance",
            batch=batch,
            purpose=PURPOSE_ENTERPRISE_ACTIVATION,
        )

    def _post(self, path: str, payload: dict):
        response = self.url_open(
            f"{path}?db={self.env.cr.dbname}",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        if hasattr(response, "read"):
            body = response.read()
        elif hasattr(response, "get_data"):
            body = response.get_data()
        else:
            body = response.content
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        return response, json.loads(body or "{}")

    def test_post_only_two_stage_protocol_and_security_headers(self):
        raw_token = self.issued["activation_token"]
        response, started = self._post(
            "/api/v1/auth/activation/start",
            {"activation_code": raw_token},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(started.get("ok"), started)
        response_url = response.geturl() if hasattr(response, "geturl") else response.url
        self.assertNotIn(raw_token, response_url)
        self.assertEqual(response.headers.get("Cache-Control"), "no-store, max-age=0")
        self.assertEqual(response.headers.get("Referrer-Policy"), "no-referrer")
        context = started.get("activation_context")
        self.assertTrue(context)

        response, completed = self._post(
            "/api/v1/auth/activation/complete",
            {
                "activation_context": context,
                "password": "StrongHttpPassword2026",
                "confirm_password": "StrongHttpPassword2026",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(completed.get("ok"), completed)
        authenticated_user = self.user.with_user(self.user)
        authenticated_user._check_credentials("StrongHttpPassword2026", authenticated_user.env)

        rejected, payload = self._post(
            "/api/v1/auth/activation/complete",
            {
                "activation_context": context,
                "password": "OtherStrongPassword2026",
                "confirm_password": "OtherStrongPassword2026",
            },
        )
        self.assertEqual(rejected.status_code, 400)
        self.assertFalse(payload.get("ok", True))
