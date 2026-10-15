"""Unit tests for the governed daily-runtime database duty entry.

The tests are pure: they never reach a host, never start a container and never
read a credential. They pin the properties the owner ruling of 2026-10-15
depends on:

* one cluster data directory has exactly one declared writer, and one duty never
  shares a name, a port, a route or a backup namespace with another;
* a duty that is declared ``to_be_created`` is created from the reviewed stack
  definition, and a duty that already exists is never rendered or restarted;
* the cluster bootstrap role and the application role are different roles, and
  the only accepted declared gap is the one that says they are still the same;
* every rendered environment value is read back and compared with the
  declaration, so the file on the host cannot describe another duty;
* the platform-admin binding is a frontend *build-time* value, so the entry
  reads the deployed build environment back instead of redeclaring it inside a
  duty environment file, where nothing would ever read it.
"""

import contextlib
import copy
import io
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from scripts.ops import daily_runtime_database_duty as duty_entry


ROOT = Path(__file__).resolve().parents[2]
DECLARATION = ROOT / "config/ops/daily_runtime_database_duties.v1.json"
ENV_TEMPLATE = ROOT / "config/ops/daily_runtime_duty_stack.env"
COMPOSE_FILE = ROOT / "config/ops/daily_runtime_duty_stack.yml"


def shipped():
    return json.loads(DECLARATION.read_text(encoding="utf-8"))


def picked(declaration, name):
    for row in declaration["duties"]:
        if row["duty"] == name:
            return row
    raise AssertionError(name)


def prospective(declaration, name):
    """One declared duty, still *not yet created*.

    The creation path must stay proven after the shipped declaration has been
    written back with the observed custody facts, so these tests ask for a duty
    that is still ``to_be_created`` instead of assuming the shipped file stays
    frozen in that state. A declaration that is ahead of its receipt is exactly
    what the write-back exists to prevent, and the pre-write shape is a decision
    input, not a property of the shipped file.
    """
    out = copy.deepcopy(declaration)
    row = picked(out, name)
    row["custody"] = {"database_present": False, "database_role_present": False,
                      "role_compliance": "to_be_created"}
    row["cluster"]["system_identifier"] = ""
    return out


def as_cluster_only(declaration, name, reason="reshaped into a cluster-only face for this test"):
    """One declared duty reshaped into a cluster-only face.

    The cluster-only rules must stay proven without depending on which duty the
    shipped declaration currently points at that face: once the customer duty
    moves on to a served face, a test that read the face off the file would stop
    testing the rule and start testing the file. A declaration that is ahead of
    its receipt is exactly what the write-back exists to prevent, so a test asks
    for the shape it wants.
    """
    out = copy.deepcopy(declaration)
    row = picked(out, name)
    row["custody"]["service_face"] = "cluster_only"
    row["custody"]["service_face_reason"] = reason
    row["stack"]["services"] = ["db"]
    row["stack"]["modules"] = []
    return out


