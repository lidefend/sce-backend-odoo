#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import unittest
from email.message import Message
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/verify/frontend_acceptance_login_probe.py"
SPEC = importlib.util.spec_from_file_location("frontend_acceptance_login_probe", MODULE_PATH)
PROBE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(PROBE)


class _Response:
    def __init__(self, body: bytes, status: int = 200, content_type: str = "application/json"):
        self._body = body
        self.status = status
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class FrontendAcceptanceLoginProbeTest(unittest.TestCase):
    def run_probe(self, response):
        secret = "fixture-secret-must-never-appear"
        output = io.StringIO()
        environment = {
            "DB_NAME": "sc_frontend_acceptance",
            "SC_ACCEPTANCE_FIXTURE_PASSWORD": secret,
        }
        with mock.patch.dict(os.environ, environment, clear=True), mock.patch.object(
            PROBE.urlrequest, "urlopen", side_effect=response if isinstance(response, Exception) else None,
            return_value=None if isinstance(response, Exception) else response,
        ), contextlib.redirect_stdout(output):
            status = PROBE.probe()
        self.assertNotIn(secret, output.getvalue())
        return status, output.getvalue()

    def test_accepts_successful_session_without_logging_token(self) -> None:
        token = "jwt-must-never-appear"
        status, output = self.run_probe(
            _Response((f'{{"ok":true,"data":{{"session":{{"token":"{token}"}}}}}}').encode())
        )
        self.assertEqual(status, 0)
        self.assertIn("PASS http=200", output)
        self.assertNotIn(token, output)

    def test_reports_sanitized_http_rejection(self) -> None:
        headers = Message()
        headers["Content-Type"] = "application/json; charset=utf-8"
        rejection = HTTPError(
            PROBE.INTENT_URL,
            401,
            "Unauthorized",
            headers,
            io.BytesIO(b'{"ok":false,"code":401,"error":{"error_code":"AUTH_DENIED"}}'),
        )
        status, output = self.run_probe(rejection)
        self.assertEqual(status, 2)
        self.assertIn(
            "FAIL http=401 content_type=application/json code=401 error_code=AUTH_DENIED",
            output,
        )

    def test_reports_sanitized_wrapped_rejection(self) -> None:
        headers = Message()
        headers["Content-Type"] = "application/json"
        rejection = HTTPError(
            PROBE.INTENT_URL,
            401,
            "Unauthorized",
            headers,
            io.BytesIO(
                b'{"jsonrpc":"2.0","result":{"ok":false,"code":401,'
                b'"error":{"error_code":"AUTH_REQUIRED"}}}'
            ),
        )
        status, output = self.run_probe(rejection)
        self.assertEqual(status, 2)
        self.assertIn("code=401 error_code=AUTH_REQUIRED", output)

    def test_rejects_missing_or_drifted_identity_before_http(self) -> None:
        for environment in (
            {"DB_NAME": "other", "SC_ACCEPTANCE_FIXTURE_PASSWORD": "secret"},
            {"DB_NAME": "sc_frontend_acceptance"},
        ):
            with self.subTest(environment=environment), mock.patch.dict(
                os.environ, environment, clear=True
            ), mock.patch.object(PROBE.urlrequest, "urlopen") as request, contextlib.redirect_stdout(
                io.StringIO()
            ):
                self.assertEqual(PROBE.probe(), 2)
                request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
