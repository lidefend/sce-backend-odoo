from __future__ import annotations

import subprocess
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts/dev/frontend_acceptance_baseline_rebuild.sh"
SCRIPT = SCRIPT_PATH.read_text(encoding="utf-8")
RUNTIME = (ROOT / "scripts/dev/frontend_acceptance_runtime.sh").read_text(encoding="utf-8")
MAKE = (ROOT / "make/dev.mk").read_text(encoding="utf-8")


def run_library(body: str) -> subprocess.CompletedProcess[str]:
    prefix = f"""
        export ROOT_DIR={ROOT}
        export ENV=dev
        export ENV_FILE={ROOT / '.env.dev'}
        export COMPOSE_PROJECT_NAME=sc-fe-r2-p1-01
        export PROJECT=sc-fe-r2-p1-01
        export DB_NAME=sc_frontend_acceptance
        export ODOO_DBFILTER='^sc_frontend_acceptance$'
        export DB_DATA=sc_fe_r2_p1_01_db
        export REDIS_DATA=sc_fe_r2_p1_01_redis
        export ODOO_DATA=sc_fe_r2_p1_01_odoo
        export DB_USER=odoo
        export SC_ENVIRONMENT=acceptance
        export SC_ALLOW_DEMO_DATA=1
        source {SCRIPT_PATH}
        set +e
    """
    return subprocess.run(
        ["bash", "-c", textwrap.dedent(prefix + body)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def run_volume_scope(
    rows: dict[str, tuple[str, str, str, str]],
    volume: str,
    service: str,
) -> subprocess.CompletedProcess[str]:
    table = "\n".join(
        f'STUB_ROWS[{cid}]="{project}|{svc}|{oneoff}|{name}"'
        for cid, (project, svc, oneoff, name) in rows.items()
    )
    ids = " ".join(rows)
    return run_library(f"""
        declare -A STUB_ROWS
        {table}
        STUB_IDS="{ids}"
        docker() {{
          if [[ "$1" == "ps" ]]; then
            [[ -n "$STUB_IDS" ]] && printf '%s\\n' $STUB_IDS
            return 0
          fi
          if [[ "$1" == "inspect" ]]; then
            local fmt="$4" row="${{STUB_ROWS[$2]}}"
            IFS='|' read -r project service oneoff name <<<"$row"
            case "$fmt" in
              *'com.docker.compose.project'*) echo "$project" ;;
              *'com.docker.compose.service'*) echo "$service" ;;
              *'com.docker.compose.oneoff'*) echo "$oneoff" ;;
              *'.Name'*) echo "/$name" ;;
              *) echo "" ;;
            esac
            return 0
          fi
          return 0
        }}
        require_volume_mount_scope "{volume}" "{service}"
    """)


class FrontendAcceptanceBaselineRebuildContractTest(unittest.TestCase):
    def test_scope_is_exact_and_does_not_accept_overrides(self) -> None:
        for marker in (
            'readonly EXPECTED_PROJECT="sc-fe-r2-p1-01"',
            'readonly EXPECTED_DATABASE="sc_frontend_acceptance"',
            'readonly EXPECTED_FILTER=\'^sc_frontend_acceptance$\'',
            'readonly EXPECTED_DB_VOLUME="sc_fe_r2_p1_01_db"',
            'readonly EXPECTED_REDIS_VOLUME="sc_fe_r2_p1_01_redis"',
            'readonly EXPECTED_ODOO_VOLUME="sc_fe_r2_p1_01_odoo"',
            'readonly EXPECTED_DATABASE_IMAGE="postgres:15"',
        ):
            self.assertIn(marker, SCRIPT)

    def test_dry_run_performs_all_non_destructive_prechecks(self) -> None:
        checks = SCRIPT.index("pre_execution_checks")
        dry_run = SCRIPT.index('if [[ "${APPLY:-0}" != "1" ]]', checks)
        confirmation = SCRIPT.index("REBUILD_DISPOSABLE_FRONTEND_ACCEPTANCE", dry_run)
        self.assertLess(checks, dry_run)
        self.assertLess(dry_run, confirmation)
        for marker in (
            "worktree must be clean",
            "require_carrier_scope",
            "require_database_volume_scope",
            "require_recovery_tools",
            "EXPECTED_DATABASES",
            "DRY_RUN EXECUTABLE PASS",
        ):
            self.assertIn(marker, SCRIPT)

    def test_database_and_volume_scope_are_proven_before_delete(self) -> None:
        self.assertIn("PostgreSQL volume database scope mismatch", SCRIPT)
        self.assertIn('docker ps -aq --filter "volume=$volume"', SCRIPT)
        self.assertIn("expected one mount consumer", SCRIPT)
        self.assertIn("db-volume.tar.gz", SCRIPT)
        prechecks = SCRIPT.index("pre_execution_checks")
        removal = SCRIPT.index('remove_volume_exact "$DB_DATA"', prechecks)
        self.assertLess(prechecks, removal)

    def test_unexpected_database_blocks_scope_precheck(self) -> None:
        result = run_library("""
            user_database_csv() { echo sc_frontend_acceptance,sc_odoo; }
            EXPECTED_DATABASES=sc_frontend_acceptance
            require_database_volume_scope
        """)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "database scope mismatch expected=sc_frontend_acceptance actual=sc_frontend_acceptance,sc_odoo",
            result.stdout,
        )

    def test_complete_database_set_passes_scope_precheck(self) -> None:
        result = run_library("""
            user_database_csv() { echo sc_frontend_acceptance,sc_odoo; }
            EXPECTED_DATABASES=sc_frontend_acceptance,sc_odoo
            require_database_volume_scope
        """)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("user_database_scope=sc_frontend_acceptance,sc_odoo", result.stdout)

    def test_apply_requires_head_confirmation_clean_tree_and_stopped_external_carriers(self) -> None:
        for marker in (
            "EXPECTED_HEAD must equal current 40-character HEAD",
            "REBUILD_DISPOSABLE_FRONTEND_ACCEPTANCE",
            "worktree must be clean",
            "managed frontend carrier must be stopped",
            "standalone acceptance backend carrier must be removed",
        ):
            self.assertIn(marker, SCRIPT)

    def test_complete_manifest_is_written_only_after_backup_validation(self) -> None:
        staging = SCRIPT.index("status=staging")
        dump_check = SCRIPT.index("pg_restore --list", staging)
        tar_check = SCRIPT.index("tar -tzf", dump_check)
        complete = SCRIPT.index("status=complete", tar_check)
        self.assertLess(staging, dump_check)
        self.assertLess(dump_check, tar_check)
        self.assertLess(tar_check, complete)
        self.assertIn("MANIFEST_SHA256", SCRIPT)

    def test_staging_bundle_is_never_accepted_as_complete(self) -> None:
        result = run_library("""
            bundle=$(mktemp -d)
            for artifact in database.dump db-volume.tar.gz odoo-volume.tar.gz redis-volume.tar.gz SHA256SUMS MANIFEST_SHA256; do
              printf x > "$bundle/$artifact"
            done
            printf 'status=staging\\n' > "$bundle/manifest.txt"
            verify_bundle "$bundle"
        """)
        self.assertNotEqual(result.returncode, 0)

    def test_recovery_checks_database_attachments_filestore_and_sessions(self) -> None:
        for marker in (
            "source_module_version",
            "expected_attachment_count",
            "expected_filestore_file_count",
            "expected_redis_key_count",
            "verify_restored_state",
            "RECOVERED verified=true",
        ):
            self.assertIn(marker, SCRIPT)

    def test_writer_stop_failure_blocks_backup(self) -> None:
        result = run_library("""
            compose_dev() { return 1; }
            freeze_writers
        """)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unable to stop managed writers", result.stdout)
        self.assertNotIn("writers_stopped=true", result.stdout)

    def test_active_database_client_blocks_cold_backup(self) -> None:
        result = run_library("""
            database_scalar() { echo 1; }
            require_no_database_clients
        """)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("still have active clients count=1", result.stdout)

    def test_recovery_compose_down_failure_never_reports_recovered(self) -> None:
        result = run_library("""
            bundle=$(mktemp -d)
            : > "$bundle/database.dump"
            verify_bundle() { return 0; }
            compose_dev() { return 1; }
            restore_recovery_bundle "$bundle"
        """)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RECOVERY_FAILED compose_down", result.stdout)
        self.assertNotIn("RECOVERED verified=true", result.stdout)

    def test_recovery_unpack_failure_never_reports_recovered(self) -> None:
        result = run_library("""
            bundle=$(mktemp -d)
            : > "$bundle/database.dump"
            verify_bundle() { return 0; }
            compose_dev() { return 0; }
            remove_volume_exact() { return 0; }
            restore_volume() { return 1; }
            restore_recovery_bundle "$bundle"
        """)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RECOVERY_FAILED session_unpack", result.stdout)
        self.assertNotIn("RECOVERED verified=true", result.stdout)

    def test_recovery_volume_delete_failure_never_reports_recovered(self) -> None:
        result = run_library("""
            verify_bundle() { return 0; }
            compose_dev() { return 0; }
            remove_volume_exact() { return 1; }
            restore_recovery_bundle /tmp/fake-bundle
        """)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RECOVERY_FAILED database_volume_remove", result.stdout)
        self.assertNotIn("RECOVERED verified=true", result.stdout)

    def test_recovery_volume_carrier_create_failure_never_reports_recovered(self) -> None:
        result = run_library("""
            verify_bundle() { return 0; }
            remove_volume_exact() { return 0; }
            compose_dev() {
              if [[ "${1:-}" == "down" ]]; then return 0; fi
              return 1
            }
            restore_recovery_bundle /tmp/fake-bundle
        """)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RECOVERY_FAILED volume_carrier_create", result.stdout)
        self.assertNotIn("RECOVERED verified=true", result.stdout)

    def test_recovery_database_restore_failure_never_reports_recovered(self) -> None:
        result = run_library("""
            verify_bundle() { return 0; }
            remove_volume_exact() { return 0; }
            restore_volume() {
              if [[ "$1" == "$DB_DATA" ]]; then return 1; fi
              return 0
            }
            compose_dev() { return 0; }
            restore_recovery_bundle /tmp/fake-bundle
        """)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RECOVERY_FAILED database_unpack", result.stdout)
        self.assertNotIn("RECOVERED verified=true", result.stdout)

    def test_recovery_post_verification_failure_never_reports_recovered(self) -> None:
        result = run_library("""
            bundle=$(mktemp -d)
            : > "$bundle/database.dump"
            verify_bundle() { return 0; }
            remove_volume_exact() { return 0; }
            restore_volume() { return 0; }
            verify_restored_state() { return 1; }
            compose_dev() {
              if [[ "${1:-} ${2:-} ${3:-}" == "ps -q db" ]]; then echo fake-db; fi
              return 0
            }
            docker() { return 0; }
            restore_recovery_bundle "$bundle"
        """)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RECOVERY_FAILED post_restore_verification", result.stdout)
        self.assertNotIn("RECOVERED verified=true", result.stdout)

    def test_recovery_reports_success_only_after_verification(self) -> None:
        result = run_library("""
            verify_bundle() { return 0; }
            remove_volume_exact() { return 0; }
            restore_volume() { return 0; }
            verify_restored_state() { echo verified-state; return 0; }
            compose_dev() { return 0; }
            restore_recovery_bundle /tmp/fake-bundle
        """)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertLess(result.stdout.index("verified-state"), result.stdout.index("RECOVERED verified=true"))

    def test_automatic_recovery_scope_stops_before_product_install_chain(self) -> None:
        self.assertIn(
            "automatic_recovery_scope=volume_removal_and_empty_infrastructure_recreation_only",
            SCRIPT,
        )
        self.assertIn("post_action=make_db_ensure_then_fixture_snapshot_and_release_gate", SCRIPT)

    def test_declared_odoo_consumers_are_accepted_together(self) -> None:
        result = run_volume_scope(
            {
                "cid-carrier": ("sc-fe-r2-p1-01", "odoo", "False", "sc-fe-r2-p1-01-odoo-1"),
                "cid-backend": ("sc-fe-r2-p1-01", "odoo", "True", "sc-backend-odoo-acceptance"),
            },
            "sc_fe_r2_p1_01_odoo",
            "odoo",
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("declared_consumers=2", result.stdout)

    def test_undeclared_one_off_odoo_consumer_blocks(self) -> None:
        result = run_volume_scope(
            {
                "cid-carrier": ("sc-fe-r2-p1-01", "odoo", "False", "sc-fe-r2-p1-01-odoo-1"),
                "cid-backend": ("sc-fe-r2-p1-01", "odoo", "True", "sc-backend-odoo-acceptance"),
                "cid-rogue": ("sc-fe-r2-p1-01", "odoo", "True", "sc-rogue-odoo-9"),
            },
            "sc_fe_r2_p1_01_odoo",
            "odoo",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("undeclared one-off mount consumer name=sc-rogue-odoo-9", result.stdout)

    def test_foreign_odoo_mount_owner_blocks(self) -> None:
        result = run_volume_scope(
            {
                "cid-foreign": ("sc-some-other-project", "odoo", "False", "foreign-odoo-1"),
            },
            "sc_fe_r2_p1_01_odoo",
            "odoo",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "mount owner mismatch project=sc-some-other-project service=odoo", result.stdout
        )

    def test_missing_compose_carrier_blocks(self) -> None:
        result = run_volume_scope(
            {
                "cid-backend": ("sc-fe-r2-p1-01", "odoo", "True", "sc-backend-odoo-acceptance"),
            },
            "sc_fe_r2_p1_01_odoo",
            "odoo",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected one compose carrier service=odoo actual=0", result.stdout)

    def test_empty_odoo_mount_scope_blocks(self) -> None:
        result = run_volume_scope({}, "sc_fe_r2_p1_01_odoo", "odoo")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("has no mount consumer service=odoo", result.stdout)

    def test_database_volume_still_requires_exactly_one_consumer(self) -> None:
        result = run_volume_scope(
            {
                "cid-db": ("sc-fe-r2-p1-01", "db", "", "sc-fe-r2-p1-01-db-1"),
                "cid-db2": ("sc-fe-r2-p1-01", "db", "", "sc-fe-r2-p1-01-db-2"),
            },
            "sc_fe_r2_p1_01_db",
            "db",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected one mount consumer service=db actual=2", result.stdout)

    def test_registered_make_entry_routes_through_governed_operation(self) -> None:
        self.assertIn("acceptance.runtime.baseline_recovery.audit:", MAKE)
        self.assertIn("acceptance.runtime.baseline_rebuild:", MAKE)
        self.assertIn("frontend_acceptance_operation_entry.sh baseline-rebuild", MAKE)
        self.assertIn("baseline-recovery-audit)", RUNTIME)
        self.assertIn("baseline-rebuild)", RUNTIME)


if __name__ == "__main__":
    unittest.main()
