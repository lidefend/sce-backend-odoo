"""Unit tests for the governed leftover-stack retirement entry.

The tests are pure: they never reach a host and never start a container. They pin
the properties the owner ruling depends on -- the reviewed stop method is the
immediate/non-checkpointing one, ``docker stop`` never appears, the plan digest
binds the exact reviewed commands, and each fail-closed guard actually refuses.
"""

import json
import unittest

from scripts.ops import daily_runtime_legacy_stack_retire as retire


def declaration(container_id="e37d48747997", kind="postgres", volume="sc_dev_db_data",
                name="sc-backend-odoo-prod-db-1"):
    return {
        "schema": "daily.runtime.retired_stacks.v1",
        "host": "sc-root",
        "survivor": {"probes": [{"name": "live_postmaster_facts", "argv": ["docker", "exec", "x"]}]},
        "stacks": [{
            "compose_project": "sc-backend-odoo-prod",
            "legacy_checkout": "/opt/projects/repos/sce-backend-odoo",
            "compose_files": ["docker-compose.yml"],
            "containers": [
                {"name": name, "id": container_id, "kind": kind,
                 "shared_volume": volume, "mount_destination": "/var/lib/postgresql/data"},
            ],
        }],
    }


def container(name, *, container_id="e37d48747997", kind="postgres", running=True,
              declared=True, started="2026-09-18 09:48:20", clients=None, redis_consumers=None):
    row = {
        "container": name, "present": True, "declared": declared, "kind": kind,
        "container_id": container_id, "running": running,
        "restart_policy": "unless-stopped", "stop_signal": "SIGINT", "state": "running",
        "cluster_facts": f"{started}|f|5D/1|7597381856873586726",
    }
    if kind == "postgres" and clients is not None:
        row["client_backends"] = clients
        row["application_clients"] = [c for c in clients if c[2]]
    if kind == "redis" and redis_consumers is not None:
        row["redis_consumers"] = redis_consumers
    return row


def facts(*, containers=None, postgres_owners=None, volume_owners=None, compose=None):
    return {
        "containers": containers if containers is not None else [
            container("sc-backend-odoo-prod-db-1", clients=[]),
            container("sc-backend-odoo-dev-db-1", container_id="8b079962b8b0",
                      declared=False, started="2026-09-24 08:28:55"),
        ],
        "postgres_data_volume_owners": postgres_owners if postgres_owners is not None else {
            "sc_dev_db_data": ["sc-backend-odoo-prod-db-1", "sc-backend-odoo-dev-db-1"],
        },
        "volume_owners": volume_owners if volume_owners is not None else {
            "sc_dev_db_data": ["sc-backend-odoo-prod-db-1", "sc-backend-odoo-dev-db-1"],
        },
        "compose_files": compose if compose is not None else [
            {"path": "/opt/projects/repos/sce-backend-odoo/docker-compose.yml",
             "exists": True, "sha256": "a" * 64},
        ],
        "legacy_checkout": {"path": "/opt/projects/repos/sce-backend-odoo", "head": "3b28", "status": []},
    }


def plan(decl=None, observed=None):
    return retire.build_plan(
        decl or declaration(), observed or facts(),
        ssh_host="sc-root", evidence_root="/opt/projects/backups/daily-runtime-legacy-retire",
    )


def failing(result):
    return sorted(row["id"] for row in result["guards"] if not row["passed"])


def steps(result):
    return [row["step"] for row in result["commands"]]


