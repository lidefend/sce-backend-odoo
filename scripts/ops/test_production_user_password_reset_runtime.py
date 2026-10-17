#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ops/production_user_password_reset_runtime.py"
SPEC = importlib.util.spec_from_file_location("production_user_password_reset_runtime", SCRIPT)
assert SPEC and SPEC.loader
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


SOURCE_SHA = "b" * 40
ODOO_DIGEST = "sha256:" + "a" * 64
FRONTEND_DIGEST = "sha256:" + "e" * 64
ODOO_IMAGE = "ghcr.io/lidefend/sce-product@" + ODOO_DIGEST
FRONTEND_IMAGE = "ghcr.io/lidefend/sce-frontend@" + FRONTEND_DIGEST


def container(service, image, env, mounts):
    return {
        "Config": {
            "Image": image,
            "Env": [f"{key}={value}" for key, value in env.items()],
            "Labels": {
                "com.docker.compose.project": "sc_production",
                "com.docker.compose.service": service,
            },
        },
        "State": {"Running": True},
        "Mounts": mounts,
    }


def release_manifest() -> dict:
    return {
        "source_sha": SOURCE_SHA,
        "oci_revision": SOURCE_SHA,
        "container_source_revision": SOURCE_SHA,
        "image_digest": ODOO_DIGEST,
        "frontend_image_digest": FRONTEND_DIGEST,
        "registry_refs": [ODOO_IMAGE, ODOO_IMAGE],
        "frontend_registry_repository": "ghcr.io/lidefend/sce-frontend",
        "frontend_registry_refs": [FRONTEND_IMAGE, FRONTEND_IMAGE],
    }


