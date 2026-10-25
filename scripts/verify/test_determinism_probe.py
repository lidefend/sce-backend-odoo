#!/usr/bin/env python3
from __future__ import annotations

import unittest

from scripts.verify.determinism_probe import normalize, main


class NormalizeTests(unittest.TestCase):
    def test_strips_odoo_timestamp(self):
        self.assertEqual(
            normalize("2026-10-25 08:00:00,123 1 INFO ? odoo: hello"),
            "? odoo: hello",
        )

    def test_strips_timing_noise(self):
        self.assertEqual(
            normalize("Ran 37 tests in 6.397s\n(0.123s)\nresult"),
            "Ran 37 tests\n(elapsed)\nresult",
        )

    def test_preserves_result_content(self):
        self.assertEqual(normalize("FAIL: a test failed"), "FAIL: a test failed")


class ProbeTests(unittest.TestCase):
    def test_deterministic_command_passes(self):
        self.assertEqual(main(["--runs", "2", "python3", "-c", "print('ok')"]), 0)

    def test_diverging_command_fails(self):
        # Wall-clock output changes across runs: the probe must report divergence.
        self.assertEqual(
            main(["--runs", "2", "python3", "-c", "import time; print(time.time_ns())"]),
            1,
        )


if __name__ == "__main__":
    unittest.main()
