from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (ROOT / "scripts/dev/frontend_acceptance_baseline_rebuild.sh").read_text(encoding="utf-8")
RUNTIME = (ROOT / "scripts/dev/frontend_acceptance_runtime.sh").read_text(encoding="utf-8")
MAKE = (ROOT / "make/dev.mk").read_text(encoding="utf-8")


class FrontendAcceptanceBaselineRebuildContractTest(unittest.TestCase):
    def test_scope_is_exact_and_does_not_accept_overrides(self) -> None:
        for marker in (
            'readonly EXPECTED_PROJECT="sc-fe-r2-p1-01"',
            'readonly EXPECTED_DATABASE="sc_frontend_acceptance"',
            'readonly EXPECTED_FILTER=\'^sc_frontend_acceptance$\'',
            'readonly EXPECTED_DB_VOLUME="sc_fe_r2_p1_01_db"',
            'readonly EXPECTED_REDIS_VOLUME="sc_fe_r2_p1_01_redis"',
            'readonly EXPECTED_ODOO_VOLUME="sc_fe_r2_p1_01_odoo"',
        ):
            self.assertIn(marker, SCRIPT)

    def test_dry_run_exits_before_backup_or_volume_removal(self) -> None:
        dry_run = SCRIPT.index('if [[ "${APPLY:-0}" != "1" ]]')
        backup = SCRIPT.index('docker exec "$db_cid" pg_dump')
        remove = SCRIPT.index('docker volume rm "$volume"', backup)
        self.assertLess(dry_run, backup)
        self.assertLess(backup, remove)

    def test_apply_requires_head_confirmation_clean_tree_and_stopped_carriers(self) -> None:
        for marker in (
            'EXPECTED_HEAD must equal current 40-character HEAD',
            'REBUILD_DISPOSABLE_FRONTEND_ACCEPTANCE',
            'worktree must be clean',
            'frontend and standalone backend carriers must be stopped first',
        ):
            self.assertIn(marker, SCRIPT)

    def test_recovery_bundle_covers_all_lifecycle_state(self) -> None:
        for marker in (
            'database.dump',
            'odoo-volume.tar.gz',
            'redis-volume.tar.gz',
            'sha256sum -c SHA256SUMS',
            'pg_restore --list',
            'restore_recovery_bundle "$bundle"',
        ):
            self.assertIn(marker, SCRIPT)

    def test_registered_make_entry_routes_through_governed_operation(self) -> None:
        self.assertIn('acceptance.runtime.baseline_recovery.audit:', MAKE)
        self.assertIn('acceptance.runtime.baseline_rebuild:', MAKE)
        self.assertIn('frontend_acceptance_operation_entry.sh baseline-rebuild', MAKE)
        self.assertIn('baseline-recovery-audit)', RUNTIME)
        self.assertIn('baseline-rebuild)', RUNTIME)


if __name__ == "__main__":
    unittest.main()
