# -*- coding: utf-8 -*-
import importlib.util
import os
import sys
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class _AccessDenied(Exception):
    pass


class _FakeCursor:
    def __init__(self, dbname):
        self.dbname = dbname


class _FakeEnv:
    def __init__(self, dbname="db_a"):
        self.cr = _FakeCursor(dbname)


class _FakeRequest:
    def __init__(self, dbname="db_a", *, header_db=None, query_db=None, session_db=None):
        self.env = _FakeEnv(dbname)
        self.session = types.SimpleNamespace(db=session_db)
        self.httprequest = types.SimpleNamespace(
            headers={
                key: value
                for key, value in {
                    "X-Odoo-DB": header_db,
                }.items()
                if value is not None
            },
            args={
                key: value
                for key, value in {
                    "db": query_db,
                }.items()
                if value is not None
            },
        )


def _namespace(namespace_id="ns_a", database="db_a", audience="tenant"):
    return types.SimpleNamespace(
        namespace_id=namespace_id,
        database_name=database,
        audience=audience,
        alias="demo",
        duty_key="demo",
        lifecycle_state="active",
    )


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_auth(fake_request, resolved=None, real_jwt=False):
    root = Path(__file__).resolve().parents[1]
    security_dir = root / "security"

    if real_jwt:
        # The audience regression is a real PyJWT 2.7 behaviour: with
        # ``require: ["aud"]`` and no ``audience=`` argument, every token that
        # carries the claim raises InvalidAudienceError.  A stub cannot prove
        # that, so this loader uses the installed library.
        sys.modules.pop("jwt", None)
        import jwt as jwt_mod  # noqa: F401  (real module for the regression test)
    else:
        jwt_mod = types.ModuleType("jwt")
        jwt_mod.ExpiredSignatureError = type("ExpiredSignatureError", (Exception,), {})
        jwt_mod.MissingRequiredClaimError = type("MissingRequiredClaimError", (Exception,), {})
        jwt_mod.InvalidTokenError = type("InvalidTokenError", (Exception,), {})
        jwt_mod.decode = lambda *args, **kwargs: {}
        jwt_mod.encode = lambda *args, **kwargs: "token"

    http_mod = types.ModuleType("odoo.http")
    http_mod.request = fake_request
    odoo_mod = types.ModuleType("odoo")
    odoo_mod.http = http_mod
    odoo_mod.SUPERUSER_ID = 1
    odoo_mod.api = types.SimpleNamespace(Environment=lambda *args, **kwargs: None)
    exc_mod = types.ModuleType("odoo.exceptions")
    exc_mod.AccessDenied = _AccessDenied
    registry_mod = types.ModuleType("odoo.modules.registry")
    registry_mod.Registry = lambda db: None
    tools_mod = types.ModuleType("odoo.tools")
    tools_mod.config = {}

    sys.modules.update(
        {
            "jwt": jwt_mod,
            "odoo": odoo_mod,
            "odoo.http": http_mod,
            "odoo.exceptions": exc_mod,
            "odoo.modules.registry": registry_mod,
            "odoo.tools": tools_mod,
        }
    )

    pkg = types.ModuleType("smart_core")
    pkg.__path__ = [str(root)]
    security_pkg = types.ModuleType("smart_core.security")
    security_pkg.__path__ = [str(security_dir)]
    sys.modules["smart_core"] = pkg
    sys.modules["smart_core.security"] = security_pkg

    _load_module("smart_core.security.namespace_errors", security_dir / "namespace_errors.py")
    resolver = _load_module(
        "smart_core.security.namespace_resolver", security_dir / "namespace_resolver.py"
    )
    resolver.resolve_entry = lambda env, headers: resolved or _namespace()
    module = _load_module("smart_core.security.auth", security_dir / "auth.py")
    module._test_resolver = resolver
    return module


