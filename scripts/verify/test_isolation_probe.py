#!/usr/bin/env python3
from __future__ import annotations

import unittest

from scripts.verify.isolation_probe import main


class IsolationProbeTests(unittest.TestCase):
    def test_order_independent_modules_pass(self):
        self.assertEqual(
            main([
                "scripts.verify.test_determinism_probe",
                "scripts.verify.test_guard_registry_audit",
            ]),
            0,
        )


if __name__ == "__main__":
    unittest.main()
