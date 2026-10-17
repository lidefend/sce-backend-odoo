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
from scripts.ops import duty_identity_test_support as duty_support


ROOT = Path(__file__).resolve().parents[2]
DECLARATION = ROOT / "config/ops/daily_runtime_database_duties.v1.json"
ENV_TEMPLATE = ROOT / "config/ops/daily_runtime_duty_stack.env"
COMPOSE_FILE = ROOT / "config/ops/daily_runtime_duty_stack.yml"

#: A frontend artifact fingerprint shaped exactly as the governed build entry
#: writes it into the artifact's own ``.build-sha256``. The duty render refuses
#: a stack that cannot name the bundle it serves, so the fixtures have to hand
#: each declared duty that artifact instead of the refusal being relaxed for
#: tests.
FRONTEND_BUILD_FINGERPRINT = "0123456789abcdef" * 4


def provision_frontend_artifact(root, duties, fingerprint=FRONTEND_BUILD_FINGERPRINT):
    """Give every declared duty the served frontend artifact its render requires.

    ``fingerprint=None`` creates the declared output directory without the
    artifact, which is a duty whose served bundle cannot be identified.
    """
    dist = os.path.join(root, "web-dist")
    os.makedirs(dist, exist_ok=True)
    if fingerprint is not None:
        with open(os.path.join(dist, ".build-sha256"), "w") as stream:
            stream.write("%s\n" % (fingerprint,))
    for duty in duties:
        duty.setdefault("stack", {})["frontend_dist_dir"] = dist
    return dist


def setUpModule():
    """Resolve the tracked template against the synthetic customer binding."""
    override = duty_support.synthetic_instances_override()
    override.start()
    unittest.addModuleCleanup(override.stop)


def shipped():
    """The declaration exactly as the entry loads it, customer binding merged in.

    It is returned whole, including the ``managed_duty_instances`` pointer, so
    the digest a test compares against is the digest of the very object the
    entry reviewed rather than a lookalike built by the test.
    """
    payload = duty_entry.duty_identity.load_declaration(DECLARATION)
    return json.loads(json.dumps(payload, ensure_ascii=False))


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


def as_declared_gap(declaration, name, reason="the bootstrap role is still the application role"):
    """One declared duty reshaped into the recorded shared-bootstrap-role gap.

    The gap rules have to stay proven after the rebuild closed the only gap the
    shipped declaration carried, so a test asks for the shape instead of reading
    it off whichever duty currently happens to be in it.
    """
    out = copy.deepcopy(declaration)
    row = picked(out, name)
    row["database_role"] = "odoo"
    row["cluster"]["maintenance_role"] = "odoo"
    row["custody"] = {
        "database_present": True,
        "database_role_present": True,
        "role_compliance": "declared_gap",
        "gap_kind": "shared_bootstrap_role",
        "gap_reason": reason,
        "gap_owner_task": "DAILY-RUNTIME-DEMO-APP-ROLE-01",
        "service_face": "initialized",
    }
    row["credential_source"] = {
        "env_file": "/opt/projects/repos/sce-product-odoo/.env.dev",
        "key": "DB_PASSWORD",
        "reason": "the adopted role already lives in the cluster data volume",
        "owning_task": "DAILY-RUNTIME-DEMO-APP-ROLE-01",
    }
    return out


