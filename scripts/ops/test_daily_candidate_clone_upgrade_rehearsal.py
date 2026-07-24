#!/usr/bin/env python3
"""Contract tests for the daily-candidate clone upgrade rehearsal gate."""

from __future__ import annotations

import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import daily_candidate_clone_upgrade_rehearsal as rehearsal  # noqa: E402


SHA = "a" * 40
DIGEST = "sha256:" + "b" * 64


def candidate(contract: dict) -> dict:
    return {
        "candidate_name": "RC6",
        "source_sha": SHA,
        "approval_status": "FROZEN",
        "ci_status": "PASS",
        "ci_run_url": "https://github.example/actions/1",
        "image_ref": f"ghcr.io/lidefend/sce-product@{DIGEST}",
        "image_revision_label": SHA,
        "image_pull_policy": "never",
        "image_locally_available": True,
    }


def isolation() -> dict:
    prefix = "sc-rc6-rehearsal-test"
    return {
        "project": prefix + "-project",
        "database_container": prefix + "-db",
        "odoo_container": prefix + "-odoo",
        "network": prefix + "-network",
        "volumes": [prefix + "-db-volume", prefix + "-fs-volume"],
        "network_internal": True,
        "public_egress_allowed": False,
        "cron_enabled": False,
        "external_write_integrations": {
            "email": False,
            "sms": False,
            "webhook": False,
            "payment": False,
            "object_storage": False,
        },
        "production_secrets_mounted": False,
        "source_database_connected": False,
        "source_filestore_mount_mode": "none",
        "mounts": [{"source": "/tmp/restored-filestore", "target": "/var/lib/odoo"}],
        "upgrade_commands": ["odoo --stop-after-init -d clone -u smart_core"],
    }


def plan() -> dict:
    return {
        "old_modules": {"smart_core": "17.0.1.0"},
        "target_modules": {"smart_core": "17.0.2.0"},
        "upgrade_commands": ["odoo --stop-after-init -d clone -u smart_core"],
        "operations": [
            {
                "id": "smart_core/17.0.2.0/post",
                "declared": True,
                "destructive": False,
                "irreversible": False,
            }
        ],
        "model_mappings": [],
        "demo_or_fixture_write": False,
        "unknown_origin_delete": False,
        "backward_compatible": True,
        "plan_versioned": True,
    }


class RehearsalContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = rehearsal.load_contract()

    def test_contract_is_bound_to_fixed_source(self) -> None:
        self.assertEqual(self.contract["source_database_name"], "sc_demo")
        self.assertEqual(
            self.contract["source_database_uuid"],
            "c838b4b6-4cd6-11f1-9590-82245e4e7b62",
        )

    def test_unfrozen_candidate_is_rejected(self) -> None:
        payload = candidate(self.contract)
        payload["approval_status"] = "PENDING"
        with self.assertRaises(rehearsal.CandidateNotFrozen):
            rehearsal.validate_candidate_payload(
                self.contract,
                payload,
                repository_head=SHA,
                worktree_clean=True,
                ancestor_commits=set(
                    self.contract["candidate"]["required_ancestor_commits"]
                ),
            )

    def test_short_candidate_sha_is_rejected(self) -> None:
        payload = candidate(self.contract)
        payload["source_sha"] = "abc123"
        with self.assertRaises(rehearsal.CandidateNotFrozen):
            rehearsal.validate_candidate_payload(
                self.contract,
                payload,
                repository_head="abc123",
                worktree_clean=True,
                ancestor_commits=set(),
            )

    def test_mutable_image_tag_is_rejected(self) -> None:
        payload = candidate(self.contract)
        payload["image_ref"] = "ghcr.io/lidefend/sce-product:rc6"
        with self.assertRaises(rehearsal.CandidateNotFrozen):
            rehearsal.validate_candidate_payload(
                self.contract,
                payload,
                repository_head=SHA,
                worktree_clean=True,
                ancestor_commits=set(
                    self.contract["candidate"]["required_ancestor_commits"]
                ),
            )

    def test_image_revision_must_match_sha(self) -> None:
        payload = candidate(self.contract)
        payload["image_revision_label"] = "c" * 40
        with self.assertRaises(rehearsal.CandidateNotFrozen):
            rehearsal.validate_candidate_payload(
                self.contract,
                payload,
                repository_head=SHA,
                worktree_clean=True,
                ancestor_commits=set(
                    self.contract["candidate"]["required_ancestor_commits"]
                ),
            )

    def test_dirty_checkout_is_rejected(self) -> None:
        with self.assertRaises(rehearsal.CandidateNotFrozen):
            rehearsal.validate_candidate_payload(
                self.contract,
                candidate(self.contract),
                repository_head=SHA,
                worktree_clean=False,
                ancestor_commits=set(
                    self.contract["candidate"]["required_ancestor_commits"]
                ),
            )

    def test_required_merge_ancestry_is_enforced(self) -> None:
        with self.assertRaises(rehearsal.CandidateNotFrozen):
            rehearsal.validate_candidate_payload(
                self.contract,
                candidate(self.contract),
                repository_head=SHA,
                worktree_clean=True,
                ancestor_commits=set(),
            )

    def test_complete_candidate_passes(self) -> None:
        result = rehearsal.validate_candidate_payload(
            self.contract,
            candidate(self.contract),
            repository_head=SHA,
            worktree_clean=True,
            ancestor_commits=set(self.contract["candidate"]["required_ancestor_commits"]),
        )
        self.assertTrue(result["candidate_frozen"])
        self.assertEqual(result["rc6_image_digest"], DIGEST)

    def test_local_image_revision_is_verified(self) -> None:
        rows = [
            {
                "Id": "sha256:" + "c" * 64,
                "Config": {"Labels": {"org.opencontainers.image.revision": SHA}},
            }
        ]
        result = rehearsal.validate_image_inspect(
            f"ghcr.io/lidefend/sce-product@{DIGEST}", SHA, rows
        )
        self.assertTrue(result["local_image_revision_traceability_pass"])
        rows[0]["Config"]["Labels"]["org.opencontainers.image.revision"] = "d" * 40
        with self.assertRaises(rehearsal.CandidateNotFrozen):
            rehearsal.validate_image_inspect(
                f"ghcr.io/lidefend/sce-product@{DIGEST}", SHA, rows
            )

    def test_source_uuid_mismatch_is_rejected(self) -> None:
        payload = {
            "source_database_name": "sc_demo",
            "source_database_uuid": "wrong",
            "continuity_backup_set_id": self.contract["continuity_backup_set_id"],
            "sentinel_set_id": self.contract["sentinel_set_id"],
            "sentinel_evidence_sha256": self.contract["sentinel_evidence_sha256"],
            "source_application_revision_prefix": "6095e201",
            "continuity_integrity_pass": True,
            "sentinel_integrity_pass": True,
            "source_runtime_healthy": True,
        }
        with self.assertRaises(rehearsal.RehearsalError):
            rehearsal.validate_source_artifacts(self.contract, payload)

    def test_sentinel_digest_mismatch_is_rejected(self) -> None:
        payload = {
            "source_database_name": "sc_demo",
            "source_database_uuid": self.contract["source_database_uuid"],
            "continuity_backup_set_id": self.contract["continuity_backup_set_id"],
            "sentinel_set_id": self.contract["sentinel_set_id"],
            "sentinel_evidence_sha256": "0" * 64,
            "source_application_revision_prefix": "6095e201",
            "continuity_integrity_pass": True,
            "sentinel_integrity_pass": True,
            "source_runtime_healthy": True,
        }
        with self.assertRaises(rehearsal.RehearsalError):
            rehearsal.validate_source_artifacts(self.contract, payload)

    def test_direct_source_database_connection_is_rejected(self) -> None:
        payload = isolation()
        payload["source_database_connected"] = True
        with self.assertRaises(rehearsal.RehearsalError):
            rehearsal.validate_isolation(self.contract, payload)

    def test_source_filestore_mount_is_rejected(self) -> None:
        payload = isolation()
        payload["source_filestore_mount_mode"] = "rw"
        with self.assertRaises(rehearsal.RehearsalError):
            rehearsal.validate_isolation(self.contract, payload)

    def test_daily_volume_mount_is_rejected(self) -> None:
        payload = isolation()
        payload["mounts"] = [
            {
                "source": "/var/lib/docker/volumes/sc_dev_odoo_data/_data",
                "target": "/var/lib/odoo",
            }
        ]
        with self.assertRaises(rehearsal.RehearsalError):
            rehearsal.validate_isolation(self.contract, payload)

    def test_external_network_is_rejected(self) -> None:
        payload = isolation()
        payload["network_internal"] = False
        with self.assertRaises(rehearsal.RehearsalError):
            rehearsal.validate_isolation(self.contract, payload)

    def test_cron_or_external_writes_are_rejected(self) -> None:
        for key in ("cron_enabled", "email"):
            with self.subTest(key=key):
                payload = isolation()
                if key == "cron_enabled":
                    payload[key] = True
                else:
                    payload["external_write_integrations"][key] = True
                with self.assertRaises(rehearsal.RehearsalError):
                    rehearsal.validate_isolation(self.contract, payload)

    def test_demo_fixture_and_module_install_paths_are_rejected(self) -> None:
        for command in (
            "odoo -d clone -i smart_construction_bundle",
            "odoo --init=smart_core -d clone",
            "python fixture_reset.py",
        ):
            with self.subTest(command=command):
                payload = isolation()
                payload["upgrade_commands"] = [command]
                with self.assertRaises(rehearsal.RehearsalError):
                    rehearsal.validate_isolation(self.contract, payload)

    def test_isolated_clone_spec_passes(self) -> None:
        result = rehearsal.validate_isolation(self.contract, isolation())
        self.assertTrue(result["clone_isolation_contract_pass"])

    def test_undeclared_destructive_migration_is_rejected(self) -> None:
        payload = plan()
        payload["operations"][0].update(destructive=True, declared=False)
        with self.assertRaises(rehearsal.RehearsalError):
            rehearsal.build_migration_plan(self.contract, payload)

    def test_unknown_origin_delete_is_rejected(self) -> None:
        payload = plan()
        payload["unknown_origin_delete"] = True
        with self.assertRaises(rehearsal.RehearsalError):
            rehearsal.build_migration_plan(self.contract, payload)

    def test_migration_plan_is_deterministic(self) -> None:
        payload = plan()
        payload["old_modules"]["smart_construction_core"] = "17.0.1.0"
        payload["target_modules"]["smart_construction_core"] = "17.0.3.0"
        first = rehearsal.build_migration_plan(self.contract, payload)
        second = rehearsal.build_migration_plan(self.contract, payload)
        self.assertEqual(first, second)
        self.assertEqual(
            [row["module"] for row in first["upgraded_modules"]],
            ["smart_construction_core", "smart_core"],
        )

    def test_rollback_mode_tracks_compatibility(self) -> None:
        compatible = rehearsal.build_migration_plan(self.contract, plan())
        self.assertEqual(compatible["rollback_mode"], "APPLICATION_IMAGE_ROLLBACK")
        payload = plan()
        payload["backward_compatible"] = False
        incompatible = rehearsal.build_migration_plan(self.contract, payload)
        self.assertEqual(
            incompatible["rollback_mode"], "PAIRED_DATABASE_FILESTORE_RESTORE"
        )

    def test_sentinel_regressions_fail_closed(self) -> None:
        baseline = {
            "comparison_pass": True,
            "fixed_sample_preservation_pass": True,
            "core_relationship_preservation_pass": True,
            "attachment_preservation_pass": True,
            "orphan_regression_pass": True,
            "unknown_origin_preservation_pass": True,
        }
        for key in tuple(baseline):
            with self.subTest(key=key):
                payload = dict(baseline)
                payload[key] = False
                with self.assertRaises(rehearsal.RehearsalError):
                    rehearsal.validate_sentinel_preservation(payload)

    def test_repeated_upgrade_requires_idempotency(self) -> None:
        payload = {
            "same_entrypoint": True,
            "exit_code_zero": True,
            "business_record_delta_zero": True,
            "duplicate_xmlid_count_zero": True,
            "permission_regression_absent": True,
            "post_repeat_sentinel_compare_pass": True,
        }
        result = rehearsal.validate_repeated_upgrade(payload)
        self.assertTrue(result["migration_idempotency_pass"])
        payload["business_record_delta_zero"] = False
        with self.assertRaises(rehearsal.RehearsalError):
            rehearsal.validate_repeated_upgrade(payload)

    def test_sensitive_values_are_rejected(self) -> None:
        for payload in (
            {"password": "hidden"},
            {"safe": "Bearer abc.def"},
            {"nested": [{"safe": "session_id=abc"}]},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(rehearsal.RehearsalError):
                    rehearsal.assert_no_sensitive_output(payload)

    def test_atomic_evidence_mode_is_0600(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "rehearsal.json"
            payload = {
                "rehearsal_set_id": "sc_demo-rc6-rehearsal-20260724T050000Z-deadbeef",
                "result": "PASS",
            }
            digest = rehearsal.atomic_write_evidence(output, payload)
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            self.assertEqual(json.loads(output.read_text()), payload)


if __name__ == "__main__":
    unittest.main()