class DeclarationTests(unittest.TestCase):
    def test_shipped_declaration_is_valid(self):
        declaration = shipped()
        self.assertEqual(declaration["schema"], duty_entry.SCHEMA)
        self.assertEqual(duty_entry.validate_declaration(declaration), [])

    def test_duty_selection_rejects_an_undeclared_duty(self):
        declaration = shipped()
        self.assertEqual(len(duty_entry.declared_duties(declaration, ["demo"])), 1)
        self.assertEqual(len(duty_entry.declared_duties(declaration, [])), 3)
        with self.assertRaises(duty_entry.DutyError):
            duty_entry.declared_duties(declaration, ["production"])

    def test_duplicated_duty_name_fails(self):
        declaration = shipped()
        declaration["duties"].append(copy.deepcopy(declaration["duties"][0]))
        with self.assertRaises(duty_entry.DutyError):
            duty_entry.declared_duties(declaration, [])

    def test_application_role_may_not_be_the_bootstrap_role(self):
        declaration = shipped()
        row = picked(declaration, "customer_tenant_dev")
        row["cluster"]["maintenance_role"] = row["database_role"]
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("bootstrap role and the application role must differ" in f for f in failures))

    def test_to_be_created_role_must_follow_the_naming_convention(self):
        declaration = shipped()
        picked(declaration, "platform_control")["database_role"] = "sc_platform_control"
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("breaks the naming convention" in f for f in failures))

    def test_declared_gap_must_name_its_kind(self):
        declaration = shipped()
        custody = picked(declaration, "demo")["custody"]
        custody.pop("gap_kind")
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("gap_kind=shared_bootstrap_role" in f for f in failures))

    def test_declared_gap_that_is_closed_is_stale(self):
        declaration = shipped()
        row = picked(declaration, "demo")
        row["database_role"] = "sc_demo_app"
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("otherwise the gap is closed" in f for f in failures))

    def test_declared_gap_needs_a_reason_and_an_owner(self):
        declaration = shipped()
        custody = picked(declaration, "demo")["custody"]
        custody["gap_owner_task"] = ""
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("a declared gap needs gap_owner_task" in f for f in failures))

    def test_two_duties_may_not_share_one_data_volume(self):
        declaration = shipped()
        picked(declaration, "customer_tenant_dev")["cluster"]["data_volume"] = "sc_dev_db_data"
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("one data directory has one writer" in f for f in failures))

    def test_two_duties_may_not_share_a_route_or_a_namespace(self):
        declaration = shipped()
        row = picked(declaration, "customer_tenant_dev")
        row["routing"]["nginx_host_port"] = 18081
        row["storage"]["backup_namespace"] = "/data/backups/daily_candidate"
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("share nginx_host_port=18081" in f for f in failures))
        self.assertTrue(any("share backup_namespace=" in f for f in failures))

    def test_dbfilter_must_be_the_exact_anchored_filter(self):
        declaration = shipped()
        picked(declaration, "platform_control")["dbfilter"] = "^sc_platform.*$"
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("exact anchored filter" in f for f in failures))

    def test_database_enumeration_must_stay_closed(self):
        declaration = shipped()
        picked(declaration, "platform_control")["routing"]["list_db"] = True
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("database enumeration closed" in f for f in failures))

    def test_filestore_scope_must_follow_its_database(self):
        declaration = shipped()
        picked(declaration, "customer_tenant_dev")["storage"]["filestore_scope"] = "sc_demo"
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("one database has one filestore" in f for f in failures))

    def test_incomplete_stack_declaration_fails(self):
        declaration = shipped()
        stack = picked(declaration, "platform_control")["stack"]
        stack.pop("customer_addons_root")
        stack["compose_file"] = "/etc/docker-compose.yml"
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("stack is incomplete" in f for f in failures))
        self.assertEqual(
            [f for f in failures if "must be a repository-relative path" in f], []
        )

    def test_stack_paths_must_be_absolute_and_relative_where_declared(self):
        declaration = shipped()
        stack = picked(declaration, "platform_control")["stack"]
        stack["compose_file"] = "/etc/docker-compose.yml"
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("must be a repository-relative path" in f for f in failures))

    def test_stack_runtime_env_must_not_be_production(self):
        declaration = shipped()
        picked(declaration, "platform_control")["stack"]["runtime_env"] = "prod"
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("non-production runtime env" in f for f in failures))

    def test_platform_admin_database_must_follow_the_naming_convention(self):
        declaration = shipped()
        declaration["platform_admin_database"] = "platform-core"
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("platform_admin_database" in f for f in failures))

    def test_ops_root_must_be_absolute(self):
        declaration = shipped()
        declaration["ops_root"] = "relative/ops"
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("ops_root must be one absolute directory path" in f for f in failures))

    def test_frontend_build_env_file_must_be_absolute(self):
        declaration = shipped()
        declaration["frontend_build_env_file"] = ".env.dev"
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(
            any("frontend_build_env_file must be one absolute file path" in f for f in failures)
        )

    def test_frontend_build_env_file_is_required(self):
        declaration = shipped()
        declaration.pop("frontend_build_env_file")
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(
            any("frontend_build_env_file must be one absolute file path" in f for f in failures)
        )

    def test_section_11_flags_must_agree_with_the_purpose(self):
        declaration = shipped()
        picked(declaration, "platform_control")["section_11"]["IS_PLATFORM_CONTROL_DATABASE"] = False
        picked(declaration, "customer_tenant_dev")["section_11"]["CUSTOMER_BUSINESS_DATA_ALLOWED"] = False
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("platform-control flag contradicts" in f for f in failures))
        self.assertTrue(any("customer business data must follow" in f for f in failures))

    def test_platform_control_duty_may_not_carry_fixture_or_tenant_data(self):
        declaration = shipped()
        table = picked(declaration, "platform_control")["section_11"]
        table["FIXTURE_ALLOWED"] = True
        picked(declaration, "platform_control")["tenant_key"] = "sc-demo-main"
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("never carries fixture data" in f for f in failures))
        self.assertTrue(any("not a tenant data space" in f for f in failures))

    def test_production_environment_id_is_refused(self):
        declaration = shipped()
        row = picked(declaration, "platform_control")
        row["environment_id"] = "production-platform-control"
        row["section_11"]["TARGET_ENVIRONMENT_ID"] = "production-platform-control"
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("not authorized to build a production environment" in f for f in failures))

    def test_a_platform_control_face_must_install_the_kernel(self):
        declaration = shipped()
        picked(declaration, "platform_control")["stack"]["modules"] = []
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(
            any("must declare %s" % (duty_entry.CONTROL_MINIMUM_MODULE,) in row for row in failures),
            failures,
        )

    def test_a_platform_control_face_may_not_install_the_industry_line(self):
        declaration = shipped()
        picked(declaration, "platform_control")["stack"]["modules"] = [
            "smart_core", "smart_construction_core",
        ]
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(
            any("industry product line" in row for row in failures), failures
        )

    def test_a_cluster_only_face_declares_exactly_its_cluster(self):
        declaration = as_cluster_only(shipped(), "customer_tenant_dev")
        row = picked(declaration, "customer_tenant_dev")
        self.assertEqual(row["custody"]["service_face"], "cluster_only")
        row["stack"]["services"] = ["db", "odoo"]
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("cluster_only face declares exactly" in r for r in failures), failures)

    def test_a_cluster_only_face_must_say_why(self):
        declaration = as_cluster_only(shipped(), "customer_tenant_dev")
        picked(declaration, "customer_tenant_dev")["custody"].pop("service_face_reason", None)
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("service_face_reason" in row for row in failures), failures)

    def test_a_served_face_must_declare_the_application_service(self):
        declaration = shipped()
        picked(declaration, "platform_control")["stack"]["services"] = ["db", "redis"]
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("must declare the odoo service" in row for row in failures), failures)

    def test_a_served_face_needs_its_database_declared_present(self):
        declaration = shipped()
        picked(declaration, "platform_control")["custody"]["database_present"] = False
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(
            any("needs its database present first" in row for row in failures), failures
        )

    def test_every_duty_declares_the_cluster_and_only_known_services(self):
        declaration = shipped()
        picked(declaration, "demo")["stack"]["services"] = ["db", "worker"]
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("undeclared services" in row for row in failures), failures)

        declaration = shipped()
        picked(declaration, "demo")["stack"]["services"] = ["redis"]
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("must include the duty cluster" in row for row in failures), failures)

    def test_a_missing_module_list_is_not_an_empty_module_list(self):
        declaration = shipped()
        picked(declaration, "customer_tenant_dev")["stack"].pop("modules")
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("missing modules" in row for row in failures), failures)
        # An intentionally empty list is a decision, and stays valid.
        self.assertEqual(duty_entry.validate_declaration(shipped()), [])

    def test_a_module_name_must_be_a_module_name(self):
        declaration = shipped()
        picked(declaration, "platform_control")["stack"]["modules"] = ["Smart-Core"]
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("invalid modules" in row for row in failures), failures)

    def test_a_duty_with_a_recorded_cluster_identity_is_never_still_to_be_created(self):
        # Once a duty exists its observed custody is written back into the
        # declaration. A declaration that still says ``to_be_created`` while the
        # cluster identity is already recorded is stale in the dangerous
        # direction: the next ``--apply`` would try to create a duty that is
        # already serving, and the read-only plan would report the world as
        # disagreeing with a declaration nobody updated.
        for row in shipped()["duties"]:
            if row["cluster"].get("system_identifier"):
                self.assertNotEqual(
                    row["custody"]["role_compliance"], "to_be_created", row["duty"]
                )

    def test_a_compliant_duty_declares_its_custody_as_present(self):
        for row in shipped()["duties"]:
            if row["custody"]["role_compliance"] == "compliant":
                self.assertTrue(row["custody"]["database_present"], row["duty"])
                self.assertTrue(row["custody"]["database_role_present"], row["duty"])

    def test_shipped_stack_surface_resolves(self):
        failures, _ = duty_entry.validate_stack_surface(
            COMPOSE_FILE.read_text(encoding="utf-8"), ENV_TEMPLATE.read_text(encoding="utf-8")
        )
        self.assertEqual(failures, [])

    def test_stack_surface_refuses_an_unresolved_compose_variable(self):
        template = ENV_TEMPLATE.read_text(encoding="utf-8")
        failures, unused = duty_entry.validate_stack_surface(
            "services:\n  db:\n    image: ${NOT_DECLARED_ANYWHERE}\n", template
        )
        self.assertTrue(any("NOT_DECLARED_ANYWHERE" in f for f in failures))
        self.assertTrue(unused)

    def test_every_readback_key_is_declared_by_the_template(self):
        import re as re_module

        template = ENV_TEMPLATE.read_text(encoding="utf-8")
        for key in duty_entry.ENV_READBACK_KEYS:
            self.assertRegex(
                template, r"(?m)^%s=" % re_module.escape(key),
                "the env template must declare %s for the readback" % key,
            )

    def test_the_build_time_admin_binding_is_not_a_duty_environment_key(self):
        """``VITE_PLATFORM_ADMIN_DB`` is read by the frontend build, not by the
        duty nginx, odoo or the browser.

        Rendering it into the duty environment would create a second, unread
        copy of the platform-admin authority that can disagree with the bundle
        users actually load. The entry reads the deployed build environment back
        instead, so neither the template nor the readback may declare it.
        """
        template = ENV_TEMPLATE.read_text(encoding="utf-8")
        self.assertNotIn("VITE_PLATFORM_ADMIN_DB", template)
        self.assertNotIn("PLATFORM_ADMIN_DB", template)
        self.assertNotIn("VITE_PLATFORM_ADMIN_DB", duty_entry.ENV_READBACK_KEYS)
        self.assertNotIn("PLATFORM_ADMIN_DB", duty_entry.ENV_READBACK_KEYS)
        self.assertNotIn(
            "PLATFORM_ADMIN_DB", COMPOSE_FILE.read_text(encoding="utf-8")
        )


