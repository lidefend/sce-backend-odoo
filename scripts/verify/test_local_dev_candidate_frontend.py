from __future__ import annotations

import importlib.util
import os
import signal
import stat
import tempfile
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

    def test_pidfile_rejects_symlink_invalid_pid_and_foreign_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            target = base / "target"
            target.write_text('{"pid":123,"head":"' + "a" * 40 + '","root":"/tmp/root"}\n', encoding="utf-8")
            link = base / "pid"
            link.symlink_to(target)
            with self.assertRaisesRegex(MODULE_UNDER_TEST.CandidateFrontendError, "non-symlink"):
                MODULE_UNDER_TEST._read_process_identity(link)

            link.unlink()
            link.write_text("not-a-pid\n", encoding="utf-8")
            link.chmod(0o600)
            with self.assertRaisesRegex(MODULE_UNDER_TEST.CandidateFrontendError, "invalid identity"):
                MODULE_UNDER_TEST._read_process_identity(link)

            link.write_text('{"pid":123,"head":"' + "a" * 40 + '","root":"/tmp/root"}\n', encoding="utf-8")
            link.chmod(0o600)
            fake_metadata = mock.Mock(st_mode=stat.S_IFREG | 0o600, st_uid=os.getuid() + 1)
            with mock.patch.object(Path, "lstat", return_value=fake_metadata):
                with self.assertRaisesRegex(MODULE_UNDER_TEST.CandidateFrontendError, "owner"):
                    MODULE_UNDER_TEST._read_process_identity(link)

            wrong_mode = mock.Mock(st_mode=stat.S_IFREG | 0o644, st_uid=os.getuid())
            with mock.patch.object(Path, "lstat", return_value=wrong_mode):
                with self.assertRaisesRegex(MODULE_UNDER_TEST.CandidateFrontendError, "0600"):
                    MODULE_UNDER_TEST._read_process_identity(link)

    def test_down_refuses_live_process_identity_mismatch(self):
        with mock.patch.object(MODULE_UNDER_TEST, "_candidate_identity", return_value=("feature/token", "a" * 40)), mock.patch.object(Path, "exists", return_value=True), mock.patch.object(
            MODULE_UNDER_TEST, "_read_process_identity", return_value={"pid": 123, "head": "b" * 40, "root": str(ROOT)}
        ), mock.patch.object(
            MODULE_UNDER_TEST, "_validate_process", side_effect=MODULE_UNDER_TEST.CandidateFrontendError("candidate process command mismatch")
        ), mock.patch.object(os, "killpg") as killpg:
            with self.assertRaisesRegex(MODULE_UNDER_TEST.CandidateFrontendError, "command mismatch"):
                MODULE_UNDER_TEST.down(ROOT)
            killpg.assert_not_called()

    def test_down_can_clean_verified_previous_head_after_branch_advances(self):
        current_head = "a" * 40
        running_head = "b" * 40
        with mock.patch.object(MODULE_UNDER_TEST, "_candidate_identity", return_value=("feature/token", current_head)), mock.patch.object(
            Path, "exists", return_value=True
        ), mock.patch.object(
            MODULE_UNDER_TEST, "_read_process_identity", return_value={"pid": 123, "head": running_head, "root": str(ROOT)}
        ), mock.patch.object(MODULE_UNDER_TEST, "_validate_process", return_value=123) as validate, mock.patch.object(
            MODULE_UNDER_TEST, "_wait_until_stopped"
        ) as wait, mock.patch.object(Path, "unlink") as unlink, mock.patch.object(os, "killpg") as killpg:
            MODULE_UNDER_TEST.down(ROOT)
        validate.assert_called_once_with(ROOT, running_head, MODULE_UNDER_TEST.PIDFILE)
        killpg.assert_called_once_with(123, signal.SIGTERM)
        wait.assert_called_once_with(123)
        unlink.assert_called_once_with(missing_ok=True)

    def test_visual_smoke_requires_routes_and_verified_process(self):
        with mock.patch.object(MODULE_UNDER_TEST, "_candidate_identity", return_value=("feature/token", "a" * 40)), mock.patch.object(
            MODULE_UNDER_TEST, "resolve_authority_env", return_value=ROOT / ".env.dev"
        ), mock.patch.object(MODULE_UNDER_TEST, "_validate_process") as validate, mock.patch.object(
            MODULE_UNDER_TEST, "_health", return_value=True
        ), mock.patch.dict(os.environ, {"CANDIDATE_VISUAL_ROUTES_JSON": ""}, clear=False):
            with self.assertRaisesRegex(MODULE_UNDER_TEST.CandidateFrontendError, "ROUTES_JSON"):
                MODULE_UNDER_TEST.visual_smoke(ROOT)
        validate.assert_called_once_with(ROOT, "a" * 40, MODULE_UNDER_TEST.PIDFILE)

    def test_visual_smoke_uses_authority_wrapper_without_credentials(self):
        source = MODULE.read_text(encoding="utf-8")
        wrapper = (ROOT / "scripts/verify/local_dev_candidate_visual_smoke.sh").read_text(encoding="utf-8")
        browser = (ROOT / "scripts/verify/local_dev_candidate_visual_smoke.mjs").read_text(encoding="utf-8")
        self.assertIn('ENV_FILE=str(authority)', source)
        self.assertNotIn("SC_DEMO_USER_PASSWORD", source)
        self.assertIn('source "${ENV_FILE}"', wrapper)
        self.assertIn('E2E_PASSWORD="${SC_DEMO_USER_PASSWORD}"', wrapper)
        self.assertIn("report.mutationCount += 1", browser)
        self.assertIn("--sc-semantic-surface-interactive", browser)
        self.assertIn("waitForStableProductSurface", browser)
        self.assertIn('[data-workspace-primary-content][aria-busy="true"]', browser)
        self.assertIn('.product-loading-shell[aria-busy="true"]', browser)
        self.assertIn("requestAnimationFrame(() => requestAnimationFrame(resolve))", browser)
        self.assertIn("isContractV2Response", browser)
        self.assertIn("response.request().postData()", browser)
        self.assertIn("response.ok()", browser)
        self.assertIn("summarizeContractH1", browser)
        self.assertIn("contractH1Nodes", browser)
        self.assertIn("nativeTitle", browser)
        self.assertIn("visibleActions", browser)
        self.assertIn("data-backend-identity", browser)
        self.assertNotIn("waitForTimeout", browser)

if __name__ == "__main__":
    unittest.main()
