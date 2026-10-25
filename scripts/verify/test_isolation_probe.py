#!/usr/bin/env python3
from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.verify.isolation_probe import main


class IsolationProbeTests(unittest.TestCase):
    def test_missing_or_zero_test_count_does_not_pass(self):
        for output in ("", "Ran 0 tests in 0.001s\nOK"):
            with self.subTest(output=output), patch(
                "scripts.verify.isolation_probe.run_modules", return_value=(0, output),
            ):
                self.assertEqual(main(["first", "second"]), 1)

    def test_failed_orders_do_not_pass(self):
        for codes in ((1, 1), (0, 1), (1, 0)):
            with self.subTest(codes=codes), patch(
                "scripts.verify.isolation_probe.run_modules",
                side_effect=[(code, "same output") for code in codes],
            ):
                self.assertEqual(main(["first", "second"]), 1)

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
