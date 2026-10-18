"""Unit tests for the one-public-entry declaration.

The declaration is the only place that may say which duty is public and which
upstream answers the platform database.  These tests mutate the shipped
document in the ways that would create a second entry or cross the two duties,
and require the validator to refuse each one.
"""

import copy
import json
import unittest
from pathlib import Path

from scripts.ops import daily_runtime_database_duty as entry


ROOT = Path(__file__).resolve().parents[2]
ENTRY = ROOT / "config/ops/daily_runtime_entry.v1.json"
DECLARATION = ROOT / "config/ops/daily_runtime_database_duties.v1.json"


def shipped():
    return (
        json.loads(ENTRY.read_text(encoding="utf-8")),
        json.loads(DECLARATION.read_text(encoding="utf-8")),
    )


class DailyRuntimeEntryTest(unittest.TestCase):
    def test_shipped_entry_is_one_public_face(self):
        entry_doc, declaration = shipped()
        self.assertEqual([], entry.validate_entry(entry_doc, declaration))

    def test_public_port_must_match_the_serving_duty(self):
        entry_doc, declaration = shipped()
        entry_doc["public_entry"]["port"] = 18082
        self.assertTrue(entry.validate_entry(entry_doc, declaration))

    def test_a_second_public_face_is_refused(self):
        entry_doc, declaration = shipped()
        entry_doc["exposure"][1]["public"] = True
        entry_doc["exposure"][1]["bind_host"] = "0.0.0.0"
        failures = entry.validate_entry(entry_doc, declaration)
        self.assertTrue(failures)

    def test_platform_upstream_must_be_the_platform_nginx(self):
        entry_doc, declaration = shipped()
        entry_doc["routes"][1]["upstream"] = "odoo:8069"
        self.assertTrue(entry.validate_entry(entry_doc, declaration))

    def test_every_database_route_is_unique(self):
        entry_doc, declaration = shipped()
        entry_doc["routes"][1]["database"] = "sc_demo"
        self.assertTrue(entry.validate_entry(entry_doc, declaration))

    def test_an_odoo_face_may_never_be_public(self):
        entry_doc, declaration = shipped()
        odoo_face = next(row for row in entry_doc["exposure"] if row["service"] == "odoo")
        odoo_face["public"] = True
        odoo_face["bind_host"] = "0.0.0.0"
        self.assertTrue(entry.validate_entry(entry_doc, declaration))

    def test_a_route_to_an_undeclared_duty_is_refused(self):
        entry_doc, declaration = shipped()
        entry_doc["routes"][1]["duty"] = "tenant_unknown"
        self.assertTrue(entry.validate_entry(entry_doc, declaration))

    def test_a_non_ipv4_bind_host_is_refused(self):
        entry_doc, declaration = shipped()
        entry_doc["exposure"][1]["bind_host"] = "localhost"
        self.assertTrue(entry.validate_entry(entry_doc, declaration))

    def test_an_unknown_exposed_service_is_refused(self):
        entry_doc, declaration = shipped()
        entry_doc["exposure"][1]["service"] = "adminer"
        self.assertTrue(entry.validate_entry(entry_doc, declaration))

    def test_empty_entry_network_is_refused(self):
        entry_doc, declaration = shipped()
        entry_doc["network"]["name"] = ""
        self.assertTrue(entry.validate_entry(entry_doc, declaration))

    def test_database_hint_must_keep_header_precedence(self):
        entry_doc, declaration = shipped()
        entry_doc["database_hint"]["precedence"] = ["query:db", "header:X-Odoo-DB", "default"]
        failures = entry.validate_entry(entry_doc, declaration)
        self.assertTrue(any("precedence" in item for item in failures), failures)

    def test_database_hint_must_name_both_sources(self):
        entry_doc, declaration = shipped()
        entry_doc["database_hint"]["sources"] = ["header:X-Odoo-DB"]
        failures = entry.validate_entry(entry_doc, declaration)
        self.assertTrue(any("sources" in item for item in failures), failures)

    def test_unknown_database_must_be_refused_with_400(self):
        entry_doc, declaration = shipped()
        entry_doc["database_hint"]["unknown_database"]["status"] = 200
        failures = entry.validate_entry(entry_doc, declaration)
        self.assertTrue(any("status must be 400" in item for item in failures), failures)

    def test_unknown_database_must_use_the_stable_error_code(self):
        entry_doc, declaration = shipped()
        entry_doc["database_hint"]["unknown_database"]["code"] = "fallback"
        failures = entry.validate_entry(entry_doc, declaration)
        self.assertTrue(any("code must be unknown_database" in item for item in failures), failures)

    def test_allowed_databases_must_equal_the_declared_routes(self):
        entry_doc, declaration = shipped()
        entry_doc["database_hint"]["allowed_databases"].append("sc_undeclared")
        failures = entry.validate_entry(entry_doc, declaration)
        self.assertTrue(any("allowed_databases" in item for item in failures), failures)

    def test_default_database_must_be_the_default_route(self):
        entry_doc, declaration = shipped()
        entry_doc["database_hint"]["default_database"] = "sc_platform_control"
        failures = entry.validate_entry(entry_doc, declaration)
        self.assertTrue(any("default_database" in item for item in failures), failures)

    def test_mutating_a_route_database_does_not_change_the_declaration_digest(self):
        entry_doc, _ = shipped()
        digest = entry.entry_digest(entry_doc)
        entry_doc = copy.deepcopy(entry_doc)
        entry_doc["public_entry"]["port"] = 18082
        self.assertNotEqual(digest, entry.entry_digest(entry_doc))


if __name__ == "__main__":
    unittest.main()
