#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mutation tests for the Batch C entry guard.

Each test removes or restores one mechanism the guard exists to protect, so a
future edit that quietly reintroduces a client database hint fails here first.
"""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/verify/nginx_proxy_db_authority_guard.py"
TEMPLATE = ROOT / "config/nginx/templates/default.conf.template"
COMPOSE = ROOT / "docker-compose.yml"
RENDERER = ROOT / "scripts/render_nginx_conf.sh"


def _load():
    spec = importlib.util.spec_from_file_location("nginx_proxy_db_authority_guard", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NginxProxyDbAuthorityGuardTest(unittest.TestCase):
    def setUp(self):
        self.guard = _load()
        self.template = TEMPLATE.read_text(encoding="utf-8")
        self.compose = COMPOSE.read_text(encoding="utf-8")
        self.renderer = RENDERER.read_text(encoding="utf-8")

    def probe(self, **overrides):
        return self.guard.probe(
            template=overrides.get("template", self.template),
            compose=overrides.get("compose", self.compose),
            renderer=overrides.get("renderer", self.renderer),
            legacy_conf_exists=False,
        )

    def test_shipped_entry_is_clean(self):
        self.assertEqual([], self.probe())

    def test_restoring_a_header_database_map_is_refused(self):
        mutated = self.template.replace(
            "map $uri $sc_path_ns {",
            "map $http_x_odoo_db $sc_legacy_header_db {\n  default $http_x_odoo_db;\n}\n\nmap $uri $sc_path_ns {",
            1,
        )
        errors = self.probe(template=mutated)
        self.assertTrue(any("$http_x_odoo_db" in item for item in errors), errors)

    def test_restoring_a_query_database_map_is_refused(self):
        mutated = self.template.replace(
            "map $uri $sc_path_ns {",
            "map $arg_db $sc_legacy_query_db {\n  default $arg_db;\n}\n\nmap $uri $sc_path_ns {",
            1,
        )
        errors = self.probe(template=mutated)
        self.assertTrue(any("$arg_db" in item for item in errors), errors)

    def test_dropping_the_namespace_stamp_is_refused(self):
        mutated = self.template.replace("    proxy_set_header X-SC-Namespace    $sc_path_ns;\n", "")
        errors = self.probe(template=mutated)
        self.assertTrue(any("X-SC-Namespace" in item for item in errors), errors)

    def test_dropping_the_missing_namespace_refusal_is_refused(self):
        mutated = self.template.replace(
            '      return 400 \'{"error":"NS_NAMESPACE_REQUIRED"}\';\n', ""
        )
        errors = self.probe(template=mutated)
        self.assertTrue(any("NS_NAMESPACE_REQUIRED" in item for item in errors), errors)

    def test_dropping_the_root_api_refusal_is_refused(self):
        mutated = self.template.replace("  location /api/ {", "  location /api-disabled/ {", 1)
        errors = self.probe(template=mutated)
        self.assertTrue(
            any("namespace-less" in item and "NS_NAMESPACE_REQUIRED" in item for item in errors),
            errors,
        )

    def test_dropping_the_relative_root_redirect_is_refused(self):
        mutated = self.template.replace("  absolute_redirect off;\n", "", 1)
        errors = self.probe(template=mutated)
        self.assertTrue(any("absolute_redirect off" in item for item in errors), errors)

    def test_dropping_the_json_default_type_is_refused(self):
        mutated = self.template.replace("  default_type application/json;\n", "", 1)
        errors = self.probe(template=mutated)
        self.assertTrue(any("application/json" in item for item in errors), errors)

    def test_dropping_the_illegal_prefix_refusal_is_refused(self):
        mutated = self.template.replace(
            '      return 404 \'{"error":"NS_UNKNOWN_NAMESPACE"}\';\n', ""
        )
        errors = self.probe(template=mutated)
        self.assertTrue(any("NS_UNKNOWN_NAMESPACE" in item for item in errors), errors)

    def test_dropping_the_tenant_fallback_location_is_refused(self):
        mutated = self.template.replace("  location ~ ^/t/ {", "  location ~ ^/t-disabled/ {", 1)
        errors = self.probe(template=mutated)
        self.assertTrue(any("NS_UNKNOWN_NAMESPACE" in item for item in errors), errors)

    def test_dropping_the_shared_secret_injection_is_refused(self):
        mutated = self.compose.replace("SC_ENTRY_SHARED_SECRET:", "SC_ENTRY_SHARED_SECRET_RETIRED:")
        errors = self.probe(compose=mutated)
        self.assertTrue(any("SC_ENTRY_SHARED_SECRET" in item for item in errors), errors)

    def test_reintroducing_a_database_default_is_refused(self):
        mutated = self.compose.replace(
            "SC_PROXY_DEFAULT_UPSTREAM:", "SC_PROXY_DEFAULT_DB: ${DB_NAME}\n      SC_PROXY_DEFAULT_UPSTREAM:", 1
        )
        errors = self.probe(compose=mutated)
        self.assertTrue(any("database-name injection" in item for item in errors), errors)

    def test_publishing_a_database_in_runtime_config_is_refused(self):
        mutated = self.renderer.replace('"entryContract":"v2"', '"odooDb":"sc_demo","entryContract":"v2"', 1)
        errors = self.probe(renderer=mutated)
        self.assertTrue(any("must not publish a database name" in item for item in errors), errors)


if __name__ == "__main__":
    unittest.main()