class RemoteProgramTests(unittest.TestCase):
    """The remote carrier is the one part of this entry that cannot be tested
    against a host, so its embedding is pinned instead.

    The first host run of this entry failed because the payload was substituted
    as a bare object into ``json.loads(...)``, and the custody readback reported
    "absent" for a database that was present because ``-Atc`` made psql consume
    the following ``-F`` and the statement as extra arguments. Both defects are
    silent in production, so they are asserted here.
    """

    def payload(self):
        return {
            "mode": "plan", "phase": "plan", "product_root": "/opt/projects/repos/sce-product-odoo",
            "ops_root": "/opt/projects/secure/daily-runtime-duties",
            "platform_admin_database": "sc_platform_control", "source_revision": "a" * 40,
            "frontend_build_env_file": "/opt/projects/repos/sce-product-odoo/.env.dev",
            "compose_sha256": "b" * 64,
            "stack": {"compose_text": "services:\n  db:\n    image: ${POSTGRES_IMAGE:-postgres:15}\n"},
            "env_template": "DB_NAME=@DB_NAME@\nLIST_DB=false\n",
            "data_destination": "/var/lib/postgresql/data",
            "duties": [{"duty": "platform_control", "custody": {"database_present": False},
                        "cluster": {"maintenance_role": "sc_platform_control_maintenance"}}],
        }

    def rendered(self):
        return duty_entry.render_remote_program(self.payload())

    def test_the_rendered_program_is_valid_python(self):
        compile(self.rendered(), "<remote>", "exec")

    def test_no_embedding_marker_survives_rendering(self):
        rendered = self.rendered()
        for marker in ("__MARKER__", "__PSQL_READBACK__", "__PAYLOAD_JSON__"):
            self.assertNotIn(marker, rendered)

    def test_a_payload_with_booleans_and_newlines_round_trips(self):
        rendered = self.rendered()
        literal = rendered.split("PAYLOAD = json.loads(", 1)[1].split("\n", 1)[0].rstrip(")")
        self.assertEqual(json.loads(json.loads(literal)), self.payload())

    def test_the_cluster_readback_avoids_a_combined_option_cluster(self):
        self.assertNotIn("-Atc", duty_entry.PSQL_READBACK)
        self.assertTrue(
            any(item.startswith("--field-separator=") for item in duty_entry.PSQL_READBACK),
            "the readback must name its separator explicitly",
        )
        self.assertFalse([item for item in duty_entry.PSQL_READBACK if item in ("-A", "-t", "-c", "-F")])

    def test_the_remote_carrier_uses_the_shared_readback_vector(self):
        self.assertIn(
            "PSQL_READBACK = %s" % (json.dumps(list(duty_entry.PSQL_READBACK)),), self.rendered()
        )

    def test_the_carrier_refuses_to_initialize_an_undeclared_face(self):
        rendered = self.rendered()
        self.assertIn("does not say service_face=to_be_initialized", rendered)
        self.assertIn("never brings up or installs into a duty nobody declared", rendered)

    def test_the_carrier_installs_the_declared_set_without_demo_data(self):
        rendered = self.rendered()
        self.assertIn("--without-demo=all", rendered)
        self.assertIn('"-i", ",".join(modules)', rendered)
        self.assertIn("--stop-after-init", rendered)
        self.assertIn('duty["stack"]["modules"]', rendered)

    def test_initialize_is_a_declared_phase_and_face(self):
        self.assertIn("initialize", duty_entry.PHASES)
        self.assertIn("to_be_initialized", duty_entry.SERVICE_FACES)
        self.assertIn("initialized", duty_entry.SERVICE_FACES)
        self.assertIn("cluster_only", duty_entry.SERVICE_FACES)

    def test_the_carrier_waits_for_the_container_bootstrap_before_installing(self):
        """The 2026-10-15 defect was two initializers in one fresh database.

        The container installs ``base`` itself, so the declared set may only be
        installed after that attempt is over. This pins the order, not just the
        presence of a wait: a wait that runs after the install would still leave
        the collision in place.
        """
        rendered = self.rendered()
        self.assertIn('entry["bootstrap"] = await_base_bootstrap(duty)', rendered)
        self.assertLess(
            rendered.index('entry["stack"]["start"] = start_services(duty)'),
            rendered.index('entry["bootstrap"] = await_base_bootstrap(duty)'),
        )
        self.assertLess(
            rendered.index('entry["bootstrap"] = await_base_bootstrap(duty)'),
            rendered.index('entry["initialize"] = install_modules(duty)'),
        )
        self.assertIn("await_base_bootstrap(duty)", rendered)
        self.assertIn("def base_readback(duty)", rendered)
        self.assertIn("def entrypoint_startup_facts(duty, container)", rendered)

    def test_the_carrier_refuses_to_become_a_second_initializer(self):
        rendered = self.rendered()
        # Read the carrier's own text rather than one source line: the refusal is
        # written as adjacent string literals and wraps.
        self.assertIn("refusing to install", rendered)
        self.assertIn("while the application's own bootstrap owns this database", rendered)
        self.assertIn("refusing to start a second initializer in the same database", rendered)
        self.assertIn('BASE_MODULE = "base"', rendered)

    def test_the_startup_facts_judge_only_the_current_startup(self):
        """A restart must not be read as a finished attempt.

        ``docker logs`` keeps every startup of one container, so the carrier has
        to scope its reading to the statements after the current entrypoint
        render line; otherwise the retry would be refused as a second failure.
        """
        rendered = self.rendered()
        self.assertIn("ENTRYPOINT_RENDER_MARKER", rendered)
        self.assertIn("text.rfind(ENTRYPOINT_RENDER_MARKER)", rendered)

    def test_the_bootstrap_plan_is_injected_once_from_the_shared_source(self):
        rendered = self.rendered()
        self.assertEqual(rendered.count("def base_bootstrap_plan("), 1)


class BootstrapOrderTests(unittest.TestCase):
    """The pure decision table behind the single-initializer wait."""

    def setUp(self):
        self.plan = duty_entry.base_bootstrap_plan

    def test_installed_base_is_ready(self):
        self.assertEqual(self.plan(True, False, 0), "ready")
        self.assertEqual(self.plan(True, True, 1), "ready")

    def test_an_in_flight_attempt_is_waited_for(self):
        self.assertEqual(self.plan(False, False, 0), "wait")
        self.assertEqual(self.plan(False, False, 1), "wait")

    def test_a_finished_attempt_without_base_is_restarted_once(self):
        self.assertEqual(self.plan(False, True, 0), "restart")

    def test_a_second_finished_failure_is_reported_not_looped(self):
        self.assertEqual(self.plan(False, True, 1), "give_up")
        self.assertEqual(self.plan(False, True, 5), "give_up")


