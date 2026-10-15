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


class EvaluationTests(unittest.TestCase):
    def declaration(self):
        return shipped()

    def observe(self, duty, **overrides):
        cluster = {"present": False, "running": False, "system_identifier": "",
                   "data_volume_owner": "", "project": "", "config_files": "", "error": ""}
        custody = {"database_present": False, "database_owner": "", "allow_connections": None,
                   "role_present": False, "role_superuser": None, "role_createdb": None,
                   "role_createrole": None, "role_canlogin": None, "public_connects": None,
                   "database_role_connects": None, "error": "cluster container is not running"}
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
                        "public_connects": False, "database_role_connects": True, "error": ""},
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
                   "database_role_connects": None, "error": ""}
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
                   "public_connects": False, "database_role_connects": True, "error": ""}
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
                   "database_role_connects": True, "error": ""}
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
                   "public_connects": None, "database_role_connects": None, "error": ""}
        verdict = {a["id"]: a["passed"] for a in duty_entry.evaluate(
            picked(declaration, "platform_control"),
            {"duty": "platform_control", "cluster": cluster, "custody": custody, "stack": None},
            declaration)}
        self.assertFalse(verdict["database_accepts_the_declared_duty"])


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
                "database_role_connects": None, "error": "",
            }
        elif compliance == "declared_gap":
            # The one declaration that describes a real, still-open gap: the
            # shared bootstrap role is a superuser that can create databases.
            custody = {
                "database_present": True, "database_owner": row["database_role"],
                "allow_connections": True, "role_present": True, "role_superuser": True,
                "role_createdb": True, "role_createrole": False, "role_canlogin": True,
                "public_connects": None, "database_role_connects": None, "error": "",
            }
        else:
            custody = {
                "database_present": True, "database_owner": row["database_role"],
                "allow_connections": True, "role_present": True, "role_superuser": False,
                "role_createdb": False, "role_createrole": False, "role_canlogin": True,
                "public_connects": False, "database_role_connects": True, "error": "",
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


if __name__ == "__main__":
    unittest.main()
