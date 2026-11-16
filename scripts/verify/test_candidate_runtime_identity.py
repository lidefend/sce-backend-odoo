from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/dev/candidate_runtime_identity.py"
SPEC = importlib.util.spec_from_file_location("candidate_runtime_identity", MODULE_PATH)
assert SPEC and SPEC.loader
IDENTITY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IDENTITY)

SHA = "052686b61a3c76c56cb85dc79358748108d942c4"
DATABASE = "sc_frontend_acceptance_candidate"
PROJECT = "sc-fe-candidate-770"
NAMESPACE = "ns_0af74d2911bf"


class CandidateRuntimeIdentityTest(unittest.TestCase):
    def test_record_readback_and_verify_round_trip(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["docker"], returncode=0, stdout=f"{NAMESPACE}\n", stderr=""
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidate-runtime-identity.json"
            with mock.patch.object(IDENTITY.subprocess, "run", return_value=completed) as run:
                namespace = IDENTITY.query_namespace(
                    compose_project=PROJECT,
                    database=DATABASE,
                )
                identity = IDENTITY.make_identity(
                    source_sha=SHA,
                    database=DATABASE,
                    compose_project=PROJECT,
                    namespace_id=namespace,
                )
                IDENTITY.write_identity(path, identity)
            self.assertEqual(namespace, NAMESPACE)
            self.assertEqual(json.loads(path.read_text())["namespace_id"], NAMESPACE)
            self.assertEqual(
                IDENTITY.load_identity(
                    path,
                    source_sha=SHA,
                    database=DATABASE,
                    compose_project=PROJECT,
                ),
                identity,
            )
            command = run.call_args.args[0]
            self.assertIn(f"{PROJECT}-db-1", command)
            self.assertIn(DATABASE, command)

    def test_query_rejects_duplicate_namespace_rows(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["docker"],
            returncode=0,
            stdout=f"{NAMESPACE}\nns_ffffffffffff\n",
            stderr="",
        )
        with mock.patch.object(IDENTITY.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(IDENTITY.IdentityError, "exactly one namespace"):
                IDENTITY.query_namespace(compose_project=PROJECT, database=DATABASE)

    def test_verify_rejects_stale_source_database_or_project(self) -> None:
        identity = IDENTITY.make_identity(
            source_sha=SHA,
            database=DATABASE,
            compose_project=PROJECT,
            namespace_id=NAMESPACE,
        )
        for field, value in (
            ("source_sha", "0" * 40),
            ("database", "sc_other_candidate"),
            ("compose_project", "sc-other-candidate"),
        ):
            with self.subTest(field=field):
                payload = dict(identity)
                payload[field] = value
                with self.assertRaisesRegex(IDENTITY.IdentityError, "mismatch"):
                    IDENTITY.verify_identity(
                        payload,
                        source_sha=SHA,
                        database=DATABASE,
                        compose_project=PROJECT,
                    )

    def test_missing_or_malformed_receipt_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.json"
            with self.assertRaisesRegex(IDENTITY.IdentityError, "missing"):
                IDENTITY.load_identity(
                    missing,
                    source_sha=SHA,
                    database=DATABASE,
                    compose_project=PROJECT,
                )
            malformed = Path(directory) / "malformed.json"
            malformed.write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(IDENTITY.IdentityError, "unreadable"):
                IDENTITY.load_identity(
                    malformed,
                    source_sha=SHA,
                    database=DATABASE,
                    compose_project=PROJECT,
                )


if __name__ == "__main__":
    unittest.main()