class EvaluationTests(unittest.TestCase):
    def declaration(self):
        return shipped()

    def observe(self, duty, **overrides):
        cluster = {"present": False, "running": False, "system_identifier": "",
                   "data_volume_owner": "", "project": "", "config_files": "", "error": ""}
        custody = {"database_present": False, "database_owner": "", "allow_connections": None,
                   "role_present": False, "role_superuser": None, "role_createdb": None,
                   "role_createrole": None, "role_canlogin": None, "public_connects": None,
                   "public_schema_create": None, "database_role_connects": None, "error": "cluster container is not running"}
        observation = {"duty": duty["duty"], "cluster": cluster, "custody": custody,
                       "stack": None, "create": None}
        observation.update(overrides)
        return observation

    def verdict(self, declaration, name, phase="plan", **overrides):
        duty = picked(declaration, name)
        assertions = duty_entry.evaluate(
            duty, self.observe(duty, **overrides), declaration, phase=phase
        )
        return {row["id"]: row["passed"] for row in assertions}

    def created(self):
        """A duty the entry has just created, observed as it really is."""
        return {
            "cluster": {"present": True, "running": True,
                        "system_identifier": "111", "data_volume_owner": "sc_platform_control_db_data",
                        "project": "sc-platform-control-dev", "config_files": "/opt/x/duty-stack.yml",
                        "error": ""},
            "custody": {"database_present": True, "database_owner": "sc_platform_control_app",
                        "allow_connections": True, "role_present": True, "role_superuser": False,
                        "role_createdb": False, "role_createrole": False, "role_canlogin": True,
                        "public_connects": False, "public_schema_create": True, "database_role_connects": True, "error": ""},
        }

    def test_a_created_duty_passes_the_apply_phase(self):
        declaration = prospective(self.declaration(), "platform_control")
        verdict = self.verdict(declaration, "platform_control", phase="apply", **self.created())
        self.assertTrue(verdict["created_database_is_present"])
        self.assertTrue(verdict["created_role_is_present"])
        self.assertTrue(verdict["application_role_is_least_privilege"])
        self.assertTrue(verdict["application_role_owns_its_database"])
        self.assertTrue(verdict["public_cannot_connect"])
        self.assertTrue(verdict["application_role_can_connect"])
        self.assertTrue(verdict["database_accepts_the_declared_duty"])

    def test_the_same_observation_fails_the_plan_phase_as_a_stale_declaration(self):
        declaration = prospective(self.declaration(), "platform_control")
        verdict = self.verdict(declaration, "platform_control", **self.created())
        self.assertFalse(verdict["custody_database_presence_matches_declaration"])
        self.assertFalse(verdict["custody_role_presence_matches_declaration"])

    def test_a_created_duty_that_is_not_least_privilege_fails_the_apply_phase(self):
        declaration = prospective(self.declaration(), "platform_control")
        observation = self.created()
        observation["custody"]["role_superuser"] = True
        verdict = self.verdict(declaration, "platform_control", phase="apply", **observation)
        self.assertFalse(verdict["application_role_is_least_privilege"])

    def test_a_created_duty_whose_database_still_denies_connections_fails(self):
        declaration = prospective(self.declaration(), "platform_control")
        observation = self.created()
        observation["custody"]["allow_connections"] = False
        verdict = self.verdict(declaration, "platform_control", phase="apply", **observation)
        self.assertFalse(verdict["database_accepts_the_declared_duty"])

    def test_a_missing_cluster_matches_a_to_be_created_declaration(self):
        declaration = prospective(self.declaration(), "platform_control")
        verdict = self.verdict(declaration, "platform_control")
        self.assertTrue(verdict["cluster_container_state_matches_declaration"])
        self.assertTrue(verdict["custody_absent_as_declared"])

    def test_an_unexpectedly_present_cluster_fails(self):
        declaration = prospective(self.declaration(), "platform_control")
        cluster = {"present": True, "running": True, "system_identifier": "",
                   "data_volume_owner": "sc_platform_control_db_data",
                   "project": "sc-platform-control-dev", "config_files": "", "error": ""}
        verdict = self.verdict(declaration, "platform_control", cluster=cluster)
        self.assertFalse(verdict["cluster_container_state_matches_declaration"])

    def test_a_cluster_catalog_read_failure_is_reported(self):
        declaration = self.declaration()
        cluster = {"present": True, "running": True, "system_identifier": "",
                   "data_volume_owner": "sc_dev_db_data", "project": "sc-backend-odoo-dev",
                   "config_files": "", "error": "FATAL: role does not exist"}
        verdict = self.verdict(declaration, "demo", cluster=cluster)
        self.assertFalse(verdict["cluster_catalog_is_readable_by_the_declared_maintenance_role"])

    def test_a_declared_duty_is_never_rendered_or_restarted(self):
        declaration = self.declaration()
        verdict = self.verdict(declaration, "demo", stack={"skipped": "not to-be-created"})
        self.assertNotIn("stack_definition_is_the_reviewed_one", verdict)
        row = picked(prospective(declaration, "platform_control"), "platform_control")
        assertions = duty_entry.evaluate(
            row, self.observe(row, stack={"skipped": "not to-be-created"}), declaration
        )
        identifiers = {a["id"]: a["passed"] for a in assertions}
        self.assertFalse(identifiers["stack_definition_is_the_reviewed_one"])

    def test_a_rendered_stack_must_match_the_declaration(self):
        declaration = prospective(self.declaration(), "platform_control")
        row = picked(declaration, "platform_control")
        stack = {
            "skipped": None, "compose_path": "/ops/duty-stack-abc.yml",
            "env_mode": "0o600", "credentials_mode": "0o600",
            "unresolved_placeholders": [],
            "start": {"returncode": 0, "error": ""},
            "env_keys": {
                "DUTY_NAME": row["duty"],
                "COMPOSE_PROJECT_NAME": row["cluster"]["compose_project"],
                "DB_NAME": row["database"],
                "DB_USER": row["database_role"],
                "DB_MAINTENANCE_USER": row["cluster"]["maintenance_role"],
                "DB_DATA": row["cluster"]["data_volume"],
                "REDIS_DATA": row["storage"]["redis_data_volume"],
                "ODOO_DATA": row["storage"]["odoo_data_volume"],
                "ODOO_DBFILTER": row["dbfilter"],
                "ODOO_PORT": str(row["routing"]["odoo_loopback_port"]),
                "NGINX_PORT": str(row["routing"]["nginx_host_port"]),
                "LIST_DB": "false",
            },
        }
        cluster = {"present": True, "running": True, "system_identifier": "",
                   "data_volume_owner": "sc_platform_control_db_data",
                   "project": "sc-platform-control-dev",
                   "config_files": "/ops/duty-stack-abc.yml", "error": ""}
        custody = {"database_present": False, "database_owner": "", "allow_connections": True,
                   "role_present": False, "role_superuser": None, "role_createdb": None,
                   "role_createrole": None, "role_canlogin": None, "public_connects": None,
                   "public_schema_create": None, "database_role_connects": None, "error": ""}
        verdict = {a["id"]: a["passed"] for a in duty_entry.evaluate(
            row, {"duty": row["duty"], "cluster": cluster, "custody": custody,
                  "stack": stack},
            declaration)}
        self.assertTrue(verdict["stack_environment_matches_declaration"])
        self.assertTrue(verdict["stack_was_created_from_the_reviewed_definition"])

        drifted = copy.deepcopy(stack)
        drifted["env_keys"]["DB_NAME"] = "sc_demo"
        drifted["unresolved_placeholders"] = ["@DB_NAME@"]
        drifted["env_mode"] = "0o644"
        drifted["start"] = {"returncode": 1, "error": "boom"}
        verdict = {a["id"]: a["passed"] for a in duty_entry.evaluate(
            row, {"duty": row["duty"], "cluster": cluster, "custody": custody,
                  "stack": drifted},
            declaration)}
        self.assertFalse(verdict["stack_environment_matches_declaration"])
        self.assertFalse(verdict["stack_environment_has_no_unresolved_placeholder"])
        self.assertFalse(verdict["stack_secret_material_is_not_world_readable"])
        self.assertFalse(verdict["stack_was_created_from_the_reviewed_definition"])

    def test_a_compliant_duty_must_show_least_privilege(self):
        declaration = self.declaration()
        row = picked(declaration, "customer_tenant_dev")
        row["custody"].update({"database_present": True, "database_role_present": True,
                               "role_compliance": "compliant"})
        row["custody"].pop("gap_reason", None)
        row["custody"].pop("gap_owner_task", None)
        row["custody"].pop("gap_kind", None)
        cluster = {"present": True, "running": True, "system_identifier": "", "error": "",
                   "data_volume_owner": "sc_tenant_baosheng_dev_db_data",
                   "project": "sc-tenant-baosheng-dev", "config_files": ""}
        custody = {"database_present": True, "database_owner": "sc_tenant_baosheng_dev_app",
                   "allow_connections": True, "role_present": True, "role_superuser": True,
                   "role_createdb": False, "role_createrole": False, "role_canlogin": True,
                   "public_connects": False, "public_schema_create": True, "database_role_connects": True, "error": ""}
        verdict = {a["id"]: a["passed"] for a in duty_entry.evaluate(
            row, {"duty": row["duty"], "cluster": cluster, "custody": custody, "stack": None},
            declaration)}
        self.assertFalse(verdict["application_role_is_least_privilege"])
        custody["role_superuser"] = False
        verdict = {a["id"]: a["passed"] for a in duty_entry.evaluate(
            row, {"duty": row["duty"], "cluster": cluster, "custody": custody, "stack": None},
            declaration)}
        self.assertTrue(verdict["application_role_is_least_privilege"])
        self.assertTrue(verdict["application_role_owns_its_database"])
        self.assertTrue(verdict["public_cannot_connect"])

    def test_a_closed_declared_gap_is_detected(self):
        declaration = self.declaration()
        cluster = {"present": True, "running": True, "system_identifier": "7597381856873586726",
                   "data_volume_owner": "sc_dev_db_data", "project": "sc-backend-odoo-dev",
                   "config_files": "", "error": ""}
        custody = {"database_present": True, "database_owner": "odoo", "allow_connections": True,
                   "role_present": True, "role_superuser": False, "role_createdb": False,
                   "role_createrole": False, "role_canlogin": True, "public_connects": True,
                   "public_schema_create": True, "database_role_connects": True, "error": ""}
        verdict = {a["id"]: a["passed"] for a in duty_entry.evaluate(
            picked(declaration, "demo"),
            {"duty": "demo", "cluster": cluster, "custody": custody, "stack": None}, declaration)}
        self.assertFalse(verdict["declared_gap_is_still_open"])

    def test_a_cut_off_database_does_not_accept_its_duty(self):
        declaration = self.declaration()
        picked(declaration, "platform_control")["custody"].update(
            {"database_present": True, "database_role_present": False})
        cluster = {"present": True, "running": True, "system_identifier": "", "error": "",
                   "data_volume_owner": "sc_platform_control_db_data",
                   "project": "sc-platform-control-dev", "config_files": ""}
        custody = {"database_present": True, "database_owner": "sc_platform_control_app",
                   "allow_connections": False, "role_present": False, "role_superuser": None,
                   "role_createdb": None, "role_createrole": None, "role_canlogin": None,
                   "public_connects": None, "public_schema_create": None, "database_role_connects": None, "error": ""}
        verdict = {a["id"]: a["passed"] for a in duty_entry.evaluate(
            picked(declaration, "platform_control"),
            {"duty": "platform_control", "cluster": cluster, "custody": custody, "stack": None},
            declaration)}
        self.assertFalse(verdict["database_accepts_the_declared_duty"])


