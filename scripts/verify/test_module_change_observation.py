#!/usr/bin/env python3
"""Offline negative tests for module.change.observation.v1."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify import module_change_observation as obsmod


def _base_obs(tmp: Path, *, result="success", ready=True, db_matches=True):
    artifact = tmp / "snapshot.json"
    artifact.write_text('{"schema": "module.runtime.facts.v1"}')
    after_sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
    before_sha = "a" * 64
    return {
        "schema": "module.change.observation.v1",
        "operation_id": "op-1",
        "db_name": "sc_dev_demo",
        "operation_origin": "cli_wrapper",
        "timestamp": "2026-11-05T00:00:00Z",
        "target_modules": ["smart_construction_core"],
        "result": result,
        "registry": {"ready": ready, "rebuilt": True, "db_matches": db_matches},
        "observer": {"name": "odoo_runtime_facts", "version": "1", "odoo_version": "17.0", "schema_version": "1"},
        "module_versions": [{"module": "smart_construction_core", "before": "17.0.0.171", "after": "17.0.0.172"}],
        "before": {"snapshot_sha256": before_sha, "fact_digest": before_sha, "module_digests": {"smart_construction_core": before_sha}},
        "after": {"snapshot_sha256": after_sha, "fact_digest": after_sha, "module_digests": {"smart_construction_core": after_sha}},
        "snapshot_artifact": {"path": "snapshot.json", "sha256": after_sha},
    }


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def assess(self, obs):
        return obsmod.assess(obs, repository=self.root)

    def test_valid_success_observation_is_admissible(self):
        result = self.assess(_base_obs(self.root))
        self.assertTrue(result["structurally_valid"], result["errors"])
        self.assertTrue(result["baseline_admissible"])
        self.assertTrue(result["artifact_persisted"])

    def test_partial_result_is_not_a_baseline(self):
        result = self.assess(_base_obs(self.root, result="partial"))
        self.assertTrue(result["structurally_valid"])
        self.assertFalse(result["baseline_admissible"])
        self.assertIn("result=partial", result["admission_reason"])

    def test_failed_result_is_not_a_baseline(self):
        result = self.assess(_base_obs(self.root, result="failed"))
        self.assertFalse(result["baseline_admissible"])

    def test_registry_not_ready_blocks_baseline(self):
        result = self.assess(_base_obs(self.root, ready=False))
        self.assertFalse(result["baseline_admissible"])

    def test_db_mismatch_blocks_baseline(self):
        result = self.assess(_base_obs(self.root, db_matches=False))
        self.assertFalse(result["baseline_admissible"])

    def test_missing_observer_field_is_structural_error(self):
        obs = _base_obs(self.root)
        obs["observer"].pop("odoo_version")
        result = self.assess(obs)
        self.assertFalse(result["structurally_valid"])

    def test_artifact_digest_mismatch_fails_verification(self):
        obs = _base_obs(self.root)
        obs["snapshot_artifact"]["sha256"] = "b" * 64
        result = self.assess(obs)
        self.assertFalse(result["artifact_persisted"])
        self.assertIn("digest mismatch", result["artifact_reason"])

    def test_missing_artifact_is_not_persisted(self):
        obs = _base_obs(self.root)
        (self.root / "snapshot.json").unlink()
        result = self.assess(obs)
        self.assertFalse(result["artifact_persisted"])


if __name__ == "__main__":
    unittest.main()
