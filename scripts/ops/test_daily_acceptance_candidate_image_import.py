from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("daily_acceptance_candidate_image_import.py")
SPEC = importlib.util.spec_from_file_location("daily_acceptance_candidate_image_import", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class DailyAcceptanceCandidateImportTests(unittest.TestCase):
    def test_preflight_rejects_every_host_except_sc_root(self):
        with self.assertRaisesRegex(module.ImportError, "restricted to sc-root"):
            module.preflight("a" * 40, "sc-prod")

    def test_boundary_preflight_requires_exact_tenant_rc_head(self):
        with mock.patch.object(module, "git") as git:
            git.side_effect = lambda *args: {
                ("branch", "--show-current"): "release/tenant-rc-baosheng-fuel-v1",
                ("rev-parse", "HEAD"): "a" * 40,
                ("status", "--porcelain", "--untracked-files=all"): "",
            }[args]
            module.preflight("a" * 40, "sc-root", allow_boundary_head=True)

    def test_boundary_preflight_rejects_feature_branch(self):
        with mock.patch.object(module, "git") as git:
            git.side_effect = lambda *args: {
                ("branch", "--show-current"): "feature/unsafe",
                ("rev-parse", "HEAD"): "a" * 40,
                ("status", "--porcelain", "--untracked-files=all"): "",
            }[args]
            with self.assertRaisesRegex(module.ImportError, "tenant RC"):
                module.preflight("a" * 40, "sc-root", allow_boundary_head=True)

    def test_archive_must_stay_under_governed_candidate_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "candidate.tar"
            archive.write_bytes(b"not-an-archive")
            with self.assertRaisesRegex(module.ImportError, "governed candidate root"):
                module.validate_archive(archive, "0" * 64, "ghcr.io/lidefend/sce-product:9.9.9-rc.99")

    def test_confirmation_is_required_before_preflight(self):
        with mock.patch.dict(module.os.environ, {}, clear=True):
            with self.assertRaisesRegex(module.ImportError, "exact daily acceptance"):
                module.import_candidate(
                    expected_sha="a" * 40,
                    archive=Path("missing"),
                    archive_sha256="b" * 64,
                    image_ref="ghcr.io/lidefend/sce-product:9.9.9-rc.99",
                    local_content_id="sha256:" + "c" * 64,
                    remote_config_id="sha256:" + "d" * 64,
                    host="sc-root",
                )

    def test_existing_exact_remote_identity_skips_stream(self):
        expected_sha = "a" * 40
        config_id = "sha256:" + "d" * 64
        with (
            mock.patch.dict(
                module.os.environ,
                {"CONFIRM_DAILY_ACCEPTANCE_CANDIDATE_IMPORT": module.CONFIRMATION},
                clear=True,
            ),
            mock.patch.object(module, "preflight"),
            mock.patch.object(module, "validate_archive", return_value=(Path("candidate.tar"), config_id)),
            mock.patch.object(module, "validate_local_image"),
            mock.patch.object(module, "remote_identity", return_value=f"{config_id}|{expected_sha}"),
            mock.patch.object(module, "stream_load") as stream,
        ):
            observed = module.import_candidate(
                expected_sha=expected_sha,
                archive=Path("candidate.tar"),
                archive_sha256="b" * 64,
                image_ref="ghcr.io/lidefend/sce-product:9.9.9-rc.99",
                local_content_id="sha256:" + "c" * 64,
                remote_config_id=config_id,
                host="sc-root",
            )
        self.assertEqual(observed, f"{config_id}|{expected_sha}")
        stream.assert_not_called()

    def test_import_rechecks_remote_identity_after_stream(self):
        expected_sha = "a" * 40
        config_id = "sha256:" + "d" * 64
        with (
            mock.patch.dict(
                module.os.environ,
                {"CONFIRM_DAILY_ACCEPTANCE_CANDIDATE_IMPORT": module.CONFIRMATION},
                clear=True,
            ),
            mock.patch.object(module, "preflight"),
            mock.patch.object(module, "validate_archive", return_value=(Path("candidate.tar"), config_id)),
            mock.patch.object(module, "validate_local_image"),
            mock.patch.object(
                module,
                "remote_identity",
                side_effect=[None, f"{config_id}|{expected_sha}"],
            ),
            mock.patch.object(module, "stream_load") as stream,
        ):
            module.import_candidate(
                expected_sha=expected_sha,
                archive=Path("candidate.tar"),
                archive_sha256="b" * 64,
                image_ref="ghcr.io/lidefend/sce-product:9.9.9-rc.99",
                local_content_id="sha256:" + "c" * 64,
                remote_config_id=config_id,
                host="sc-root",
            )
        stream.assert_called_once()


if __name__ == "__main__":
    unittest.main()