class ServiceFaceTests(unittest.TestCase):
    """The declared service face must be provable, not assumed.

    ``service_face`` is what keeps a stopped application from reading as a
    finished build, and what keeps the entry from bringing up an application
    nobody declared.
    """

    def declaration(self):
        return shipped()

    def observe(self, duty, face_overrides=None, **overrides):
        service = service_matching(duty)
        if face_overrides:
            service.update(face_overrides)
        cluster = {"present": True, "running": True, "system_identifier": "",
                   "data_volume_owner": duty["cluster"]["data_volume"],
                   "project": duty["cluster"]["compose_project"], "config_files": "", "error": ""}
        custody = {"database_present": True, "database_owner": duty["database_role"],
                   "allow_connections": True, "role_present": True, "role_superuser": False,
                   "role_createdb": False, "role_createrole": False, "role_canlogin": True,
                   "public_connects": False, "public_schema_create": True, "database_role_connects": True, "error": ""}
        observation = {"duty": duty["duty"], "cluster": cluster, "custody": custody,
                       "stack": None, "service": service}
        observation.update(overrides)
        return observation

    def verdict(self, duty, *, phase="plan", initialize=False, **kwargs):
        assertions = duty_entry.evaluate(
            duty, self.observe(duty, **kwargs), self.declaration(),
            phase=phase, initialize=initialize,
        )
        return {row["id"]: row["passed"] for row in assertions}

    def initialized(self, declaration, name):
        row = copy.deepcopy(picked(declaration, name))
        row["custody"]["service_face"] = "initialized"
        return row

    def test_a_served_duty_must_show_its_services_running(self):
        row = self.initialized(self.declaration(), "platform_control")
        verdict = self.verdict(row)
        self.assertTrue(verdict["declared_services_are_running"])
        self.assertTrue(verdict["declared_modules_are_installed"])
        self.assertTrue(verdict["no_undeclared_service_is_running"])

        verdict = self.verdict(row, face_overrides={"running_services": ["db"]})
        self.assertFalse(verdict["declared_services_are_running"])
        self.assertTrue(verdict["no_undeclared_service_is_running"])

    def test_a_served_duty_must_show_its_declared_modules_installed(self):
        row = self.initialized(self.declaration(), "platform_control")
        verdict = self.verdict(row, face_overrides={"module_states": {}})
        self.assertFalse(verdict["declared_modules_are_installed"])

    def test_an_undeclared_service_on_a_served_duty_is_refused(self):
        row = self.initialized(self.declaration(), "platform_control")
        verdict = self.verdict(row, face_overrides={
            "running_services": sorted(set(row["stack"]["services"]) | {"worker"}),
        })
        self.assertFalse(verdict["no_undeclared_service_is_running"])

    def test_a_control_plane_that_installed_the_industry_line_is_refused(self):
        row = self.initialized(self.declaration(), "platform_control")
        verdict = self.verdict(row, face_overrides={
            "installed_industry_modules": ["smart_construction_core"],
        })
        self.assertFalse(verdict["platform_control_face_carries_no_industry_module"])

    def test_a_cluster_only_duty_that_runs_an_application_is_refused(self):
        row = picked(as_cluster_only(self.declaration(), "customer_tenant_dev"),
                     "customer_tenant_dev")
        self.assertTrue(self.verdict(row)["cluster_only_face_declares_only_the_cluster"])
        verdict = self.verdict(row, face_overrides={"running_services": ["db", "odoo"]})
        self.assertFalse(verdict["cluster_only_face_declares_only_the_cluster"])

    def test_a_declaration_that_is_already_initialized_fails_the_read_only_plan(self):
        """The write-back is the only thing that makes an initialized face a declaration.

        The shipped duty has been written back, so the stale shape is rebuilt
        here on purpose: a declaration that still says ``to_be_initialized``
        while the world is already initialized must fail the read-only plan, or
        the next initialize would bring up a face that is already up.
        """
        row = picked(self.declaration(), "platform_control")
        self.assertEqual(row["custody"]["service_face"], "initialized")
        stale = copy.deepcopy(row)
        stale["custody"]["service_face"] = "to_be_initialized"
        self.assertTrue(
            self.verdict(stale)["service_face_is_not_initialized_before_the_write_back"]
        )
        assertions = duty_entry.evaluate(
            stale, self.observe(row), self.declaration(), phase="plan"
        )
        verdict = {item["id"]: item["passed"] for item in assertions}
        self.assertFalse(verdict["service_face_is_not_initialized_before_the_write_back"])

    def test_the_initialize_phase_is_judged_against_the_target_face(self):
        row = picked(self.declaration(), "platform_control")
        stale = copy.deepcopy(row)
        stale["custody"]["service_face"] = "to_be_initialized"
        target = service_matching(self.initialized(self.declaration(), "platform_control"))

        # A read-only plan of the same world would be a stale declaration...
        plan = {item["id"]: item["passed"] for item in duty_entry.evaluate(
            stale, self.observe(stale, face_overrides=target), self.declaration(), phase="plan",
        )}
        self.assertIn("service_face_is_not_initialized_before_the_write_back", plan)

        # ...but as the target of the initialize run it is the expected shape.
        initialized = {item["id"]: item["passed"] for item in duty_entry.evaluate(
            stale, self.observe(stale, face_overrides=target), self.declaration(),
            phase="apply", initialize=True,
        )}
        self.assertTrue(initialized["declared_services_are_running"])
        self.assertTrue(initialized["declared_modules_are_installed"])
        self.assertNotIn("service_face_is_not_initialized_before_the_write_back", initialized)

    def test_an_initialize_run_does_not_excuse_a_missing_face(self):
        row = picked(self.declaration(), "platform_control")
        verdict = {item["id"]: item["passed"] for item in duty_entry.evaluate(
            row, self.observe(row, face_overrides={"running_services": ["db"], "module_states": {}}),
            self.declaration(), phase="apply", initialize=True,
        )}
        self.assertFalse(verdict["declared_services_are_running"])
        self.assertFalse(verdict["declared_modules_are_installed"])

    def test_an_application_face_that_cannot_create_its_own_schema_fails_closed(self):
        """The defect that the first host run of ``--phase initialize`` exposed.

        The duty's database was present, owned by the declared role, connectable
        and least-privilege -- and its application could still not create a table
        in ``public``. Every other custody fact said "healthy", so the entry must
        carry the one fact that distinguishes "created" from "usable".
        """
        declaration = self.declaration()
        duty = picked(declaration, "platform_control")
        observation = self.observe(duty)
        observation["custody"]["public_schema_create"] = False
        verdict = {row["id"]: row["passed"] for row in duty_entry.evaluate(
            duty, observation, declaration)}
        self.assertFalse(verdict["application_role_can_create_in_its_public_schema"])

    def test_a_cluster_only_face_is_not_asked_for_an_application_schema(self):
        declaration = self.declaration()
        duty = picked(as_cluster_only(declaration, "customer_tenant_dev"),
                      "customer_tenant_dev")
        observation = self.observe(duty)
        observation["custody"]["public_schema_create"] = False
        verdict = {row["id"]: row["passed"] for row in duty_entry.evaluate(
            duty, observation, declaration)}
        self.assertNotIn("application_role_can_create_in_its_public_schema", verdict)


