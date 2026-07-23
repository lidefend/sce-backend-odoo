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


if __name__ == "__main__":
    unittest.main(verbosity=2)
