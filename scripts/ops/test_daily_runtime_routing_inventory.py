"""Unit tests for the read-only daily runtime routing inventory.

These tests are pure: they never reach a host. They pin the two invariants the
tool exists for -- one cluster data directory has one live postmaster, and one
database is served by at most one instance with an exact filter -- plus the
read-only contract.
"""

import json
import tempfile
import unittest
from pathlib import Path

from scripts.ops import daily_runtime_routing_inventory as routing


def instance(container, database, dbfilter=None, port="", volume="sc_dev_odoo_data",
             service="odoo"):
    return {
        "container": container,
        "project": "sc-backend-odoo-dev",
        "service": service,
        "image": "odoo17-odoo:latest",
        "database": database,
        "dbfilter": f"^{database}$" if dbfilter is None else dbfilter,
        "list_db_env": "",
        "host_ports": (
            [{"container_port": "8069/tcp", "host_port": port}] if port else []
        ),
        "volumes": [
            {"type": "volume", "name": volume, "destination": "/var/lib/odoo"},
        ],
    }


def payload(instances, cluster_databases=None, volume_owners=None, error=""):
    return {
        "cluster_container": "sc-backend-odoo-dev-db-1",
        "cluster_database": "sc_demo",
        "cluster_databases": (
            cluster_databases if cluster_databases is not None
            else ["postgres", "sc_demo", "sc_odoo", "sc_platform_core"]
        ),
        "cluster_error": error,
        "cluster_system_identifier": "7597381856873586726",
        "postgres_data_volume_owners": (
            volume_owners if volume_owners is not None
            else {"sc_dev_db_data": ["sc-backend-odoo-dev-db-1"]}
        ),
        "instances": instances,
        "running_containers": ["sc-backend-odoo-dev-db-1"],
        "data_destination": "/var/lib/postgresql/data",
        "writes": False,
    }


def assertion(verdict, identifier):
    for row in verdict["assertions"]:
        if row["id"] == identifier:
            return row
    raise AssertionError(f"missing assertion {identifier}")