def build_fact(declaration, **overrides):
    """The deployed frontend build environment the declaration expects."""
    fact = {
        "path": declaration.get("frontend_build_env_file"),
        "present": True,
        "sha256": "d" * 64,
        "platform_admin_db": declaration.get("platform_admin_database"),
        "error": "",
    }
    fact.update(overrides)
    return fact


class DeploymentBindingTests(unittest.TestCase):
    """The platform-admin binding is one deployment-wide fact.

    ``VITE_PLATFORM_ADMIN_DB`` is baked into the served bundle when the frontend
    build runs, so one file governs every duty on this host. It is judged on its
    own so a duty that was created exactly as declared is never reported as a
    failed creation because the explicitly sequenced switch has not happened yet.
    """

    def test_the_deployed_build_must_name_the_declared_database(self):
        declaration = shipped()
        verdict = duty_entry.deployment_binding(declaration, build_fact(declaration))
        self.assertTrue(verdict["passed"])
        self.assertEqual(
            verdict["id"],
            "frontend_build_env_names_the_declared_platform_admin_database",
        )
        self.assertEqual(verdict["detail"]["declared"], "sc_platform_control")

    def test_a_build_that_names_another_database_is_refused(self):
        declaration = shipped()
        verdict = duty_entry.deployment_binding(declaration, build_fact(
            declaration, platform_admin_db="sc_platform_core",
            error="the deployed frontend build names sc_platform_core, not the declared "
                  "sc_platform_control",
        ))
        self.assertFalse(verdict["passed"])
        self.assertEqual(verdict["detail"]["observed"], "sc_platform_core")

    def test_a_missing_build_environment_is_refused(self):
        declaration = shipped()
        verdict = duty_entry.deployment_binding(declaration, build_fact(
            declaration, present=False, platform_admin_db="", sha256="",
            error="the declared frontend build environment file is missing",
        ))
        self.assertFalse(verdict["passed"])

    def test_an_unreported_build_fact_is_not_a_pass(self):
        declaration = shipped()
        self.assertFalse(duty_entry.deployment_binding(declaration, {})["passed"])
        self.assertFalse(duty_entry.deployment_binding(declaration, None)["passed"])


def service_matching(row):
    """The service face an observation must show for one declared duty.

    A duty that declares an application must show its services running and its
    declared minimum module set installed; a duty that declares only its cluster
    must show exactly that; a duty that declares itself not yet initialized must
    still look uninitialized, because that is the shape the write-back replaces.
    """
    face = row["custody"].get("service_face")
    services = list(row["stack"]["services"])
    if face == "initialized":
        running = services
        modules = {name: "installed" for name in row["stack"]["modules"]}
    elif face == "to_be_initialized":
        running = [name for name in services if name == "db"]
        modules = {}
    else:
        running = ["db"]
        modules = {}
    industry = sorted(
        name for name in modules if str(name).startswith(duty_entry.INDUSTRY_MODULE_PREFIX)
    )
    return {
        "project": row["cluster"]["compose_project"],
        "running_services": sorted(running),
        "containers": {name: {"name": name, "state": "running"} for name in running},
        "module_states": modules,
        "installed_industry_modules": industry,
        "error": "",
    }


def observation_matching(declaration):
    """An observation that agrees with every declared duty.

    Used instead of a host: it lets a test exercise the whole plan path
    (embedding, evaluation, reporting) without reaching a machine.
    """
    rows = []
    for row in declaration["duties"]:
        compliance = row["custody"]["role_compliance"]
        wants_creation = compliance == "to_be_created"
        if wants_creation:
            custody = {
                "database_present": False, "database_owner": "", "allow_connections": None,
                "role_present": False, "role_superuser": None, "role_createdb": None,
                "role_createrole": None, "role_canlogin": None, "public_connects": None,
                "public_schema_create": None, "database_role_connects": None, "error": "",
            }
        elif compliance == "declared_gap":
            # The one declaration that describes a real, still-open gap: the
            # shared bootstrap role is a superuser that can create databases.
            custody = {
                "database_present": True, "database_owner": row["database_role"],
                "allow_connections": True, "role_present": True, "role_superuser": True,
                "role_createdb": True, "role_createrole": False, "role_canlogin": True,
                "public_connects": None, "public_schema_create": True, "database_role_connects": None,
                "error": "",
            }
        else:
            custody = {
                "database_present": True, "database_owner": row["database_role"],
                "allow_connections": True, "role_present": True, "role_superuser": False,
                "role_createdb": False, "role_createrole": False, "role_canlogin": True,
                "public_connects": False, "public_schema_create": True, "database_role_connects": True, "error": "",
            }
        rows.append({
            "duty": row["duty"],
            "cluster": {
                "present": not wants_creation, "running": not wants_creation,
                "system_identifier": row["cluster"].get("system_identifier", ""), "error": "",
                "data_volume_owner": row["cluster"]["data_volume"],
                "project": row["cluster"]["compose_project"], "config_files": "",
            },
            "custody": custody,
            "stack": None,
            "service": service_matching(row),
        })
    return {
        "duties": rows,
        "frontend_build": build_fact(declaration),
    }


