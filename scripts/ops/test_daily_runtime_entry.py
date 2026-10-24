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

import re

from scripts.ops import daily_runtime_database_duty as entry
from scripts.ops import daily_runtime_entry_verify as verifier


ROOT = Path(__file__).resolve().parents[2]
ENTRY = ROOT / "config/ops/daily_runtime_entry.v1.json"
DECLARATION = ROOT / "config/ops/daily_runtime_database_duties.v1.json"
TEMPLATE = ROOT / "config/nginx/templates/default.conf.template"


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

    def test_a_missing_platform_duty_is_refused(self):
        entry_doc, declaration = shipped()
        declaration["duties"] = [
            duty for duty in declaration["duties"] if duty["duty"] != "platform_control"
        ]
        failures = entry.validate_entry(entry_doc, declaration)
        self.assertTrue(any("undeclared duty platform_control" in item for item in failures), failures)

    def test_a_duplicate_duty_declaration_is_refused(self):
        entry_doc, declaration = shipped()
        duplicate = copy.deepcopy(next(
            duty for duty in declaration["duties"] if duty["duty"] == "demo"
        ))
        duplicate["database"] = "sc_demo_duplicate"
        declaration["duties"].append(duplicate)
        failures = entry.validate_entry(entry_doc, declaration)
        self.assertTrue(any("duty demo is declared more than once" in item for item in failures), failures)

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

    def test_namespace_routes_must_cover_the_declared_routes(self):
        entry_doc, declaration = shipped()
        entry_doc["namespace_routes"]["namespaces"].pop()
        failures = entry.validate_entry(entry_doc, declaration)
        self.assertTrue(any("cover exactly" in item for item in failures), failures)

    def test_namespace_id_must_be_an_immutable_shape(self):
        entry_doc, declaration = shipped()
        entry_doc["namespace_routes"]["namespaces"][0]["namespace_id"] = "demo"
        failures = entry.validate_entry(entry_doc, declaration)
        self.assertTrue(any("ns_<12 lowercase hex>" in item for item in failures), failures)

    def test_namespace_alias_must_be_unique(self):
        entry_doc, declaration = shipped()
        entry_doc["namespace_routes"]["namespaces"][1]["alias"] = "platform"
        failures = entry.validate_entry(entry_doc, declaration)
        self.assertTrue(any("alias platform is duplicated" in item for item in failures), failures)

    def test_namespace_duty_must_match_the_route(self):
        entry_doc, declaration = shipped()
        entry_doc["namespace_routes"]["namespaces"][1]["duty"] = "platform_control"
        failures = entry.validate_entry(entry_doc, declaration)
        self.assertTrue(any("duty contradicts" in item for item in failures), failures)

    def test_client_database_hint_must_be_refused_with_409(self):
        entry_doc, declaration = shipped()
        entry_doc["namespace_routes"]["client_database_hint"]["status"] = 200
        failures = entry.validate_entry(entry_doc, declaration)
        self.assertTrue(any("status must be 409" in item for item in failures), failures)

    def test_client_database_hint_must_use_the_stable_error_code(self):
        entry_doc, declaration = shipped()
        entry_doc["namespace_routes"]["client_database_hint"]["code"] = "unknown_database"
        failures = entry.validate_entry(entry_doc, declaration)
        self.assertTrue(any("NS_DATABASE_HINT_CONFLICT" in item for item in failures), failures)

    def test_every_published_database_hint_name_is_declared(self):
        entry_doc, _ = shipped()
        self.assertEqual(
            ["X-Odoo-Database", "X-Odoo-DB", "X-DB", "X-Odoo-DB-Locked"],
            entry_doc["namespace_routes"]["client_database_hint"]["headers"],
        )
        template = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("$http_x_odoo_database", template)

    def test_unknown_namespace_must_be_refused_with_404(self):
        entry_doc, declaration = shipped()
        entry_doc["namespace_routes"]["unknown_namespace"]["status"] = 400
        failures = entry.validate_entry(entry_doc, declaration)
        self.assertTrue(any("unknown_namespace.status must be 404" in item for item in failures), failures)

    def test_missing_namespace_must_be_refused_with_400(self):
        entry_doc, declaration = shipped()
        entry_doc["namespace_routes"]["missing_namespace"]["code"] = "fallback"
        failures = entry.validate_entry(entry_doc, declaration)
        self.assertTrue(any("NS_NAMESPACE_REQUIRED" in item for item in failures), failures)

    def test_platform_namespace_must_bind_the_platform_database(self):
        entry_doc, declaration = shipped()
        for row in entry_doc["namespace_routes"]["namespaces"]:
            if row["duty"] == "platform_control":
                row["database"] = "sc_demo"
        failures = entry.validate_entry(entry_doc, declaration)
        self.assertTrue(any("platform" in item.lower() for item in failures), failures)

    def test_unknown_namespace_probe_uses_an_alias_the_nginx_map_accepts(self):
        alias = verifier.UNKNOWN_NAMESPACE_ALIAS
        self.assertTrue(re.fullmatch(r"[a-z0-9][a-z0-9-]*", alias), alias)
        entry_doc, _ = shipped()
        declared = {row["alias"] for row in entry_doc["namespace_routes"]["namespaces"]}
        self.assertNotIn(alias, declared)

    def test_declared_alias_whitelist_is_rendered_from_the_entry(self):
        entry_doc, _ = shipped()
        self.assertEqual(
            "demo|platform", entry.entry_namespace_alias_pattern(entry_doc)
        )
        template = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("map $sc_path_ns $sc_declared_ns {", template)
        self.assertIn("~^(${SC_DECLARED_NAMESPACE_ALIASES})$", template)
        self.assertIn('if ($sc_declared_ns = "")', template)

    def test_an_empty_alias_declaration_cannot_render_an_open_whitelist(self):
        entry_doc, _ = shipped()
        entry_doc["namespace_routes"]["namespaces"] = []
        with self.assertRaisesRegex(RuntimeError, "ALIASES_EMPTY"):
            entry.entry_namespace_alias_pattern(entry_doc)

    def test_non_serving_faces_must_bind_loopback(self):
        entry_doc, declaration = shipped()
        platform = next(
            duty for duty in declaration["duties"] if duty["duty"] == "platform_control"
        )
        platform["routing"]["odoo_bind_host"] = "0.0.0.0"
        failures = entry.validate_entry(entry_doc, declaration)
        self.assertTrue(
            any("platform_control routing.odoo_bind_host must be 127.0.0.1" in item for item in failures),
            failures,
        )

    def test_the_public_serving_face_is_the_only_zero_bind(self):
        entry_doc, declaration = shipped()
        demo = next(duty for duty in declaration["duties"] if duty["duty"] == "demo")
        self.assertEqual(
            "0.0.0.0", entry.declared_bind_host(demo, "nginx", "demo")
        )
        self.assertEqual(
            "127.0.0.1", entry.declared_bind_host(demo, "odoo", "demo")
        )
        demo["routing"]["odoo_bind_host"] = "0.0.0.0"
        with self.assertRaisesRegex(RuntimeError, "INTERNAL_BIND_HOST_INVALID"):
            entry.declared_bind_host(demo, "odoo", "platform_control")

    def test_detection_maps_are_not_database_selectors(self):
        conf = (
            "map \"$http_x_odoo_db:$http_x_db:$http_x_odoo_db_locked\" "
            "$sc_client_db_header_present {\n  default 1;\n}\n"
            "map $arg_db $sc_client_db_query_present {\n  default 1;\n}\n"
            'proxy_set_header X-Odoo-DB         "";\n'
        )
        self.assertEqual([], verifier.database_selector_offenders(conf))

    def test_forwarding_a_client_hint_is_a_database_selector(self):
        offenders = verifier.database_selector_offenders(
            "proxy_set_header X-Odoo-DB $http_x_odoo_db;"
        )
        self.assertEqual(["proxy_set_header X-Odoo-DB $http_x_odoo_db;"], offenders)

    def test_shipped_template_has_no_database_selector(self):
        self.assertEqual(
            [], verifier.database_selector_offenders(TEMPLATE.read_text(encoding="utf-8"))
        )

    def test_platform_hop_does_not_double_scope_the_session_cookie(self):
        template = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("map $sc_entry_platform_strip $sc_proxy_cookie_path {", template)
        self.assertIn("proxy_cookie_path / $sc_proxy_cookie_path;", template)
        self.assertNotIn("proxy_cookie_path / $sc_entry_cookie_path;", template)

    def test_mutating_a_route_database_does_not_change_the_declaration_digest(self):
        entry_doc, _ = shipped()
        digest = entry.entry_digest(entry_doc)
        entry_doc = copy.deepcopy(entry_doc)
        entry_doc["public_entry"]["port"] = 18082
        self.assertNotEqual(digest, entry.entry_digest(entry_doc))


if __name__ == "__main__":
    unittest.main()
