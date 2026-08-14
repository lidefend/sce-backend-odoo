# -*- coding: utf-8 -*-
import json

from odoo.tests.common import HttpCase, tagged


@tagged("post_install", "-at_install", "sc_auth_compat")
class TestAuthenticationCompatibility(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.login = "sc_auth_compat_user"
        cls.password = "AuthCompatibility-2026"
        cls.user = cls.env["res.users"].sudo().create({
            "name": "Authentication Compatibility User",
            "login": cls.login,
            "password": cls.password,
            "active": True,
            "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
        })

    @staticmethod
    def _json_response(response):
        body = response.read() if hasattr(response, "read") else response
        if isinstance(body, bytes):
            body = body.decode("utf-8")
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
        self.assertEqual(result.get("code"), 401)

    def test_http_login_rejects_inactive_user(self):
        self.user.sudo().write({"active": False})

        result = self._login(self.password)

        self.assertFalse(result.get("ok"), result)
        self.assertEqual(result.get("code"), 401)
