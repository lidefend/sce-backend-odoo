#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Falsification test for the nginx proxy-database authority guard.

The guard is a text probe over two shipped configuration carriers, so the only
way to know it still proves anything is to falsify it on purpose: each case
breaks one fact and asserts that the guard reports that exact break.  The first
case keeps the shipped configuration intact, so the baseline is proven good
before any negative case is trusted.
"""
from __future__ import annotations

import unittest
from pathlib import Path

import nginx_proxy_db_authority_guard as guard

ROOT = guard.ROOT
TEMPLATE = guard.TEMPLATE
COMPOSE = guard.COMPOSE


class NginxProxyDbAuthorityGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.template = TEMPLATE.read_text(encoding="utf-8")
        cls.compose = COMPOSE.read_text(encoding="utf-8")

    def probe(self, *, template: str | None = None, compose: str | None = None, legacy: bool = False):
        return guard.probe(
            template=self.template if template is None else template,
            compose=self.compose if compose is None else compose,
            legacy_conf_exists=legacy,
        )

    def test_shipped_configuration_settles_the_proxy_database_from_the_profile(self):
        self.assertEqual([], self.probe())

    def test_inlining_a_database_literal_in_the_fallback_is_rejected(self):
        mutated = self.template.replace(guard.FALLBACK_LINE, "  ''      sc_demo;")
        self.assertNotEqual(mutated, self.template)
        errors = self.probe(template=mutated)
        self.assertTrue(any("fallback must be" in error for error in errors), errors)

    def test_dropping_the_explicit_db_passthrough_is_rejected(self):
        mutated = self.template.replace(
            "map $arg_db $sc_proxy_query_db {", "map $arg_db $sc_proxy_query_db_disabled {"
        )
        self.assertNotEqual(mutated, self.template)
        errors = self.probe(template=mutated)
        self.assertTrue(any("declared header > query > default precedence" in error for error in errors), errors)

    def test_reversing_the_declared_precedence_is_rejected(self):
        mutated = self.template.replace(
            "map $sc_proxy_header_db $sc_proxy_hinted_db {",
            "map $sc_proxy_query_db $sc_proxy_hinted_db {",
        )
        self.assertNotEqual(mutated, self.template)
        errors = self.probe(template=mutated)
        self.assertTrue(any("declared header > query > default precedence" in error for error in errors), errors)

    def test_dropping_the_allowed_database_check_is_rejected(self):
        mutated = self.template.replace(
            "map $sc_proxy_db $sc_proxy_db_allowed {",
            "map $sc_proxy_db $sc_proxy_db_allowed_disabled {",
        )
        self.assertNotEqual(mutated, self.template)
        errors = self.probe(template=mutated)
        self.assertTrue(any("allowed set" in error for error in errors), errors)

    def test_accepting_an_unknown_database_is_rejected(self):
        mutated = self.template.replace(
            guard.UNKNOWN_REFUSAL_LINE, "    return 200 '{\"error\":\"unknown_database\"}';"
        )
        self.assertNotEqual(mutated, self.template)
        errors = self.probe(template=mutated)
        self.assertTrue(any("HTTP 400 `unknown_database`" in error for error in errors), errors)

    def test_dropping_the_profile_injection_is_rejected(self):
        mutated = self.compose.replace(guard.COMPOSE_INJECTION, "SC_PROXY_DEFAULT_DB: sc_demo")
        self.assertNotEqual(mutated, self.compose)
        errors = self.probe(compose=mutated)
        self.assertTrue(any("must inject the profile database" in error for error in errors), errors)

    def test_dropping_the_allowed_pattern_injection_is_rejected(self):
        mutated = self.compose.replace(
            "      SC_PROXY_ALLOWED_DB_PATTERN: '${SC_PROXY_ALLOWED_DB_PATTERN:-~^.+$}'\n", ""
        )
        self.assertNotEqual(mutated, self.compose)
        errors = self.probe(compose=mutated)
        self.assertTrue(any("allowed database pattern" in error for error in errors), errors)

    def test_widening_envsubst_to_every_variable_is_rejected(self):
        mutated = self.compose.replace(f"      {guard.COMPOSE_FILTER}\n", "")
        self.assertNotEqual(mutated, self.compose)
        errors = self.probe(compose=mutated)
        self.assertTrue(any("must restrict envsubst" in error for error in errors), errors)

    def test_mounting_a_pre_rendered_literal_config_is_rejected(self):
        mutated = self.compose.replace(
            guard.TEMPLATE_MOUNT, "./config/nginx/conf.d/default.conf:/etc/nginx/conf.d/default.conf:ro"
        )
        self.assertNotEqual(mutated, self.compose)
        errors = self.probe(compose=mutated)
        self.assertTrue(any("must not mount a pre-rendered literal config" in error for error in errors), errors)
        self.assertTrue(any("must render the template" in error for error in errors), errors)

    def test_reintroducing_the_literal_config_carrier_is_rejected(self):
        errors = self.probe(legacy=True)
        self.assertTrue(any("must not exist" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
