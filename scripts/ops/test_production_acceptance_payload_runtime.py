from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("production_acceptance_payload_runtime.py")
SPEC = importlib.util.spec_from_file_location("production_acceptance_payload_runtime", SCRIPT)
assert SPEC and SPEC.loader
RUNTIME = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNTIME)


class ProductionAcceptancePayloadRuntimeTests(unittest.TestCase):
    def test_accepts_scoped_plan_identity(self) -> None:
        RUNTIME.validate_identity(
            "sc_restore_20260808t105229z_d3e5bb8a",
            "baosheng-fuel-20260808-v1",
            "a" * 64,
            "plan",
        )

    def test_rejects_restore_path_escape(self) -> None:
        with self.assertRaisesRegex(RUNTIME.PayloadRuntimeError, "restore identity"):
            RUNTIME.validate_identity("../sc_production", "payload-v1", "a" * 64, "plan")

    def test_rejects_payload_path_escape(self) -> None:
        with self.assertRaisesRegex(RUNTIME.PayloadRuntimeError, "payload identity"):
            RUNTIME.validate_identity(
                "sc_restore_20260808t105229z_d3e5bb8a", "../payload", "a" * 64, "plan"
            )

    def test_import_requires_exact_confirmation_before_runtime_inspection(self) -> None:
        with mock.patch.dict(RUNTIME.os.environ, {}, clear=True):
            with self.assertRaisesRegex(RUNTIME.PayloadRuntimeError, "exact isolated acceptance"):
                RUNTIME.execute(
                    "sc_restore_20260808t105229z_d3e5bb8a",
                    "baosheng-fuel-20260808-v1",
                    "a" * 64,
                    "import",
                )

    def test_missing_container_empty_id_is_not_present(self) -> None:
        with mock.patch.object(RUNTIME, "run", return_value="") as command:
            self.assertFalse(RUNTIME.container_exists("sc_restore_example_payload_plan"))
        self.assertIn("--format", command.call_args.args[0])

    def test_existing_container_exact_id_is_present(self) -> None:
        with mock.patch.object(RUNTIME, "run", return_value="a" * 64):
            self.assertTrue(RUNTIME.container_exists("sc_restore_example_payload_plan"))

    def test_failed_batch_resume_is_confined_to_confirmed_import(self) -> None:
        self.assertEqual(RUNTIME.resume_failed_mode("import"), "1")
        self.assertEqual(RUNTIME.resume_failed_mode("plan"), "0")
        self.assertEqual(RUNTIME.resume_failed_mode("verify"), "0")


if __name__ == "__main__":
    unittest.main()
