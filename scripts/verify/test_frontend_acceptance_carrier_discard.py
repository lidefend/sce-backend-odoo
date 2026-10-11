from __future__ import annotations

import subprocess
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts/dev/frontend_acceptance_carrier_discard.sh"
SCRIPT = SCRIPT_PATH.read_text(encoding="utf-8")
# The single authoritative carrier identity is declared once in the shared
# common file and *consumed* by both lifecycle entries; the guards below must
# therefore assert the declaration in the common source and its consumption in
# each entry, instead of expecting a duplicated inline declaration.
COMMON_PATH = ROOT / "scripts/dev/frontend_acceptance_carrier_common.sh"
COMMON = COMMON_PATH.read_text(encoding="utf-8")
PROVISION_PATH = ROOT / "scripts/dev/frontend_acceptance_carrier_provision.sh"
PROVISION = PROVISION_PATH.read_text(encoding="utf-8")
ENTRY = (ROOT / "scripts/dev/frontend_acceptance_operation_entry.sh").read_text(encoding="utf-8")
MAKE = (ROOT / "make/dev.mk").read_text(encoding="utf-8")

PREAMBLE = f"""
    export ROOT_DIR={ROOT}
    source {SCRIPT_PATH}
    set +e
    export COMPOSE_PROJECT_NAME=sc-fe-r2-p1-01
    export DB_NAME=sc_frontend_acceptance
    export ODOO_DBFILTER='^sc_frontend_acceptance$'
    export DB_DATA=sc_fe_r2_p1_01_db
    export REDIS_DATA=sc_fe_r2_p1_01_redis
    export ODOO_DATA=sc_fe_r2_p1_01_odoo
    export SC_ENVIRONMENT=acceptance
    export SC_ALLOW_DEMO_DATA=1
"""