class RoutingInventoryTest(unittest.TestCase):
    def test_clean_topology_passes_and_reports_unserved_databases(self):
        verdict = routing.evaluate(
            "sc_demo",
            payload([instance("sc-backend-odoo-dev-odoo-1", "sc_demo", port="8070")]),
        )
        self.assertTrue(verdict["passed"])
        self.assertEqual(verdict["served_databases"], ["sc_demo"])
        self.assertEqual(
            verdict["unserved_databases"], ["sc_odoo", "sc_platform_core"]
        )
        self.assertEqual(
            verdict["duty_gap"]["databases_without_serving_instance"],
            ["sc_odoo", "sc_platform_core"],
        )

    def test_two_live_postmasters_on_one_cluster_volume_fail(self):
        verdict = routing.evaluate(
            "sc_demo",
            payload(
                [instance("sc-backend-odoo-dev-odoo-1", "sc_demo", port="8070")],
                volume_owners={
                    "sc_dev_db_data": [
                        "sc-backend-odoo-dev-db-1",
                        "sc-backend-odoo-prod-db-1",
                    ]
                },
            ),
        )
        self.assertFalse(verdict["passed"])
        row = assertion(verdict, "one_live_postmaster_per_cluster_data_volume")
        self.assertFalse(row["passed"])
        self.assertIn("sc-backend-odoo-prod-db-1", row["detail"]["sc_dev_db_data"])

    def test_non_exact_filter_fails(self):
        verdict = routing.evaluate(
            "sc_demo",
            payload([
                instance("sc-backend-odoo-dev-odoo-1", "sc_demo", dbfilter=".*", port="8070")
            ]),
        )
        self.assertFalse(verdict["passed"])
        self.assertEqual(
            assertion(verdict, "application_instance_filter_is_exact")["detail"],
            ["sc-backend-odoo-dev-odoo-1"],
        )

    def test_two_instances_serving_one_database_fail(self):
        verdict = routing.evaluate(
            "sc_demo",
            payload([
                instance("a-odoo-1", "sc_demo", port="8070"),
                instance("b-odoo-1", "sc_demo", port="8071", volume="b-odoo-data"),
            ]),
        )
        self.assertFalse(verdict["passed"])
        self.assertEqual(
            assertion(verdict, "single_serving_instance_per_database")["detail"],
            {"sc_demo": ["a-odoo-1", "b-odoo-1"]},
        )

    def test_duplicate_published_host_port_fails(self):
        verdict = routing.evaluate(
            "sc_demo",
            payload([
                instance("a-odoo-1", "sc_demo", port="8070"),
                instance("b-odoo-1", "sc_other", port="8070", volume="b-odoo-data"),
            ]),
        )
        self.assertFalse(verdict["passed"])
        self.assertEqual(
            assertion(verdict, "published_host_port_unique")["detail"],
            {"8070": ["a-odoo-1", "b-odoo-1"]},
        )

    def test_duplicate_address_family_binding_is_not_a_port_collision(self):
        row = instance("a-odoo-1", "sc_demo", port="8070")
        row["host_ports"] = [
            {"container_port": "8069/tcp", "host_port": "8070"},
            {"container_port": "8069/tcp", "host_port": "8070"},
        ]
        verdict = routing.evaluate("sc_demo", payload([row]))
        self.assertTrue(verdict["passed"])
        self.assertTrue(assertion(verdict, "published_host_port_unique")["passed"])

    def test_shared_instance_data_volume_fails(self):
        verdict = routing.evaluate(
            "sc_demo",
            payload([
                instance("a-odoo-1", "sc_demo", port="8070"),
                instance("b-odoo-1", "sc_other", port="8071"),
            ]),
        )
        self.assertFalse(verdict["passed"])
        self.assertEqual(
            assertion(verdict, "instance_data_volume_distinct")["detail"],
            {"sc_dev_odoo_data": ["a-odoo-1", "b-odoo-1"]},
        )

    def test_cluster_readback_error_fails(self):
        verdict = routing.evaluate(
            "sc_demo",
            payload([], cluster_databases=[], error="connection refused"),
        )
        self.assertFalse(verdict["passed"])
        self.assertFalse(assertion(verdict, "cluster_databases_observed")["passed"])

    def test_inventory_write_flag_is_enforced(self):
        sample = payload([instance("a-odoo-1", "sc_demo", port="8070")])
        sample["writes"] = True
        verdict = routing.evaluate("sc_demo", sample)
        self.assertFalse(verdict["passed"])
        self.assertFalse(assertion(verdict, "inventory_is_read_only")["passed"])

    def test_retired_stack_running_again_fails(self):
        sample = payload([instance("sc-backend-odoo-dev-odoo-1", "sc_demo", port="8070")])
        sample["running_containers"] = ["sc-backend-odoo-dev-odoo-1", "sc-backend-odoo-prod-db-1"]
        verdict = routing.evaluate("sc_demo", sample, retired=["sc-backend-odoo-prod-db-1"])
        self.assertFalse(verdict["passed"])
        self.assertEqual(
            assertion(verdict, "retired_stack_is_not_running")["detail"]["running_retired"],
            ["sc-backend-odoo-prod-db-1"],
        )

    def test_declared_retired_stack_that_is_stopped_passes(self):
        verdict = routing.evaluate(
            "sc_demo",
            payload([instance("sc-backend-odoo-dev-odoo-1", "sc_demo", port="8070")]),
            retired=["sc-backend-odoo-prod-db-1"],
        )
        self.assertTrue(verdict["passed"])

    def test_retired_names_come_from_the_declaration_only(self):
        declaration = {
            "schema": "daily.runtime.retired_stacks.v1",
            "stacks": [{"containers": [{"name": "sc-backend-odoo-prod-db-1", "id": "e37d48747997"},
                                       {"name": "sc-backend-odoo-prod-redis-1", "id": "2193b4da1469"}]}],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "retired.json"
            path.write_text(json.dumps(declaration), encoding="utf-8")
            self.assertEqual(
                routing.retired_container_names(path),
                ["sc-backend-odoo-prod-db-1", "sc-backend-odoo-prod-redis-1"],
            )

    def test_retired_declaration_with_a_foreign_schema_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "retired.json"
            path.write_text(json.dumps({"schema": "other"}), encoding="utf-8")
            with self.assertRaises(routing.InventoryError):
                routing.retired_container_names(path)

    def test_missing_retired_declaration_is_refused(self):
        with self.assertRaises(routing.InventoryError):
            routing.retired_container_names("/nonexistent/retired.json")

    def test_repository_declaration_lists_the_leftover_pair(self):
        path = Path(routing.__file__).resolve().parents[2] / "config/ops/daily_runtime_retired_stacks.v1.json"
        names = routing.retired_container_names(path)
        self.assertIn("sc-backend-odoo-prod-db-1", names)
        self.assertIn("sc-backend-odoo-prod-redis-1", names)

    def test_marker_payload_reads_last_line(self):
        self.assertEqual(
            routing.marker_payload('noise\n' + routing.MARKER + '{"a": 1}\n'),
            {"a": 1},
        )
        self.assertIsNone(routing.marker_payload("noise only\n"))

    def test_exact_filter_helper(self):
        self.assertTrue(routing._exact_filter(instance("a", "sc_demo")))
        self.assertFalse(routing._exact_filter(instance("a", "sc_demo", dbfilter="^sc_demo")))
        self.assertFalse(routing._exact_filter(instance("a", "sc_demo", dbfilter="^sc_demo.*$")))


if __name__ == "__main__":
    unittest.main()
