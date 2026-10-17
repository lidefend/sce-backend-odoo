"""Unit tests for the read-only daily runtime routing inventory.

These tests are pure: they never reach a host. They pin the two invariants the
tool exists for -- one cluster data directory has one live postmaster, and one
database is served by at most one instance with an exact filter -- plus the
read-only contract.
"""

import json
import tempfile
import unittest
from unittest import mock
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


def payload(instances, cluster_databases=None, volume_owners=None, error="",
            cluster_role="sc_demo_maintenance", cluster_role_error=""):
    return {
        "cluster_container": "sc-backend-odoo-dev-db-1",
        "cluster_container_project": "sc-backend-odoo-dev",
        "cluster_database": "sc_demo",
        "cluster_role": cluster_role,
        "cluster_role_source": "container_environment" if cluster_role else "",
        "cluster_role_error": cluster_role_error,
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


class RoutingInventoryRoleTests(unittest.TestCase):
    """The cluster probe must name the role the carrier actually created.

    A hard-coded ``-U odoo`` is a carrier assumption. It happens to exist on the
    workstation cluster and does not exist on the rebuilt remote cluster, where
    the same tool reported ``FATAL: role "odoo" does not exist``.
    """

    sha = "80da1af3d060201cebbddc58146e940a7f34b570"

    def test_generated_program_carries_the_discovered_role_and_never_odoo(self):
        program = routing._render_program(
            "sc_dev_demo", "sc-local-dev-db-1", "sc_demo_maintenance",
            "sc-local-dev",
        ).decode("utf-8")
        self.assertIn('DATABASE_ROLE = "sc_demo_maintenance"', program)
        self.assertIn('"psql",\n            "-U",\n            role,', program)
        self.assertNotIn('"-U",\n            "odoo",', program)
        self.assertIn('EXPECTED_PROJECT = "sc-local-dev"', program)

    def test_empty_role_renders_environment_discovery_instead_of_a_default(self):
        program = routing._render_program(
            "sc_demo", "sc-demo-dev-db-1", "", "",
        ).decode("utf-8")
        self.assertIn('DATABASE_ROLE = ""', program)
        self.assertIn("POSTGRES_USER", program)
        self.assertIn("DATABASE_ROLE_UNRESOLVED", program)
        self.assertNotIn('"odoo"', program)

    def test_an_unresolved_role_fails_the_verdict(self):
        verdict = routing.evaluate(
            "sc_demo",
            payload([instance("a-odoo-1", "sc_demo", port="8070")],
                    cluster_role="", cluster_role_error="DATABASE_ROLE_UNRESOLVED"),
        )
        self.assertFalse(verdict["passed"])
        self.assertFalse(assertion(verdict, "cluster_role_resolved")["passed"])

    def test_the_expected_compose_project_is_asserted_when_given(self):
        good = routing.evaluate(
            "sc_demo",
            payload([instance("a-odoo-1", "sc_demo", port="8070")]),
            expected_project="sc-backend-odoo-dev",
        )
        self.assertTrue(good["passed"])
        bad = routing.evaluate(
            "sc_demo",
            payload([instance("a-odoo-1", "sc_demo", port="8070")]),
            expected_project="sc-local-dev",
        )
        self.assertFalse(bad["passed"])
        self.assertFalse(
            assertion(bad, "cluster_container_is_the_expected_project")["passed"]
        )

    def test_the_probe_is_removed_when_the_readback_raises(self):
        class Result:
            def __init__(self, returncode=0, stdout=b"", stderr=b""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        head = Result(stdout=(self.sha + "\n").encode())
        upload = Result()
        calls = []

        def fake_ssh(_host, command, input_bytes=None):
            calls.append(command)
            if command.startswith("cd /opt/projects/repos"):
                return head
            if command.startswith("cat > "):
                self.assertTrue(input_bytes)
                return upload
            if command.startswith("python3 "):
                raise RuntimeError("transport lost")
            if command.startswith("rm -f "):
                return Result()
            raise AssertionError("unexpected command: %s" % command)

        with mock.patch.object(routing, "ssh", side_effect=fake_ssh):
            with self.assertRaisesRegex(RuntimeError, "transport lost"):
                routing.inventory(
                    self.sha, "sc_demo", "sc-host", "sc-demo-dev-db-1",
                )
        self.assertEqual(calls[-1], "rm -f " + routing.REMOTE_TMP)


class RoutingInventorySelectorAndIdentityTests(unittest.TestCase):
    """A collected fact must have a consumer, or it is not evidence.

    ``list_db_env`` was collected and never asserted, so an instance with
    ``ODOO_LIST_DB=true`` still produced PASS -- a serving port that answers
    database enumeration passes the routing verdict unchanged. The identity
    probe had the mirror defect: a non-zero exit was swallowed and an empty
    ``system_identifier`` was reported as a successful observation.
    """

    def test_a_serving_instance_with_list_db_true_fails(self):
        row = instance("sc-local-dev-odoo-1", "sc_dev_demo", port="8070")
        row["list_db_env"] = "true"
        verdict = routing.evaluate("sc_dev_demo", payload([row]))
        self.assertFalse(verdict["passed"])
        closed = assertion(verdict, "database_enumeration_closed")
        self.assertFalse(closed["passed"])
        self.assertEqual(closed["detail"]["open_selector_instances"], ["sc-local-dev-odoo-1"])

    def test_every_open_selector_spelling_is_refused(self):
        for spelling in ("1", "true", "TRUE", "yes", "on"):
            row = instance("odoo-1", "sc_dev_demo", port="8070")
            row["list_db_env"] = spelling
            verdict = routing.evaluate("sc_dev_demo", payload([row]))
            self.assertFalse(
                verdict["passed"], "list_db_env=%r must not pass" % (spelling,)
            )

    def test_absent_or_false_selector_stays_closed(self):
        for value in ("", "0", "false", "False", "off"):
            row = instance("odoo-1", "sc_dev_demo", port="8070")
            row["list_db_env"] = value
            verdict = routing.evaluate("sc_dev_demo", payload([row]))
            self.assertTrue(
                verdict["passed"], "list_db_env=%r must stay closed" % (value,)
            )

    def test_a_non_serving_container_publishing_no_port_is_not_a_selector(self):
        # The database/ingress containers inherit the application environment;
        # only the instance that publishes a host port serves enumeration.
        row = instance("db-1", "sc_dev_demo", port="")
        row["list_db_env"] = "true"
        verdict = routing.evaluate("sc_dev_demo", payload([row]))
        self.assertTrue(verdict["passed"])

    def test_an_unobserved_system_identifier_fails(self):
        observed = payload([instance("odoo-1", "sc_dev_demo", port="8070")])
        observed["cluster_system_identifier"] = ""
        observed["cluster_system_identifier_error"] = (
            'psql: error: connection to server on socket failed'
        )
        verdict = routing.evaluate("sc_dev_demo", observed)
        self.assertFalse(verdict["passed"])
        self.assertFalse(
            assertion(verdict, "cluster_system_identifier_observed")["passed"]
        )

    def test_a_zero_exit_probe_with_an_empty_identifier_fails(self):
        observed = payload([instance("odoo-1", "sc_dev_demo", port="8070")])
        observed["cluster_system_identifier"] = ""
        verdict = routing.evaluate("sc_dev_demo", observed)
        self.assertFalse(verdict["passed"])


class RoutingInventoryProbeExecutionTests(unittest.TestCase):
    """Run the generated probe against a fake docker daemon.

    The role is discovered inside the cluster container, not in this process,
    so the fail-closed path for an invalid discovered role is only provable by
    executing the rendered program.
    """

    sha = "80da1af3d060201cebbddc58146e940a7f34b570"

    fake_docker = """#!/usr/bin/env python3
import json
import os
import sys

state = json.load(open(os.environ["FAKE_DOCKER_STATE"], encoding="utf-8"))
argv = sys.argv[1:]
if argv[0] == "ps":
    print("\\n".join(state["running"]))
elif argv[0] == "inspect":
    print(json.dumps(state["inspected"]))
elif argv[0] == "exec":
    sql = argv[-1]
    if "pg_database" in sql:
        if state.get("database_error"):
            sys.stderr.write(state["database_error"])
            sys.exit(2)
        print("\\n".join(state["databases"]))
    else:
        if state.get("system_identifier_error"):
            sys.stderr.write(state["system_identifier_error"])
            sys.exit(2)
        print(state["system_identifier"])
else:
    sys.exit("unsupported docker call: %r" % (argv,))
"""

    def inspect_entry(self, role):
        return {
            "Name": "/sc-local-dev-db-1",
            "Config": {
                "Image": "postgres:15",
                "Labels": {"com.docker.compose.project": "sc-local-dev"},
                "Env": ["POSTGRES_USER=%s" % role] if role is not None else [],
            },
            "Mounts": [{"Type": "volume", "Name": "sc_local_dev_db_data",
                        "Destination": "/var/lib/postgresql/data"}],
            "NetworkSettings": {"Ports": {}},
        }

    def run_probe(self, state):
        import os
        import subprocess

        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            docker = bin_dir / "docker"
            docker.write_text(self.fake_docker, encoding="utf-8")
            docker.chmod(0o755)
            state_path = Path(tmp) / "state.json"
            state_path.write_text(json.dumps(state), encoding="utf-8")
            env = dict(os.environ)
            env["PATH"] = "%s:%s" % (bin_dir, env.get("PATH", ""))
            env["FAKE_DOCKER_STATE"] = str(state_path)
            program = routing._render_program(
                "sc_dev_demo", "sc-local-dev-db-1", "", "sc-local-dev",
            )
            result = subprocess.run(
                ["python3", "-"], input=program, capture_output=True, env=env,
            )
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return routing.marker_payload(result.stdout.decode())

    def state(self, **overrides):
        state = {
            "running": ["sc-local-dev-db-1"],
            "inspected": [self.inspect_entry("odoo"), {
                "Name": "/sc-local-dev-odoo-1",
                "Config": {
                    "Image": "odoo17-odoo:latest",
                    "Labels": {"com.docker.compose.project": "sc-local-dev",
                               "com.docker.compose.service": "odoo"},
                    "Env": ["ODOO_DB=sc_dev_demo", "ODOO_DBFILTER=^sc_dev_demo$"],
                },
                "Mounts": [{"Type": "volume", "Name": "sc_local_dev_odoo_data",
                            "Destination": "/var/lib/odoo"}],
                "NetworkSettings": {"Ports": {"8069/tcp": [
                    {"HostIp": "0.0.0.0", "HostPort": "8070"},
                    {"HostIp": "::", "HostPort": "8070"},
                ]}},
            }],
            "databases": ["postgres", "sc_dev_demo"],
            "system_identifier": "7674830867180216358",
        }
        state.update(overrides)
        return state

    def test_the_probe_discovers_the_role_from_the_cluster_environment(self):
        observed = self.run_probe(self.state())
        self.assertEqual(observed["cluster_role"], "odoo")
        self.assertEqual(observed["cluster_role_source"], "container_environment")
        self.assertEqual(observed["cluster_role_error"], "")
        self.assertEqual(observed["cluster_system_identifier"], "7674830867180216358")
        verdict = routing.evaluate("sc_dev_demo", observed, expected_project="sc-local-dev")
        self.assertTrue(verdict["passed"])

    def test_the_probe_refuses_an_invalid_environment_role(self):
        observed = self.run_probe(
            self.state(inspected=[self.inspect_entry("bad role; drop")])
        )
        self.assertEqual(observed["cluster_role"], "")
        self.assertTrue(
            observed["cluster_role_error"].startswith("DATABASE_ROLE_INVALID:"),
            observed["cluster_role_error"],
        )
        self.assertEqual(observed["cluster_databases"], [])
        verdict = routing.evaluate("sc_dev_demo", observed)
        self.assertFalse(verdict["passed"])
        self.assertFalse(assertion(verdict, "cluster_role_resolved")["passed"])

    def test_the_probe_refuses_a_non_ascii_environment_role(self):
        # str.isalnum() accepts non-ASCII letters, so the check must be an
        # explicit role-name pattern, not a character-class sweep.
        observed = self.run_probe(
            self.state(inspected=[self.inspect_entry("роль")])
        )
        self.assertEqual(observed["cluster_role"], "")
        self.assertTrue(
            observed["cluster_role_error"].startswith("DATABASE_ROLE_INVALID:"),
            observed["cluster_role_error"],
        )

    def test_the_probe_marks_a_failed_identity_query_as_unobserved(self):
        observed = self.run_probe(
            self.state(system_identifier_error='psql: error: permission denied')
        )
        self.assertEqual(observed["cluster_system_identifier"], "")
        self.assertIn("permission denied", observed["cluster_system_identifier_error"])
        verdict = routing.evaluate("sc_dev_demo", observed)
        self.assertFalse(verdict["passed"])
        self.assertFalse(
            assertion(verdict, "cluster_system_identifier_observed")["passed"]
        )

    def test_the_probe_marks_a_failed_catalog_query_as_an_error(self):
        observed = self.run_probe(
            self.state(database_error='FATAL: role "odoo" does not exist')
        )
        self.assertIn("does not exist", observed["cluster_error"])
        verdict = routing.evaluate("sc_dev_demo", observed)
        self.assertFalse(verdict["passed"])
        self.assertFalse(assertion(verdict, "cluster_databases_observed")["passed"])


    def test_the_probe_is_removed_when_the_upload_fails(self):
        class Result:
            def __init__(self, returncode=0, stdout=b"", stderr=b""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        head = Result(stdout=(self.sha + "\n").encode())
        calls = []

        def fake_ssh(_host, command, input_bytes=None):
            calls.append(command)
            if command.startswith("cd /opt/projects/repos"):
                return head
            if command.startswith("cat > "):
                return Result(returncode=1, stderr=b"disk full")
            if command.startswith("rm -f "):
                return Result()
            raise AssertionError("unexpected command: %s" % command)

        with mock.patch.object(routing, "ssh", side_effect=fake_ssh):
            with self.assertRaisesRegex(routing.InventoryError, "upload failed"):
                routing.inventory(
                    self.sha, "sc_demo", "sc-host", "sc-demo-dev-db-1",
                )
        self.assertEqual(calls[-1], "rm -f " + routing.REMOTE_TMP)

    def test_an_invalid_database_role_argument_is_refused(self):
        with self.assertRaisesRegex(routing.InventoryError, "plain role name"):
            routing.inventory(
                self.sha, "sc_demo", "sc-host", "sc-demo-dev-db-1",
                database_role="odoo; drop",
            )

class RoutingInventoryDutyBindingTests(unittest.TestCase):
    """A database *name* stops being a target identity once two carriers share it.

    The refusal is read from the shipped declaration, not from a stub: it now
    names the rebuilt demo duty and the preserved historic source with the same
    ``sc_demo``, so an entry that receives only ``--database`` would otherwise
    have to guess which carrier it is measuring.
    """

    instances = Path(__file__).with_name("synthetic_duty_instances.sample.json")

    def reader(self, _path: str) -> str:
        return self.instances.read_text(encoding="utf-8")

    def options(self, **overrides):
        options = mock.Mock()
        options.duty = ""
        options.database = "sc_demo"
        options.ssh_host = "sc-root"
        for key, value in overrides.items():
            setattr(options, key, value)
        return options

    def test_a_bare_database_name_no_longer_binds_a_carrier(self) -> None:
        with self.assertRaisesRegex(routing.InventoryError, "DUTY_IDENTITY_DATABASE_AMBIGUOUS:sc_demo"):
            routing.bind_target(self.options(), instances_reader=self.reader)

    def test_naming_the_duty_binds_the_rebuilt_demo_carrier(self) -> None:
        binding = routing.bind_target(
            self.options(duty="demo"), instances_reader=self.reader
        )
        self.assertEqual(binding["database"], "sc_demo")
        self.assertEqual(binding["database_role"], "sc_demo_app")
        self.assertEqual(binding["compose_project"], "sc-demo-dev")
        self.assertEqual(binding["database_container"], "sc-demo-dev-db-1")
        self.assertEqual(binding["database_volume"], "sc_demo_db_data")
        self.assertEqual(binding["data_purpose"], "demo")

    def test_the_cluster_read_is_the_bound_duty_cluster_not_a_remembered_name(self) -> None:
        # Reading a catalog from a remembered container name is how this entry
        # would have kept reporting the historic source after the carrier moved.
        binding = routing.bind_target(
            self.options(duty="demo"), instances_reader=self.reader
        )
        self.assertEqual(
            routing.resolve_cluster_container("", binding), "sc-demo-dev-db-1"
        )

    def test_an_explicit_container_stays_available_for_a_cross_carrier_audit(self) -> None:
        binding = routing.bind_target(
            self.options(duty="demo"), instances_reader=self.reader
        )
        self.assertEqual(
            routing.resolve_cluster_container("sc-backend-odoo-dev-db-1", binding),
            "sc-backend-odoo-dev-db-1",
        )

    def test_no_legacy_container_name_is_shipped_as_a_default(self) -> None:
        # A module-level default would re-introduce the silent cross-carrier
        # read for every caller that does not pass the flag itself.
        self.assertFalse(
            [name for name in dir(routing) if "CLUSTER_CONTAINER" in name
             and getattr(routing, name) and not name.startswith("__")],
            "the tool must derive its cluster from the bound duty",
        )


if __name__ == "__main__":
    unittest.main()