def run_with_identity(body: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", textwrap.dedent(PREAMBLE + body)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


class CarrierDiscardGuardTests(unittest.TestCase):
    def test_exact_identity_accepted(self) -> None:
        result = run_with_identity("( carrier_require_exact_identity ); echo rc=$?")
        self.assertIn("rc=0", result.stdout)

    def test_project_mismatch_denied(self) -> None:
        result = run_with_identity(
            textwrap.dedent(
                """
                export COMPOSE_PROJECT_NAME=sc-local-dev
                ( carrier_require_exact_identity ); echo rc=$?
                """
            )
        )
        self.assertIn("rc=2", result.stdout)
        self.assertIn("compose project mismatch", result.stdout)

    def test_database_mismatch_denied(self) -> None:
        result = run_with_identity(
            textwrap.dedent(
                """
                export DB_NAME=sc_demo
                ( carrier_require_exact_identity ); echo rc=$?
                """
            )
        )
        self.assertIn("rc=2", result.stdout)
        self.assertIn("database mismatch", result.stdout)

    def test_dbfilter_mismatch_denied(self) -> None:
        result = run_with_identity(
            textwrap.dedent(
                """
                export ODOO_DBFILTER='^sc_demo$'
                ( carrier_require_exact_identity ); echo rc=$?
                """
            )
        )
        self.assertIn("rc=2", result.stdout)
        self.assertIn("dbfilter mismatch", result.stdout)

    def test_volume_identity_mismatch_denied(self) -> None:
        for variable in ("DB_DATA", "REDIS_DATA", "ODOO_DATA"):
            with self.subTest(variable=variable):
                result = run_with_identity(
                    textwrap.dedent(
                        f"""
                        export {variable}=sc_fe_r2_p1_01_other
                        ( carrier_require_exact_identity ); echo rc=$?
                        """
                    )
                )
                self.assertIn("rc=2", result.stdout)
                self.assertIn("volume mismatch", result.stdout)

    def test_environment_scope_mismatch_denied(self) -> None:
        result = run_with_identity(
            textwrap.dedent(
                """
                export SC_ENVIRONMENT=production
                ( carrier_require_exact_identity ); echo rc=$?
                """
            )
        )
        self.assertIn("rc=2", result.stdout)

    def test_missing_confirmation_denied(self) -> None:
        result = run_with_identity(
            textwrap.dedent(
                """
                unset CONFIRM_ACCEPTANCE_CARRIER_DISCARD
                ( carrier_require_confirmation CONFIRM_ACCEPTANCE_CARRIER_DISCARD "DISCARD_MANAGED_ACCEPTANCE_CARRIER" ); echo rc=$?
                """
            )
        )
        self.assertIn("rc=2", result.stdout)
        self.assertIn("DISCARD_MANAGED_ACCEPTANCE_CARRIER", result.stdout)

    def test_wrong_confirmation_denied(self) -> None:
        result = run_with_identity(
            textwrap.dedent(
                """
                export CONFIRM_ACCEPTANCE_CARRIER_DISCARD=discard
                ( carrier_require_confirmation CONFIRM_ACCEPTANCE_CARRIER_DISCARD "DISCARD_MANAGED_ACCEPTANCE_CARRIER" ); echo rc=$?
                """
            )
        )
        self.assertIn("rc=2", result.stdout)

    def test_confirmation_accepted(self) -> None:
        result = run_with_identity(
            textwrap.dedent(
                """
                export CONFIRM_ACCEPTANCE_CARRIER_DISCARD=DISCARD_MANAGED_ACCEPTANCE_CARRIER
                ( carrier_require_confirmation CONFIRM_ACCEPTANCE_CARRIER_DISCARD "DISCARD_MANAGED_ACCEPTANCE_CARRIER" ); echo rc=$?
                """
            )
        )
        self.assertIn("rc=0", result.stdout)


class CarrierDiscardMounterTests(unittest.TestCase):
    def test_declared_service_consumers_allowed(self) -> None:
        result = run_with_identity(
            textwrap.dedent(
                """
                docker() {
                  case "$1" in
                    volume) return 0 ;;
                    ps) echo cid1 ;;
                    inspect)
                      case "$*" in
                        *com.docker.compose.project*) echo sc-fe-r2-p1-01 ;;
                        *com.docker.compose.service*) echo db ;;
                        *com.docker.compose.oneoff*) echo False ;;
                        *) return 0 ;;
                      esac
                      ;;
                  esac
                }
                ( require_no_foreign_mounter sc_fe_r2_p1_01_db ); echo rc=$?
                """
            )
        )
        self.assertIn("rc=0", result.stdout)

    def test_foreign_project_mounter_denied(self) -> None:
        result = run_with_identity(
            textwrap.dedent(
                """
                docker() {
                  case "$1" in
                    volume) return 0 ;;
                    ps) echo cid1 ;;
                    inspect) echo sc-backend-odoo-acceptance ;;
                  esac
                }
                ( require_no_foreign_mounter sc_fe_r2_p1_01_odoo ); echo rc=$?
                """
            )
        )
        self.assertIn("rc=2", result.stdout)
        self.assertIn("foreign mounter", result.stdout)

    def test_undeclared_service_mounter_denied(self) -> None:
        result = run_with_identity(
            textwrap.dedent(
                """
                docker() {
                  case "$1" in
                    volume) return 0 ;;
                    ps) echo cid1 ;;
                    inspect)
                      case "$*" in
                        *com.docker.compose.project*) echo sc-fe-r2-p1-01 ;;
                        *com.docker.compose.service*) echo sidecar ;;
                        *com.docker.compose.oneoff*) echo False ;;
                        *) return 0 ;;
                      esac
                      ;;
                  esac
                }
                ( require_no_foreign_mounter sc_fe_r2_p1_01_odoo ); echo rc=$?
                """
            )
        )
        self.assertIn("rc=2", result.stdout)
        self.assertIn("undeclared service", result.stdout)

    def test_undeclared_oneoff_mounter_denied(self) -> None:
        result = run_with_identity(
            textwrap.dedent(
                """
                docker() {
                  case "$1" in
                    volume) return 0 ;;
                    ps) echo cid1 ;;
                    inspect)
                      case "$*" in
                        *com.docker.compose.project*) echo sc-fe-r2-p1-01 ;;
                        *com.docker.compose.service*) echo odoo ;;
                        *com.docker.compose.oneoff*) echo True ;;
                        *) return 0 ;;
                      esac
                      ;;
                  esac
                }
                ( require_no_foreign_mounter sc_fe_r2_p1_01_odoo ); echo rc=$?
                """
            )
        )
        self.assertIn("rc=2", result.stdout)
        self.assertIn("undeclared one-off mounter", result.stdout)

    def test_absent_volume_is_not_a_mounter(self) -> None:
        result = run_with_identity(
            textwrap.dedent(
                """
                docker() { return 1; }
                ( require_no_foreign_mounter sc_fe_r2_p1_01_odoo ); echo rc=$?
                """
            )
        )
        self.assertIn("rc=0", result.stdout)

    def test_carrier_absent_requires_volumes_and_containers_gone(self) -> None:
        absent = run_with_identity(
            textwrap.dedent(
                """
                docker() { return 1; }
                ( carrier_absent ); echo rc=$?
                """
            )
        )
        self.assertIn("rc=0", absent.stdout)
        present = run_with_identity(
            textwrap.dedent(
                """
                docker() {
                  case "$1" in
                    volume) return 0 ;;
                    ps) echo cid1 ;;
                  esac
                }
                ( carrier_absent ); echo rc=$?
                """
            )
        )
        self.assertIn("rc=1", present.stdout)


class CarrierDiscardSourceGuards(unittest.TestCase):
    def test_common_declares_exact_managed_identity(self) -> None:
        for marker in (
            'EXPECTED_PROJECT="sc-fe-r2-p1-01"',
            'EXPECTED_DATABASE="sc_frontend_acceptance"',
            "EXPECTED_FILTER='^sc_frontend_acceptance$'",
            'EXPECTED_DB_VOLUME="sc_fe_r2_p1_01_db"',
            'EXPECTED_REDIS_VOLUME="sc_fe_r2_p1_01_redis"',
            'EXPECTED_ODOO_VOLUME="sc_fe_r2_p1_01_odoo"',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, COMMON)

    def test_entry_consumes_the_shared_identity(self) -> None:
        self.assertIn(
            'source "$ROOT_DIR/scripts/dev/frontend_acceptance_carrier_common.sh"', SCRIPT
        )
        self.assertIn('CONFIRM_PHRASE="DISCARD_MANAGED_ACCEPTANCE_CARRIER"', SCRIPT)
        # The identity must not be re-declared inline, which is exactly the
        # drift the shared file exists to prevent.
        self.assertNotIn('EXPECTED_PROJECT="sc-fe-r2-p1-01"', SCRIPT)

    def test_script_uses_governed_compose_wrapper_only(self) -> None:
        self.assertIn("compose_dev down --remove-orphans", SCRIPT)
        self.assertNotIn("docker compose", SCRIPT)
        self.assertNotIn("docker-compose", SCRIPT)

    def test_script_reads_back_absence_after_removal(self) -> None:
        self.assertIn('fail "volume remains', SCRIPT)
        self.assertIn("containers remain for project=", SCRIPT)

    def test_script_refuses_while_carriers_run(self) -> None:
        # The stop precondition is owned by the shared carrier guard and is
        # invoked by the entry before any removal.
        self.assertIn("run make frontend.acceptance.down first", COMMON)
        self.assertIn("run make backend.acceptance.down first", COMMON)
        self.assertIn("carrier_carriers_stopped", SCRIPT)

    def test_script_is_local_only_p4_entry(self) -> None:
        self.assertIn("P4 environment entry", SCRIPT)
        self.assertIn("never be invoked from CI", SCRIPT)

    def test_entry_denies_carrier_discard_in_ci(self) -> None:
        self.assertIn("carrier-discard|carrier-provision)", ENTRY)
        self.assertIn(
            "managed acceptance carrier $operation is a local P4 environment entry", ENTRY
        )

    def test_make_target_is_guarded_and_requires_confirmation(self) -> None:
        self.assertIn("acceptance.runtime.carrier.discard: guard.prod.forbid", MAKE)
        self.assertIn(
            'CONFIRM_ACCEPTANCE_CARRIER_DISCARD="$${CONFIRM_ACCEPTANCE_CARRIER_DISCARD:-}"',
            MAKE,
        )
        self.assertIn("frontend_acceptance_carrier_discard.sh", MAKE)

    def test_make_unit_target_covers_the_new_entry(self) -> None:
        self.assertIn("scripts.verify.test_frontend_acceptance_carrier_discard", MAKE)


class CarrierProvisionSourceGuards(unittest.TestCase):
    def test_entry_consumes_the_shared_identity_and_requires_confirmation(self) -> None:
        self.assertIn(
            'source "$ROOT_DIR/scripts/dev/frontend_acceptance_carrier_common.sh"', PROVISION
        )
        self.assertIn('CONFIRM_PHRASE="PROVISION_MANAGED_ACCEPTANCE_CARRIER"', PROVISION)
        self.assertIn("carrier_require_exact_identity", PROVISION)
        self.assertIn(
            "carrier_require_confirmation CONFIRM_ACCEPTANCE_CARRIER_PROVISION", PROVISION
        )
        self.assertNotIn('EXPECTED_PROJECT="sc-fe-r2-p1-01"', PROVISION)

    def test_entry_uses_governed_compose_wrapper_and_delegates_db_bootstrap(self) -> None:
        self.assertIn("compose_dev up -d --wait db redis", PROVISION)
        self.assertIn("compose_dev up -d --wait odoo", PROVISION)
        self.assertNotIn("docker compose", PROVISION)
        self.assertNotIn("docker-compose", PROVISION)
        # Database creation, module install and baseline upgrade stay owned by
        # the existing governed provisioning script rather than being re-derived.
        self.assertIn("scripts/test/frontend_acceptance_db_ensure.sh", PROVISION)

    def test_entry_reads_back_operational_state(self) -> None:
        self.assertIn("carrier_all_containers_present", PROVISION)
        self.assertIn('carrier_fail "managed database is absent"', PROVISION)

    def test_entry_is_local_only_p4_and_guarded_in_ci(self) -> None:
        self.assertIn("P4 environment entry", PROVISION)
        self.assertIn("never be invoked from CI", PROVISION)
        self.assertIn("acceptance.runtime.carrier.provision: guard.prod.forbid", MAKE)
        self.assertIn("frontend_acceptance_carrier_provision.sh", MAKE)


if __name__ == "__main__":
    unittest.main()