class EntryGuardTests(unittest.TestCase):
    def run_main(self, argv, environ=None):
        stream = io.StringIO()
        saved = dict(os.environ)
        os.environ.pop(duty_entry.CONFIRM_ENV, None)
        if environ:
            os.environ.update(environ)
        try:
            with contextlib.redirect_stderr(stream):
                code = duty_entry.main(argv)
        finally:
            os.environ.clear()
            os.environ.update(saved)
        return code, stream.getvalue()

    def test_apply_requires_the_exact_confirmation_token(self):
        code, output = self.run_main([
            "--ssh-host", "sc-root", "--apply", "--report", "/tmp/duty-guard.json",
        ])
        self.assertEqual(code, 2)
        self.assertIn(duty_entry.CONFIRM_ENV, output)

    def test_apply_requires_the_reviewed_declaration_digest(self):
        code, output = self.run_main(
            ["--ssh-host", "sc-root", "--apply", "--report", "/tmp/duty-guard.json"],
            {duty_entry.CONFIRM_ENV: duty_entry.CONFIRMATION},
        )
        self.assertEqual(code, 2)
        self.assertIn("DAILY_DUTY_REVIEWED_DECLARATION_DIGEST_REQUIRED", output)

    def test_apply_refuses_a_stale_declaration_digest(self):
        code, output = self.run_main(
            ["--ssh-host", "sc-root", "--apply", "--expect-declaration-digest", "0" * 64,
             "--report", "/tmp/duty-guard.json"],
            {duty_entry.CONFIRM_ENV: duty_entry.CONFIRMATION},
        )
        self.assertEqual(code, 2)
        self.assertIn("DAILY_DUTY_DECLARATION_DIGEST_MISMATCH", output)

    def test_the_plan_digest_is_never_reported_as_the_declaration_digest(self):
        # The value an ``--apply`` must echo is the digest of the reviewed
        # declaration. Reporting the plan's own digest under the same name would
        # point an operator at the one guard that stops an unreviewed edit.
        head = types.SimpleNamespace(returncode=0, stdout=b"a" * 40 + b"\n", stderr=b"")
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "plan.json"
            stream = io.StringIO()
            with mock.patch.object(duty_entry, "ssh", return_value=head), \
                 mock.patch.object(duty_entry, "remote_duties",
                                   return_value=observation_matching(shipped())), \
                 contextlib.redirect_stdout(stream):
                code = duty_entry.main([
                    "--ssh-host", "sc-root", "--report", str(report),
                ])
            self.assertEqual(code, 0)
            payload = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(payload["declaration_digest"], duty_entry.declaration_digest(shipped()))
        self.assertNotEqual(payload["declaration_digest"], payload["plan_digest"])
        self.assertEqual(json.loads(stream.getvalue())["declaration_digest"],
                         payload["declaration_digest"])
        expected = observation_matching(shipped())["frontend_build"]
        self.assertEqual(payload["frontend_build_env_file"],
                         shipped()["frontend_build_env_file"])
        self.assertEqual(payload["frontend_build"], expected)
        self.assertTrue(payload["deployment_binding"]["passed"])
        self.assertEqual(payload["plan"]["deployment_binding"],
                         payload["deployment_binding"])

    def test_a_stale_build_binding_fails_the_deployment_plan(self):
        head = types.SimpleNamespace(returncode=0, stdout=b"a" * 40 + b"\n", stderr=b"")
        observation = observation_matching(shipped())
        observation["frontend_build"] = build_fact(
            shipped(), platform_admin_db="sc_platform_core",
            error="the deployed frontend build names sc_platform_core, not the declared "
                  "sc_platform_control",
        )
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "plan.json"
            stream = io.StringIO()
            with mock.patch.object(duty_entry, "ssh", return_value=head), \
                 mock.patch.object(duty_entry, "remote_duties", return_value=observation), \
                 contextlib.redirect_stdout(stream):
                code = duty_entry.main(["--ssh-host", "sc-root", "--report", str(report)])
            payload = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(code, 1)
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual(
            [row["failed_assertions"] for row in payload["plan"]["duties"]], [[], [], []]
        )
        self.assertFalse(payload["deployment_binding"]["passed"])

    def test_the_host_must_be_a_configured_alias(self):
        code, output = self.run_main(["--ssh-host", "sc root; rm -rf /", "--report", "/tmp/x.json"])
        self.assertEqual(code, 2)
        self.assertIn("host alias", output)

    def test_an_invalid_expected_sha_is_refused(self):
        code, output = self.run_main(
            ["--ssh-host", "sc-root", "--expected-sha", "HEAD", "--report", "/tmp/x.json"]
        )
        self.assertEqual(code, 2)
        self.assertIn("commit identity", output)

class FakeResult:
    """The shape of one finished command inside the rendered carrier."""

    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


class FakeSubprocess:
    """Stands in for the ``subprocess`` module inside the rendered carrier.

    The carrier only reaches a host through ``subprocess.run``, so replacing
    that one module is enough to execute the *real* rendered program in-process
    and observe the command order it chooses.
    """

    class TimeoutExpired(Exception):
        def __init__(self, command, timeout):
            super().__init__("command timed out after %s seconds" % (timeout,))
            self.command = command
            self.timeout = timeout

    def __init__(self, base_installed=True, entrypoint_log=""):
        self.commands = []
        self.raises = []
        #: A duty the entry is allowed to initialize is a duty whose own
        #: container bootstrap has already installed ``base``: the entry waits
        #: for that fact, so a fake that never reports it would model the
        #: collision instead of the order.
        self.base_installed = base_installed
        #: What the container's own startup has written so far. An empty log is
        #: an attempt still in flight; a log that reached the server line is a
        #: finished attempt, which is the only state a restart may follow.
        self.entrypoint_log = entrypoint_log

    def run(self, command, **kwargs):
        self.commands.append(list(command))
        for index, predicate in enumerate(self.raises):
            if predicate(list(command)):
                del self.raises[index]
                raise self.TimeoutExpired(command, kwargs.get("timeout"))
        if list(command[:2]) == ["docker", "ps"]:
            return FakeResult(stdout="sc-platform-control-dev-odoo-1\n")
        text = " ".join(str(item) for item in command)
        if list(command[:2]) == ["docker", "logs"]:
            return FakeResult(stdout=self.entrypoint_log)
        if "to_regclass('public.ir_module_module')" in text:
            return FakeResult(stdout="t\n" if self.base_installed else "f\n")
        if "WHERE name = 'base'" in text:
            return FakeResult(stdout="installed\n" if self.base_installed else "\n")
        return FakeResult()


