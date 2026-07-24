#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import production_acceptance_harness as harness


class FakeAcceptanceHandler(BaseHTTPRequestHandler):
    login_count = 0
    tokens: set[str] = set()
    authorization_by_token: dict[str, int] = {}

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _reply(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/":
            body = b'<html><script src="/assets/index-test.js"></script></html>'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/assets/index-test.js":
            body = b"console.log('acceptance')"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        size = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(size).decode("utf-8"))
        intent = payload.get("intent")
        auth = self.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        if intent == "login":
            if self.headers.get("X-Anonymous-Intent") != "1":
                self._reply(403, {"ok": False, "error": {"code": "AUTH_REQUIRED"}})
                return
            type(self).login_count += 1
            token = f"clean-token-{type(self).login_count}"
            type(self).tokens.add(token)
            self._reply(200, {"ok": True, "data": {"token": token}})
            return
        if not token or token not in type(self).tokens:
            self._reply(401, {"ok": False, "error": {"code": "AUTH_REQUIRED"}})
            return
        type(self).authorization_by_token[token] = type(self).authorization_by_token.get(token, 0) + 1
        if intent == "system.init":
            self._reply(
                200,
                {
                    "ok": True,
                    "data": {
                        "role_surface": {"role_code": "business_config_admin"},
                        "nav": [
                            {
                                "label": "智慧施工管理平台",
                                "children": [
                                    {"label": "我的工作"},
                                    {"label": "项目台账"},
                                    {"label": "合同中心"},
                                    {"label": "付款办理"},
                                ],
                            }
                        ],
                        "workspace_home": {
                            "actions": [
                                {"key": "open_my_work", "intent": "ui.contract"}
                            ]
                        },
                    },
                },
            )
            return
        if intent == "ui.contract":
            self._reply(200, {"ok": True, "data": {"nav": []}})
            return
        if intent == "api.data":
            self._reply(200, {"ok": True, "data": {"records": []}})
            return
        self._reply(404, {"ok": False, "error": {"code": "NOT_FOUND"}})


class ProductionAcceptanceHarnessTest(unittest.TestCase):
    def setUp(self) -> None:
        FakeAcceptanceHandler.login_count = 0
        FakeAcceptanceHandler.tokens = set()
        FakeAcceptanceHandler.authorization_by_token = {}
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeAcceptanceHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_two_runs_use_distinct_clean_http_tokens(self) -> None:
        report = harness.run_acceptance(
            base_url=self.base_url,
            db_name="sc_demo",
            login="candidate-user",
            password="never-print-this-password",
            run_count=2,
        )
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["run_count"], 2)
        self.assertTrue(report["repeated_clean_session_pass"])
        self.assertEqual(len(FakeAcceptanceHandler.tokens), 2)
        self.assertTrue(all(count >= 5 for count in FakeAcceptanceHandler.authorization_by_token.values()))
        serialized = json.dumps(report)
        self.assertNotIn("never-print-this-password", serialized)
        self.assertNotIn("clean-token-", serialized)

    def test_harness_has_no_odoo_request_or_direct_token_generation_dependency(self) -> None:
        source = Path(harness.__file__).read_text(encoding="utf-8")
        self.assertNotIn("from odoo", source)
        self.assertNotIn("import odoo", source)
        self.assertNotIn("generate_" + "token(", source)
        self.assertNotIn("odoo " + "shell", source)

    def test_package_digest_changes_when_package_content_changes(self) -> None:
        observed = harness.package_digest()
        self.assertRegex(observed, r"^[0-9a-f]{64}$")
        self.assertEqual(observed, harness.package_digest())


if __name__ == "__main__":
    unittest.main()
