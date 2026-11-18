#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_backend_module_test import run_module


class RunBackendModuleTestTests(unittest.TestCase):
    def run_command(self, command: list[str], timeout: float = 2.0) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "module.log"
            code = run_module(
                module="smart_core",
                timeout_seconds=timeout,
                heartbeat_seconds=0.05,
                log_path=log_path,
                command=command,
            )
            return code, log_path.read_text(encoding="utf-8")

    def test_success_streams_output_and_finishes(self) -> None:
        code, output = self.run_command([
            sys.executable,
            "-c",
            "print('test-one PASS')",
        ])
        self.assertEqual(0, code)
        self.assertIn("test-one PASS", output)
        self.assertIn("status=passed", output)

    def test_failure_preserves_nonzero_exit_and_partial_log(self) -> None:
        code, output = self.run_command([
            sys.executable,
            "-c",
            "import sys; print('partial'); sys.exit(7)",
        ])
        self.assertEqual(7, code)
        self.assertIn("partial", output)
        self.assertIn("status=failed", output)

    def test_timeout_kills_the_process_group_and_writes_heartbeat(self) -> None:
        code, output = self.run_command([
            sys.executable,
            "-c",
            "import time; print('started', flush=True); time.sleep(10)",
        ], timeout=0.2)
        self.assertEqual(124, code)
        self.assertIn("started", output)
        self.assertIn("status=running", output)
        self.assertIn("status=timeout", output)
        self.assertIn("exit_code=124", output)

    def test_invalid_module_is_rejected_before_spawn(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                run_module(
                    module="../escape",
                    timeout_seconds=1,
                    heartbeat_seconds=0.1,
                    log_path=Path(directory) / "module.log",
                    command=[sys.executable, "-c", "raise SystemExit(0)"],
                )


if __name__ == "__main__":
    unittest.main()