class ReviewedStopMethodTest(unittest.TestCase):
    def test_postgres_orphan_is_stopped_by_immediate_shutdown(self):
        result = plan()
        kill = [row for row in result["commands"] if row["step"].startswith("stop_")]
        self.assertEqual([row["signal"] for row in kill], ["SIGQUIT"])
        self.assertEqual(kill[0]["argv"], ["docker", "kill", "--signal=SIGQUIT", "sc-backend-odoo-prod-db-1"])
        self.assertIn("Immediate Shutdown", kill[0]["authority"])

    def test_docker_stop_is_never_issued(self):
        result = plan()
        for row in result["commands"]:
            self.assertNotEqual(row["argv"][:2], ["docker", "stop"])
            self.assertNotEqual(row["argv"][:2], ["docker", "rm"])
        self.assertNotIn("docker", [part for row in result["commands"] for part in row["argv"] if part == "stop"])

    def test_redis_orphan_is_stopped_without_a_shutdown_handler(self):
        decl = declaration(container_id="2193b4da1469", kind="redis", volume="sc_dev_redis_data",
                           name="sc-backend-odoo-prod-redis-1")
        observed = facts(
            containers=[container("sc-backend-odoo-prod-redis-1", container_id="2193b4da1469",
                                  kind="redis", redis_consumers=[])],
            postgres_owners={},
            volume_owners={"sc_dev_redis_data": ["sc-backend-odoo-prod-redis-1", "sc-backend-odoo-dev-redis-1"]},
        )
        result = plan(decl, observed)
        kill = [row for row in result["commands"] if row["step"].startswith("stop_")]
        self.assertEqual(kill[0]["argv"], ["docker", "kill", "sc-backend-odoo-prod-redis-1"])
        self.assertEqual(kill[0]["signal"], "SIGKILL")

    def test_idle_container_only_loses_its_restart_path(self):
        decl = declaration(container_id="1e98ca9bb863", kind="idle", volume="sc_dev_odoo_data",
                           name="sc-backend-odoo-prod-odoo-1")
        observed = facts(
            containers=[container("sc-backend-odoo-prod-odoo-1", container_id="1e98ca9bb863",
                                  kind="idle", running=False)],
            postgres_owners={},
            volume_owners={"sc_dev_odoo_data": ["sc-backend-odoo-prod-odoo-1", "sc-backend-odoo-dev-odoo-1"]},
        )
        result = plan(decl, observed)
        self.assertEqual(steps(result), ["remove_automatic_restart_path"])
        self.assertEqual(result["commands"][0]["argv"],
                         ["docker", "update", "--restart=no", "sc-backend-odoo-prod-odoo-1"])

    def test_clean_orphan_passes_every_guard(self):
        result = plan()
        self.assertEqual(failing(result), [])
        self.assertEqual(steps(result), ["remove_automatic_restart_path", "stop_postgres_immediate_shutdown"])


class PlanDigestTest(unittest.TestCase):
    def test_digest_is_stable_for_the_same_plan(self):
        self.assertEqual(plan()["digest"], plan()["digest"])

    def test_digest_changes_with_the_declared_container_identity(self):
        other = declaration(container_id="deadbeefcafe")
        observed = facts(containers=[
            container("sc-backend-odoo-prod-db-1", container_id="deadbeefcafe", clients=[]),
            container("sc-backend-odoo-dev-db-1", container_id="8b079962b8b0", declared=False,
                      started="2026-09-24 08:28:55"),
        ])
        self.assertNotEqual(plan()["digest"], plan(other, observed)["digest"])

    def test_compose_neutralise_records_the_reviewed_digest_of_the_file(self):
        result = plan()
        self.assertEqual(len(result["compose_neutralise"]), 1)
        entry = result["compose_neutralise"][0]
        self.assertTrue(entry["to"].endswith(".retired-" + retire.STAMP_PLACEHOLDER))
        self.assertEqual(entry["sha256"], "a" * 64)


