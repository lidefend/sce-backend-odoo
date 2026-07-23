#!/usr/bin/env python3
from __future__ import annotations

import atexit
import hashlib
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("production_db_contract", ROOT / "scripts/release/production_db_contract.py")
assert SPEC and SPEC.loader
contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract)

RELEASE_IDENTITY_TMP = tempfile.TemporaryDirectory()
atexit.register(RELEASE_IDENTITY_TMP.cleanup)
RELEASE_IDENTITY_ROOT = Path(RELEASE_IDENTITY_TMP.name)


def formal_env(db: str = "sc_migration_rehearsal") -> dict[str, str]:
    source_sha = "a" * 40
    image_digest = "sha256:" + "b" * 64
    manifest = RELEASE_IDENTITY_ROOT / f"{db}-product-release-manifest.json"
    checksum = RELEASE_IDENTITY_ROOT / f"{db}-product-release-manifest.sha256"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "product_release_manifest.v3",
                "repository": "lidefend/sce-backend-odoo",
                "branch": "main",
                "source_sha": source_sha,
                "oci_revision": source_sha,
                "container_source_revision": source_sha,
                "image_digest": image_digest,
                "registry_repository": "ghcr.io/lidefend/sce-product",
                "registry_refs": [f"ghcr.io/lidefend/sce-product@{image_digest}"] * 2,
                "local_image_id": "sha256:" + "1" * 64,
                "archive_config_digest": "sha256:" + "2" * 64,
                "archive_reload_image_id": "sha256:" + "3" * 64,
                "archive_sha256": "c" * 64,
                "baseline_checksum": "d" * 64,
                "scan": {
                    "status": "completed",
                    "source_sha": source_sha,
                    "image_digest": image_digest,
                    "counts": {
                        "CRITICAL": 0,
                        "HIGH": 0,
                        "MEDIUM": 1,
                        "LOW": 2,
                        "SECRET": 0
                    },
                    "policy": {"result": "pass"}
                }
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    checksum.write_text(
        f"{hashlib.sha256(manifest.read_bytes()).hexdigest()}  {manifest.name}\n",
        encoding="utf-8",
    )
    env = {
        "TARGET_DB": db,
        "SC_ENVIRONMENT": "migration_rehearsal" if db == "sc_migration_rehearsal" else "production",
        "SC_FILESTORE_SCOPE": db,
        "SC_ALLOW_DEMO_DATA": "0",
        "SC_SOURCE_REVISION": source_sha,
        "EXPECTED_RELEASE_SHA": source_sha,
        "EXPECTED_IMAGE_DIGEST": image_digest,
        "RELEASE_MANIFEST_PATH": str(manifest),
        "RELEASE_MANIFEST_CHECKSUM_PATH": str(checksum),
        "TARGET_MODULE": "smart_construction_core",
        "PLATFORM_RELEASE_DB": db,
    }
    for key, suffix in {
        "SC_DATABASE_VOLUME": "postgres", "SC_REDIS_VOLUME": "redis", "SC_FILESTORE_VOLUME": "filestore",
        "SC_SESSION_VOLUME": "sessions", "SC_TMP_VOLUME": "tmp", "SC_LOG_VOLUME": "logs",
    }.items():
        env[key] = f"sce-{db}-{suffix}"
    return env


