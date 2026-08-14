# -*- coding: utf-8 -*-
import json
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

import jwt

from odoo import SUPERUSER_ID, api, fields
from odoo.exceptions import AccessDenied, AccessError
from odoo.modules.registry import Registry
from odoo.tests.common import HttpCase, tagged

from odoo.addons.smart_core.models.auth_credential_policy import SERVICE_CONTEXT_KEY
from odoo.addons.smart_core.core.handler_registry import HANDLER_REGISTRY
from odoo.addons.smart_core.security.auth import (
    _validated_token_principal,
)
from odoo.addons.smart_core.security.credential_service import (
    THROTTLE_MAX_FAILURES,
    _fingerprint,
    _next_throttle_failure_values,
    assert_principal_scope,
    authenticate_api_key,
    issue_machine_api_key,
    revoke_machine_api_key,
    rotate_machine_api_key,
)


@tagged("post_install", "-at_install", "sc_auth_credential")
class TestAuthCredentialFramework(HttpCase):

    def setUp(self):
        super().setUp()
        suffix = uuid.uuid4().hex[:10]
        self.password = f"CredentialFramework-{suffix}"
        self.jwt_secret = "auth-framework-test-signing-secret-2026-08-14-64-bytes-minimum"
        previous_secret = os.environ.get("SC_JWT_SECRET")
        os.environ["SC_JWT_SECRET"] = self.jwt_secret
        self.addCleanup(
            lambda: os.environ.pop("SC_JWT_SECRET", None)
            if previous_secret is None
            else os.environ.__setitem__("SC_JWT_SECRET", previous_secret)
        )
        self.client_identity = f"198.51.100.{int(suffix[:2], 16) % 200 + 1}"
        registry = Registry(self.env.cr.dbname)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env["ir.config_parameter"].sudo().set_param("sc.jwt.secret", self.jwt_secret)
            company_a = env["res.company"].sudo().create({"name": f"Auth Company A {suffix}"})
            company_b = env["res.company"].sudo().create({"name": f"Auth Company B {suffix}"})
            user = env["res.users"].sudo().create({
                "name": f"Auth Machine Owner {suffix}",
                "login": f"auth_machine_owner_{suffix}",
                "password": self.password,
                "active": True,
                "company_id": company_a.id,
                "company_ids": [(6, 0, [company_a.id, company_b.id])],
                "groups_id": [(6, 0, [env.ref("base.group_user").id])],
            })
            self.company_a_id = company_a.id
            self.company_b_id = company_b.id
            self.user_id = user.id
            self.user_login = user.login
            cr.commit()
        self.company_a = self.env["res.company"].sudo().browse(self.company_a_id)
        self.company_b = self.env["res.company"].sudo().browse(self.company_b_id)
        self.user = self.env["res.users"].sudo().browse(self.user_id)

    def _issue(self, **overrides):
        values = {
            "actor_user": self.user,
            "password": self.password,
            "name": "CI integration",
            "scopes": ["intent.read"],
            "company_ids": [self.company_a.id],
            "expires_at": fields.Datetime.now() + timedelta(hours=1),
            "trace_id": "auth-framework-test",
        }
        values.update(overrides)
        registry = Registry(self.env.cr.dbname)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            values["actor_user"] = env["res.users"].sudo().browse(self.user_id)
            policy, secret = issue_machine_api_key(env, **values)
            policy_id = policy.id
            cr.commit()
        return self.env["sc.auth.credential.policy"].sudo().browse(policy_id), secret

    def _authenticate(self, secret, **overrides):
        values = {
            "database": self.env.cr.dbname,
            "secret": secret,
            "requested_scopes": ["intent.read"],
            "fingerprint_pepper": "test-only-pepper",
            "client_identity": self.client_identity,
        }
        values.update(overrides)
        return authenticate_api_key(**values)

    def _revoke(self, policy, **overrides):
        registry = Registry(self.env.cr.dbname)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            values = {
                "policy": env["sc.auth.credential.policy"].sudo().browse(policy.id),
                "actor_user": env["res.users"].sudo().browse(self.user_id),
                "trace_id": "revoke-test",
            }
            values.update(overrides)
            revoke_machine_api_key(env, **values)
            cr.commit()
        policy.invalidate_recordset()
        return policy

    def _write_persistent(self, model, record_id, values):
        registry = Registry(self.env.cr.dbname)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            record = env[model].sudo().browse(record_id)
            context = {SERVICE_CONTEXT_KEY: True} if model == "sc.auth.credential.policy" else {}
            record.with_context(**context).write(values)
            cr.commit()
        self.env[model].sudo().browse(record_id).invalidate_recordset()

    def _json_response(self, response):
        self.last_http_status = int(
            getattr(response, "status_code", None)
            or getattr(response, "code", None)
            or getattr(response, "status", None)
            or 0
        )
        body = response
        for _index in range(3):
            if isinstance(body, (bytes, str)):
                break
            if callable(getattr(body, "json", None)):
                parsed = body.json()
                if isinstance(parsed, dict):
                    return parsed
                body = parsed
            elif hasattr(body, "get_data"):
                body = body.get_data(as_text=True)
            elif hasattr(body, "content"):
                body = body.content
            elif hasattr(body, "text"):
                body = body.text
            elif hasattr(body, "data"):
                body = body.data
            elif hasattr(body, "read"):
                body = body.read()
            else:
                break
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        if isinstance(body, dict):
            return body
        return json.loads(body or "{}")

    def _http_intent(self, intent, params, *, token="", anonymous=False):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if anonymous:
            headers["X-Anonymous-Intent"] = "true"
        response = self.url_open(
            f"/api/v1/intent?db={self.env.cr.dbname}",
            data=json.dumps({"intent": intent, "params": params}),
            headers=headers,
        )
        return self._json_response(response)

    def _human_token(self):
        result = self._http_intent(
            "login",
            {
                "db": self.env.cr.dbname,
                "credential": {
                    "type": "password",
                    "login": self.user_login,
                    "secret": self.password,
                },
            },
            anonymous=True,
        )
        self.assertTrue(result.get("ok"), result)
        token = (((result.get("data") or {}).get("session") or {}).get("token"))
        self.assertTrue(token, result)
        return token

    def test_native_key_is_one_time_and_policy_contains_no_secret(self):
        policy, secret = self._issue()

        self.assertTrue(secret)
        serialized = json.dumps(policy.read()[0], default=str)
        self.assertNotIn(secret, serialized)
        self.assertEqual(policy.credential_id, f"odoo_api_key:{policy.native_key_id}")
        self.assertTrue(policy.native_key_exists())

    def test_valid_key_returns_narrow_machine_principal(self):
        policy, secret = self._issue()

        principal = self._authenticate(secret)

        self.assertEqual(principal.auth_method, "api_key")
        self.assertEqual(principal.credential_id, policy.credential_id)
        self.assertEqual(principal.scopes, ("intent.read",))
        self.assertEqual(principal.allowed_company_ids, (self.company_a.id,))
        self.assertNotIn(self.company_b.id, principal.allowed_company_ids)
        policy.invalidate_recordset(["last_used_at", "usage_count"])
        self.assertTrue(policy.last_used_at)
        self.assertEqual(policy.usage_count, 1)

    def test_company_policy_selects_an_allowed_company_without_expanding_scope(self):
        _policy, secret = self._issue(company_ids=[self.company_b.id])

        principal = self._authenticate(secret)

        self.assertEqual(principal.company_id, self.company_b.id)
        self.assertEqual(principal.allowed_company_ids, (self.company_b.id,))
        self.assertNotIn(self.company_a.id, principal.allowed_company_ids)

    def test_scope_cannot_expand_and_write_is_denied(self):
        _policy, secret = self._issue()

        with self.assertRaises(AccessDenied):
            self._authenticate(secret, requested_scopes=["intent.write"])
        principal = self._authenticate(secret)
        with self.assertRaises(AccessError):
            assert_principal_scope(
                principal,
                intent_name="api.data.write",
                params={"model": "res.partner", "op": "write"},
            )
        with self.assertRaises(AccessError):
            assert_principal_scope(
                principal,
                intent_name="api.data",
                params={"model": "res.partner", "op": "write"},
            )

        self.assertTrue(assert_principal_scope(
            principal,
            intent_name="api.data",
            params={"model": "res.partner", "op": "list"},
        ))

    def test_api_data_machine_scope_uses_same_top_level_precedence_as_handler(self):
        _policy, secret = self._issue()
        read_principal = self._authenticate(secret)
        conflicting = {
            "model": "res.partner",
            "op": "write",
            "payload": {"op": "list"},
        }

        with self.assertRaises(AccessError):
            assert_principal_scope(
                read_principal,
                intent_name="api.data",
                params=conflicting,
            )

        _write_policy, write_secret = self._issue(scopes=["intent.write"])
        write_principal = self._authenticate(
            write_secret,
            requested_scopes=["intent.write"],
        )
        self.assertTrue(assert_principal_scope(
            write_principal,
            intent_name="api.data",
            params=conflicting,
        ))

    def test_machine_access_uses_explicit_handler_metadata_and_unknown_denies(self):
        _policy, secret = self._issue()
        principal = self._authenticate(secret)

        for intent in (
            "chatter.post",
            "global.message.send",
            "global.message.read",
            "missing.machine.intent",
        ):
            with self.subTest(intent=intent), self.assertRaises(AccessError):
                assert_principal_scope(principal, intent_name=intent, params={})

        declared = {}
        for intent, handler in HANDLER_REGISTRY.items():
            access = str(getattr(handler, "MACHINE_ACCESS", "deny") or "deny").strip().lower()
            self.assertIn(access, {"deny", "read", "write", "dynamic"}, intent)
            declared.setdefault(handler, access)
            if getattr(handler, "NON_IDEMPOTENT_ALLOWED", ""):
                self.assertNotEqual(access, "read", intent)
            if access == "dynamic":
                self.assertIn("machine_access_for", handler.__dict__, intent)
        self.assertGreater(len(declared), 100)

    def test_intent_specific_scope_cannot_override_handler_machine_denial(self):
        _policy, secret = self._issue(scopes=["intent:chatter.post"])
        principal = self._authenticate(secret, requested_scopes=["intent:chatter.post"])

        with self.assertRaises(AccessError):
            assert_principal_scope(principal, intent_name="chatter.post", params={})

    def test_write_scope_can_use_handler_declared_write_operation(self):
        _policy, secret = self._issue(scopes=["intent.write"])
        principal = self._authenticate(secret, requested_scopes=["intent.write"])

        self.assertTrue(assert_principal_scope(
            principal,
            intent_name="api.data",
            params={"model": "res.partner", "op": "write"},
        ))
        with self.assertRaises(AccessError):
            assert_principal_scope(
                principal,
                intent_name="api.data",
                params={"model": "res.partner", "op": "unknown_future_operation"},
            )

    def test_native_key_creation_rejects_duplicate_prefix_without_binding_policy(self):
        fixed_entropy = lambda size: b"\x5a" * size
        registry = Registry(self.env.cr.dbname)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            user_env = api.Environment(cr, self.user_id, {"interactive": True})
            with patch("odoo.addons.base.models.res_users.os.urandom", side_effect=fixed_entropy):
                existing_secret = user_env["res.users.apikeys"]._generate(
                    "smart_core.machine",
                    "collision sentinel",
                )
            cr.commit()

        with self.assertRaises(AccessError):
            with registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                with patch("odoo.addons.base.models.res_users.os.urandom", side_effect=fixed_entropy):
                    issue_machine_api_key(
                        env,
                        actor_user=env["res.users"].sudo().browse(self.user_id),
                        password=self.password,
                        name="must not bind ambiguous native key",
                        scopes=["intent.read"],
                        company_ids=[self.company_a_id],
                        expires_at=fields.Datetime.now() + timedelta(hours=1),
                        trace_id="duplicate-prefix-test",
                    )

        self.env.cr.execute(
            "SELECT count(*) FROM res_users_apikeys WHERE user_id = %s AND index = %s",
            [self.user_id, existing_secret[:8]],
        )
        self.assertEqual(self.env.cr.fetchone()[0], 1)
        self.assertFalse(self.env["sc.auth.credential.policy"].sudo().search([
            ("user_id", "=", self.user_id),
            ("name", "=", "must not bind ambiguous native key"),
        ]))

    def test_concurrent_native_key_creation_binds_each_unique_native_record(self):
        database = self.env.cr.dbname
        barrier = threading.Barrier(2)

        def create_key(index):
            registry = Registry(database)
            barrier.wait(timeout=10)
            with registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                policy, secret = issue_machine_api_key(
                    env,
                    actor_user=env["res.users"].sudo().browse(self.user_id),
                    password=self.password,
                    name=f"concurrent integration {index}",
                    scopes=["intent.read"],
                    company_ids=[self.company_a_id],
                    expires_at=fields.Datetime.now() + timedelta(hours=1),
                    trace_id=f"concurrent-key-{index}",
                )
                result = (policy.id, policy.native_key_id, policy.credential_id, secret[:8])
                cr.commit()
                return result

        with ThreadPoolExecutor(max_workers=2) as pool:
            rows = list(pool.map(create_key, (1, 2)))

        native_ids = {row[1] for row in rows}
        self.assertEqual(len(native_ids), 2)
        for _policy_id, native_id, credential_id, prefix in rows:
            self.assertEqual(credential_id, f"odoo_api_key:{native_id}")
            self.env.cr.execute(
                "SELECT count(*) FROM res_users_apikeys WHERE id = %s AND user_id = %s AND index = %s",
                [native_id, self.user_id, prefix],
            )
            self.assertEqual(self.env.cr.fetchone()[0], 1)

    def test_revocation_removes_native_key_and_rejects_exchange(self):
        policy, secret = self._issue()

        self._revoke(policy)

        self.assertEqual(policy.state, "revoked")
        self.assertFalse(policy.native_key_exists())
        with self.assertRaises(AccessDenied):
            self._authenticate(secret)

    def test_revocation_immediately_invalidates_issued_machine_token(self):
        policy, secret = self._issue()
        principal = self._authenticate(secret)
        payload = principal.claims()

        self._revoke(policy, trace_id="revoke-token-test")

        with self.assertRaises(AccessDenied):
            _validated_token_principal(payload, self.user, self.env)

    def test_policy_company_narrowing_immediately_invalidates_machine_token(self):
        policy, secret = self._issue(company_ids=[self.company_a.id, self.company_b.id])
        principal = self._authenticate(secret)
        payload = principal.claims()
        self._write_persistent(
            "sc.auth.credential.policy",
            policy.id,
            {"company_ids": [(6, 0, [self.company_b.id])]},
        )

        with self.assertRaises(AccessDenied):
            _validated_token_principal(payload, self.user, self.env)

    def test_role_claims_are_revalidated_against_odoo_groups(self):
        _policy, secret = self._issue()
        payload = self._authenticate(secret).claims()
        payload["role_xmlids"] = sorted(set(payload["role_xmlids"] + ["base.group_system"]))

        with self.assertRaises(AccessDenied):
            _validated_token_principal(payload, self.user, self.env)

    def test_rotation_revokes_predecessor_and_returns_distinct_native_key(self):
        policy, old_secret = self._issue()

        registry = Registry(self.env.cr.dbname)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            replacement, new_secret = rotate_machine_api_key(
                env,
                policy=env["sc.auth.credential.policy"].sudo().browse(policy.id),
                actor_user=env["res.users"].sudo().browse(self.user_id),
                password=self.password,
                trace_id="rotate-test",
            )
            replacement_id = replacement.id
            cr.commit()
        policy.invalidate_recordset()
        replacement = self.env["sc.auth.credential.policy"].sudo().browse(replacement_id)

        self.assertNotEqual(new_secret, old_secret)
        self.assertEqual(policy.state, "revoked")
        self.assertEqual(replacement.rotated_from_id, policy)
        with self.assertRaises(AccessDenied):
            self._authenticate(old_secret)
        self.assertEqual(self._authenticate(new_secret).credential_id, replacement.credential_id)

    def test_expired_key_is_rejected(self):
        policy, secret = self._issue()
        self._write_persistent("sc.auth.credential.policy", policy.id, {
            "expires_at": fields.Datetime.now() - timedelta(seconds=1),
        })

        with self.assertRaises(AccessDenied) as rejected:
            self._authenticate(secret)
        self.assertEqual(str(rejected.exception), "API key is expired")

    def test_list_projects_expiry_and_audits_transition_exactly_once(self):
        policy, _secret = self._issue()
        self._write_persistent("sc.auth.credential.policy", policy.id, {
            "expires_at": fields.Datetime.now() - timedelta(seconds=1),
        })
        token = self._human_token()

        first = self._http_intent("auth.credential.list", {}, token=token)
        second = self._http_intent("auth.credential.list", {}, token=token)

        self.assertTrue(first.get("ok"), first)
        self.assertTrue(second.get("ok"), second)
        first_rows = (first.get("data") or {}).get("credentials") or []
        first_policy = next(row for row in first_rows if row.get("credential_id") == policy.credential_id)
        self.assertEqual(first_policy.get("state"), "expired")
        policy.invalidate_recordset(["state"])
        self.assertEqual(policy.state, "expired")
        audits = self.env["sc.auth.credential.audit"].sudo().search([
            ("credential_id", "=", policy.credential_id),
            ("event_code", "=", "AUTH_API_KEY_EXPIRED"),
        ])
        self.assertEqual(len(audits), 1)

    def test_inactive_user_is_rejected(self):
        _policy, secret = self._issue()
        self._write_persistent("res.users", self.user.id, {"active": False})

        with self.assertRaises(AccessDenied):
            self._authenticate(secret)

    def test_repeated_failures_are_rate_limited_without_storing_key(self):
        bad_secret = "0" * 40
        now = fields.Datetime.now()
        state = {}
        for _index in range(THROTTLE_MAX_FAILURES):
            state.update(_next_throttle_failure_values(
                now=now,
                window_started_at=state.get("window_started_at"),
                failure_count=state.get("failure_count", 0),
            ))

        self.assertEqual(state["failure_count"], THROTTLE_MAX_FAILURES)
        self.assertGreater(state["blocked_until"], now)
        subject_hash = _fingerprint(self.client_identity, "test-only-pepper")
        self.assertNotIn(bad_secret, subject_hash)
        self.assertEqual(len(subject_hash), 64)

    def test_wrong_api_key_is_rejected(self):
        with self.assertRaises(AccessDenied):
            self._authenticate("0" * 40)

    def test_http_machine_exchange_returns_short_scoped_token_and_audit(self):
        policy, secret = self._issue()
        response = self.url_open(
            f"/api/v1/intent?db={self.env.cr.dbname}",
            data=json.dumps({
                "intent": "auth.machine.token",
                "params": {
                    "db": self.env.cr.dbname,
                    "credential": {
                        "type": "api_key",
                        "secret": secret,
                        "requested_scope": ["intent.read"],
                    },
                },
            }),
            headers={"Content-Type": "application/json", "X-Anonymous-Intent": "true"},
        )
        result = self._json_response(response)

        self.assertTrue(result.get("ok"), result)
        data = result.get("data") or {}
        token = (data.get("session") or {}).get("token")
        self.assertTrue(token, result)
        payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
        self.assertEqual(payload.get("auth_method"), "api_key")
        self.assertEqual(payload.get("principal_type"), "machine")
        self.assertLessEqual(int(payload["exp"]) - int(payload["iat"]), 15 * 60)
        self.assertEqual((data.get("principal") or {}).get("credential_id"), policy.credential_id)
        audit = self.env["sc.auth.credential.audit"].sudo().search([
            ("credential_id", "=", policy.credential_id),
            ("event_code", "=", "AUTH_MACHINE_TOKEN_ISSUED"),
        ], limit=1)
        self.assertTrue(audit)
        self.assertNotIn(secret, json.dumps(audit.read()[0], default=str))

    def test_http_human_can_create_list_rotate_and_revoke_native_key(self):
        token = self._human_token()
        create_result = self._http_intent(
            "auth.credential.create",
            {
                "name": "HTTP managed integration",
                "scope": ["intent.read"],
                "company_ids": [self.company_a.id],
                "credential": {"type": "password", "secret": self.password},
            },
            token=token,
        )
        self.assertTrue(create_result.get("ok"), create_result)
        created_data = create_result.get("data") or {}
        credential_id = (created_data.get("credential") or {}).get("credential_id")
        first_secret = created_data.get("api_key")
        self.assertTrue(credential_id, create_result)
        self.assertTrue(first_secret, create_result)
        self.assertEqual(created_data.get("secret_display"), "once")
        self.assertEqual(
            ((create_result.get("meta") or {}).get("evidence_policy") or {}).get("browser_capture"),
            "forbidden_while_visible",
        )

        list_result = self._http_intent("auth.credential.list", {}, token=token)
        self.assertTrue(list_result.get("ok"), list_result)
        list_text = json.dumps(list_result, default=str)
        self.assertNotIn(first_secret, list_text)
        listed = (list_result.get("data") or {}).get("credentials") or []
        self.assertIn(credential_id, {row.get("credential_id") for row in listed})
        self.assertFalse((list_result.get("data") or {}).get("secret_returned"))

        rotate_result = self._http_intent(
            "auth.credential.rotate",
            {
                "credential_id": credential_id,
                "credential": {"type": "password", "secret": self.password},
            },
            token=token,
        )
        self.assertTrue(rotate_result.get("ok"), rotate_result)
        rotated_data = rotate_result.get("data") or {}
        replacement_id = (rotated_data.get("credential") or {}).get("credential_id")
        replacement_secret = rotated_data.get("api_key")
        self.assertTrue(replacement_id, rotate_result)
        self.assertTrue(replacement_secret, rotate_result)
        self.assertNotEqual(replacement_secret, first_secret)
        self.assertTrue(rotated_data.get("predecessor_revoked"))
        self.assertEqual(
            ((rotate_result.get("meta") or {}).get("evidence_policy") or {}).get("classification"),
            "one_time_secret",
        )

        revoke_result = self._http_intent(
            "auth.credential.revoke",
            {"credential_id": replacement_id},
            token=token,
        )
        self.assertTrue(revoke_result.get("ok"), revoke_result)
        self.assertTrue((revoke_result.get("data") or {}).get("sessions_invalidated"))
        self.assertEqual(
            ((revoke_result.get("data") or {}).get("credential") or {}).get("state"),
            "revoked",
        )

    def test_machine_token_cannot_manage_credentials(self):
        _policy, secret = self._issue()
        exchange = self._http_intent(
            "auth.machine.token",
            {
                "db": self.env.cr.dbname,
                "credential": {
                    "type": "api_key",
                    "secret": secret,
                    "requested_scope": ["intent.read"],
                },
            },
            anonymous=True,
        )
        self.assertTrue(exchange.get("ok"), exchange)
        token = (((exchange.get("data") or {}).get("session") or {}).get("token"))
        self.assertTrue(token, exchange)

        result = self._http_intent("auth.credential.list", {}, token=token)

        self.assertFalse(result.get("ok"), result)
        self.assertIn(self.last_http_status, (401, 403))

    def test_machine_token_cannot_route_an_authenticated_intent_to_another_database(self):
        _policy, secret = self._issue()
        exchange = self._http_intent(
            "auth.machine.token",
            {
                "db": self.env.cr.dbname,
                "credential": {
                    "type": "api_key",
                    "secret": secret,
                    "requested_scope": ["intent.read"],
                },
            },
            anonymous=True,
        )
        token = (((exchange.get("data") or {}).get("session") or {}).get("token"))
        self.assertTrue(token, exchange)

        response = self.url_open(
            f"/api/v1/intent?db={self.env.cr.dbname}",
            data=json.dumps({
                "intent": "api.data",
                "params": {
                    "db": "other_database",
                    "model": "res.company",
                    "op": "search_read",
                    "domain": [],
                    "fields": ["id"],
                    "limit": 1,
                },
            }),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        )
        result = self._json_response(response)

        self.assertFalse(result.get("ok"), result)
        self.assertIn(self.last_http_status, (401, 403))

    def test_http_machine_exchange_rejects_cross_database_route(self):
        _policy, secret = self._issue()
        response = self.url_open(
            f"/api/v1/intent?db={self.env.cr.dbname}",
            data=json.dumps({
                "intent": "auth.machine.token",
                "params": {
                    "db": "other_database",
                    "credential": {"type": "api_key", "secret": secret},
                },
            }),
            headers={"Content-Type": "application/json", "X-Anonymous-Intent": "true"},
        )
        result = self._json_response(response)

        self.assertFalse(result.get("ok"), result)
        self.assertEqual(self.last_http_status, 401)

    def test_api_key_never_falls_back_to_password_login(self):
        _policy, secret = self._issue()
        response = self.url_open(
            f"/api/v1/intent?db={self.env.cr.dbname}",
            data=json.dumps({
                "intent": "login",
                "params": {
                    "db": self.env.cr.dbname,
                    "credential": {
                        "type": "password",
                        "login": self.user.login,
                        "secret": secret,
                    },
                },
            }),
            headers={"Content-Type": "application/json", "X-Anonymous-Intent": "true"},
        )
        result = self._json_response(response)

        self.assertFalse(result.get("ok"), result)
        self.assertEqual(self.last_http_status, 401)

    def test_interactive_login_rejects_api_key_credential_type(self):
        _policy, secret = self._issue()
        response = self.url_open(
            f"/api/v1/intent?db={self.env.cr.dbname}",
            data=json.dumps({
                "intent": "login",
                "params": {
                    "db": self.env.cr.dbname,
                    "credential": {
                        "type": "api_key",
                        "login": self.user.login,
                        "secret": secret,
                    },
                },
            }),
            headers={"Content-Type": "application/json", "X-Anonymous-Intent": "true"},
        )
        result = self._json_response(response)

        self.assertFalse(result.get("ok"), result)
        self.assertEqual(self.last_http_status, 400)
