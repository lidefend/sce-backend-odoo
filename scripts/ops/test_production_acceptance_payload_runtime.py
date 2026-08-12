from __future__ import annotations

import importlib.util
import json
import tempfile
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
            "sample_tenant",
            "sample-fuel-20260808-v1",
            "a" * 64,
            "plan",
        )

    def test_rejects_restore_path_escape(self) -> None:
        with self.assertRaisesRegex(RUNTIME.PayloadRuntimeError, "restore identity"):
            RUNTIME.validate_identity(
                "../sc_production", "sample_tenant", "payload-v1", "a" * 64, "plan"
            )

    def test_rejects_payload_path_escape(self) -> None:
        with self.assertRaisesRegex(RUNTIME.PayloadRuntimeError, "payload identity"):
            RUNTIME.validate_identity(
                "sc_restore_20260808t105229z_d3e5bb8a",
                "sample_tenant",
                "../payload",
                "a" * 64,
                "plan",
            )

    def test_rejects_invalid_tenant_identity(self) -> None:
        with self.assertRaisesRegex(RUNTIME.PayloadRuntimeError, "tenant identity"):
            RUNTIME.validate_identity(
                "sc_restore_20260808t105229z_d3e5bb8a",
                "../tenant",
                "payload-v1",
                "a" * 64,
                "plan",
            )

    def test_manifest_tenant_must_match_explicit_runtime_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            payload_root = Path(temporary)
            (payload_root / "manifest.json").write_text(
                json.dumps(
                    {
                        "tenant_key": "another_tenant",
                        "payload_checksum": "a" * 64,
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RUNTIME.PayloadRuntimeError, "tenant identity differs"):
                RUNTIME._load_manifest(payload_root, "sample_tenant", "a" * 64)

    def test_import_requires_exact_confirmation_before_runtime_inspection(self) -> None:
        with mock.patch.dict(RUNTIME.os.environ, {}, clear=True):
            with self.assertRaisesRegex(RUNTIME.PayloadRuntimeError, "exact isolated acceptance"):
                RUNTIME.execute(
                    "sc_restore_20260808t105229z_d3e5bb8a",
                    "sample_tenant",
                    "sample-fuel-20260808-v1",
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

    def test_database_fingerprint_ignores_pg_dump_restrict_nonce(self) -> None:
        first = mock.Mock(
            stdout=iter([b"\\restrict abc\n", b"CREATE TABLE x();\n", b"\\unrestrict abc\n"]),
            stderr=mock.Mock(read=mock.Mock(return_value=b"")),
            wait=mock.Mock(return_value=0),
        )
        second = mock.Mock(
            stdout=iter([b"\\restrict xyz\n", b"CREATE TABLE x();\n", b"\\unrestrict xyz\n"]),
            stderr=mock.Mock(read=mock.Mock(return_value=b"")),
            wait=mock.Mock(return_value=0),
        )
        with mock.patch.object(RUNTIME.subprocess, "Popen", side_effect=[first, second]):
            self.assertEqual(
                RUNTIME.database_fingerprint("restore_db", "isolated"),
                RUNTIME.database_fingerprint("restore_db", "isolated"),
            )

    def test_database_fingerprint_streams_without_buffering_dump(self) -> None:
        process = mock.Mock(
            stdout=iter([b"CREATE TABLE x();\n", b"COPY x FROM stdin;\n"]),
            stderr=mock.Mock(read=mock.Mock(return_value=b"")),
            wait=mock.Mock(return_value=0),
        )
        with mock.patch.object(RUNTIME.subprocess, "Popen", return_value=process) as popen:
            observed = RUNTIME.database_fingerprint("restore_db", "isolated")
        self.assertEqual(
            observed,
            RUNTIME.hashlib.sha256(b"CREATE TABLE x();\nCOPY x FROM stdin;\n").hexdigest(),
        )
        self.assertIs(popen.call_args.kwargs["stdout"], RUNTIME.subprocess.PIPE)

    def test_database_fingerprint_rejects_failed_dump(self) -> None:
        process = mock.Mock(
            stdout=iter([]),
            stderr=mock.Mock(read=mock.Mock(return_value=b"pg_dump: failed\n")),
            wait=mock.Mock(return_value=1),
        )
        with mock.patch.object(RUNTIME.subprocess, "Popen", return_value=process):
            with self.assertRaisesRegex(RUNTIME.PayloadRuntimeError, "pg_dump: failed"):
                RUNTIME.database_fingerprint("restore_db", "isolated")

    def test_protected_counts_require_exact_two_integer_rows(self) -> None:
        with mock.patch.object(RUNTIME, "run", return_value="4\n9\n"):
            self.assertEqual(RUNTIME.protected_counts("restore_db", "isolated"), (4, 9))
        with mock.patch.object(RUNTIME, "run", return_value="4\ninvalid\n"):
            with self.assertRaisesRegex(RUNTIME.PayloadRuntimeError, "counts are invalid"):
                RUNTIME.protected_counts("restore_db", "isolated")


if __name__ == "__main__":
    unittest.main()