def declared_gap_duty(declaration):
    """A duty rebuilt into the recorded gap shape, with the reshaped declaration."""
    name = "demo"
    return name, as_declared_gap(declaration, name)


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
        _, declaration = declared_gap_duty(shipped())
        custody = picked(declaration, "demo")["custody"]
        custody.pop("gap_kind")
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("gap_kind=shared_bootstrap_role" in f for f in failures))

    def test_declared_gap_that_is_closed_is_stale(self):
        _, declaration = declared_gap_duty(shipped())
        row = picked(declaration, "demo")
        row["database_role"] = "sc_demo_app"
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("otherwise the gap is closed" in f for f in failures))

    def test_declared_gap_needs_a_reason_and_an_owner(self):
        _, declaration = declared_gap_duty(shipped())
        custody = picked(declaration, "demo")["custody"]
        custody["gap_owner_task"] = ""
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("a declared gap needs gap_owner_task" in f for f in failures))

    def test_a_duty_that_keeps_the_bootstrap_role_must_adopt_its_credential(self):
        """An existing role cannot be handed a generated secret.

        The 2026-10-16 demo refresh rendered a fresh application secret for the
        ``odoo`` role already living inside ``sc_dev_db_data``. The role kept the
        password it was created with, the application was recreated with the
        rendered one, and the only visible symptom was an application that
        restarted forever while every other duty reported healthy. A declaration
        that says "the bootstrap role is still the application role" therefore
        has to say where that role's credential comes from.
        """
        _, declaration = declared_gap_duty(shipped())
        picked(declaration, "demo").pop("credential_source")
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("can only adopt its credential" in f for f in failures), failures)

    def test_the_shipped_demo_duty_owns_its_application_credential(self):
        """The rebuilt carrier creates its own role, so it owns its own secret.

        The 2026-10-16 rebuild replaced the pre-governance cluster the demo duty
        borrowed (and the ``odoo`` bootstrap role it adopted) with a carrier the
        entry creates itself. A duty that creates its role mints the credential
        that role is created with; adopting a foreign file would make an object
        this entry owns depend on one it does not.
        """
        declaration = shipped()
        row = picked(declaration, "demo")
        self.assertNotIn("credential_source", row)
        self.assertEqual(row["database_role"], row["database"] + "_app")
        self.assertNotEqual(row["cluster"]["maintenance_role"], row["database_role"])
        self.assertEqual(duty_entry.validate_declaration(declaration), [])

    def test_an_adopted_credential_source_needs_a_reason_and_an_owner(self):
        _, declaration = declared_gap_duty(shipped())
        source = picked(declaration, "demo")["credential_source"]
        source["owning_task"] = ""
        source["reason"] = ""
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("credential_source needs reason" in f for f in failures), failures)
        self.assertTrue(any("credential_source needs owning_task" in f for f in failures), failures)

    def test_an_adopted_credential_source_must_be_one_absolute_file(self):
        _, declaration = declared_gap_duty(shipped())
        source = picked(declaration, "demo")["credential_source"]
        source["env_file"] = "relative/.env.dev"
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("must be one absolute file path" in f for f in failures), failures)

    def test_an_adopted_credential_may_not_be_written_by_a_duty_or_this_checkout(self):
        """The adopted credential must not be one this entry can render away.

        A source inside the duty namespace would be rewritten by the next duty
        render, and a source inside this checkout would let a branch change what
        the running duty authenticates with.
        """
        _, declaration = declared_gap_duty(shipped())
        source = picked(declaration, "demo")["credential_source"]
        source["env_file"] = os.path.join(str(duty_entry.ROOT), "ops", "duty.env")
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("outside this repository checkout" in f for f in failures), failures)
        source["env_file"] = os.path.join(declaration["ops_root"], "demo.env")
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(
            any("outside the governed duty namespace" in f for f in failures), failures
        )

    def test_an_adopted_credential_key_must_be_duty_secret_material(self):
        _, declaration = declared_gap_duty(shipped())
        source = picked(declaration, "demo")["credential_source"]
        source["key"] = "DB_NAME"
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("is not duty secret material" in f for f in failures), failures)
        source["key"] = ""
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("credential_source.key is required" in f for f in failures), failures)

    def test_an_adopted_credential_source_names_only_declared_keys(self):
        _, declaration = declared_gap_duty(shipped())
        picked(declaration, "demo")["credential_source"]["password"] = "x"
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("names unknown keys password" in f for f in failures), failures)

    def test_a_duty_that_creates_its_own_role_owns_its_own_credential(self):
        """Creating a role and adopting one are different situations.

        A ``to_be_created`` duty creates its role with the credential it renders,
        so adopting one would make an object this entry owns depend on a foreign
        file. The refusal keeps adoption from becoming a general escape hatch.
        """
        declaration = prospective(shipped(), "platform_control")
        picked(declaration, "platform_control")["credential_source"] = {
            "env_file": "/opt/projects/repos/sce-product-odoo/.env.dev",
            "key": "DB_PASSWORD", "reason": "x", "owning_task": "y",
        }
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("owns the credential it creates" in f for f in failures), failures)

    def test_two_duties_may_not_share_one_data_volume(self):
        declaration = shipped()
        target = picked(declaration, "customer_tenant_dev")
        target["cluster"]["data_volume"] = picked(declaration, "platform_control")["cluster"]["data_volume"]
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("one data directory has one writer" in f for f in failures))

    def test_two_duties_may_not_share_a_route_or_a_namespace(self):
        declaration = shipped()
        row = picked(declaration, "customer_tenant_dev")
        donor = picked(declaration, "platform_control")
        row["routing"]["nginx_host_port"] = donor["routing"]["nginx_host_port"]
        row["storage"]["backup_namespace"] = donor["storage"]["backup_namespace"]
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(
            any("share nginx_host_port=%s" % (donor["routing"]["nginx_host_port"],) in f
                for f in failures), failures)
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

    def test_a_demo_duty_that_names_no_seed_carrier_is_refused(self):
        """A demo duty may not reach ``--phase seed`` without saying what seeds it.

        The governed entry runs the product's own demo chain and never a step
        list of its own, so a demo duty whose ``demo_seed`` section is missing or
        empty has nothing for that entry to run. Refusing the *declaration* is
        what keeps "seed it somehow" from becoming an entry that guesses.
        """
        for empty in (None, {}):
            declaration = shipped()
            row = picked(declaration, "demo")
            if empty is None:
                row.pop("demo_seed")
            else:
                row["demo_seed"] = empty
            failures = duty_entry.validate_declaration(declaration)
            self.assertTrue(
                any("must name its demo-seed carrier and profile" in f for f in failures), failures
            )

    def test_a_demo_seed_carrier_must_be_the_products_own_demo_module(self):
        """A second demo-data lane is refused, not merely discouraged.

        The owner named ``smart_construction_demo`` as the demo duty's carrier.
        A declaration that pointed at another module would make the governed
        entry run a chain nothing in the product owns, which is exactly the
        substitute-fixture lane the ruling excludes.
        """
        declaration = shipped()
        picked(declaration, "demo")["demo_seed"]["carrier"] = "some_other_demo_module"
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(
            any("is not the product's own demo-data carrier" in f for f in failures), failures
        )

    def test_a_demo_seed_profile_must_be_a_safe_profile_name(self):
        for profile in ("", "Demo Full", "demo-full", "1demo", "../../etc/passwd"):
            declaration = shipped()
            picked(declaration, "demo")["demo_seed"]["profile"] = profile
            failures = duty_entry.validate_declaration(declaration)
            self.assertTrue(
                any("is not a safe profile name" in f for f in failures),
                (profile, failures),
            )
        declaration = shipped()
        picked(declaration, "demo")["demo_seed"]["profile"] = "demo_full"
        self.assertEqual(duty_entry.validate_declaration(declaration), [])

    def test_a_demo_seed_must_name_the_product_chain_stages(self):
        """A demo duty names the chain it is seeded with, stages and all.

        The entry runs no step of its own, so a declaration that named only a
        profile would ask the entry to run the profile against a duty whose
        scenarios were never loaded -- the 2026-10-16 shape, which raised
        mid-chain. Refusing the declaration is what keeps that from being an
        entry that guesses the rest of the chain.
        """
        for stages in (None, [], "release_seed", [1, 2]):
            declaration = shipped()
            picked(declaration, "demo")["demo_seed"]["stages"] = stages
            failures = duty_entry.validate_declaration(declaration)
            self.assertTrue(
                any("demo_seed.stages must name the product chain stages" in f for f in failures),
                (stages, failures),
            )

    def test_a_demo_seed_stage_the_product_does_not_have_is_refused(self):
        declaration = shipped()
        picked(declaration, "demo")["demo_seed"]["stages"] = ["release_seed", "profile", "extra"]
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(
            any("names unknown stage(s) extra" in f for f in failures), failures
        )

    def test_a_demo_seed_stage_list_may_not_repeat_a_stage(self):
        declaration = shipped()
        picked(declaration, "demo")["demo_seed"]["stages"] = ["release_seed", "profile", "profile"]
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(any("repeats a stage" in f for f in failures), failures)

    def test_a_demo_seed_stage_list_must_run_the_declared_profile(self):
        """Seeding the scenarios and never the profile is a partial carrier.

        The duty declares ``profile=demo_full``; a stage list that omits the
        ``profile`` stage would create scenario rows and no business chain while
        still reporting a chain that executed.
        """
        declaration = shipped()
        picked(declaration, "demo")["demo_seed"]["stages"] = ["release_seed"]
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(
            any("never runs the declared profile demo_full" in f for f in failures), failures
        )

    def test_a_demo_seed_needs_an_authority_and_a_reason(self):
        """The seed is a write; the declaration has to say who authorized it."""
        for key in ("authority", "reason"):
            declaration = shipped()
            picked(declaration, "demo")["demo_seed"][key] = "  "
            failures = duty_entry.validate_declaration(declaration)
            self.assertTrue(any("demo_seed.%s is required" % (key,) in f for f in failures), failures)

    def test_only_a_demo_duty_may_declare_a_demo_seed(self):
        """A duty that is not the demo duty may never carry a demo-seed section.

        Without this, a carrier duty could pick up demo seeding by copying a
        neighbour's declaration, and the demo-data switch would follow a
        ``data_purpose`` the duty does not have.
        """
        declaration = shipped()
        donor = copy.deepcopy(picked(declaration, "demo")["demo_seed"])
        picked(declaration, "platform_control")["demo_seed"] = donor
        failures = duty_entry.validate_declaration(declaration)
        self.assertTrue(
            any("only a duty that declares data_purpose=demo may declare demo_seed" in f
                for f in failures), failures
        )

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

    def test_the_shipped_stack_hands_the_runtime_environment_to_the_container(self):
        """The env file naming the runtime environment is not the same fact as
        the container reading it.

        `render_odoo_conf` may only drop an unavailable optional addon root when
        `ENV` says the runtime is not production, and the platform database
        contract reads `SC_ENVIRONMENT`. A stack that declares the environment in
        its env file and never forwards it keeps an `addons_path` entry for a
        directory the duty does not mount, and every `/api/*` route then fails
        before dispatch -- which is exactly what the daily control plane did on
        2026-10-16 while reporting itself healthy.
        """
        compose = COMPOSE_FILE.read_text(encoding="utf-8")
        for key in duty_entry.APPLICATION_ENVIRONMENT_KEYS:
            self.assertIn(
                "%s: ${%s}" % (key, key),
                compose,
                "the duty stack must forward %s into the application container" % key,
            )

    def test_a_declared_env_key_nothing_reads_is_refused(self):
        """A declared value with no consumer is a silent no-op, so it fails.

        This is the assertion that would have caught the 2026-10-16 defect at the
        declaration boundary instead of at a 500 from a serving duty.
        """
        template = ENV_TEMPLATE.read_text(encoding="utf-8")
        compose = COMPOSE_FILE.read_text(encoding="utf-8")
        undeclared_again = compose.replace("      ENV: ${ENV}\n", "")
        self.assertNotEqual(undeclared_again, compose)
        failures, unused = duty_entry.validate_stack_surface(undeclared_again, template)
        self.assertIn("ENV", unused)
        self.assertTrue(
            any("ENV" in row and "neither the stack nor the host entry reads" in row
                for row in failures),
            failures,
        )

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
        for marker in ("__MARKER__", "__PSQL_READBACK__", "__PAYLOAD_JSON__",
                       "__BASE_BOOTSTRAP_PLAN__", "__DEMO_SEED_PROGRAM__",
                       "__REFRESH_REFUSAL__",
                       "__UPGRADE_REFUSAL__", "__PRUNE_SUPERSEDED_STACKS__"):
            self.assertNotIn(marker, rendered)

    def test_the_injected_demo_seed_chain_runs_the_declared_stages_in_order(self):
        """The chain is the product's own functions, in the declaration's order.

        The 2026-10-16 rebuild proved why this is pinned: the seed entry ran the
        ``demo_full`` profile alone, the profile's payment step resolved an S69
        contract xmlid that only the release scenario set creates, the chain
        raised, and the duty still read as seeded. A chain that is assembly
        rather than text would let that regression back in silently.
        """
        program = duty_entry.demo_seed_program("smart_construction_demo",
                                               ["release_seed", "profile"])
        self.assertIn("from odoo.addons.smart_construction_demo.tools.scenario_loader "
                      "import load_release_seed", program)
        self.assertIn("from odoo.addons.smart_construction_demo.seed import run_steps", program)
        self.assertLess(program.index("load_release_seed(env, mode='update')"),
                        program.index("run_steps(env, profile)"))
        self.assertIn("os.environ['SC_DEMO_SEED_STAGES'].split(',')", program)
        self.assertIn("env.cr.commit()", program)
        compile("def _f():\n" + "\n".join("    " + line for line in program.splitlines()),
                "<chain>", "exec")

    def test_the_injected_demo_seed_chain_refuses_a_stage_the_product_does_not_have(self):
        """An unknown stage raises inside the container instead of being skipped.

        Silently skipping it would report a shorter chain as a completed one,
        which is exactly the shape that made a partial carrier look seeded.
        """
        program = duty_entry.demo_seed_program("smart_construction_demo", ["profile"])
        self.assertIn("raise RuntimeError('unknown declared demo-seed stage: ' + stage)", program)

    def test_the_injected_chain_names_the_carrier_the_declaration_named(self):
        program = duty_entry.demo_seed_program("some_other_module", ["release_seed"])
        self.assertIn("from odoo.addons.some_other_module.seed import run_steps", program)
        self.assertNotIn("smart_construction_demo", program)

    def test_superseded_rendered_stacks_are_pruned(self):
        """A re-render writes a second file name, so the replaced one is deleted.

        The rendered name carries the digest of the definition it came from, and
        every consumer resolves the stack by shape while refusing to proceed when
        more than one is present. Leaving the superseded file behind would turn a
        successful refresh into a duty whose stack cannot be resolved at all.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            superseded = root / "duty-stack-1a5ca02d60da.yml"
            current = root / "duty-stack-b888e8a54f5e.yml"
            unrelated = root / "platform_control.env"
            for path in (superseded, current, unrelated):
                path.write_text("services: {}\n", encoding="utf-8")
            removed = duty_entry.prune_superseded_stack_files(str(root), str(current))
            self.assertEqual(removed, [str(superseded)])
            self.assertFalse(superseded.exists())
            self.assertTrue(current.exists())
            self.assertTrue(unrelated.exists())

    def test_refresh_refuses_every_duty_that_is_not_already_serving(self):
        """Refresh re-renders a serving duty, so it refuses anything else.

        A refresh that ran against an uninitialized duty would recreate a stack
        around a database nobody had made, and one that ran against a duty the
        declaration still calls `to_be_created` would do the same while also
        hiding that the duty was never created.
        """
        serving = {"custody": {"role_compliance": "compliant", "service_face": "initialized"}}
        self.assertEqual(duty_entry.refresh_refusal(serving, cluster_running=True), "")

        to_be_created = {"custody": {"role_compliance": "to_be_created",
                                     "service_face": "initialized"}}
        self.assertIn("to be created",
                      duty_entry.refresh_refusal(to_be_created, cluster_running=True))

        uninitialized = {"custody": {"role_compliance": "compliant",
                                     "service_face": "to_be_initialized"}}
        self.assertIn("initialize phase",
                      duty_entry.refresh_refusal(uninitialized, cluster_running=True))

        cluster_only = {"custody": {"role_compliance": "compliant",
                                    "service_face": "cluster_only"}}
        self.assertIn("initialize phase",
                      duty_entry.refresh_refusal(cluster_only, cluster_running=True))

        self.assertIn("cluster is not running",
                      duty_entry.refresh_refusal(serving, cluster_running=False))

    def test_upgrade_refuses_every_duty_that_is_not_already_serving(self):
        """An upgrade rewrites a schema, so it is the narrowest phase of all.

        A refresh recreates containers; an upgrade runs the declared module
        set's migrations against a database in place. Everything a refresh
        refuses is therefore refused here too, and a duty whose own bootstrap
        never finished installing ``base`` is refused as well: migrating a
        half-built database is how a duty becomes unreadable by everything,
        including the entry that broke it.
        """
        serving = {"custody": {"role_compliance": "compliant", "service_face": "initialized"},
                   "stack": {"modules": ["smart_core"]}}
        self.assertEqual(
            duty_entry.upgrade_refusal(serving, cluster_running=True, base_installed=True), "")

        to_be_created = {"custody": {"role_compliance": "to_be_created",
                                     "service_face": "initialized"},
                         "stack": {"modules": ["smart_core"]}}
        self.assertIn("to be created", duty_entry.upgrade_refusal(
            to_be_created, cluster_running=True, base_installed=True))

        uninitialized = {"custody": {"role_compliance": "compliant",
                                     "service_face": "to_be_initialized"},
                         "stack": {"modules": ["smart_core"]}}
        self.assertIn("initialize phase", duty_entry.upgrade_refusal(
            uninitialized, cluster_running=True, base_installed=True))

        cluster_only = {"custody": {"role_compliance": "compliant",
                                    "service_face": "cluster_only"},
                        "stack": {"modules": ["smart_core"]}}
        self.assertIn("initialize phase", duty_entry.upgrade_refusal(
            cluster_only, cluster_running=True, base_installed=True))

        self.assertIn("cluster is not running", duty_entry.upgrade_refusal(
            serving, cluster_running=False, base_installed=True))
        self.assertIn("base module is not installed", duty_entry.upgrade_refusal(
            serving, cluster_running=True, base_installed=False))

        no_modules = {"custody": {"role_compliance": "compliant",
                                  "service_face": "initialized"}, "stack": {"modules": []}}
        self.assertIn("names no module", duty_entry.upgrade_refusal(
            no_modules, cluster_running=True, base_installed=True))

    def test_the_upgrade_phase_names_its_own_confirmation(self):
        """A phase that rewrites a schema may not inherit the provision token.

        ``main`` falls back to the creation token for any phase a table does not
        name, so an unlisted phase would accept
        ``PROVISION_DAILY_RUNTIME_DATABASE_DUTY`` and read as a provision while
        running migrations.
        """
        confirm_env, confirm_value = duty_entry.PHASE_CONFIRMATIONS["upgrade"]
        self.assertEqual(confirm_env, "SC_CONFIRM_DAILY_RUNTIME_DUTY_UPGRADE")
        self.assertEqual(confirm_value, "UPGRADE_DAILY_RUNTIME_DUTY_DECLARED_MODULES")
        self.assertNotEqual((confirm_env, confirm_value),
                            (duty_entry.CONFIRM_ENV, duty_entry.CONFIRMATION))
        self.assertNotEqual((confirm_env, confirm_value),
                            duty_entry.PHASE_CONFIRMATIONS["refresh"])
        self.assertIn("upgrade", duty_entry.PHASES)

    def test_the_carrier_captures_a_verified_point_before_it_rewrites_the_schema(self):
        """The point has to exist *and* be verified before the write starts.

        A dump nobody listed is an assumption; the ordering is what keeps the
        entry from rewriting a duty it could not return to.
        """
        rendered = self.rendered()
        self.assertIn('entry["recovery_point"] = capture_duty_recovery_point(duty)', rendered)
        self.assertLess(
            rendered.index('entry["recovery_point"] = capture_duty_recovery_point(duty)'),
            rendered.index('entry["upgrade"] = upgrade_declared_modules(duty)'),
        )
        self.assertIn("pg_restore", rendered)
        self.assertIn("--list", rendered)
        self.assertIn("not captured and verified", rendered)

    def test_the_carrier_upgrades_only_the_declared_module_set(self):
        rendered = self.rendered()
        self.assertIn('"-u", ",".join(modules)', rendered)
        carrier = rendered.split("def upgrade_declared_modules(", 1)[1].split("def duty_entry(", 1)[0]
        self.assertIn("--stop-after-init", carrier)
        self.assertIn("--without-demo=all", carrier)
        self.assertNotIn('"-i", ",".join(modules)', carrier)
        self.assertIn('duty["stack"]["modules"]', carrier)

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

    def verdict(self, declaration, name, phase="plan", upgrade=False, **overrides):
        duty = picked(declaration, name)
        assertions = duty_entry.evaluate(
            duty, self.observe(duty, **overrides), declaration, phase=phase, upgrade=upgrade,
        )
        return {row["id"]: row["passed"] for row in assertions}

    def upgraded(self):
        """A serving duty observed just after the carrier rewrote its schema."""
        return {
            "cluster": {"present": True, "running": True, "system_identifier": "7696799124996268070",
                        "data_volume_owner": "sc_platform_control_db_data",
                        "project": "sc-platform-control-dev", "config_files": "/opt/x/duty-stack.yml",
                        "error": ""},
            "custody": {"database_present": True, "database_owner": "sc_platform_control_app",
                        "allow_connections": True, "role_present": True, "role_superuser": False,
                        "role_createdb": False, "role_createrole": False, "role_canlogin": True,
                        "public_connects": False, "public_schema_create": True,
                        "database_role_connects": True, "error": ""},
            "service": {"project": "sc-platform-control-dev",
                        "running_services": ["db", "redis", "odoo", "nginx"],
                        "containers": {}, "module_states": {"smart_core": "installed"},
                        "installed_industry_modules": [], "error": ""},
            "recovery_point": {"namespace": "/data/backups/daily-platform-control",
                               "directory": "/data/backups/daily-platform-control/"
                                            "sc_platform_control-20261016T000000Z-abcd1234",
                               "path": "/data/backups/daily-platform-control/"
                                       "sc_platform_control-20261016T000000Z-abcd1234/database.dump",
                               "database": "sc_platform_control", "bytes": 4096, "returncode": 0,
                               "verified": True, "sha256": "c" * 64, "restore_entries": 42,
                               "error": ""},
            "upgrade": {"container": "sc-platform-control-dev-odoo-1", "modules": ["smart_core"],
                        "returncode": 0, "upgraded": True,
                        "module_states": {"smart_core": "installed"}, "tail": ""},
        }

    def test_an_upgrade_is_only_reportable_with_a_verified_point_and_a_loaded_set(self):
        declaration = self.declaration()
        row = picked(declaration, "platform_control")
        observation = self.observe(row, **self.upgraded())
        verdict = {a["id"]: a["passed"] for a in duty_entry.evaluate(
            row, observation, declaration, phase="apply", upgrade=True)}
        self.assertTrue(verdict["a_verified_recovery_point_precedes_the_upgrade"])
        self.assertTrue(verdict["the_declared_module_upgrade_completed"])

        observation["recovery_point"]["verified"] = False
        observation["recovery_point"]["error"] = "the captured artifact does not list"
        verdict = {a["id"]: a["passed"] for a in duty_entry.evaluate(
            row, observation, declaration, phase="apply", upgrade=True)}
        self.assertFalse(verdict["a_verified_recovery_point_precedes_the_upgrade"])

        observation = self.observe(row, **self.upgraded())
        observation["upgrade"] = {"error": "the pre-upgrade recovery point was not captured",
                                  "upgraded": False, "returncode": 1, "modules": ["smart_core"]}
        verdict = {a["id"]: a["passed"] for a in duty_entry.evaluate(
            row, observation, declaration, phase="apply", upgrade=True)}
        self.assertFalse(verdict["the_declared_module_upgrade_completed"])

        observation = self.observe(row, **self.upgraded())
        observation["upgrade"]["module_states"] = {"smart_core": "to upgrade"}
        verdict = {a["id"]: a["passed"] for a in duty_entry.evaluate(
            row, observation, declaration, phase="apply", upgrade=True)}
        self.assertFalse(verdict["the_declared_module_upgrade_completed"])

    def test_the_upgrade_assertions_stay_out_of_every_other_phase(self):
        declaration = self.declaration()
        row = picked(declaration, "platform_control")
        verdict = {a["id"]: a["passed"] for a in duty_entry.evaluate(
            row, self.observe(row, **self.upgraded()), declaration, phase="apply")}
        self.assertNotIn("a_verified_recovery_point_precedes_the_upgrade", verdict)
        self.assertNotIn("the_declared_module_upgrade_completed", verdict)

    def served_identity(self, *, published_revision=None, published_fingerprint=None,
                        declared_fingerprint=FRONTEND_BUILD_FINGERPRINT):
        """A serving duty observed together with the identity its route publishes.

        ``declared_fingerprint=None`` models an artifact the entry could not read
        at all, which is a duty the render would have refused: the verdict still
        has to say so instead of counting the container as identified.
        """
        revision = "a" * 40
        return {
            "cluster": {"present": True, "running": True, "system_identifier": "7696799124996268070",
                        "data_volume_owner": "sc_platform_control_db_data",
                        "project": "sc-platform-control-dev", "config_files": "/opt/x/duty-stack.yml",
                        "error": ""},
            "custody": {"database_present": True, "database_owner": "sc_platform_control_app",
                        "allow_connections": True, "role_present": True, "role_superuser": False,
                        "role_createdb": False, "role_createrole": False, "role_canlogin": True,
                        "public_connects": False, "public_schema_create": True,
                        "database_role_connects": True, "error": ""},
            "application_config": {
                "container": "sc-platform-control-dev-odoo-1",
                "environment": {"ENV": "dev", "SC_ENVIRONMENT": "dev",
                                "SC_SOURCE_REVISION": (revision if published_revision is None
                                                       else published_revision),
                                "FRONTEND_BUILD_SHA256": (FRONTEND_BUILD_FINGERPRINT
                                                          if published_fingerprint is None
                                                          else published_fingerprint)},
                "addons_path": [], "missing_addons_roots": [], "error": ""},
            "runtime_identity": {
                "declared": {"SC_SOURCE_REVISION": revision,
                             "FRONTEND_BUILD_SHA256": declared_fingerprint or ""},
                "served_build_sha256": declared_fingerprint or "",
                "build_env_build_sha256": declared_fingerprint or "",
                "artifact_path": "/opt/projects/repos/sce-product-odoo/frontend/apps/web/dist-dev/.build-sha256",
                "fingerprint_error": "" if declared_fingerprint else "no fingerprint",
                "pointer": "/opt/projects/repos/sce-product-odoo/.env.dev"},
        }

    def test_the_verdict_reads_the_identity_the_route_publishes(self):
        """The revision is not the bundle, so both are judged from the container.

        A stack that forwards ``SC_SOURCE_REVISION`` alone answers with an
        anonymous bundle: the revision moves, the served artifact stays at its
        previous generation, and nothing in the readback can tell the two apart.
        The verdict must therefore compare what the *container* publishes with
        the identity the duty declared, including the artifact fingerprint.
        """
        declaration = self.declaration()
        row = picked(declaration, "platform_control")
        identifier = "served_container_publishes_the_declared_runtime_identity"

        verdict = {a["id"]: a["passed"] for a in duty_entry.evaluate(
            row, self.observe(row, **self.served_identity()), declaration, phase="apply")}
        self.assertTrue(verdict[identifier])

        stale = self.served_identity(published_revision="b" * 40)
        verdict = {a["id"]: a["passed"] for a in duty_entry.evaluate(
            row, self.observe(row, **stale), declaration, phase="apply")}
        self.assertFalse(verdict[identifier], "a container publishing another revision is not this duty")

        anonymous = self.served_identity(published_fingerprint="")
        verdict = {a["id"]: a["passed"] for a in duty_entry.evaluate(
            row, self.observe(row, **anonymous), declaration, phase="apply")}
        self.assertFalse(verdict[identifier],
                         "an unidentified served bundle must not read as this duty")

        unreadable = self.served_identity(declared_fingerprint=None)
        verdict = {a["id"]: a["passed"] for a in duty_entry.evaluate(
            row, self.observe(row, **unreadable), declaration, phase="apply")}
        self.assertFalse(verdict[identifier],
                         "an artifact the entry cannot read declares no identity to match")

    def seeded(self):
        """The demo duty observed just after its own seed chain reported."""
        return {
            "cluster": {"present": True, "running": True, "system_identifier": "4242",
                        "data_volume_owner": "sc_demo_db_data", "project": "sc-demo-dev",
                        "config_files": "/opt/x/duty-stack.yml", "error": ""},
            "custody": {"database_present": True, "database_owner": "sc_demo_app",
                        "allow_connections": True, "role_present": True, "role_superuser": False,
                        "role_createdb": False, "role_createrole": False, "role_canlogin": True,
                        "public_connects": False, "public_schema_create": True,
                        "database_role_connects": True, "error": ""},
            "service": {"project": "sc-demo-dev",
                        "running_services": ["db", "redis", "odoo", "nginx"],
                        "containers": {},
                        "module_states": {"smart_core": "installed",
                                          "smart_construction_core": "installed",
                                          "smart_construction_demo": "installed"},
                        "installed_industry_modules": ["smart_construction_core"], "error": ""},
            "seed": {"container": "sc-demo-dev-odoo-1", "carrier": "smart_construction_demo",
                     "profile": "demo_full", "returncode": 0,
                     "executed": ["dictionary", "project_skeleton"],
                     "tail": "[demo.seed] executed=dictionary,project_skeleton",
                     "scope": {"container": "sc-demo-dev-odoo-1", "environment": "demo",
                               "allow_demo_data": "1", "password_present": True, "error": ""}},
        }

    def seed_verdict(self, observation, declaration=None):
        declaration = declaration if declaration is not None else self.declaration()
        row = picked(declaration, "demo")
        return {a["id"]: a["passed"] for a in duty_entry.evaluate(
            row, self.observe(row, **observation), declaration, phase="apply", seed=True)}

    def test_a_demo_seed_is_only_reportable_from_the_declared_carrier_and_switch(self):
        """Three facts, and none of them is satisfied by the declaration alone.

        The chain lives inside the product module the declaration names, and its
        own guard re-reads the database, the environment and the explicit
        demo-data switch *inside the container*. Comparing the observed scope
        with the declaration is what keeps a declaration that says "demo" from
        being reported as a seed by a container that never received the switch.
        """
        verdict = self.seed_verdict(self.seeded())
        self.assertTrue(verdict["demo_seed_names_the_product_carrier_and_profile"], verdict)
        self.assertTrue(verdict["seeded_container_carries_the_declared_demo_data_switch"], verdict)
        self.assertTrue(verdict["the_declared_demo_seed_profile_reported_an_executed_chain"], verdict)

    def test_a_container_that_cannot_prove_the_demo_switch_is_not_seeded(self):
        for key, value in (("environment", "dev"), ("environment", ""), ("allow_demo_data", "0"),
                           ("allow_demo_data", ""), ("password_present", False)):
            with self.subTest(key=key, value=value):
                observation = self.seeded()
                observation["seed"]["scope"][key] = value
                verdict = self.seed_verdict(observation)
                self.assertFalse(
                    verdict["seeded_container_carries_the_declared_demo_data_switch"], verdict
                )
                # The other two facts are about the declaration and the chain's
                # own report; a switch that cannot be proven must not take them
                # down with it, or every fact would collapse into one.
                self.assertTrue(verdict["the_declared_demo_seed_profile_reported_an_executed_chain"])

    def test_a_seed_that_reported_nothing_executed_is_not_a_seed(self):
        """A silent no-op is the failure shape, not an empty success.

        ``run_steps`` returning nothing means the declared profile ran no step:
        the database may be untouched, or the profile may name steps that no
        longer exist. Both have to be reported rather than counted as done.
        """
        for overrides in ({"executed": []}, {"returncode": 1},
                          {"profile": "some_other_profile"}):
            with self.subTest(**overrides):
                observation = self.seeded()
                observation["seed"].update(overrides)
                verdict = self.seed_verdict(observation)
                self.assertFalse(
                    verdict["the_declared_demo_seed_profile_reported_an_executed_chain"], verdict
                )

    def test_a_duty_that_is_not_the_demo_carrier_is_not_seeded(self):
        declaration = copy.deepcopy(self.declaration())
        picked(declaration, "demo")["demo_seed"]["carrier"] = "another_demo_module"
        verdict = self.seed_verdict(self.seeded(), declaration=declaration)
        self.assertFalse(verdict["demo_seed_names_the_product_carrier_and_profile"])

    def test_the_seed_assertions_stay_out_of_every_other_phase(self):
        """Only ``--phase seed`` asks the seed questions.

        The observation is shaped like a completed seed, so a phase that judged
        it would report it: the absence of the three assertions in every other
        phase is what proves they belong to the seed phase alone.
        """
        declaration = self.declaration()
        row = picked(declaration, "demo")
        observation = self.observe(row, **self.seeded())
        seeded = {a["id"]: a["passed"] for a in duty_entry.evaluate(
            row, observation, declaration, phase="apply", seed=True)}
        self.assertTrue(seeded["demo_seed_names_the_product_carrier_and_profile"])
        for phase in ("plan", "apply"):
            with self.subTest(phase=phase):
                other = {a["id"]: a["passed"] for a in duty_entry.evaluate(
                    row, observation, declaration, phase=phase)}
                self.assertNotIn("demo_seed_names_the_product_carrier_and_profile", other)
                self.assertNotIn("seeded_container_carries_the_declared_demo_data_switch", other)
                self.assertNotIn("the_declared_demo_seed_profile_reported_an_executed_chain", other)

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

    def test_a_duty_entry_that_raised_is_never_a_pass(self):
        """A salvaged error is a verdict, not a footnote.

        The 2026-10-16 rebuild reported ``applied: true`` and ``PASS`` for a duty
        the carrier had refused: the error was recorded beside the readback, but
        nothing turned it into an assertion, and the single remaining assertion
        ("the custody is absent as declared") was true of the very fact that
        nothing had been created.
        """
        declaration = prospective(self.declaration(), "demo")
        duty = picked(declaration, "demo")
        observation = self.observe(
            duty, error="RuntimeError: DAILY_DUTY_CREDENTIAL_IDENTITY_DRIFT:DB_USER:demo")
        verdict = {a["id"]: a["passed"] for a in duty_entry.evaluate(
            duty, observation, declaration, phase="apply")}
        self.assertFalse(verdict["duty_entry_completed_without_an_error"])
        self.assertNotIn("custody_absent_as_declared", verdict)

    def test_a_creating_apply_that_lands_no_custody_is_not_a_pass(self):
        """Absence matches a to-be-created declaration only before it is created."""
        declaration = prospective(self.declaration(), "demo")
        duty = picked(declaration, "demo")
        applied = {a["id"]: a["passed"] for a in duty_entry.evaluate(
            duty, self.observe(duty), declaration, phase="apply")}
        self.assertFalse(applied["created_duty_landed_the_declared_custody"])
        self.assertNotIn("custody_absent_as_declared", applied)
        planned = {a["id"]: a["passed"] for a in duty_entry.evaluate(
            duty, self.observe(duty), declaration, phase="plan")}
        self.assertTrue(planned["custody_absent_as_declared"])

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
        # The demo duty is now the *carrier being created*, which is exactly the
        # duty this entry must render. The rule under test is about a duty that
        # already exists, so it is asked of one whose custody is already declared
        # compliant rather than of whichever duty the file currently points at
        # that shape.
        verdict = self.verdict(
            declaration, "platform_control", stack={"skipped": "not to-be-created"})
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
                "SC_ALLOW_DEMO_DATA": (
                    "1" if row["data_purpose"] == "demo" else "0"
                ),
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

    def test_a_staged_service_start_is_judged_by_its_steps(self):
        """The initialize phase starts services in stages, not with one return code.

        ``initialize`` waits for the cluster services and only then starts the
        application, so its start entry is a list of per-stage steps while the
        ``stack`` phase's entry is a single ``start_cluster`` return code.
        Reading only ``returncode`` judged the initialize phase's own step list
        as "not created from the reviewed definition" for ever, and on
        2026-10-16 that reported a duty whose services had in fact started as a
        failed one. Both shapes are the entry's own output, so both are read; a
        step list that reports a failure, and one that reports nothing started,
        still fail.
        """
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
                "SC_ALLOW_DEMO_DATA": (
                    "1" if row["data_purpose"] == "demo" else "0"
                ),
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

        def verdict_for(start):
            staged = copy.deepcopy(stack)
            staged["start"] = start
            return {a["id"]: a["passed"] for a in duty_entry.evaluate(
                row, {"duty": row["duty"], "cluster": cluster, "custody": custody,
                      "stack": staged},
                declaration)}

        verdict = verdict_for({
            "declared": ["db", "redis", "odoo", "nginx"],
            "steps": [{"stage": "cluster", "returncode": 0},
                      {"stage": "application", "returncode": 0}],
        })
        self.assertTrue(verdict["stack_was_created_from_the_reviewed_definition"])

        verdict = verdict_for({
            "declared": ["db", "redis", "odoo", "nginx"],
            "steps": [{"stage": "cluster", "returncode": 0},
                      {"stage": "application", "returncode": 1}],
        })
        self.assertFalse(verdict["stack_was_created_from_the_reviewed_definition"])

        verdict = verdict_for({"declared": ["db", "redis", "odoo", "nginx"], "steps": []})
        self.assertFalse(verdict["stack_was_created_from_the_reviewed_definition"])

        verdict = verdict_for({"returncode": 1, "error": "boom"})
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
                   "data_volume_owner": "sc_tenant_sample_dev_db_data",
                   "project": "sc-tenant-sample-dev", "config_files": ""}
        custody = {"database_present": True, "database_owner": "sc_tenant_sample_dev_app",
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
        # The 2026-10-16 rebuild closed the only gap the shipped declaration
        # carried, so the demo duty no longer *is* the gap shape. The rule stays
        # proven by asking for that shape explicitly instead of reading it off
        # whichever duty currently happens to be in it.
        declaration = as_declared_gap(self.declaration(), "demo")
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

    def test_a_serving_duty_must_show_the_declared_runtime_environment(self):
        """A duty that says it serves must prove its container reads what the
        declaration names, and that every addon root it was rendered with exists.

        Without this the 2026-10-16 shape passes every other assertion: the
        declaration, the env file, the custody facts and the module states all
        agree while the container sees neither `ENV` nor `SC_ENVIRONMENT`, keeps
        an `addons_path` entry for an unmounted directory, and answers 500 on
        every `/api/*` route.

        The assertion belongs to a face that serves: a duty whose cluster is not
        up is judged by the creation assertions and never reaches the
        application readback.
        """
        row = self.initialized(self.declaration(), "platform_control")
        application = {
            "container": "sc-platform-control-dev-odoo-1",
            "environment": {"ENV": "dev", "SC_ENVIRONMENT": "dev"},
            "addons_path": ["/mnt/source-addons"],
            "missing_addons_roots": [],
            "error": "",
        }
        verdict = self.verdict(row, application_config=application)
        self.assertTrue(verdict["application_container_reads_the_declared_runtime_environment"])
        self.assertTrue(verdict["served_addons_path_has_no_unmounted_root"])

        blind = copy.deepcopy(application)
        blind["environment"] = {"ENV": "", "SC_ENVIRONMENT": ""}
        blind["addons_path"] = ["/mnt/source-addons", "/mnt/test-addons"]
        blind["missing_addons_roots"] = ["/mnt/test-addons"]
        verdict = self.verdict(row, application_config=blind)
        self.assertFalse(verdict["application_container_reads_the_declared_runtime_environment"])
        self.assertFalse(verdict["served_addons_path_has_no_unmounted_root"])

        half_blind = copy.deepcopy(application)
        half_blind["environment"] = {"ENV": "dev", "SC_ENVIRONMENT": ""}
        verdict = self.verdict(row, application_config=half_blind)
        self.assertFalse(verdict["application_container_reads_the_declared_runtime_environment"])

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

    def test_a_role_that_already_exists_cannot_be_served_by_another_secret(self):
        """The designated credential is a checked fact, not an assumption.

        The 2026-10-16 demo refresh recreated the application with a freshly
        rendered password while the ``odoo`` role inside ``sc_dev_db_data`` kept
        the one it was created with: every service but the application reported
        healthy, and the only symptom was an application that restarted forever.
        Reading the designated credential back makes that disagreement a failed
        assertion instead of an incident.
        """
        accepted = {"designated": True, "authenticated": True, "role": "odoo",
                    "database": "sc_demo", "source": "/opt/projects/repos/sce-product-odoo/.env.dev",
                    "from_source": True, "error": ""}
        verdict = self.verdict(self.initialized(self.declaration(), "demo"),
                              application_credential=accepted)
        self.assertTrue(verdict["declared_application_credential_authenticates_the_cluster"])

        rejected = dict(accepted, authenticated=False,
                        error='FATAL:  password authentication failed for user "odoo"')
        verdict = self.verdict(self.initialized(self.declaration(), "demo"),
                              application_credential=rejected)
        self.assertFalse(verdict["declared_application_credential_authenticates_the_cluster"])

        unobserved = self.verdict(self.initialized(self.declaration(), "demo"))
        self.assertNotIn("declared_application_credential_authenticates_the_cluster", unobserved)

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

    def __init__(self, base_installed=True, entrypoint_log="", inspect_stdout="",
                 module_states=None, container_environment=None, demo_password_present=True,
                 seed_executed=("dictionary",), seed_returncode=0):
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
        #: What ``docker inspect`` reports for the cluster container. The empty
        #: default is a duty whose cluster is not there yet, which is what the
        #: ordering tests want; a seed runs against a *running* duty, so it
        #: hands the readback shape in.
        self.inspect_stdout = inspect_stdout
        #: The module states the duty's own catalog reports.
        self.module_states = dict(module_states or {})
        #: What ``printenv`` answers from inside the application container.
        self.container_environment = dict(container_environment or {})
        self.demo_password_present = demo_password_present
        self.seed_executed = list(seed_executed)
        self.seed_returncode = seed_returncode

    def run(self, command, **kwargs):
        self.commands.append(list(command))
        for index, predicate in enumerate(self.raises):
            if predicate(list(command)):
                del self.raises[index]
                raise self.TimeoutExpired(command, kwargs.get("timeout"))
        if list(command[:2]) == ["docker", "ps"]:
            project = "sc-platform-control-dev"
            for item in command:
                if str(item).startswith("label=com.docker.compose.project="):
                    project = str(item).split("=", 2)[2]
            return FakeResult(stdout="%s-odoo-1\n" % (project,))
        if list(command[:2]) == ["docker", "inspect"]:
            if "--format" in command:
                return FakeResult(stdout="")
            return FakeResult(stdout=self.inspect_stdout)
        text = " ".join(str(item) for item in command)
        if list(command[:2]) == ["docker", "logs"]:
            return FakeResult(stdout=self.entrypoint_log)
        if list(command[:2]) == ["docker", "exec"] and "printenv" in command:
            key = command[command.index("printenv") + 1]
            return FakeResult(stdout=self.container_environment.get(key, "") + "\n")
        if (list(command[:2]) == ["docker", "exec"] and "-lc" in command
                and "SC_DEMO_USER_PASSWORD" in text):
            return FakeResult(stdout="present\n" if self.demo_password_present else "absent\n")
        if "odoo" in command and "shell" in command:
            return FakeResult(
                stdout="[demo.seed] executed=%s\n" % (",".join(self.seed_executed),),
                returncode=self.seed_returncode,
            )
        if "to_regclass('public.ir_module_module')" in text:
            return FakeResult(stdout="t\n" if self.base_installed else "f\n")
        if "WHERE name = 'base'" in text:
            return FakeResult(stdout="installed\n" if self.base_installed else "\n")
        if "FROM ir_module_module WHERE name IN (" in text:
            return FakeResult(stdout="".join(
                "%s|%s\n" % (name, state) for name, state in sorted(self.module_states.items())))
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
            "database": "sc_platform_control" if name == "platform_control" else "sc_tenant_sample_dev",
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

    def demo_duty(self):
        """The demo carrier the 2026-10-16 rebuild creates, as the carrier sees it."""
        return {
            "duty": "demo",
            "database": "sc_demo",
            "database_role": "sc_demo_app",
            "dbfilter": "^sc_demo$",
            "data_purpose": "demo",
            "demo_seed": {"carrier": "smart_construction_demo", "profile": "demo_full",
                          "stages": ["release_seed", "profile"],
                          "authority": "docs/ops/iterations/x.md",
                          "reason": "the owner named the product's own demo carrier"},
            "custody": {"database_present": True, "database_role_present": True,
                        "role_compliance": "compliant", "service_face": "initialized"},
            "cluster": {"container": "sc-demo-dev-db-1",
                        "compose_project": "sc-demo-dev",
                        "data_volume": "sc_demo_db_data",
                        "maintenance_role": "sc_demo_maintenance"},
            "storage": {"redis_data_volume": "sc_demo_redis_data",
                        "odoo_data_volume": "sc_demo_odoo_data"},
            "routing": {"odoo_loopback_port": 8070, "nginx_host_port": 18081},
            "stack": {
                "services": ["db", "redis", "odoo", "nginx"],
                "modules": ["smart_core", "smart_construction_core", "smart_construction_demo"],
                "runtime_env": "demo",
                "product_root": "/opt/projects/repos/sce-product-odoo",
                "postgres_image": "postgres:15",
                "odoo_image": "odoo17-odoo:latest",
                "frontend_dist_dir": "/opt/projects/repos/sce-product-odoo/frontend/apps/web/dist-dev",
                "demo_addons_root": "/opt/projects/repos/sce-product-odoo/demo_addons",
                "customer_addons_root": "/opt/projects/runtime-addons-empty",
            },
        }

    def running_cluster(self, duty):
        """The ``docker inspect`` readback of a cluster that is already serving."""
        return json.dumps([{
            "State": {"Running": True},
            "Config": {"Labels": {
                "com.docker.compose.project": duty["cluster"]["compose_project"],
                "com.docker.compose.project.config_files": "/opt/x/duty-stack.yml",
            }},
            "Mounts": [{"Destination": "/var/lib/postgresql/data",
                        "Name": duty["cluster"]["data_volume"]}],
        }])

    def installs(self, fake):
        """Module installations: ``odoo -i``, which a seed must never issue."""
        return [c for c in fake.commands
                if c[:2] == ["docker", "exec"] and "-i" in c and "odoo" in c
                and "shell" not in c]

    def seeds(self, fake):
        return [c for c in fake.commands if "odoo" in c and "shell" in c]

    def payload(self, duties, ops_root, *, mode="apply", phase="initialize",
                bootstrap_timeout=1800, bootstrap_poll=15, frontend_build_env=None):
        import hashlib

        build_env_file = os.path.join(ops_root, "absent-build.env")
        if frontend_build_env is not None:
            build_env_file = os.path.join(ops_root, "build.env")
            with open(build_env_file, "w") as stream:
                stream.write(frontend_build_env)
        return {
            "mode": mode,
            "phase": phase,
            "product_root": "/opt/projects/repos/sce-product-odoo",
            "ops_root": ops_root,
            "platform_admin_database": "sc_platform_control",
            "frontend_build_env_file": build_env_file,
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
                bootstrap_timeout=1800, bootstrap_poll=15, frontend_build_env=None,
                fingerprint=FRONTEND_BUILD_FINGERPRINT):
        with tempfile.TemporaryDirectory() as ops_root:
            provision_frontend_artifact(ops_root, duties, fingerprint=fingerprint)
            rendered = duty_entry.render_remote_program(
                self.payload(duties, ops_root, mode=mode, phase=phase,
                             bootstrap_timeout=bootstrap_timeout, bootstrap_poll=bootstrap_poll,
                             frontend_build_env=frontend_build_env)
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

    def test_a_duty_that_cannot_name_its_served_frontend_build_is_never_created(self):
        """A stack that serves a bundle it cannot identify is refused, not started.

        ``/api/runtime-version`` is the only place the running system answers
        which frontend sits behind the route, and the acceptance lanes key the
        reuse of their observations on that artifact. A duty rendered without it
        would publish an anonymous bundle and silently degrade every reuse key
        from the artifact to the deployment, so the render refuses -- and the
        refusal must arrive before anything is started, not as a healthy stack
        nobody can identify afterwards.
        """
        cases = (
            ("no artifact in the declared output directory", None, None),
            ("an artifact that is not a sha256", "not-a-frontend-fingerprint", None),
            ("an artifact the deployed build environment contradicts", FRONTEND_BUILD_FINGERPRINT,
             "VITE_PLATFORM_ADMIN_DB=sc_platform_control\nFRONTEND_BUILD_SHA256=%s\n" % ("f" * 64,)),
        )
        for label, fingerprint, frontend_env in cases:
            with self.subTest(label):
                fake = FakeSubprocess()
                report = self.execute(fake, [self.duty()], fingerprint=fingerprint,
                                      frontend_build_env=frontend_env)
                entry = report["duties"][0]
                self.assertIn("DAILY_DUTY_FRONTEND_BUILD_IDENTITY", entry["error"] or "", entry)
                self.assertEqual(self.ups(fake), [],
                                 "a duty the entry cannot identify must not be started")

    def test_the_environment_vector_is_read_in_one_round_trip(self):
        """Every declared duty is walked on every run, so the probe is one call.

        A per-key ``docker exec`` multiplies the container-namespace cost by the
        number of identity keys for facts that are read in the same instant, and
        the runtime environment, the published identity and the addon-root scan
        are all read together. They therefore travel in a single NUL-separated
        probe, and a regression back to separate container entries fails here.
        """
        fake = FakeSubprocess()
        self.execute(fake, [self.duty()])
        probes = [command for command in fake.commands
                  if command[:2] == ["docker", "exec"] and "printf '%s\\0'" in " ".join(command)]
        self.assertEqual(len(probes), 1, fake.commands)
        for key in ("ENV", "SC_ENVIRONMENT", "SC_SOURCE_REVISION", "FRONTEND_BUILD_SHA256"):
            self.assertIn('"$%s"' % (key,), probes[0][-1])
        self.assertIn("addons_path", probes[0][-1])

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

    def seeded_fake(self, duty, **overrides):
        settings = {
            "inspect_stdout": self.running_cluster(duty),
            "module_states": {name: "installed" for name in duty["stack"]["modules"]},
            "container_environment": {"SC_ENVIRONMENT": "demo", "SC_ALLOW_DEMO_DATA": "1"},
        }
        settings.update(overrides)
        return FakeSubprocess(**settings)

    def test_the_seed_phase_runs_the_declared_profile_without_installing_anything(self):
        """The seed is the product's own chain, not a module install or a direct write.

        ``--phase initialize`` already installed the declared set, and
        ``--phase seed`` only writes business rows -- through the profile the
        *declaration* names, inside the running container. A seed that issued
        ``odoo -i`` would be a second initializer, and one that wrote a terminal
        state directly would be the bypass closed in PR #665/#666.
        """
        duty = self.demo_duty()
        fake = self.seeded_fake(duty)
        report = self.execute(fake, [duty], phase="seed")
        settled = report["duties"][0]
        self.assertEqual(settled["error"], "")
        self.assertFalse(self.installs(fake), "the seed phase installs no module set")
        self.assertFalse([c for c in fake.commands if "stop-after-init" in c])

        seeded = self.seeds(fake)
        self.assertEqual(len(seeded), 1, "one seed chain, run once")
        command = seeded[0]
        self.assertIn("SC_DEMO_SEED_PROFILE=demo_full", command)
        # The chain is the declared stage list, not the profile alone: the
        # release scenario set has to run before the profile, because the
        # profile's payment step resolves an S69 contract xmlid that only that
        # set creates. A command that carried the profile without the stages
        # would re-open the 2026-10-16 shape.
        self.assertIn("SC_DEMO_SEED_STAGES=release_seed,profile", command)
        self.assertEqual(command[command.index("-d") + 1], "sc_demo")
        self.assertIn("--no-http", command)
        self.assertEqual(settled["seed"]["profile"], "demo_full")
        self.assertEqual(settled["seed"]["stages"], ["release_seed", "profile"])
        self.assertEqual(settled["seed"]["executed"], ["dictionary"])
        self.assertEqual(settled["seed"]["carrier"], "smart_construction_demo")

    def test_a_duty_whose_declared_stages_are_not_runnable_is_not_seeded(self):
        """A declaration that names no runnable chain seeds nothing.

        The declaration validation refuses this shape before any write, and the
        seed itself refuses it again rather than running whichever stage it can
        still recognise: a chain the declaration did not name is not a chain this
        entry may report as the duty's demo data.
        """
        for stages in ([], ["release_seed"], ["release_seed", "profile", "extra"]):
            with self.subTest(stages=stages):
                duty = self.demo_duty()
                duty["demo_seed"]["stages"] = stages
                fake = self.seeded_fake(duty)
                report = self.execute(fake, [duty], phase="seed")
                settled = report["duties"][0]
                self.assertEqual(self.seeds(fake), [], "nothing runs for a chain that is not runnable")
                self.assertIn("stage list", settled["seed"]["error"])
                self.assertNotIn("executed", settled["seed"],
                                 "a chain that never ran reports no executed steps")
                self.assertEqual(settled["seed"]["stages"], stages)

    def test_the_seeded_rows_are_only_claimed_visible_after_the_application_is_restarted(self):
        """The serving process holds its own registry and its own ACL caches.

        Reporting seeded rows from a container that has not reloaded them is a
        claim rather than an observation, so the restart and the health wait are
        ordered *after* the chain and asserted here.
        """
        duty = self.demo_duty()
        fake = self.seeded_fake(duty)
        self.execute(fake, [duty], phase="seed")
        seed = fake.commands.index(self.seeds(fake)[0])
        restart = self.index_of(fake, lambda c: c[:2] == ["docker", "restart"])
        wait = self.index_of(fake, lambda c: c[-2:] == ["--wait", "odoo"])
        self.assertLess(seed, restart)
        self.assertLess(restart, wait)

    def test_a_container_that_cannot_prove_the_demo_switch_is_never_seeded(self):
        for key, value in (("SC_ENVIRONMENT", "dev"), ("SC_ALLOW_DEMO_DATA", "0"),
                           ("SC_ALLOW_DEMO_DATA", "")):
            with self.subTest(key=key, value=value):
                duty = self.demo_duty()
                environment = {"SC_ENVIRONMENT": "demo", "SC_ALLOW_DEMO_DATA": "1"}
                environment[key] = value
                fake = self.seeded_fake(duty, container_environment=environment)
                report = self.execute(fake, [duty], phase="seed")
                settled = report["duties"][0]
                self.assertFalse(self.seeds(fake), "the chain may not run without the switch")
                self.assertIn("demo-data switch", settled["seed"]["error"])

    def test_a_container_without_a_demo_password_is_never_seeded(self):
        """The chain's own guard needs the password; a container without one refuses.

        The value is never read back, which is why this models *presence* rather
        than a password: the entry reports whether the container holds one and
        nothing more.
        """
        duty = self.demo_duty()
        fake = self.seeded_fake(duty, demo_password_present=False)
        report = self.execute(fake, [duty], phase="seed")
        self.assertFalse(self.seeds(fake))
        self.assertIn("no demo user password", report["duties"][0]["seed"]["error"])

    def test_a_chain_that_reported_nothing_executed_is_not_a_completed_seed(self):
        duty = self.demo_duty()
        fake = self.seeded_fake(duty, seed_executed=())
        report = self.execute(fake, [duty], phase="seed")
        settled = report["duties"][0]
        self.assertEqual(settled["seed"]["executed"], [])
        self.assertIn("did not report an executed chain", settled["seed"]["error"])
        self.assertFalse([c for c in fake.commands if c[:2] == ["docker", "restart"]],
                         "a chain that ran no step has nothing to reload")

    def test_a_duty_that_is_not_fully_installed_is_never_seeded(self):
        """Seeding is downstream of the declared module set.

        The chain lives inside the demo module, so a duty that has not installed
        it is refused rather than seeded into a database that cannot run the
        profile.
        """
        duty = self.demo_duty()
        fake = self.seeded_fake(
            duty, module_states={"smart_core": "installed", "smart_construction_core": "installed"})
        report = self.execute(fake, [duty], phase="seed")
        settled = report["duties"][0]
        self.assertFalse(self.seeds(fake))
        self.assertIn("smart_construction_demo", settled["seed"]["missing_modules"])

    def test_a_stopped_cluster_is_never_seeded(self):
        duty = self.demo_duty()
        fake = self.seeded_fake(duty, inspect_stdout="")
        report = self.execute(fake, [duty], phase="seed")
        self.assertFalse(self.seeds(fake))
        self.assertIn("cluster is not running", report["duties"][0]["seed"]["error"])


class ProbeSubprocess:
    """Stands in for ``subprocess`` for the application credential probe."""

    def __init__(self, *, address="192.168.32.9", accepts=True):
        self.commands = []
        self.environments = []
        self.address = address
        self.accepts = accepts

    def run(self, command, **kwargs):
        self.commands.append([str(item) for item in command])
        self.environments.append(dict(kwargs.get("env") or {}))
        if list(command[:2]) == ["docker", "inspect"] and "--format" in command:
            return FakeResult(stdout=self.address + " \n")
        if self.accepts:
            return FakeResult(stdout="1\n")
        return FakeResult(
            stdout="",
            stderr='psql: error: connection to server failed: FATAL:  password authentication failed for user "odoo"',
            returncode=2,
        )


class ApplicationCredentialTests(unittest.TestCase):
    """A duty that adopts a cluster must adopt that cluster's credential.

    The 2026-10-16 demo refresh recreated the application against a freshly
    rendered secret while the ``odoo`` role inside ``sc_dev_db_data`` kept the
    password it was created with. Every service but the application reported
    healthy, so the disagreement had to be found by reading the application's
    log. These tests pin both halves of the fix: the credential the declaration
    designates is probed over the network path the application itself uses, and
    the rendered duty environment is converged onto that designation.
    """

    COMPOSE_TEXT = "services:\n  db:\n    image: postgres:15\n"
    ENV_TEMPLATE = (
        "DB_NAME=@DB_NAME@\n"
        "DB_USER=@DB_USER@\n"
        "DB_PASSWORD=@DB_PASSWORD@\n"
        "DB_MAINTENANCE_USER=@DB_MAINTENANCE_USER@\n"
        "DB_MAINTENANCE_PASSWORD=@DB_MAINTENANCE_PASSWORD@\n"
        "ADMIN_PASSWD=@ADMIN_PASSWD@\n"
        "JWT_SECRET=@JWT_SECRET@\n"
        "SC_BOOTSTRAP_SECRET=@SC_BOOTSTRAP_SECRET@\n"
        "FRONTEND_BUILD_SHA256=@FRONTEND_BUILD_SHA256@\n"
        "LIST_DB=false\n"
    )
    ADOPTED = "a" * 64

    def duty(self, source_env_file, frontend_dist_dir="/opt/projects/repos/sce-product-odoo/frontend/apps/web/dist-dev"):
        return {
            "duty": "demo",
            "database": "sc_demo",
            "database_role": "odoo",
            "dbfilter": "^sc_demo$",
            "cluster": {"container": "sc-backend-odoo-dev-db-1",
                        "compose_project": "sc-backend-odoo-dev",
                        "data_volume": "sc_dev_db_data",
                        "maintenance_role": "odoo"},
            "storage": {"redis_data_volume": "sc_dev_redis_data",
                        "odoo_data_volume": "sc_dev_odoo_data"},
            "routing": {"odoo_loopback_port": 8070, "nginx_host_port": 18081},
            "stack": {"compose_file": "config/ops/daily_runtime_duty_stack.yml",
                      "env_template": "config/ops/daily_runtime_duty_stack.env",
                      "runtime_env": "dev", "odoo_image": "odoo17-odoo:latest",
                      "postgres_image": "postgres:15",
                      "product_root": "/opt/projects/repos/sce-product-odoo",
                      "frontend_dist_dir": frontend_dist_dir,
                      "demo_addons_root": "/opt/projects/runtime-addons-empty",
                      "customer_addons_root": "/opt/projects/runtime-addons-empty",
                      "services": ["db", "redis", "odoo", "nginx"],
                      "modules": ["smart_construction_core"]},
            "credential_source": {"env_file": source_env_file, "key": "DB_PASSWORD",
                                  "reason": "the cluster predates this duty",
                                  "owning_task": "DAILY-RUNTIME-DEMO-APP-ROLE-01"},
        }

    def carrier(self, callback, fake=None):
        with tempfile.TemporaryDirectory() as ops_root:
            import hashlib

            payload = {
                "mode": "plan", "phase": "plan",
                "product_root": "/opt/projects/repos/sce-product-odoo",
                "ops_root": ops_root,
                "platform_admin_database": "sc_platform_control",
                "frontend_build_env_file": os.path.join(ops_root, "absent-build.env"),
                "source_revision": "a" * 40,
                "compose_sha256": hashlib.sha256(self.COMPOSE_TEXT.encode("utf-8")).hexdigest(),
                "stack": {"compose_text": self.COMPOSE_TEXT},
                "env_template": self.ENV_TEMPLATE,
                "data_destination": "/var/lib/postgresql/data",
                "duties": [],
            }
            rendered = duty_entry.render_remote_program(payload)
            namespace = {"__name__": "__carrier__"}
            if fake is None:
                with contextlib.redirect_stdout(io.StringIO()):
                    exec(compile(rendered, "<remote-carrier>", "exec"), namespace)
                return callback(namespace, ops_root)
            saved = sys.modules.get("subprocess")
            sys.modules["subprocess"] = fake
            try:
                # The carrier binds ``subprocess`` at import time, so the stand-in
                # has to be installed *before* the rendered program is executed.
                with contextlib.redirect_stdout(io.StringIO()):
                    exec(compile(rendered, "<remote-carrier>", "exec"), namespace)
                return callback(namespace, ops_root)
            finally:
                if saved is None:
                    sys.modules.pop("subprocess", None)
                else:
                    sys.modules["subprocess"] = saved

    def source_file(self, root, password):
        path = os.path.join(root, "environment.env")
        with open(path, "w") as stream:
            stream.write("DB_PASSWORD=%s\nOTHER=value\n" % (password,))
        return path

    def test_the_probe_leaves_the_container_and_comes_back_over_the_network(self):
        """A probe that stays inside the database proves nothing.

        ``pg_hba`` grants ``trust`` on the local socket and on ``127.0.0.1``, so
        a probe that connects there succeeds with *any* password -- which is
        exactly the false pass this test was written after. The probe has to
        reach the cluster's own network address, and the secret must travel in
        the process environment rather than in an argument vector every account
        on the host can read.
        """
        with tempfile.TemporaryDirectory() as root:
            source = self.source_file(root, self.ADOPTED)
            fake = ProbeSubprocess()

            def run(namespace, _ops_root):
                return namespace["application_credential_facts"](self.duty(source))

            facts = self.carrier(run, fake)
        self.assertTrue(facts["designated"])
        self.assertTrue(facts["from_source"])
        self.assertTrue(facts["authenticated"], facts)
        self.assertEqual(facts["source"], source)
        probe = fake.commands[-1]
        self.assertEqual(probe[:3], ["docker", "exec", "-e"])
        self.assertIn("PGPASSWORD", probe)
        self.assertIn("192.168.32.9", probe)
        self.assertNotIn("/var/lib/postgresql/data", probe)
        self.assertFalse(
            [item for item in probe if item in ("127.0.0.1", "localhost", "::1")],
            "the probe must not connect where pg_hba grants trust",
        )
        self.assertNotIn(self.ADOPTED, " ".join(probe))
        self.assertEqual(fake.environments[-1].get("PGPASSWORD"), self.ADOPTED)

    def test_a_rejected_designated_credential_is_reported_not_defaulted(self):
        with tempfile.TemporaryDirectory() as root:
            source = self.source_file(root, self.ADOPTED)
            fake = ProbeSubprocess(accepts=False)

            def run(namespace, _ops_root):
                return namespace["application_credential_facts"](self.duty(source))

            facts = self.carrier(run, fake)
        self.assertTrue(facts["designated"])
        self.assertFalse(facts["authenticated"])
        self.assertIn("password authentication failed", facts["error"])

    def test_a_source_without_the_declared_key_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            source = os.path.join(root, "environment.env")
            with open(source, "w") as stream:
                stream.write("SOMETHING_ELSE=value\n")
            fake = ProbeSubprocess()

            def run(namespace, _ops_root):
                return namespace["application_credential_facts"](self.duty(source))

            facts = self.carrier(run, fake)
        self.assertFalse(facts["designated"])
        self.assertIsNone(facts["authenticated"])
        self.assertIn("carries no DB_PASSWORD", facts["error"])
        self.assertEqual(fake.commands, [], "an unresolved credential must not be probed")

    def test_a_cluster_without_a_network_address_is_not_probed(self):
        with tempfile.TemporaryDirectory() as root:
            source = self.source_file(root, self.ADOPTED)
            fake = ProbeSubprocess(address="")

            def run(namespace, _ops_root):
                return namespace["application_credential_facts"](self.duty(source))

            facts = self.carrier(run, fake)
        self.assertTrue(facts["designated"])
        self.assertIsNone(facts["authenticated"])
        self.assertIn("has no network address", facts["error"])

    def test_the_rendered_environment_is_converged_onto_the_designated_credential(self):
        """The rendered duty environment must equal what the role already accepts.

        A rendered file that disagrees with the declaration's designated source
        is the defect this entry existed to prevent, so it is rewritten: the
        authority for a cluster this duty did not create is the file the
        declaration names, not whatever secret an earlier render generated.
        """
        with tempfile.TemporaryDirectory() as root:
            source = self.source_file(root, self.ADOPTED)
            duty = self.duty(source, provision_frontend_artifact(root, []))

            def run(namespace, ops_root):
                stale = os.path.join(ops_root, "demo.env")
                with open(stale, "w") as stream:
                    stream.write("DB_PASSWORD=%s\nDB_MAINTENANCE_PASSWORD=%s\n"
                                 % ("b" * 64, "c" * 64))
                os.chmod(stale, 0o600)
                facts = namespace["materialise_stack_files"](duty)
                return (facts, dict(namespace["read_env_file"](stale)),
                        os.stat(stale).st_mode & 0o777)

            facts, rendered, mode = self.carrier(run)
        self.assertTrue(facts["credentials_created"])
        self.assertEqual(facts["env_keys"]["FRONTEND_BUILD_SHA256"], FRONTEND_BUILD_FINGERPRINT)
        self.assertEqual(rendered["DB_PASSWORD"], self.ADOPTED)
        self.assertEqual(rendered["DB_MAINTENANCE_PASSWORD"], self.ADOPTED)
        self.assertNotIn("b" * 64, json.dumps(rendered))
        self.assertNotIn("c" * 64, json.dumps(rendered))
        self.assertEqual(facts["credential_adopted_from"], source)
        self.assertEqual(facts["credentials_mode"], "0o600")
        self.assertEqual(mode, 0o600)

    def rebuilt_demo_duty(self, duty):
        """The demo duty as the 2026-10-16 rebuild declares it.

        The legacy carrier and the rebuilt duty share the duty *name*, not the
        carrier: the rebuilt one names its own cluster, its own application role
        and its own maintenance role, so it creates the credential it uses.
        """
        duty = copy.deepcopy(duty)
        duty.pop("credential_source")
        duty["database_role"] = "sc_demo_app"
        duty["cluster"]["compose_project"] = "sc-demo-dev"
        duty["cluster"]["container"] = "sc-demo-dev-db-1"
        duty["cluster"]["maintenance_role"] = "sc_demo_maintenance"
        return duty

    def test_a_foreign_carrier_file_is_never_adopted_or_overwritten(self):
        """One duty name may not become two carriers' environment file.

        ``demo.env`` still belongs to ``sc-backend-odoo-dev`` and still owns the
        surviving cluster's role password. Adopting it would refuse the rebuild
        for ever; overwriting it would destroy a credential the protected
        historic source still needs and render a duty the legacy route does not
        revive from. The file is therefore left byte-identical and the rebuilt
        duty is rendered into its carrier-qualified name.
        """
        with tempfile.TemporaryDirectory() as root:
            duty = self.rebuilt_demo_duty(self.duty(
                os.path.join(root, "absent.env"), provision_frontend_artifact(root, [])))
            legacy = ("DUTY_NAME=demo\nCOMPOSE_PROJECT_NAME=sc-backend-odoo-dev\n"
                      "DB_NAME=sc_demo\nDB_USER=odoo\nDB_MAINTENANCE_USER=odoo\n"
                      "DB_PASSWORD=%s\n" % ("f" * 64,))

            def run(namespace, ops_root):
                path = os.path.join(ops_root, "demo.env")
                with open(path, "w") as stream:
                    stream.write(legacy)
                os.chmod(path, 0o600)
                with open(path, "rb") as stream:
                    before = stream.read()
                facts = namespace["materialise_stack_files"](duty)
                with open(path, "rb") as stream:
                    after = stream.read()
                return facts, before, after

            facts, before, after = self.carrier(run)
        self.assertEqual(before, after, "the legacy carrier's file must not be touched")
        self.assertEqual(os.path.basename(facts["env_path"]), "sc-demo-dev.env")
        self.assertEqual(os.path.basename(facts["credentials_path"]), "sc-demo-dev.env")
        self.assertTrue(facts["credentials_created"])
        self.assertEqual(facts["credentials_mode"], "0o600")
        self.assertEqual(facts["env_mode"], "0o600")

    def test_a_file_that_claims_this_carrier_but_drifts_still_refuses(self):
        """Carrier identity resolves the file; it never excuses a drifted one.

        A file that names *this* carrier is this duty's own file, so an identity
        key that disagrees with the declaration is a drift to refuse, not a
        second carrier to route around.
        """
        with tempfile.TemporaryDirectory() as root:
            duty = self.rebuilt_demo_duty(self.duty(os.path.join(root, "absent.env")))

            def run(namespace, ops_root):
                path = os.path.join(ops_root, "sc-demo-dev.env")
                with open(path, "w") as stream:
                    stream.write("COMPOSE_PROJECT_NAME=sc-demo-dev\nDB_USER=odoo\n")
                os.chmod(path, 0o600)
                return namespace["duty_credentials"](duty)

            with self.assertRaises(RuntimeError) as raised:
                self.carrier(run)
        self.assertIn("IDENTITY_DRIFT", str(raised.exception))


    def test_a_duty_that_creates_its_own_role_still_generates_its_own_secret(self):
        """Adoption is not a general escape hatch: no source, no adoption."""
        with tempfile.TemporaryDirectory() as root:
            duty = self.duty(os.path.join(root, "absent.env"))
            duty.pop("credential_source")
            duty["cluster"]["maintenance_role"] = "sc_demo_maintenance"

            def run(namespace, ops_root):
                values, path, created = namespace["duty_credentials"](duty)
                return values, os.stat(path).st_mode & 0o777

            values, mode = self.carrier(run)
        self.assertTrue(values["DB_PASSWORD"])
        self.assertEqual(len(values["DB_PASSWORD"]), 64)
        self.assertNotEqual(values["DB_PASSWORD"], values["DB_MAINTENANCE_PASSWORD"])
        self.assertEqual(mode, 0o600)

    def test_one_role_has_one_password(self):
        """The declared gap is one login, so two duty keys cannot disagree."""
        with tempfile.TemporaryDirectory() as root:
            duty = self.duty(os.path.join(root, "absent.env"))
            duty.pop("credential_source")

            def run(namespace, ops_root):
                stale = os.path.join(ops_root, "demo.env")
                with open(stale, "w") as stream:
                    stream.write("DB_PASSWORD=%s\nDB_MAINTENANCE_PASSWORD=%s\n"
                                 % ("d" * 64, "e" * 64))
                return namespace["duty_credentials"](duty)[0]

            values = self.carrier(run)
        self.assertEqual(values["DB_PASSWORD"], values["DB_MAINTENANCE_PASSWORD"])


if __name__ == "__main__":
    unittest.main()
