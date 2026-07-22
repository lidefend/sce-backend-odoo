#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("production_db_contract", ROOT / "scripts/release/production_db_contract.py")
assert SPEC and SPEC.loader
contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract)


def formal_env(db: str = "sc_migration_rehearsal") -> dict[str, str]:
    env = {
        "TARGET_DB": db,
        "SC_ENVIRONMENT": "migration_rehearsal" if db == "sc_migration_rehearsal" else "production",
        "SC_FILESTORE_SCOPE": db,
        "SC_ALLOW_DEMO_DATA": "0",
        "SC_SOURCE_REVISION": "a" * 40,
        "EXPECTED_RELEASE_SHA": "a" * 40,
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

    def test_base_image_has_digest(self): self.assertRegex(self.dockerfile.splitlines()[0], r"^FROM odoo:17\.0@sha256:[0-9a-f]{64}$")
    def test_no_distribution_upgrade(self): self.assertNotRegex(self.dockerfile, r"apt(?:-get)?\s+(?:dist-upgrade|full-upgrade|upgrade)")
    def test_empty_addon_directories_created(self):
        for path in ("/mnt/customer-addons", "/mnt/test-addons", "/mnt/source-addons"): self.assertIn(path, self.dockerfile)
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
    def test_compose_does_not_default_target_database(self): self.assertIn("TARGET_DB:?TARGET_DB is required", self.compose)
    def test_compose_disables_demo(self): self.assertIn('SC_ALLOW_DEMO_DATA: "0"', self.compose)
    def test_compose_requires_explicit_colocated_platform_database(self):
        self.assertIn("PLATFORM_RELEASE_DB:?PLATFORM_RELEASE_DB is required", self.compose)
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
