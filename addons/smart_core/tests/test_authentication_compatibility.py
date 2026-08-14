# -*- coding: utf-8 -*-
import json
import os
import uuid

from odoo import SUPERUSER_ID, api
from odoo.modules.registry import Registry
from odoo.tests.common import HttpCase, tagged


@tagged("post_install", "-at_install", "sc_auth_compat")
class TestAuthenticationCompatibility(HttpCase):

    def setUp(self):
        super().setUp()
        suffix = uuid.uuid4().hex[:10]
        self.login = f"sc_auth_compat_user_{suffix}"
        self.password = f"AuthCompatibility-{suffix}"
        previous_secret = os.environ.get("SC_JWT_SECRET")
        os.environ["SC_JWT_SECRET"] = "auth-compatibility-test-signing-secret-2026-08-14-64-bytes"
        self.addCleanup(
            lambda: os.environ.pop("SC_JWT_SECRET", None)
            if previous_secret is None
            else os.environ.__setitem__("SC_JWT_SECRET", previous_secret)
        )
        registry = Registry(self.env.cr.dbname)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env["ir.config_parameter"].sudo().set_param(
                "sc.jwt.secret",
                "auth-compatibility-test-signing-secret-2026-08-14-64-bytes",
            )
            user = env["res.users"].sudo().create({
                "name": f"Authentication Compatibility User {suffix}",
                "login": self.login,
                "password": self.password,
                "active": True,
                "groups_id": [(6, 0, [env.ref("base.group_user").id])],
            })
            self.user_id = user.id
            cr.commit()
        self.user = self.env["res.users"].sudo().browse(self.user_id)

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

    def _login(self, password, *, database=None):
        database = self.env.cr.dbname if database is None else database
        response = self.url_open(
            f"/api/v1/intent?db={database}",
            data=json.dumps({
                "intent": "login",
                "params": {
                    "login": self.login,
                    "password": password,
                    "db": database,
                    "contract_mode": "default",
                },
            }),
            headers={
                "Content-Type": "application/json",
                "X-Anonymous-Intent": "true",
            },
        )
        return self._json_response(response)

    def test_http_login_accepts_correct_password(self):
        result = self._login(self.password)

        self.assertTrue(result.get("ok"), result)
        session = (result.get("data") or {}).get("session") or {}
        self.assertTrue(session.get("token"), result)

    def test_http_login_preserves_explicit_database_route(self):
        result = self._login(self.password, database=self.env.cr.dbname)

        self.assertTrue(result.get("ok"), result)
        session = (result.get("data") or {}).get("session") or {}
        self.assertEqual(session.get("db"), self.env.cr.dbname)

    def test_http_login_rejects_wrong_password(self):
        result = self._login("wrong-password")

        self.assertFalse(result.get("ok"), result)
        self.assertEqual(self.last_http_status, 401)

    def test_http_login_rejects_inactive_user(self):
        registry = Registry(self.env.cr.dbname)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env["res.users"].sudo().browse(self.user_id).write({"active": False})
            cr.commit()

        result = self._login(self.password)

        self.assertFalse(result.get("ok"), result)
        self.assertEqual(self.last_http_status, 401)
