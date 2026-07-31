#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("production_candidate_manifest_sync.py")
SPEC = importlib.util.spec_from_file_location("production_candidate_manifest_sync", SCRIPT)
assert SPEC and SPEC.loader
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class CandidateManifestSyncTests(unittest.TestCase):
    def test_rc12_formal_manifest_set_matches_exact_identity(self):
        directory = sync.SECURE_ROOT / "rc12-final-image-rehearsal/manifests"
        digests = sync.validate(
            directory,
            "3fb17948feacb34c2574668eaba7ddb2ad4bef26",
            "sha256:cecdeb03ea68a1d2ddead0cf3f3ffb7a391948ba7de92e3919b752b7635d3a1d",
            "1.0.0-rc.12",
        )
        self.assertEqual(set(digests), set(sync.FILES))

    def test_remote_contract_is_new_immutable_directory_only(self):
        source = sync.REMOTE_INSTALL
        self.assertIn('/opt/sce/candidates', source)
        self.assertIn('os.replace(staging, target)', source)
        self.assertIn('immutable target differs', source)
        self.assertNotIn('docker', source)
        self.assertNotIn('systemctl', source)
        self.assertNotIn('shutil.rmtree(target)', source)


if __name__ == "__main__":
    unittest.main()