class DatabaseGuardTests(unittest.TestCase):
    def test_runtime_accepts_rehearsal(self): contract.validate("runtime", formal_env())
    def test_missing_database_fails_closed(self):
        with self.assertRaises(contract.ContractError): contract.validate("runtime", {})
    def test_sc_prod_is_always_forbidden(self):
        with self.assertRaises(contract.ContractError): contract.validate("upgrade", formal_env("sc_prod"))
    def test_postgres_is_forbidden(self):
        with self.assertRaises(contract.ContractError): contract.validate("init", formal_env("postgres"))
    def test_arbitrary_database_is_forbidden(self):
        with self.assertRaises(contract.ContractError): contract.validate("runtime", formal_env("other_database"))
    def test_production_init_requires_confirmation(self):
        with self.assertRaises(contract.ContractError): contract.validate("init", formal_env("sc_production"))
    def test_production_upgrade_requires_confirmation(self):
        with self.assertRaises(contract.ContractError): contract.validate("upgrade", formal_env("sc_production"))
    def test_production_upgrade_accepts_exact_confirmation(self):
        env = formal_env("sc_production"); env["SC_PRODUCTION_CHANGE_APPROVED"] = contract.PRODUCTION_CONFIRMATION
        contract.validate("upgrade", env)
    def test_platform_configuration_is_a_guarded_mutation(self):
        env = formal_env("sc_production")
        with self.assertRaises(contract.ContractError): contract.validate("configure-platform", env)
        env["SC_PRODUCTION_CHANGE_APPROVED"] = contract.PRODUCTION_CONFIRMATION
        contract.validate("configure-platform", env)
    def test_release_sha_must_match_image(self):
        env = formal_env(); env["EXPECTED_RELEASE_SHA"] = "b" * 40
        with self.assertRaises(contract.ContractError): contract.validate("upgrade", env)
    def test_release_manifest_is_required_for_mutation(self):
        env = formal_env(); env.pop("RELEASE_MANIFEST_PATH")
        with self.assertRaises(contract.ContractError): contract.validate("upgrade", env)
    def test_release_manifest_source_must_match(self):
        env = formal_env()
        manifest = Path(env["RELEASE_MANIFEST_PATH"])
        payload = json.loads(manifest.read_text())
        payload["source_sha"] = "b" * 40
        manifest.write_text(json.dumps(payload) + "\n")
        checksum = Path(env["RELEASE_MANIFEST_CHECKSUM_PATH"])
        checksum.write_text(f"{hashlib.sha256(manifest.read_bytes()).hexdigest()}  {manifest.name}\n")
        with self.assertRaises(contract.ContractError): contract.validate("upgrade", env)
    def test_release_manifest_checksum_must_match(self):
        env = formal_env()
        Path(env["RELEASE_MANIFEST_CHECKSUM_PATH"]).write_text(f"{'0' * 64}  manifest.json\n")
        with self.assertRaises(contract.ContractError): contract.validate("upgrade", env)
    def test_production_rejects_demo_flag(self):
        env = formal_env("sc_production"); env["SC_ALLOW_DEMO_DATA"] = "1"
        with self.assertRaises(contract.ContractError): contract.validate("runtime", env)
    def test_production_rejects_fixture_module(self):
        env = formal_env("sc_production"); env["SC_PRODUCTION_CHANGE_APPROVED"] = contract.PRODUCTION_CONFIRMATION; env["TARGET_MODULE"] = "customer_fixture"
        with self.assertRaises(contract.ContractError): contract.validate("install", env)
    def test_filestore_scope_must_match_database(self):
        env = formal_env(); env["SC_FILESTORE_SCOPE"] = "sc_production"
        with self.assertRaises(contract.ContractError): contract.validate("runtime", env)
    def test_filestore_volumes_are_isolated(self):
        env = formal_env(); env["SC_FILESTORE_VOLUME"] = "sce-sc_production-filestore"
        with self.assertRaises(contract.ContractError): contract.validate("runtime", env)
    def test_platform_database_is_required_explicitly(self):
        env = formal_env(); env.pop("PLATFORM_RELEASE_DB")
        with self.assertRaises(contract.ContractError): contract.validate("runtime", env)
    def test_platform_database_must_match_business_database(self):
        env = formal_env(); env["PLATFORM_RELEASE_DB"] = "sc_platform_core"
        with self.assertRaises(contract.ContractError): contract.validate("runtime", env)


class StaticContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dockerfile = (ROOT / "Dockerfile.production-candidate").read_text()
        cls.entrypoint = (ROOT / "scripts/release/production_odoo_entrypoint.sh").read_text()
        cls.manager = (ROOT / "scripts/release/production_db_manage.sh").read_text()
        cls.compose = (ROOT / "docker-compose.production-candidate.yml").read_text()
        cls.acceptance = (ROOT / "scripts/release/production_contract_image_acceptance.sh").read_text()
        cls.release_make = (ROOT / "make/release.mk").read_text()
        cls.identity = (ROOT / "scripts/release/release_source_identity.py").read_text()
        cls.first_fresh_cleanup = (
            ROOT / "scripts/release/production_first_fresh_cleanup.py"
        ).read_text()
        cls.admin_harden = (
            ROOT / "scripts/release/production_admin_harden.py"
        ).read_text()
        cls.admin_identity_baseline = (
            ROOT / "scripts/release/production_admin_identity_baseline.py"
        ).read_text()
        cls.formal_module_install = (
            ROOT / "scripts/release/production_formal_module_install.py"
        ).read_text()
        cls.production_command_policy = (
            ROOT / "docs/ops/prod_command_policy.md"
        ).read_text()

    def test_base_image_has_digest(self): self.assertRegex(self.dockerfile.splitlines()[0], r"^FROM odoo:17\.0@sha256:[0-9a-f]{64}$")
    def test_no_distribution_upgrade(self): self.assertNotRegex(self.dockerfile, r"apt(?:-get)?\s+(?:dist-upgrade|full-upgrade|upgrade)")
    def test_empty_addon_directories_created(self):
        for path in ("/mnt/customer-addons", "/mnt/test-addons", "/mnt/source-addons"): self.assertIn(path, self.dockerfile)
    def test_candidate_image_copies_versioned_locked_menu_contract(self):
        for name in (
            "formal_business_product_menu_policy_v1.json",
            "formal_business_product_menu_policy_v1.json.sha256",
        ):
            self.assertIn(f"COPY scripts/verify/baselines/{name} /opt/sce-product/contracts/{name}", self.dockerfile)
            self.assertTrue((ROOT / "scripts/verify/baselines" / name).is_file())
    def test_approved_tax_certificate_initialization_remains_formal_and_non_legacy(self):
        for token in (
            "TAX_CERTIFICATE_INITIALIZATION PASS",
            "sc.tax.certificate.registration",
            "action_sc_tax_certificate_registration_user",
            "menu_sc_tax_certificate_registration_user",
            "sc.legacy.payment.residual.fact",
        ):
            self.assertIn(token, self.acceptance)
        self.assertNotIn("CREATE MODEL sc.legacy.payment.residual.fact", self.acceptance)
    def test_runtime_storage_avoids_base_image_volume(self):
        self.assertIn("/opt/sce-runtime/filestore", self.dockerfile)
        self.assertNotIn("/var/lib/odoo/filestore", self.dockerfile)
    def test_normal_entrypoint_never_mutates_database(self):
        for token in ("CREATE DATABASE", "DROP DATABASE", "createdb", "-i base", " -u ", "restore"): self.assertNotIn(token, self.entrypoint)
    def test_normal_entrypoint_uses_read_only_session(self): self.assertIn("default_transaction_read_only=on", self.entrypoint)
    def test_health_path_is_read_only(self):
        self.assertIn("preflight|health) readonly_probe", self.manager)
        self.assertIn("base is not installed", self.manager)
    def test_compose_images_are_digest_pinned(self): self.assertEqual(len(re.findall(r"image: .*@sha256:[0-9a-f]{64}", self.compose)), 2)
    def test_application_services_require_digest_addressed_refs(self):
        self.assertIn("ODOO_IMAGE_REF with image@sha256 digest is required", self.compose)
        self.assertIn("NGINX_IMAGE_REF with image@sha256 digest is required", self.compose)
        self.assertNotIn("image: ${CANDIDATE_IMAGE", self.compose)
        self.assertIn("PRODUCTION_COMPOSE_PROJECT:?PRODUCTION_COMPOSE_PROJECT is required", self.compose)
    def test_compose_does_not_default_target_database(self): self.assertIn("TARGET_DB:?TARGET_DB is required", self.compose)
    def test_compose_disables_demo(self): self.assertIn('SC_ALLOW_DEMO_DATA: "0"', self.compose)
    def test_compose_requires_explicit_colocated_platform_database(self):
        self.assertIn("PLATFORM_RELEASE_DB:?PLATFORM_RELEASE_DB is required", self.compose)
    def test_candidate_source_sha_has_no_hardcoded_default(self):
        self.assertIn("SOURCE_SHA ?=", self.release_make)
        self.assertNotIn("CANDIDATE_SOURCE_SHA ?=", self.release_make)
        self.assertNotIn("c93e40c5e2613c0b9389492f185365c1d498e7d2", self.release_make)
        self.assertIn("SOURCE_SHA is required", self.release_make)
    def test_formal_repository_identity_is_exact(self):
        self.assertIn('EXPECTED_REPOSITORY = "lidefend/sce-backend-odoo"', self.identity)
        self.assertIn('EXPECTED_REMOTE_URL = "https://github.com/lidefend/sce-backend-odoo.git"', self.identity)
    def test_compose_mounts_release_manifest_for_fail_closed_validation(self):
        self.assertIn("RELEASE_MANIFEST_PATH:?RELEASE_MANIFEST_PATH is required", self.compose)
        self.assertIn("RELEASE_MANIFEST_CHECKSUM_PATH:?RELEASE_MANIFEST_CHECKSUM_PATH is required", self.compose)
        self.assertIn("EXPECTED_IMAGE_DIGEST:?EXPECTED_IMAGE_DIGEST is required", self.compose)
    def test_compose_binds_odoo_to_loopback(self): self.assertIn('127.0.0.1:${CANDIDATE_ODOO_PORT', self.compose)
    def test_odoo_config_disables_database_manager(self): self.assertIn("list_db = False", (ROOT / "config/odoo.conf.template").read_text())
    def test_odoo_database_endpoint_is_explicit(self):
        config = (ROOT / "config/odoo.conf.template").read_text()
        self.assertIn("db_host = ${DB_HOST}", config)
        self.assertIn("db_port = ${DB_PORT}", config)
    def test_isolated_acceptance_is_make_wrapped(self):
        release_make = (ROOT / "make/release.mk").read_text()
        self.assertIn("release.production.contract.image.acceptance:", release_make)
        self.assertIn("production_contract_image_acceptance.sh", release_make)
    def test_draft_pr_uses_governed_make_entry(self):
        codex_make = (ROOT / "make/codex.mk").read_text()
        self.assertIn("PR_DRAFT ?= 0", codex_make)
        self.assertIn('1) draft_arg="--draft"', codex_make)
        self.assertIn("PR_DRAFT must be 0 or 1", codex_make)
    def test_init_cleanup_is_not_exposed_as_general_management_action(self):
        actions = self.manager.split('case "$ACTION" in', 1)[1].split(") ;;", 1)[0]
        self.assertNotIn("drop", actions)
        helper = (ROOT / "scripts/release/production_db_init.py").read_text()
        self.assertIn("cleanup_created", helper)
        self.assertIn('validate("init", active_env)', helper)

    def test_production_identity_preflight_is_not_forbidden_in_production(self):
        target = self.release_make.split(
            "release.production.identity.preflight:", 1
        )[1].split("\n\n", 1)[0]
        self.assertNotIn("guard.prod.forbid", target)

    def test_production_mutations_keep_danger_guard(self):
        for name in (
            "release.production.infrastructure.up",
            "release.production.runtime.up",
            "release.production.db.init",
            "release.production.module.install",
            "release.production.module.upgrade",
            "release.production.platform.configure",
            "release.production.platform.snapshot.initialize",
            "release.production.admin.harden",
            "release.production.admin_identity.baseline",
            "release.production.formal_modules.install_missing",
        ):
            declaration = self.release_make.split(f"{name}:", 1)[1].splitlines()[0]
            self.assertIn("guard.prod.danger", declaration)

    def test_first_fresh_cleanup_is_fixed_scope_and_confirmation_guarded(self):
        self.assertIn(
            "CONFIRM_FRESH_PRODUCTION_DEPLOY=YES_DELETE_OLD_PROJECT_DATA is required",
            self.release_make,
        )
        self.assertIn("OLD_CONTAINERS = {", self.first_fresh_cleanup)
        self.assertIn("OLD_NETWORKS = {", self.first_fresh_cleanup)
        self.assertIn("OLD_VOLUMES = {", self.first_fresh_cleanup)
        self.assertNotIn("system prune", self.first_fresh_cleanup)
        self.assertNotIn("volume prune", self.first_fresh_cleanup)

    def test_admin_harden_is_exact_scope_and_confirmation_guarded(self):
        target = self.release_make.split(
            "release.production.admin.harden:", 1
        )[1].split("\n\n", 1)[0]
        self.assertIn("guard.prod.danger", target.splitlines()[0])
        self.assertIn(
            "CONFIRM_ADMIN_HARDEN=YES_HARDEN_FRESH_PRODUCTION_ADMIN is required",
            target,
        )
        self.assertIn("-e SC_BOOTSTRAP_ADMIN_PASSWORD", target)
        self.assertNotIn("FORMAL_ACCEPTANCE_PASSWORD", target)
        self.assertNotIn("ADMIN_PASSWD", target)
        self.assertIn('TARGET_LOGIN = "admin"', self.admin_harden)
        self.assertIn('TARGET_DATABASE = "sc_production"', self.admin_harden)
        self.assertIn('target.write({"password": password})', self.admin_harden)
        self.assertNotIn(".execute(", self.admin_harden)

    def test_admin_identity_baseline_is_canonical_and_confirmation_guarded(self):
        target = self.release_make.split(
            "release.production.admin_identity.baseline:", 1
        )[1].split("\n\n", 1)[0]
        self.assertIn("guard.prod.danger", target.splitlines()[0])
        self.assertIn(
            "CONFIRM_ADMIN_IDENTITY_BASELINE="
            "YES_APPLY_FRESH_PRODUCTION_ADMIN_IDENTITY_BASELINE is required",
            target,
        )
        self.assertIn(
            "release.production.admin_identity.baseline",
            self.production_command_policy,
        )
        self.assertIn(
            'CANONICAL_ROLE_XMLIDS = ("smart_core.group_smart_core_admin",)',
            self.admin_identity_baseline,
        )
        self.assertIn(
            'EXPECTED_CURRENT_EVIDENCE = "no_authoritative_role"',
            self.admin_identity_baseline,
        )
        self.assertIn(
            'target.write(',
            self.admin_identity_baseline,
        )
        self.assertIn(
            '"groups_id"',
            self.admin_identity_baseline,
        )
        self.assertEqual(
            self.admin_identity_baseline.count("odoo_env.cr.execute("),
            2,
        )
        self.assertIn(
            'odoo_env.cr.execute("SET TRANSACTION READ ONLY")',
            self.admin_identity_baseline,
        )
        self.assertIn(
            'odoo_env.cr.execute("SHOW transaction_read_only")',
            self.admin_identity_baseline,
        )
        self.assertIn(
            '"planned_write_model": PLANNED_WRITE_MODEL',
            self.admin_identity_baseline,
        )
        self.assertIn(
            '"planned_relation_append_count": append_count',
            self.admin_identity_baseline,
        )
        self.assertIn(
            '"observed_after_dry_run"',
            self.admin_identity_baseline,
        )
        self.assertIn(
            '"fingerprints"',
            self.admin_identity_baseline,
        )
        for contract in (
            "ADMIN_IDENTITY_RUN_ID",
            "ADMIN_IDENTITY_TOOL_SOURCE_SHA",
            "ADMIN_IDENTITY_DEPLOYED_PATH",
        ):
            self.assertIn(contract, target)
            self.assertIn(contract, self.admin_identity_baseline)
        self.assertIn(
            'EVIDENCE_SCHEMA_VERSION = "admin-identity-baseline-evidence-v3"',
            self.admin_identity_baseline,
        )
        self.assertIn(
            'DEPLOYMENT_METADATA_NAME = "deployment-tool-metadata.json"',
            self.admin_identity_baseline,
        )
        self.assertIn(
            '"coverage": "canonical-json-excluding-integrity"',
            self.admin_identity_baseline,
        )
        self.assertIn(
            '$(ADMIN_IDENTITY_DEPLOYED_PATH):$(ADMIN_IDENTITY_DEPLOYED_PATH):ro',
            target,
        )
        self.assertNotIn("base.group_system", self.admin_identity_baseline)
        self.assertNotIn("group_sc_super_admin", self.admin_identity_baseline)
        self.assertIn(
            "ADMIN_IDENTITY_BASELINE_MODE ?= dry-run",
            self.release_make,
        )

    def test_formal_module_closure_has_a_dedicated_production_contract(self):
        target = self.release_make.split(
            "release.production.formal_modules.install_missing:", 1
        )[1].split("\n\n", 1)[0]
        self.assertIn("guard.prod.danger", target.splitlines()[0])
        self.assertIn(
            "CONFIRM_FORMAL_MODULE_INSTALL=YES_INSTALL_MISSING_FORMAL_MODULES is required",
            target,
        )
        self.assertIn(
            "production_formal_module_install.py execute",
            target,
        )
        self.assertNotIn("TARGET_MODULE=", target)
        self.assertIn(
            "release.production.formal_modules.install_missing",
            self.production_command_policy,
        )
        self.assertIn(
            'CONFIRMATION = "YES_INSTALL_MISSING_FORMAL_MODULES"',
            self.formal_module_install,
        )
        self.assertIn(
            'BACKUP_CONFIG_PATH = Path("/etc/scems/production-backup.env")',
            self.formal_module_install,
        )
        self.assertIn(
            'BACKUP_ROOT = "/data/backups/sc_production"',
            self.formal_module_install,
        )
        self.assertIn(
            "process environment backup override is forbidden",
            self.formal_module_install,
        )
        backup_template = (
            ROOT / "deploy/production-backup/production-backup.env.example"
        ).read_text()
        self.assertIn(
            "BACKUP_ROOT=/data/backups/sc_production", backup_template
        )
        self.assertNotIn("sce-sc-production-", backup_template)
        backup_source = (
            ROOT / "scripts/release/production_colocated_backup.py"
        ).read_text()
        for token in (
            'CHECKSUM_FILE = "SHA256SUMS"',
            "previous_umask = os.umask(0o077)",
            "temporary_directory.chmod(0o700)",
            "path.chmod(0o600)",
            "require_artifact_contract=True",
            "os.rename(temporary_directory, final_directory)",
            "pg_restore\", \"-l",
        ):
            self.assertIn(token, backup_source)
        self.assertLess(
            backup_source.index("_write_checksums(temporary_directory)"),
            backup_source.index(
                "os.rename(temporary_directory, final_directory)"
            ),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