class TestAuthTokenBoundaries(unittest.TestCase):
    def setUp(self):
        self.auth = _load_auth(_FakeRequest("db_a"))

    def test_extract_bearer_token_requires_bearer_scheme(self):
        self.assertEqual(self.auth._extract_bearer_token("Bearer abc.def"), "abc.def")
        with self.assertRaises(_AccessDenied):
            self.auth._extract_bearer_token("Basic abc.def")
        with self.assertRaises(_AccessDenied):
            self.auth._extract_bearer_token("Bearer")

    def test_token_user_id_must_be_positive_integer(self):
        self.assertEqual(self.auth._token_user_id({"user_id": "7"}), 7)
        with self.assertRaises(_AccessDenied):
            self.auth._token_user_id({"user_id": "bad"})
        with self.assertRaises(_AccessDenied):
            self.auth._token_user_id({"user_id": 0})

    def test_session_user_id_must_be_positive_integer(self):
        self.assertEqual(self.auth._session_user_id("9"), 9)
        with self.assertRaises(_AccessDenied):
            self.auth._session_user_id("bad")
        with self.assertRaises(_AccessDenied):
            self.auth._session_user_id(0)

    def test_token_db_namespace_and_audience_must_match_entry_namespace(self):
        self.auth._ensure_token_db_matches_request("db_a", "ns_a", "tenant")
        with self.assertRaises(_AccessDenied):
            self.auth._ensure_token_db_matches_request("db_b", "ns_a", "tenant")
        with self.assertRaises(_AccessDenied):
            self.auth._ensure_token_db_matches_request("db_a", "ns_other", "tenant")
        with self.assertRaises(_AccessDenied):
            self.auth._ensure_token_db_matches_request("db_a", "ns_a", "platform-admin")

    def test_namespace_target_must_match_the_instance_database(self):
        auth = _load_auth(
            _FakeRequest("db_other"),
            resolved=_namespace(database="db_a"),
        )
        with self.assertRaises(_AccessDenied):
            auth._ensure_token_db_matches_request("db_a", "ns_a", "tenant")
        with self.assertRaises(_AccessDenied):
            auth._ensure_token_db_matches_request("db_a", "ns_a", "tenant")

    def test_token_version_bump_invalidates_without_changing_the_secret(self):
        self.assertTrue(self.auth.token_version_is_current(2, 2))
        self.assertFalse(self.auth.token_version_is_current(1, 2))
        self.assertFalse(self.auth.token_version_is_current("bad", 2))
        with patch.dict(os.environ, {"SC_JWT_SECRET": "x" * 32, "JWT_SECRET": ""}):
            before = self.auth._get_secret_key()
            self.assertFalse(self.auth.token_version_is_current(1, 2))
            after = self.auth._get_secret_key()
        self.assertEqual(before, after)

    def test_request_db_comes_from_entry_namespace_not_client_hints(self):
        auth = _load_auth(_FakeRequest("default_db", header_db="target_from_header"))
        self.assertEqual(auth._request_db_name(), "db_a")

        auth = _load_auth(_FakeRequest("default_db", query_db="target_from_query"))
        self.assertEqual(auth._request_db_name(), "db_a")

        auth = _load_auth(_FakeRequest("default_db", session_db="target_from_session"))
        self.assertEqual(auth._request_db_name(), "db_a")

    def test_jwt_secret_is_explicit_and_at_least_32_bytes(self):
        with patch.dict(os.environ, {"SC_JWT_SECRET": "short", "JWT_SECRET": ""}):
            with self.assertRaises(_AccessDenied):
                self.auth._get_secret_key()
        configured = "x" * 32
        with patch.dict(os.environ, {"SC_JWT_SECRET": configured, "JWT_SECRET": ""}):
            self.assertEqual(self.auth._get_secret_key(), configured)


class TestTokenAudienceBinding(unittest.TestCase):
    """A token's ``aud`` is a namespace claim, not a PyJWT verification input."""

    SECRET = "s" * 32

    def setUp(self):
        self.auth = _load_auth(_FakeRequest("db_a"), real_jwt=True)
        self._env = patch.dict(os.environ, {"SC_JWT_SECRET": self.SECRET, "JWT_SECRET": ""})
        self._env.start()
        self.addCleanup(self._env.stop)

    def _token(self, **overrides):
        now = int(time.time())
        claims = {
            "exp": now + 60,
            "iat": now,
            "jti": "jti-1",
            "token_version": 0,
            "user_id": 5,
            "db": "db_a",
            "principal_type": "human",
            "auth_method": "password",
            "credential_id": "1",
            "scope": "interactive",
            "company_id": 1,
            "allowed_company_ids": [1],
            "role_xmlids": ["base.group_user"],
            "credential_epoch": 0,
            "namespace_id": "ns_a",
            "aud": "tenant",
        }
        claims.update(overrides)
        return self.auth.jwt.encode(claims, self.SECRET, algorithm=self.auth.ALGORITHM)

    def test_token_carrying_an_audience_claim_decodes(self):
        # Regression: PyJWT 2.7 raised InvalidAudienceError here and every
        # batch-C token was rejected as invalid.
        claims = self.auth.decode_token(self._token())
        self.assertEqual(claims["aud"], "tenant")

    def test_decode_does_not_let_pyjwt_pick_the_audience(self):
        captured = {}

        def _capture(token, key, algorithms=None, options=None):
            captured.update(options or {})
            return {}

        original = self.auth.jwt.decode
        self.auth.jwt.decode = _capture
        try:
            self.auth.decode_token("t")
        finally:
            self.auth.jwt.decode = original
        self.assertFalse(captured.get("verify_aud"))
        self.assertIn("aud", captured.get("require") or [])

    def test_missing_audience_is_still_a_missing_required_claim(self):
        token = self._token()
        claims = self.auth.jwt.decode(
            token,
            self.SECRET,
            algorithms=[self.auth.ALGORITHM],
            options={"verify_aud": False},
        )
        claims.pop("aud")
        without_aud = self.auth.jwt.encode(claims, self.SECRET, algorithm=self.auth.ALGORITHM)
        with self.assertRaises(_AccessDenied) as raised:
            self.auth.decode_token(without_aud)
        self.assertIn("缺少必要字段", str(raised.exception))

    def test_tenant_token_cannot_be_replayed_on_the_platform_namespace(self):
        claims = self.auth.decode_token(self._token())
        self.auth._ensure_token_db_matches_request(
            claims["db"], claims["namespace_id"], claims["aud"]
        )
        with self.assertRaises(_AccessDenied) as raised:
            self.auth._ensure_token_db_matches_request(
                claims["db"], claims["namespace_id"], "platform-admin"
            )
        self.assertIn("NS_TOKEN_AUDIENCE_MISMATCH", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