class GuardTest(unittest.TestCase):
    def test_missing_declared_container_is_refused(self):
        observed = facts(containers=[
            container("sc-backend-odoo-dev-db-1", container_id="8b079962b8b0", declared=False),
        ])
        self.assertIn("declared_container_present", failing(plan(None, observed)))

    def test_mismatched_container_identity_is_refused(self):
        observed = facts(containers=[
            container("sc-backend-odoo-prod-db-1", container_id="000000000000", clients=[]),
            container("sc-backend-odoo-dev-db-1", container_id="8b079962b8b0", declared=False),
        ])
        self.assertIn("declared_container_identity_matches", failing(plan(None, observed)))

    def test_declared_stack_that_shares_no_volume_is_refused(self):
        observed = facts(
            postgres_owners={"sc_dev_db_data": ["sc-backend-odoo-dev-db-1"]},
            volume_owners={"sc_dev_db_data": ["sc-backend-odoo-dev-db-1"]},
        )
        self.assertIn("declared_stack_is_a_shared_writer", failing(plan(None, observed)))

    def test_retiring_the_newest_writer_is_refused(self):
        observed = facts(containers=[
            container("sc-backend-odoo-prod-db-1", started="2026-10-01 00:00:00", clients=[]),
            container("sc-backend-odoo-dev-db-1", container_id="8b079962b8b0", declared=False,
                      started="2026-09-24 08:28:55"),
        ])
        self.assertIn("declared_postgres_is_not_the_newest_writer", failing(plan(None, observed)))

    def test_a_retired_orphan_passes_the_newest_writer_guard(self):
        # Post-condition of the retirement: the declared postmaster is stopped, so it
        # is not a writer and no stop command is planned for it. The collector only
        # reads cluster facts from a running container, so a stopped one has none.
        retired = container("sc-backend-odoo-prod-db-1", running=False, clients=[])
        retired.pop("cluster_facts")
        observed = facts(containers=[
            retired,
            container("sc-backend-odoo-dev-db-1", container_id="8b079962b8b0", declared=False,
                      started="2026-09-24 08:28:55"),
        ])
        result = plan(None, observed)
        guard = next(row for row in result["guards"]
                     if row["id"] == "declared_postgres_is_not_the_newest_writer")
        self.assertTrue(guard["passed"], guard["detail"])
        self.assertTrue(guard["detail"]["declared_postgres_already_retired"])
        self.assertEqual(failing(result), [])
        self.assertEqual(steps(result), ["remove_automatic_restart_path"])

    def test_a_retired_orphan_with_an_unreported_survivor_is_refused(self):
        # "The orphan is stopped" must never be read from a survivor whose cluster
        # facts could not be read: that is an unreachable survivor, not a retirement.
        retired = container("sc-backend-odoo-prod-db-1", running=False, clients=[])
        retired.pop("cluster_facts")
        unreachable = container("sc-backend-odoo-dev-db-1", container_id="8b079962b8b0", declared=False)
        unreachable.pop("cluster_facts")
        observed = facts(containers=[retired, unreachable])
        guard = next(row for row in plan(None, observed)["guards"]
                     if row["id"] == "declared_postgres_is_not_the_newest_writer")
        self.assertFalse(guard["passed"])
        self.assertEqual(guard["detail"]["survivors_unreported"], ["sc-backend-odoo-dev-db-1"])

    def test_orphan_with_an_application_client_is_refused(self):
        observed = facts(containers=[
            container("sc-backend-odoo-prod-db-1", clients=[["sc_demo", "odoo", "192.168.32.4", "idle"]]),
            container("sc-backend-odoo-dev-db-1", container_id="8b079962b8b0", declared=False),
        ])
        self.assertIn("declared_container_has_no_application_consumer", failing(plan(None, observed)))

    def test_redis_orphan_with_a_consumer_is_refused(self):
        decl = declaration(container_id="2193b4da1469", kind="redis", volume="sc_dev_redis_data",
                           name="sc-backend-odoo-prod-redis-1")
        observed = facts(
            containers=[container("sc-backend-odoo-prod-redis-1", container_id="2193b4da1469",
                                  kind="redis", redis_consumers=["id=9 addr=172.18.0.9:51000 ... cmd=get"])],
            postgres_owners={},
            volume_owners={"sc_dev_redis_data": ["sc-backend-odoo-prod-redis-1", "sc-backend-odoo-dev-redis-1"]},
        )
        self.assertIn("declared_redis_has_no_application_consumer", failing(plan(decl, observed)))

    def test_a_running_idle_container_is_refused(self):
        decl = declaration(container_id="1e98ca9bb863", kind="idle", volume="sc_dev_odoo_data",
                           name="sc-backend-odoo-prod-odoo-1")
        observed = facts(
            containers=[container("sc-backend-odoo-prod-odoo-1", container_id="1e98ca9bb863", kind="idle")],
            postgres_owners={},
            volume_owners={"sc_dev_odoo_data": ["sc-backend-odoo-prod-odoo-1", "sc-backend-odoo-dev-odoo-1"]},
        )
        self.assertIn("declared_idle_container_is_not_running", failing(plan(decl, observed)))


class DeclarationTest(unittest.TestCase):
    def test_declaration_rejects_an_unknown_container_kind(self):
        with self.assertRaises(retire.RetireError):
            retire.load_declaration_from_text(json.dumps({
                "schema": "daily.runtime.retired_stacks.v1",
                "stacks": [{"compose_project": "p", "containers": [{"name": "n", "id": "x", "kind": "vm"}]}],
            }))

    def test_declaration_rejects_a_foreign_schema(self):
        with self.assertRaises(retire.RetireError):
            retire.load_declaration_from_text(json.dumps({"schema": "something.else", "stacks": []}))

    def test_repository_declaration_is_valid_and_covers_both_writers(self):
        declaration_path = retire.ROOT / retire.DEFAULT_DECLARATION
        loaded = retire.load_declaration(declaration_path)
        kinds = {row["kind"] for row in loaded["stacks"][0]["containers"]}
        self.assertEqual(kinds, {"postgres", "redis", "idle"})
        volumes = {row["shared_volume"] for row in loaded["stacks"][0]["containers"]}
        self.assertIn("sc_dev_db_data", volumes)
        self.assertIn("sc_dev_redis_data", volumes)


if __name__ == "__main__":
    unittest.main()