class RuntimeContextTests(unittest.TestCase):
    def setUp(self):
        runtime = {
            "TARGET_DB": "sc_production",
            "DB_NAME": "sc_production",
            "ODOO_DB": "sc_production",
            "ODOO_DBFILTER": "^sc_production$",
            "PLATFORM_RELEASE_DB": "sc_production",
            "SC_ENVIRONMENT": "production",
            "EXPECTED_IMAGE_DIGEST": ODOO_DIGEST,
            "EXPECTED_FRONTEND_IMAGE_DIGEST": FRONTEND_DIGEST,
            "ODOO_IMAGE_REF": ODOO_IMAGE,
            "FRONTEND_IMAGE_REF": FRONTEND_IMAGE,
            "EXPECTED_RELEASE_SHA": SOURCE_SHA,
            "DB_USER": "runtime-user",
            "DB_PASSWORD": "runtime-db-secret",
            "JWT_SECRET": "runtime-jwt-secret",
            "ADMIN_PASSWD": "runtime-admin-secret",
        }
        self.containers = {
            "odoo": container(
                "odoo",
                ODOO_IMAGE,
                runtime,
                [
                    {"Destination": "/opt/sce-release/product-release-manifest.json", "Source": "/candidate/manifest.json"},
                    {"Destination": "/opt/sce-release/product-release-manifest.sha256", "Source": "/candidate/manifest.sha256"},
                    {"Destination": "/mnt/customer-addons", "Source": "/customer/addons"},
                    {"Destination": "/opt/sce-runtime/filestore", "Name": "filestore"},
                    {"Destination": "/opt/sce-runtime/sessions", "Name": "sessions"},
                    {"Destination": "/opt/sce-runtime/tmp", "Name": "tmp"},
                    {"Destination": "/opt/sce-runtime/logs", "Name": "logs"},
                ],
            ),
            "nginx": container("nginx", FRONTEND_IMAGE, {}, []),
            "db": container("db", "postgres@sha256:" + "c" * 64, {}, [{"Destination": "/var/lib/postgresql/data", "Name": "database"}]),
            "redis": container("redis", "redis@sha256:" + "d" * 64, {}, [{"Destination": "/data", "Name": "redis"}]),
        }
        self.manifest = release_manifest()
        self.active_env = {
            "DB_USER": "stale-user",
            "DB_PASSWORD": "stale-db-secret",
            "JWT_SECRET": "stale-jwt-secret",
            "ADMIN_PASSWD": "stale-admin-secret",
        }

    def resolve(self):
        return helper.resolve_compose_environment(
            self.containers, self.active_env, self.manifest
        )

    def test_resolves_only_current_runtime_identity_and_mounts(self):
        result = self.resolve()
        self.assertEqual(result["PRODUCTION_COMPOSE_PROJECT"], "sc_production")
        self.assertEqual(result["TARGET_DB"], "sc_production")
        self.assertEqual(result["SC_DATABASE_VOLUME"], "database")
        self.assertEqual(result["SC_CUSTOMER_ADDONS_ROOT"], "/customer/addons")
        self.assertEqual(result["DB_USER"], "runtime-user")
        self.assertEqual(result["DB_PASSWORD"], "runtime-db-secret")

    def test_returns_two_independent_image_identities(self):
        result = self.resolve()
        self.assertEqual(result["ODOO_IMAGE_REF"], ODOO_IMAGE)
        self.assertEqual(result["EXPECTED_IMAGE_DIGEST"], ODOO_DIGEST)
        self.assertEqual(result["FRONTEND_IMAGE_REF"], FRONTEND_IMAGE)
        self.assertEqual(result["EXPECTED_FRONTEND_IMAGE_DIGEST"], FRONTEND_DIGEST)
        self.assertNotEqual(result["ODOO_IMAGE_REF"], result["FRONTEND_IMAGE_REF"])

    def test_shared_odoo_and_frontend_image_fails_closed(self):
        self.containers["nginx"]["Config"]["Image"] = ODOO_IMAGE
        with self.assertRaisesRegex(helper.RuntimeContextError, "distinct"):
            self.resolve()

    def test_frontend_repository_drift_fails_closed(self):
        other = "ghcr.io/example/product@" + FRONTEND_DIGEST
        self.containers["nginx"]["Config"]["Image"] = other
        with self.assertRaisesRegex(helper.RuntimeContextError, "repository"):
            self.resolve()

    def test_frontend_digest_format_fails_closed(self):
        self.containers["nginx"]["Config"]["Image"] = "ghcr.io/lidefend/sce-frontend@sha256:" + "e" * 63
        with self.assertRaisesRegex(helper.RuntimeContextError, "identity"):
            self.resolve()

    def test_manifest_frontend_digest_drift_fails_closed(self):
        self.manifest["frontend_image_digest"] = "sha256:" + "f" * 64
        with self.assertRaisesRegex(helper.RuntimeContextError, "frontend digest"):
            self.resolve()

    def test_manifest_odoo_digest_drift_fails_closed(self):
        self.manifest["image_digest"] = "sha256:" + "f" * 64
        with self.assertRaisesRegex(helper.RuntimeContextError, "Odoo digest"):
            self.resolve()

    def test_manifest_frontend_reference_drift_fails_closed(self):
        self.manifest["frontend_registry_refs"] = [ODOO_IMAGE, ODOO_IMAGE]
        with self.assertRaisesRegex(helper.RuntimeContextError, "frontend image reference"):
            self.resolve()

    def test_runtime_frontend_digest_drift_fails_closed(self):
        env = self.containers["odoo"]["Config"]["Env"]
        self.containers["odoo"]["Config"]["Env"] = [
            item
            for item in env
            if not item.startswith("EXPECTED_FRONTEND_IMAGE_DIGEST=")
        ] + ["EXPECTED_FRONTEND_IMAGE_DIGEST=sha256:" + "f" * 64]
        with self.assertRaisesRegex(helper.RuntimeContextError, "identity"):
            self.resolve()

    def test_runtime_frontend_reference_drift_fails_closed(self):
        env = self.containers["odoo"]["Config"]["Env"]
        self.containers["odoo"]["Config"]["Env"] = [
            item
            for item in env
            if not item.startswith("FRONTEND_IMAGE_REF=")
        ] + ["FRONTEND_IMAGE_REF=" + ODOO_IMAGE]
        with self.assertRaisesRegex(helper.RuntimeContextError, "identity"):
            self.resolve()

    def test_runtime_or_secret_drift_fails_closed(self):
        original = list(self.containers["odoo"]["Config"]["Env"])
        self.containers["odoo"]["Config"]["Env"] = ["TARGET_DB=sc_demo"]
        with self.assertRaises(helper.RuntimeContextError):
            self.resolve()
        self.containers["odoo"]["Config"]["Env"] = [
            item
            for item in original
            if not item.startswith("DB_PASSWORD=")
        ]
        with self.assertRaises(helper.RuntimeContextError):
            self.resolve()

    def test_release_manifest_is_checksum_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "product-release-manifest.json"
            checksum_path = root / "product-release-manifest.sha256"
            payload = b'{"source_sha": "bound"}'
            manifest_path.write_bytes(payload)
            checksum_path.write_text(
                hashlib.sha256(payload).hexdigest() + "  product-release-manifest.json\n",
                encoding="utf-8",
            )
            mounts = self.containers["odoo"]["Mounts"]
            for mount in mounts:
                if mount["Destination"] == "/opt/sce-release/product-release-manifest.json":
                    mount["Source"] = str(manifest_path)
                if mount["Destination"] == "/opt/sce-release/product-release-manifest.sha256":
                    mount["Source"] = str(checksum_path)
            self.assertEqual(
                helper._release_manifest(self.containers["odoo"]),
                {"source_sha": "bound"},
            )
            manifest_path.write_bytes(b'{"source_sha": "tampered"}')
            with self.assertRaisesRegex(helper.RuntimeContextError, "checksum"):
                helper._release_manifest(self.containers["odoo"])

    def test_source_contains_no_secret_output_or_password_transport(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("--password", source)
        self.assertNotIn("stdin=", source)
        self.assertNotIn("DB_PASSWORD=", source)
        self.assertIn("resolved[name] = runtime[name]", source)
        self.assertIn("os.execvpe", source)
        self.assertIn('"docker",\n        "compose"', source)

    def test_verification_mode_is_forwarded_without_password_transport(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('parser.add_argument("--mode", choices=("reset", "verify")', source)
        self.assertIn('--mode "{mode}"', source)
        self.assertNotIn("--password", source)


if __name__ == "__main__":
    unittest.main()
