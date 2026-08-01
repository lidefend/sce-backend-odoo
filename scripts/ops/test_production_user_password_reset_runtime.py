#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ops/production_user_password_reset_runtime.py"
SPEC = importlib.util.spec_from_file_location("production_user_password_reset_runtime", SCRIPT)
assert SPEC and SPEC.loader
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


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


class RuntimeContextTests(unittest.TestCase):
    def setUp(self):
        image = "ghcr.io/example/product@sha256:" + "a" * 64
        runtime = {
            "TARGET_DB": "sc_production",
            "DB_NAME": "sc_production",
            "ODOO_DB": "sc_production",
            "ODOO_DBFILTER": "^sc_production$",
            "PLATFORM_RELEASE_DB": "sc_production",
            "SC_ENVIRONMENT": "production",
            "EXPECTED_IMAGE_DIGEST": "sha256:" + "a" * 64,
            "EXPECTED_RELEASE_SHA": "b" * 40,
            "DB_USER": "runtime-user",
            "DB_PASSWORD": "runtime-db-secret",
            "JWT_SECRET": "runtime-jwt-secret",
            "ADMIN_PASSWD": "runtime-admin-secret",
        }
        self.containers = {
            "odoo": container(
                "odoo",
                image,
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
            "nginx": container("nginx", image, {}, []),
            "db": container("db", "postgres@sha256:" + "c" * 64, {}, [{"Destination": "/var/lib/postgresql/data", "Name": "database"}]),
            "redis": container("redis", "redis@sha256:" + "d" * 64, {}, [{"Destination": "/data", "Name": "redis"}]),
        }
        self.active_env = {
            "DB_USER": "stale-user",
            "DB_PASSWORD": "stale-db-secret",
            "JWT_SECRET": "stale-jwt-secret",
            "ADMIN_PASSWD": "stale-admin-secret",
        }

    def test_resolves_only_current_runtime_identity_and_mounts(self):
        result = helper.resolve_compose_environment(self.containers, self.active_env)
        self.assertEqual(result["PRODUCTION_COMPOSE_PROJECT"], "sc_production")
        self.assertEqual(result["TARGET_DB"], "sc_production")
        self.assertEqual(result["SC_DATABASE_VOLUME"], "database")
        self.assertEqual(result["SC_CUSTOMER_ADDONS_ROOT"], "/customer/addons")
        self.assertEqual(result["DB_USER"], "runtime-user")
        self.assertEqual(result["DB_PASSWORD"], "runtime-db-secret")

    def test_runtime_or_secret_drift_fails_closed(self):
        original = list(self.containers["odoo"]["Config"]["Env"])
        self.containers["odoo"]["Config"]["Env"] = ["TARGET_DB=sc_demo"]
        with self.assertRaises(helper.RuntimeContextError):
            helper.resolve_compose_environment(self.containers, self.active_env)
        self.containers["odoo"]["Config"]["Env"] = [
            item
            for item in original
            if not item.startswith("DB_PASSWORD=")
        ]
        with self.assertRaises(helper.RuntimeContextError):
            helper.resolve_compose_environment(self.containers, self.active_env)

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
