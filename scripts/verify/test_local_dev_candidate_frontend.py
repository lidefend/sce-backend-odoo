from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "scripts/dev/local_dev_candidate_frontend.py"
SPEC = importlib.util.spec_from_file_location("local_dev_candidate_frontend", MODULE)
assert SPEC and SPEC.loader
MODULE_UNDER_TEST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE_UNDER_TEST)


class CandidateFrontendContractTest(unittest.TestCase):
    def test_topic_branch_and_exact_sha_are_required(self):
        with mock.patch.object(MODULE_UNDER_TEST, "_git_output", side_effect=[str(ROOT), "feature/token", "a" * 40, ""]), mock.patch.dict(
            os.environ,
            {"CANDIDATE_GIT_HEAD": "a" * 40, "CONFIRM_LOCAL_DEV_CANDIDATE_FRONTEND": MODULE_UNDER_TEST.CONFIRMATION},
            clear=False,
        ):
            self.assertEqual(MODULE_UNDER_TEST._candidate_identity(ROOT), ("feature/token", "a" * 40))

    def test_main_and_sha_drift_fail_closed(self):
        with mock.patch.object(MODULE_UNDER_TEST, "_git_output", side_effect=[str(ROOT), "main", "a" * 40, ""]), mock.patch.dict(os.environ, {"CANDIDATE_GIT_HEAD": "a" * 40, "CONFIRM_LOCAL_DEV_CANDIDATE_FRONTEND": MODULE_UNDER_TEST.CONFIRMATION}, clear=False):
            with self.assertRaisesRegex(MODULE_UNDER_TEST.CandidateFrontendError, "allowed topic"):
                MODULE_UNDER_TEST._candidate_identity(ROOT)
        with mock.patch.object(MODULE_UNDER_TEST, "_git_output", side_effect=[str(ROOT), "feature/token", "a" * 40, ""]), mock.patch.dict(os.environ, {"CANDIDATE_GIT_HEAD": "b" * 40, "CONFIRM_LOCAL_DEV_CANDIDATE_FRONTEND": MODULE_UNDER_TEST.CONFIRMATION}, clear=False):
            with self.assertRaisesRegex(MODULE_UNDER_TEST.CandidateFrontendError, "equal"):
                MODULE_UNDER_TEST._candidate_identity(ROOT)

    def test_dirty_candidate_fails_closed(self):
        with mock.patch.object(MODULE_UNDER_TEST, "_git_output", side_effect=[str(ROOT), "feature/token", "a" * 40, "? dirty"]), mock.patch.dict(os.environ, {"CANDIDATE_GIT_HEAD": "a" * 40, "CONFIRM_LOCAL_DEV_CANDIDATE_FRONTEND": MODULE_UNDER_TEST.CONFIRMATION}, clear=False):
            with self.assertRaisesRegex(MODULE_UNDER_TEST.CandidateFrontendError, "clean"):
                MODULE_UNDER_TEST._candidate_identity(ROOT)

    def test_make_receives_only_governed_authority_and_candidate_dist(self):
        dev_make = (ROOT / "make/dev.mk").read_text(encoding="utf-8")
        self.assertIn("local.dev.candidate.frontend.up", dev_make)
        self.assertIn("local_dev_candidate_frontend.py up", dev_make)
        source = MODULE.read_text(encoding="utf-8")
        self.assertIn("resolve_authority_env(root)", source)
        self.assertIn('"FRONTEND_DIST_DIR=frontend/apps/web/dist-dev"', source)
        self.assertIn('API_PROXY = "http://127.0.0.1:18081"', source)
        self.assertNotIn("docker compose", source)

    def test_candidate_browser_probe_is_fixed_to_the_managed_carrier(self):
        dev_make = (ROOT / "make/dev.mk").read_text(encoding="utf-8")
        target = dev_make.split("local.dev.candidate.project_create_contract_action_scope:", 1)[1].split("\n\n", 1)[0]
        self.assertIn("local.dev.candidate.frontend.health", target)
        self.assertIn("LOCAL_DEV_CANDIDATE_FRONTEND_BINDING=1", target)
        probe = (ROOT / "scripts/verify/local_dev_project_create_contract_action_scope.sh").read_text(encoding="utf-8")
        self.assertIn('1) frontend_url="http://127.0.0.1:5176"', probe)
        self.assertIn('*) echo "invalid local.dev candidate frontend binding selector"', probe)
        self.assertNotIn("LOCAL_DEV_FRONTEND_URL", probe)


if __name__ == "__main__":
    unittest.main()
