#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Negative and positive cases for the login-envelope consumption guard."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import login_envelope_consumption_guard as guard


CLEAN_READER = """
from python_http_smoke_utils import extract_login_token

def token_from_login(resp):
    token = extract_login_token(resp)
    if not token:
        raise RuntimeError("login response missing token")
    return token
"""

DECLARED_SESSION = """
def token_from_login(resp):
    data = resp.get("data") or {}
    session = data.get("session") or {}
    return session.get("token")
"""

BOOTSTRAP_FLAT = """
def token_from_bootstrap(http_post_json, url, params):
    resp = http_post_json(url, params)
    data = resp.get("data") or {}
    token = data.get("token")
    return token
"""

NAIVE_TOP_LEVEL = """
def token_from_login(login_resp):
    token = (login_resp.get("data") or {}).get("token")
    if not token:
        raise RuntimeError("login response missing token")
    return token
"""

NAIVE_LOGIN_DATA = """
def token_from_login(helper, login_payload):
    login_data = helper.unwrap_data(login_payload)
    token = str(login_data.get("token") or "").strip()
    return token
"""

NAIVE_DATA_ALIAS = """
def token_from_login(http_post_json, url, params):
    login_resp = http_post_json(url, {"intent": "login", "params": params})
    data = login_resp.get("data")
    token = data.get("token")
    return token
"""

UNPARSEABLE = "def broken(:\n    pass\n"


class LoginEnvelopeConsumptionGuardTest(unittest.TestCase):
    def test_clean_shared_reader_has_no_violation(self) -> None:
        self.assertEqual(guard.find_violations("scripts/verify/clean.py", CLEAN_READER), [])

    def test_declared_session_path_has_no_violation(self) -> None:
        self.assertEqual(guard.find_violations("scripts/verify/session.py", DECLARED_SESSION), [])

    def test_bootstrap_flat_token_is_allowed(self) -> None:
        # session.bootstrap publishes a flat data.token; its consumers are not login consumers.
        self.assertEqual(guard.find_violations("scripts/verify/bootstrap.py", BOOTSTRAP_FLAT), [])

    def test_naive_top_level_idiom_is_flagged(self) -> None:
        self.assertTrue(guard.find_violations("scripts/verify/naive.py", NAIVE_TOP_LEVEL))

    def test_naive_login_derived_alias_is_flagged(self) -> None:
        self.assertTrue(guard.find_violations("scripts/verify/naive2.py", NAIVE_LOGIN_DATA))

    def test_naive_data_alias_is_flagged(self) -> None:
        self.assertTrue(guard.find_violations("scripts/verify/naive3.py", NAIVE_DATA_ALIAS))

    def test_unparseable_source_fails_closed(self) -> None:
        self.assertTrue(guard.find_violations("scripts/verify/broken.py", UNPARSEABLE))

    def test_scan_is_clean_then_detects_injected_naive_reader(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts" / "verify").mkdir(parents=True)
            (root / "scripts" / "verify" / "good.py").write_text(CLEAN_READER, encoding="utf-8")

            # Baseline: the clean tree passes before any injection.
            self.assertEqual(guard.scan_root(root), [])

            # Inject a naive consumer; the guard must fail closed on it.
            (root / "scripts" / "verify" / "injected.py").write_text(NAIVE_TOP_LEVEL, encoding="utf-8")
            violations = guard.scan_root(root)
            self.assertTrue(violations)
            self.assertTrue(any("injected.py" in line for line in violations))

    def test_repository_scan_is_clean(self) -> None:
        self.assertEqual(guard.scan_repository(), [])


if __name__ == "__main__":
    unittest.main()
