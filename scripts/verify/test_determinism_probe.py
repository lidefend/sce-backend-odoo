#!/usr/bin/env python3
from __future__ import annotations

import unittest
from unittest.mock import patch

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
    def test_zero_tests_do_not_pass(self):
        with patch("scripts.verify.determinism_probe.run", return_value=(0, "Ran 0 tests in 0.001s\nOK")):
            self.assertEqual(main(["--runs", "2", "test-command"]), 1)

    def test_identical_failures_do_not_pass(self):
        with patch("scripts.verify.determinism_probe.run", return_value=(1, "FAILED")):
            self.assertEqual(main(["--runs", "2", "test-command"]), 1)

    def test_one_or_zero_runs_are_not_a_comparison(self):
        for count in ("-1", "0", "1"):
            with self.subTest(count=count), patch("sys.stderr"), self.assertRaises(SystemExit):
                main(["--runs", count, "test-command"])

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
