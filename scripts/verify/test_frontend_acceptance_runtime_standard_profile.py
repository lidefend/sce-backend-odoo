from __future__ import annotations

import subprocess
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "scripts/dev/frontend_acceptance_runtime.sh"


def _helper_block() -> str:
    text = RUNTIME.read_text(encoding="utf-8")
    start = text.index("standard_profile_name() {")
    end = text.index("# Exact existing standard-preview adapter inputs")
    return text[start:end]


def _run(profile: str, body: str) -> subprocess.CompletedProcess[str]:
    script = textwrap.dedent(
        f"""
        set -u
        export SC_ACCEPTANCE_RUNTIME_PROFILE={profile}
        export FRONTEND_ACCEPTANCE_PORT=5178
        export VITE_API_PROXY_TARGET=http://127.0.0.1:18088
        {_helper_block()}
        {body}
        """
    )
    return subprocess.run(
        ["bash", "-c", script],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


class StandardProfileGuardTests(unittest.TestCase):
    def test_unknown_profile_fails_closed(self) -> None:
        result = _run("typo", 'standard_profile_name; echo rc=$?')
        self.assertIn("DENY: unknown acceptance runtime profile: typo", result.stdout)
        self.assertIn("rc=2", result.stdout)

    def test_local_profile_preserved(self) -> None:
        result = _run(
            "local",
            'echo name=$(standard_profile_name); echo url=$(standard_preview_url); echo db=$(standard_expected_db)',
        )
        self.assertIn("name=local", result.stdout)
        self.assertIn("url=http://127.0.0.1:5180", result.stdout)
        self.assertIn("db=sc_frontend_acceptance", result.stdout)

    def test_candidate_profile_isolated(self) -> None:
        result = _run(
            "candidate",
            'echo name=$(standard_profile_name); echo url=$(standard_preview_url); echo db=$(standard_expected_db); echo api=$(standard_api_url)',
        )
        self.assertIn("name=candidate", result.stdout)
        self.assertIn("url=http://127.0.0.1:5178", result.stdout)
        self.assertIn("db=sc_frontend_acceptance_candidate", result.stdout)
        self.assertIn("api=http://127.0.0.1:18088", result.stdout)

    def test_candidate_is_candidate(self) -> None:
        result = _run("candidate", "standard_profile_is_candidate; echo rc=$?")
        self.assertIn("rc=0", result.stdout)

    def test_local_is_not_candidate(self) -> None:
        result = _run("local", "standard_profile_is_candidate; echo rc=$?")
        self.assertIn("rc=1", result.stdout)


if __name__ == "__main__":
    unittest.main()
