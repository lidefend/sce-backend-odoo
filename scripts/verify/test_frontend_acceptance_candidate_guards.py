from __future__ import annotations

import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "scripts/dev/frontend_acceptance_runtime.sh"


def _guard_block() -> str:
    text = RUNTIME.read_text(encoding="utf-8")
    start = text.index("standard_profile_name() {")
    end = text.index("# Exact existing standard-preview adapter inputs")
    return text[start:end]


class CandidateGuardHarness:
    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.receipt = Path(self.tmp.name) / "candidate-runtime-identity.json"

    def write_receipt(self, namespace: str | None) -> str:
        if namespace is None:
            return str(self.receipt)
        self.receipt.write_text(json.dumps({"namespace_id": namespace}), encoding="utf-8")
        return str(self.receipt)

    def run(
        self,
        profile: str,
        guard: str,
        *,
        served_sha: str = "9d17a9bf04cef2481ff1840d41d87d6806680ee4",
        served_db: str = "sc_frontend_acceptance_candidate",
        live_ns: str = "ns_live",
        receipt_ns: str = "ns_live",
        receipt_path: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if receipt_path is None:
            receipt_path = self.write_receipt(receipt_ns)
        expected_sha = "9d17a9bf04cef2481ff1840d41d87d6806680ee4"
        mocks = textwrap.dedent(
            f"""
            git() {{ echo "{expected_sha}"; }}
            container_env_value() {{ if [[ "$2" == SC_SOURCE_REVISION ]]; then echo "{served_sha}"; else echo "{served_db}"; fi; }}
            docker() {{ echo "{live_ns}"; }}
            python3() {{ echo "{receipt_ns}"; }}
            export CANDIDATE_RUNTIME_IDENTITY_RECEIPT="{receipt_path}"
            export ROOT_DIR=/fixture
            export BACKEND_ACCEPTANCE_NAME=cand-backend
            export COMPOSE_PROJECT_NAME=sc-fe-candidate-770
            export DB_USER=odoo
            export DB_NAME=sc_frontend_acceptance_candidate
            export FRONTEND_ACCEPTANCE_PORT=5178
            export VITE_API_PROXY_TARGET=http://127.0.0.1:18088
            """
        )
        script = (
            "set -u\n"
            f"export SC_ACCEPTANCE_RUNTIME_PROFILE={profile}\n"
            + mocks
            + _guard_block()
            + f"\n{guard}; echo rc=$?\n"
        )
        return subprocess.run(
            ["bash", "-c", script],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )


class CandidateIdentityGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.h = CandidateGuardHarness()

    def tearDown(self) -> None:
        self.h.tmp.cleanup()

    def test_candidate_identity_guard_passes_on_exact_identity(self) -> None:
        result = self.h.run("candidate", "candidate_identity_guard")
        self.assertIn("rc=0", result.stdout)

    def test_candidate_identity_guard_blocks_served_sha_mismatch(self) -> None:
        result = self.h.run(
            "candidate",
            "candidate_identity_guard",
            served_sha="0" * 40,
        )
        self.assertIn("rc=2", result.stdout)
        self.assertIn("served revision", result.stdout)

    def test_candidate_identity_guard_blocks_shared_database(self) -> None:
        result = self.h.run(
            "candidate",
            "candidate_identity_guard",
            served_db="sc_frontend_acceptance",
        )
        self.assertIn("rc=2", result.stdout)
        self.assertIn("shared acceptance database", result.stdout)

    def test_local_profile_skips_candidate_guards(self) -> None:
        result = self.h.run("local", "candidate_identity_guard")
        self.assertIn("rc=0", result.stdout)

    def test_unknown_profile_fails_closed_in_guard(self) -> None:
        result = self.h.run("typo", "candidate_identity_guard")
        self.assertIn("rc=2", result.stdout)


class CandidateDbUuidGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.h = CandidateGuardHarness()

    def tearDown(self) -> None:
        self.h.tmp.cleanup()

    def test_db_uuid_guard_passes_on_match(self) -> None:
        result = self.h.run("candidate", "candidate_db_uuid_guard", live_ns="ns_live", receipt_ns="ns_live")
        self.assertIn("rc=0", result.stdout)

    def test_db_uuid_guard_blocks_mismatch(self) -> None:
        result = self.h.run("candidate", "candidate_db_uuid_guard", live_ns="ns_other", receipt_ns="ns_live")
        self.assertIn("rc=2", result.stdout)
        self.assertIn("DB UUID mismatch", result.stdout)

    def test_db_uuid_guard_blocks_empty_namespace(self) -> None:
        result = self.h.run("candidate", "candidate_db_uuid_guard", live_ns="", receipt_ns="ns_live")
        self.assertIn("rc=2", result.stdout)

    def test_db_uuid_guard_blocks_missing_receipt(self) -> None:
        result = self.h.run(
            "candidate",
            "candidate_db_uuid_guard",
            receipt_path=str(Path(self.h.tmp.name) / "missing.json"),
        )
        self.assertIn("rc=2", result.stdout)
        self.assertIn("receipt missing", result.stdout)

    def test_unknown_profile_fails_closed_in_db_uuid_guard(self) -> None:
        result = self.h.run("typo", "candidate_db_uuid_guard")
        self.assertIn("rc=2", result.stdout)


if __name__ == "__main__":
    unittest.main()
