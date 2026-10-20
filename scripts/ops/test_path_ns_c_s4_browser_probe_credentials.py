#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guard the S4 browser probe's per-entry credential contract.

The probe signs the same-name ``admin`` into two namespaces.  It must never
carry a literal password: each entry's secret comes from its own governed
environment variable, and a missing variable fails closed before Playwright is
loaded.  This is a source-level guard because the probe needs a live browser to
run; the contract it protects is decidable without one.
"""

from __future__ import annotations

import unittest
from pathlib import Path

PROBE = Path(__file__).with_name("path_ns_c_s4_browser_probe.mjs")


class ProbeCredentialContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = PROBE.read_text(encoding="utf-8")

    def test_no_literal_password_is_checked_in(self) -> None:
        self.assertNotIn("'123456'", self.source)
        self.assertNotIn('"123456"', self.source)

    def test_each_entry_owns_its_governed_environment_variable(self) -> None:
        self.assertIn("SC_DEMO_USER_PASSWORD", self.source)
        self.assertIn("SC_PLATFORM_ADMIN_PASSWORD", self.source)

    def test_missing_credentials_are_resolved_before_playwright_is_required(self) -> None:
        self.assertLess(
            self.source.index("resolveEntryCredential("),
            self.source.index("createRequire(pwPath)(pwPath)"),
        )

    def test_login_fills_the_resolved_credential(self) -> None:
        self.assertIn("await page.fill('input[aria-label=\"账号\"]', credential.login);", self.source)
        self.assertIn("await page.fill('input[aria-label=\"密码\"]', credential.password);", self.source)


if __name__ == "__main__":
    unittest.main()