class CarrierExecutionTests(unittest.TestCase):
    """The carrier is executed, not only read, for the order it must respect.

    The first host run of this entry failed here: the entry waited for the
    application's health *before* installing into it, and a duty's route can
    only become healthy once its database carries the declared module set, so
    the wait could never succeed and the failure arrived as an unhandled
    ``TimeoutExpired`` that lost every duty's readback. Both halves are pinned
    below against the real rendered program.
    """

    COMPOSE_TEXT = "services:\n  db:\n    image: postgres:15\n"

    def duty(self, name="platform_control", face="to_be_initialized"):
        return {
            "duty": name,
            "database": "sc_platform_control" if name == "platform_control" else "sc_tenant_baosheng_dev",
            "database_role": "sc_platform_control_app",
            "dbfilter": "^sc_platform_control$",
            "custody": {"database_present": True, "database_role_present": True,
                        "role_compliance": "compliant", "service_face": face},
            "cluster": {"container": "sc-platform-control-dev-db-1",
                        "compose_project": "sc-platform-control-dev",
                        "data_volume": "sc_platform_control_db_data",
                        "maintenance_role": "sc_platform_control_maintenance"},
            "storage": {"redis_data_volume": "sc_platform_control_redis_data",
                        "odoo_data_volume": "sc_platform_control_odoo_data"},
            "routing": {"odoo_loopback_port": 18083, "nginx_host_port": 18082},
            "stack": {
                "services": ["db", "redis", "odoo", "nginx"],
                "modules": ["smart_core"],
                "runtime_env": "dev",
                "product_root": "/opt/projects/repos/sce-product-odoo",
                "postgres_image": "postgres:15",
                "odoo_image": "odoo17-odoo:latest",
                "frontend_dist_dir": "/opt/projects/repos/sce-product-odoo/frontend/apps/web/dist-dev",
                "demo_addons_root": "/opt/projects/runtime-addons-empty",
                "customer_addons_root": "/opt/projects/runtime-addons-empty",
            },
        }

    def payload(self, duties, ops_root, *, mode="apply", phase="initialize",
                bootstrap_timeout=1800, bootstrap_poll=15):
        import hashlib

        return {
            "mode": mode,
            "phase": phase,
            "product_root": "/opt/projects/repos/sce-product-odoo",
            "ops_root": ops_root,
            "platform_admin_database": "sc_platform_control",
            "frontend_build_env_file": os.path.join(ops_root, "absent-build.env"),
            "source_revision": "a" * 40,
            "compose_sha256": hashlib.sha256(self.COMPOSE_TEXT.encode("utf-8")).hexdigest(),
            "stack": {"compose_text": self.COMPOSE_TEXT},
            "env_template": "DB_NAME=@DB_NAME@\nLIST_DB=false\n",
            "data_destination": "/var/lib/postgresql/data",
            "bootstrap_timeout": bootstrap_timeout,
            "bootstrap_poll": bootstrap_poll,
            "duties": duties,
        }

    def execute(self, fake, duties, *, mode="apply", phase="initialize",
                bootstrap_timeout=1800, bootstrap_poll=15):
        with tempfile.TemporaryDirectory() as ops_root:
            rendered = duty_entry.render_remote_program(
                self.payload(duties, ops_root, mode=mode, phase=phase,
                             bootstrap_timeout=bootstrap_timeout, bootstrap_poll=bootstrap_poll)
            )
            captured = io.StringIO()
            saved = sys.modules.get("subprocess")
            sys.modules["subprocess"] = fake
            try:
                with contextlib.redirect_stdout(captured):
                    exec(compile(rendered, "<remote-carrier>", "exec"), {"__name__": "__carrier__"})
            finally:
                if saved is None:
                    sys.modules.pop("subprocess", None)
                else:
                    sys.modules["subprocess"] = saved
        return json.loads(captured.getvalue().split(duty_entry.MARKER, 1)[1])

    def index_of(self, fake, predicate):
        for index, command in enumerate(fake.commands):
            if predicate(command):
                return index
        raise AssertionError("no command matched: %s" % (fake.commands,))

    def ups(self, fake):
        return [c for c in fake.commands if "up" in c and c[:2] == ["docker", "compose"]]

    def test_the_cluster_is_waited_for_and_the_application_is_not(self):
        fake = FakeSubprocess()
        self.execute(fake, [self.duty()])
        cluster = [c for c in self.ups(fake) if c[-2:] == ["db", "redis"]]
        application = [c for c in self.ups(fake) if c[-2:] == ["-d", "odoo"]]
        self.assertEqual(len(cluster), 1)
        self.assertEqual(len(application), 1)
        self.assertIn("--wait", cluster[0])
        self.assertNotIn(
            "--wait", application[0],
            "the application's health is a consequence of the declared module set; "
            "waiting for it before installing into the duty can never succeed",
        )
        # The health of the application is waited for *after* it holds the
        # declared modules, which is the only moment that health is reachable.
        install = self.index_of(
            fake, lambda c: c[:2] == ["docker", "exec"] and "-i" in c and "odoo" in c
        )
        confirm = self.index_of(fake, lambda c: c[-2:] == ["--wait", "odoo"])
        self.assertLess(install, confirm)

    def test_the_route_is_started_only_after_the_declared_modules_are_installed(self):
        fake = FakeSubprocess()
        self.execute(fake, [self.duty()])
        install = self.index_of(
            fake, lambda c: c[:2] == ["docker", "exec"] and "-i" in c and "odoo" in c
        )
        route = self.index_of(fake, lambda c: "up" in c and c[-1] == "nginx")
        self.assertLess(
            install, route,
            "a route that waits for the application's health must come after the "
            "installation that makes that health reachable",
        )
        self.assertIn("--wait", fake.commands[route])
        self.assertIn("smart_core", fake.commands[install])

    def test_the_application_is_granted_its_own_schema_before_installation(self):
        """Owning a database is not the same as being able to initialize it.

        The first host run of this entry created a database whose owner was then
        refused ``CREATE TABLE public.…``, and the entry reported it as a healthy
        duty because nothing in the readback looked at the schema. The grant is
        therefore issued for the duty's own database, before the installation
        that needs it.
        """
        fake = FakeSubprocess()
        self.execute(fake, [self.duty()])
        grants = [c for c in fake.commands
                  if c[:2] == ["docker", "exec"] and "GRANT USAGE, CREATE ON SCHEMA public" in " ".join(c)]
        self.assertEqual(len(grants), 1)
        grant = grants[0]
        self.assertIn("sc_platform_control_app", " ".join(grant))
        self.assertEqual(grant[grant.index("-d") + 1], "sc_platform_control")
        install = self.index_of(
            fake, lambda c: c[:2] == ["docker", "exec"] and "-i" in c and "odoo" in c
        )
        self.assertLess(fake.commands.index(grant), install)

    def test_a_duty_that_raises_is_reported_with_its_readback(self):
        fake = FakeSubprocess()
        fake.raises.append(lambda command: "up" in command)
        report = self.execute(fake, [self.duty()])
        self.assertTrue(report["writes"])
        self.assertEqual(len(report["duties"]), 1)
        settled = report["duties"][0]
        self.assertIn("TimeoutExpired", settled["error"])
        self.assertIsNotNone(
            settled["cluster"],
            "a duty that raised must still report the facts observed after it, or a "
            "partial write becomes an unrecorded one",
        )
        self.assertIsNotNone(settled["service"])

    def test_the_entry_waits_for_the_container_bootstrap_before_installing(self):
        """The wait is ordered, not merely present.

        The 2026-10-15 host run started the application and installed into it
        while the container's own entrypoint was still installing ``base`` in
        the same fresh database; ``ir_actions`` was created twice and the duty
        was left half built. What prevents that is the *order* below.
        """
        fake = FakeSubprocess()
        self.execute(fake, [self.duty()])
        readback = self.index_of(
            fake, lambda c: "docker" == c[0] and "exec" in c
            and "to_regclass('public.ir_module_module')" in " ".join(c)
        )
        install = self.index_of(
            fake, lambda c: c[:2] == ["docker", "exec"] and "-i" in c and "odoo" in c
        )
        self.assertLess(
            readback, install,
            "the declared set may only be installed once the container's own base "
            "bootstrap is over",
        )

    def test_an_unfinished_bootstrap_is_never_installed_into(self):
        """A duty whose base install has not finished is not installed into.

        Two guards are asserted here: the wait fails closed on its own bound,
        and the installation refuses a database whose ``base`` is missing. The
        two must not be the same guard, or a wait that timed out would still
        hand the duty to the installer.
        """
        fake = FakeSubprocess(base_installed=False)
        report = self.execute(fake, [self.duty()], bootstrap_timeout=0, bootstrap_poll=0)
        settled = report["duties"][0]
        self.assertFalse(
            [c for c in fake.commands
             if c[:2] == ["docker", "exec"] and "-i" in c and "odoo" in c],
            "no second initializer may run while the first one owns the database",
        )
        self.assertIn("refusing to", json.dumps(settled, ensure_ascii=False))
        self.assertFalse(settled["bootstrap"]["ready"])
        self.assertIn("error", settled["bootstrap"])

    def test_a_finished_failed_bootstrap_is_restarted_once(self):
        """A finished failed attempt is retried once, and only once.

        Restarting is safe exactly because the previous attempt is over; a
        restart that interrupted a live attempt would be an interrupted
        initialization, which is the hazard this wait exists to remove.
        """
        fake = FakeSubprocess(
            base_installed=False,
            entrypoint_log="[entrypoint] render odoo.conf: a -> b\n"
                           "[entrypoint] start odoo\n",
        )
        report = self.execute(fake, [self.duty()], bootstrap_timeout=0, bootstrap_poll=0)
        restarts = [c for c in fake.commands if c[:2] == ["docker", "restart"]]
        self.assertEqual(len(restarts), 1)
        self.assertEqual(report["duties"][0]["bootstrap"]["restarts"], 1)

    def test_an_attempt_still_in_flight_is_never_restarted(self):
        fake = FakeSubprocess(
            base_installed=False,
            entrypoint_log="[entrypoint] render odoo.conf: a -> b\n"
                           "[entrypoint] bootstrap base (without demo)\n",
        )
        report = self.execute(fake, [self.duty()], bootstrap_timeout=0, bootstrap_poll=0)
        self.assertFalse([c for c in fake.commands if c[:2] == ["docker", "restart"]])
        self.assertEqual(report["duties"][0]["bootstrap"]["restarts"], 0)

    def test_a_failing_duty_does_not_hide_a_later_duty(self):
        fake = FakeSubprocess()
        fake.raises.append(lambda command: "up" in command)
        report = self.execute(fake, [self.duty(), self.duty(name="customer_tenant_dev")])
        self.assertEqual([row["duty"] for row in report["duties"]],
                         ["platform_control", "customer_tenant_dev"])
        self.assertIn("TimeoutExpired", report["duties"][0]["error"])
        self.assertEqual(report["duties"][1]["error"], "")


if __name__ == "__main__":
    unittest.main()
