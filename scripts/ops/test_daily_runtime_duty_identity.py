#!/usr/bin/env python3
"""Unit tests for the governed duty-identity resolver and its managed binding.

The product tree may not carry a customer identity, so the concrete binding of a
customer duty lives in the managed directory under ``ops_root``, outside the git
checkout.  These tests pin the properties that relocation depends on:

* the tracked template carries the generic duties and names the managed
  directory as the source of a customer duty, and it carries no customer duty
  itself;
* resolution merges the two documents and refuses a missing, unreadable,
  placeholder-carrying, wrongly named, duplicated or self-contradicting binding
  instead of substituting a guessed identity;
* the explicit override names a source, it is never a fallback, so an unset
  value still reads the governed document and stops when that is absent;
* the write path stores the reviewed bytes 0600 outside the checkout, keeps the
  previous revision, replaces the file atomically and reads the digest back;
* the duty entry reads the managed binding through this resolver and refuses
  when the host does not hold the revision it reviewed.

They are pure: no host is reached and no container is started.
"""

from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.ops import daily_runtime_database_duty as duty_entry
from scripts.ops import daily_runtime_duty_identity as identity


ROOT = Path(__file__).resolve().parents[2]
DECLARATION = ROOT / "config/ops/daily_runtime_database_duties.v1.json"
ENTRY = ROOT / "config/ops/daily_runtime_entry.v1.json"
SYNTHETIC_INSTANCES = ROOT / "scripts/ops/synthetic_duty_instances.sample.json"


def tracked_template() -> dict:
    return json.loads(DECLARATION.read_text(encoding="utf-8"))


def naming() -> dict:
    return tracked_template()["naming"]


def synthetic_instance(**overrides) -> dict:
    """One governed customer binding, synthetic in every value."""
    instance = {
        "duty": "customer_tenant_dev",
        "database": "sc_tenant_sample_dev",
        "database_role": "sc_tenant_sample_dev_app",
        "dbfilter": "^sc_tenant_sample_dev$",
        "environment_id": "daily-dev-sample",
        "tenant_key": "sample",
        "data_purpose": "customer",
        "cluster": {
            "container": "sc-tenant-sample-dev-db-1",
            "compose_project": "sc-tenant-sample-dev",
            "data_volume": "sc_tenant_sample_dev_db_data",
            "maintenance_role": "sc_tenant_sample_dev_maintenance",
            "system_identifier": "1",
        },
        "custody": {"database_present": True, "database_role_present": True,
                    "role_compliance": "compliant", "service_face": "initialized"},
        "storage": {
            "compose_project": "sc-tenant-sample-dev",
            "odoo_data_volume": "sc_tenant_sample_dev_odoo_data",
            "redis_data_volume": "sc_tenant_sample_dev_redis_data",
            "filestore_scope": "sc_tenant_sample_dev",
            "session_namespace": "sc_tenant_sample_dev",
            "backup_namespace": "/data/backups/daily-tenant-sample-dev",
        },
        "routing": {
            "nginx_host_port": 18090,
            "nginx_bind_host": "127.0.0.1",
            "odoo_loopback_port": 18091,
            "odoo_bind_host": "127.0.0.1",
            "list_db": False,
        },
        "section_11": {
            "TARGET_DATABASE_ROLE": "customer_tenant",
            "TARGET_TENANT_ID": "sample",
            "TARGET_ENVIRONMENT_ID": "daily-dev-sample",
            "IS_PLATFORM_CONTROL_DATABASE": False,
            "IS_INDUSTRY_CATALOG_DATABASE": False,
            "IS_CUSTOMER_TENANT_DATABASE": True,
            "IS_ISOLATED_REHEARSAL_DATABASE": False,
            "CUSTOMER_BUSINESS_DATA_ALLOWED": True,
            "FIXTURE_ALLOWED": False,
            "EXACT_DATABASE_FILTER_CONFIRMED": True,
            "FILESTORE_IDENTITY_CONFIRMED": True,
        },
    }
    instance.update(overrides)
    return instance


def instances_document(*duties) -> str:
    return json.dumps(
        {
            "schema": identity.INSTANCES_SCHEMA,
            "authority": "docs/governance/database_architecture_policy.md",
            "duties": list(duties) or [synthetic_instance()],
        },
        ensure_ascii=False,
    )


class TemplateTests(unittest.TestCase):
    """The tracked document is the part every customer receives."""

    def test_the_template_names_the_managed_directory_as_the_source(self):
        managed = tracked_template()["managed_duty_instances"]
        self.assertEqual(managed["source"], identity.MANAGED_SOURCE)
        self.assertEqual(managed["file"], "daily_runtime_duty_instances.v1.json")
        self.assertTrue(str(tracked_template()["ops_root"]).startswith("/"))

    def test_the_template_carries_only_the_generic_duties(self):
        """A customer duty in the template would hand one tenant's identity to all."""
        declared = tracked_template()["duties"]
        self.assertEqual(sorted(row["duty"] for row in declared), ["demo", "platform_control"])
        for row in declared:
            self.assertNotEqual(row.get("data_purpose"), "customer")


    def test_a_self_contained_declaration_needs_no_managed_directory(self):
        """A server that declares no customer duty is legitimate, not a fallback."""
        payload = {"schema": identity.SCHEMA, "duties": [{"duty": "demo"}]}
        self.assertEqual(identity.load_declaration(_write(payload)), payload)

    def test_a_declaration_must_name_the_managed_directory(self):
        payload = {
            "schema": identity.SCHEMA,
            "managed_duty_instances": {"source": "somewhere_else", "file": "x.json"},
            "ops_root": "/opt/x",
            "duties": [{"duty": "demo"}],
        }
        with self.assertRaisesRegex(identity.DutyIdentityError, "managed directory"):
            identity.load_declaration(_write(payload))

    def test_the_tracked_template_resolves_with_its_synthetic_binding(self):
        with mock.patch.dict(
            os.environ, {"SC_DAILY_RUNTIME_DUTY_INSTANCES": str(SYNTHETIC_INSTANCES)}
        ):
            duties = identity.load_duties()
            resolved = identity.resolve("customer_tenant_dev")
        self.assertEqual(sorted(duties), ["customer_tenant_dev", "demo", "platform_control"])
        self.assertEqual(resolved["data_purpose"], "customer")
        self.assertEqual(resolved["tenant_key"], "sample")
        self.assertEqual(resolved["dbfilter"], "^sc_tenant_sample_dev$")


class BindingRefusalTests(unittest.TestCase):
    """Every reason a managed binding cannot govern a duty."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def _declaration(self, payload=None) -> Path:
        return _write(payload or tracked_template(), self.root)

    def _load(self, document: str):
        return identity.merge_instances(
            tracked_template(), identity.parse_instances(document, "<test>")
        )

    def test_a_missing_binding_stops(self):
        """An absent binding is a stop, never a guessed identity."""
        declaration = tracked_template()
        declaration["ops_root"] = str(self.root)
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(identity.DutyIdentityError, "unreadable"):
                identity.read_instances_document(declaration)

    def test_the_override_is_a_source_not_a_fallback(self):
        declaration = tracked_template()
        with mock.patch.dict(os.environ, {}, clear=True):
            target, _, source = identity.managed_instances_source(declaration)
        self.assertEqual(source, "managed")
        self.assertEqual(target, "%s/%s" % (declaration["ops_root"],
                                            declaration["managed_duty_instances"]["file"]))
        with mock.patch.dict(os.environ, {"SC_DAILY_RUNTIME_DUTY_INSTANCES": "/tmp/staged.json"}):
            target, _, source = identity.managed_instances_source(
                declaration, staging_reader=lambda path: "staged"
            )
        self.assertEqual((source, target), ("override", "/tmp/staged.json"))

    def test_a_binding_must_carry_every_governed_key(self):
        instance = synthetic_instance()
        instance.pop("routing")
        with self.assertRaisesRegex(identity.DutyIdentityError, "lacks keys routing"):
            self._load(instances_document(instance))

    def test_a_placeholder_in_a_binding_is_a_stop(self):
        """Substituting a pattern here would decide a customer identity at run time."""
        instance = synthetic_instance(tenant_key="<tenant_key>")
        instance["section_11"]["TARGET_TENANT_ID"] = "<tenant_key>"
        with self.assertRaisesRegex(identity.DutyIdentityError, "unresolved placeholder"):
            self._load(instances_document(instance))

    def test_a_binding_may_not_restate_a_declared_duty(self):
        instance = synthetic_instance(duty="demo")
        with self.assertRaisesRegex(identity.DutyIdentityError, "declared twice"):
            self._load(instances_document(instance))

    def test_a_binding_must_follow_the_naming_rules(self):
        cases = (
            ("database", "sc_tenant_sample_prod"),
            ("database_role", "sc_tenant_sample"),
            ("compose_project", "tenant-sample"),
        )
        for key, value in cases:
            with self.subTest(key=key):
                instance = synthetic_instance()
                if key == "compose_project":
                    instance["cluster"]["compose_project"] = value
                else:
                    instance[key] = value
                with self.assertRaisesRegex(identity.DutyIdentityError, "breaks the naming"):
                    self._load(instances_document(instance))

    def test_a_declared_gap_relaxes_only_the_application_role_name(self):
        """The one recorded exception never relaxes the database name."""
        instance = synthetic_instance()
        instance["custody"] = {"database_present": True, "database_role_present": True,
                               "role_compliance": "declared_gap",
                               "gap_kind": identity.DECLARED_ROLE_GAP_KIND}
        instance["database_role"] = "odoo"
        self.assertTrue(identity.role_naming_is_declared_gap(instance))
        merged = identity.merge_instances(
            tracked_template(), identity.parse_instances(instances_document(instance), "<test>")
        )
        self.assertIn("customer_tenant_dev", [row["duty"] for row in merged["duties"]])
        instance["database"] = "sc_tenant_sample_prod"
        with self.assertRaisesRegex(identity.DutyIdentityError, "database sc_tenant_sample_prod"):
            identity.merge_instances(
                tracked_template(), identity.parse_instances(instances_document(instance), "<test>")
            )

    def test_a_binding_must_select_exactly_its_database(self):
        instance = synthetic_instance(dbfilter="^sc_tenant_sample_dev")
        with self.assertRaisesRegex(identity.DutyIdentityError, "does not select exactly"):
            self._load(instances_document(instance))

    def test_section_11_must_agree_with_the_binding(self):
        for key, value in (("TARGET_TENANT_ID", "someone-else"),
                           ("TARGET_ENVIRONMENT_ID", "daily-dev-other")):
            with self.subTest(key=key):
                instance = synthetic_instance()
                instance["section_11"][key] = value
                with self.assertRaisesRegex(identity.DutyIdentityError, "disagrees"):
                    self._load(instances_document(instance))

    def test_an_instances_document_must_be_one_schema_with_duties(self):
        for document, expected in (
            ("not json", "not valid JSON"),
            (json.dumps({"schema": "other", "duties": [{}]}), "unexpected schema"),
            (json.dumps({"schema": identity.INSTANCES_SCHEMA, "duties": []}), "list no duty"),
        ):
            with self.subTest(document=document[:40]):
                with self.assertRaisesRegex(identity.DutyIdentityError, expected):
                    identity.parse_instances(document, "<test>")


class InstancesLocationTests(unittest.TestCase):
    def test_the_file_must_be_one_plain_name(self):
        declaration = tracked_template()
        for name in ("/etc/passwd", "sub/dir.json", ".hidden"):
            with self.subTest(name=name):
                declaration["managed_duty_instances"]["file"] = name
                with self.assertRaisesRegex(identity.DutyIdentityError, "one plain file name"):
                    identity.instances_location(declaration)

    def test_the_ops_root_must_be_one_absolute_directory(self):
        declaration = tracked_template()
        for value in ("relative/path", "/opt/trailing/"):
            with self.subTest(value=value):
                declaration["ops_root"] = value
                with self.assertRaisesRegex(identity.DutyIdentityError, "absolute directory"):
                    identity.instances_location(declaration)


class SshReaderTests(unittest.TestCase):
    """The workstation-side entry reads the governed document over the governed channel."""

    def _run(self, returncode, stdout, stderr=""):
        completed = mock.Mock(returncode=returncode, stdout=stdout, stderr=stderr)
        return mock.patch.object(identity.subprocess, "run", return_value=completed)

    def test_the_reader_returns_the_text_it_read(self):
        with self._run(0, instances_document()):
            text = identity.ssh_instances_reader("sc-root")("/opt/x/instances.json")
        self.assertEqual(text, instances_document())

    def test_the_reader_refuses_a_nonzero_exit(self):
        with self._run(1, "", "no such file"):
            with self.assertRaisesRegex(identity.DutyIdentityError, "unreadable on sc-root"):
                identity.ssh_instances_reader("sc-root")("/opt/x/instances.json")

    def test_the_reader_refuses_an_empty_document(self):
        with self._run(0, "\n"):
            with self.assertRaisesRegex(identity.DutyIdentityError, "empty on sc-root"):
                identity.ssh_instances_reader("sc-root")("/opt/x/instances.json")


class ResolveTests(unittest.TestCase):
    """Every case here injects the reader, so the shell must not select the source.

    The override names a source; a developer shell that happens to export it must
    not decide which document these cases resolve, or a run of this suite would
    depend on the operator's environment instead of the assertion.
    """

    def setUp(self):
        environ = mock.patch.dict(os.environ, {}, clear=True)
        environ.start()
        self.addCleanup(environ.stop)

    def test_resolve_returns_the_declared_identity(self):
        text = instances_document()
        declaration = _write(tracked_template())
        resolved = identity.resolve(
            "customer_tenant_dev", declaration, instances_reader=lambda path: text
        )
        self.assertEqual(resolved["database"], "sc_tenant_sample_dev")
        self.assertEqual(resolved["database_role"], "sc_tenant_sample_dev_app")

    def test_resolve_stops_on_a_duplicate_duty_name(self):
        payload = tracked_template()
        payload["duties"].append(dict(payload["duties"][-1]))
        with self.assertRaisesRegex(identity.DutyIdentityError, "declaration: demo"):
            identity.resolve("demo", _write(payload), instances_reader=lambda path: instances_document())

    def test_resolve_stops_on_an_undeclared_duty(self):
        with self.assertRaisesRegex(identity.DutyIdentityError, "undeclared duty"):
            identity.resolve("production", _write(tracked_template()),
                             instances_reader=lambda path: instances_document())


class ProtectedHistoricSourceTests(unittest.TestCase):
    """A preserved database carrier is a name collision by construction.

    Before the 2026-10-16 demo rebuild one carrier answered to ``sc_demo``.  The
    rebuild creates a second one and *preserves* the first, so a bare database
    name stops identifying a target.  These cases pin the two properties that
    keep that honest: the historic section is validated as its own declaration,
    and it can never be the carrier a duty entry ends up writing to.
    """

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def _source(self, **overrides) -> dict:
        source = {
            "source_id": "pre_governance_shared_cluster",
            "database": "sc_demo",
            "cluster": {
                "container": "sc-backend-odoo-dev-db-1",
                "compose_project": "sc-backend-odoo-dev",
                "data_volume": "sc_dev_db_data",
            },
            "visibility": "read_only_historic",
            "authority": "docs/ops/user_data_production_boundary_v1.md",
            "reason": "preserved in place so a bare database name stops resolving",
        }
        source.update(overrides)
        return source

    def _declaration(self, source=None) -> Path:
        payload = tracked_template()
        payload["protected_historic_sources"] = [source or self._source()]
        return _write(payload, self.root)

    def _refuses(self, message: str, source=None):
        with self.assertRaisesRegex(identity.DutyIdentityError, message):
            identity.load_declaration(self._declaration(source))

    def test_an_absent_section_is_a_legitimate_shape(self):
        payload = tracked_template()
        payload.pop("protected_historic_sources", None)
        self.assertEqual(identity.protected_historic_sources(payload), [])
        loaded = identity.load_declaration(
            _write(payload, self.root), instances_reader=lambda path: instances_document()
        )
        self.assertNotIn("protected_historic_sources", loaded)

    def test_a_declared_section_must_be_a_non_empty_list(self):
        payload = tracked_template()
        payload["protected_historic_sources"] = []
        with self.assertRaisesRegex(identity.DutyIdentityError, "non-empty list"):
            identity.load_declaration(_write(payload, self.root))
        payload["protected_historic_sources"] = {"source_id": "x"}
        with self.assertRaisesRegex(identity.DutyIdentityError, "non-empty list"):
            identity.load_declaration(_write(payload, self.root))

    def test_the_shipped_declaration_carries_one_validated_source(self):
        declaration = tracked_template()
        sources = identity.protected_historic_sources(declaration)
        self.assertEqual([entry["source_id"] for entry in sources],
                         ["pre_governance_shared_cluster"])

    def test_every_governed_key_is_required(self):
        for key in identity.PROTECTED_HISTORIC_SOURCE_KEYS:
            source = self._source()
            source.pop(key)
            self._refuses("lacks keys %s" % (key,), source)

    def test_the_source_id_must_be_a_safe_identifier(self):
        self._refuses("not a safe identifier", self._source(source_id="Pre Governance"))
        self._refuses("not a safe identifier", self._source(source_id="9cluster"))

    def test_two_sources_may_not_share_an_id(self):
        payload = tracked_template()
        payload["protected_historic_sources"] = [self._source(), self._source(
            database="sc_demo_archive",
            cluster={"container": "sc-archive-db-1", "compose_project": "sc-archive",
                     "data_volume": "sc_archive_db_data"},
        )]
        with self.assertRaisesRegex(identity.DutyIdentityError, "duplicate protected historic source id"):
            identity.load_declaration(_write(payload, self.root))

    def test_the_database_must_be_a_plain_database_name(self):
        """History names the carrier; the name still has to be safe to interpolate."""
        self._refuses("is not a plain database name", self._source(database="Demo-DB"))
        self._refuses("is not a plain database name", self._source(database="sc demo"))

    def test_an_unknown_visibility_is_refused(self):
        """A source with no declared visibility is a source nobody decided about."""
        self._refuses("visibility must be one of", self._source(visibility="writable"))

    def test_authority_and_reason_must_be_stated(self):
        self._refuses("needs authority", self._source(authority=""))
        self._refuses("needs reason", self._source(reason="   "))

    def test_the_cluster_must_name_its_carrier(self):
        self._refuses("cluster must be an object", self._source(cluster="sc-backend-odoo-dev"))
        self._refuses("cluster.container", self._source(cluster={
            "container": "Sc Backend", "compose_project": "sc-backend-odoo-dev",
            "data_volume": "sc_dev_db_data"}))
        self._refuses("cluster.data_volume", self._source(cluster={
            "container": "sc-backend-odoo-dev-db-1", "compose_project": "sc-backend-odoo-dev",
            "data_volume": ""}))

    def test_a_preserved_source_may_not_be_the_duty_itself(self):
        """Sharing a container or a PGDATA with a duty would make it one writer."""
        with self.assertRaisesRegex(identity.DutyIdentityError, "shares a cluster container"):
            identity.load_declaration(self._declaration(self._source(cluster={
                "container": "sc-demo-dev-db-1", "compose_project": "sc-backend-odoo-dev",
                "data_volume": "sc_dev_db_data"})))
        with self.assertRaisesRegex(identity.DutyIdentityError, "shares a cluster container"):
            identity.load_declaration(self._declaration(self._source(cluster={
                "container": "sc-backend-odoo-dev-db-1", "compose_project": "sc-backend-odoo-dev",
                "data_volume": "sc_demo_db_data"})))


class DutyCarrierResolutionTests(unittest.TestCase):
    """One database name, one carrier, or a stop that names every candidate."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def _resolve(self, database, payload=None):
        return identity.resolve_duty_carrier(
            database, _write(payload or tracked_template(), self.root),
            instances_reader=lambda path: instances_document(),
        )

    def test_one_name_with_one_duty_resolves_to_that_duty(self):
        carrier = self._resolve("sc_platform_control")
        self.assertEqual(carrier["kind"], identity.CARRIER_DUTY)
        self.assertEqual(carrier["id"], "platform_control")
        self.assertEqual(carrier["database_container"], "sc-platform-control-dev-db-1")
        self.assertTrue(carrier["writable"])

    def test_the_shipped_demo_name_is_ambiguous_on_purpose(self):
        """The rebuild makes ``sc_demo`` name a duty *and* a preserved source."""
        with self.assertRaisesRegex(
            identity.DutyIdentityError, "DUTY_IDENTITY_DATABASE_AMBIGUOUS:sc_demo"
        ):
            self._resolve("sc_demo")

    def test_a_preserved_source_is_never_a_duty_target(self):
        payload = tracked_template()
        payload["protected_historic_sources"] = [{
            "source_id": "only_source",
            "database": "sc_odoo",
            "cluster": {"container": "sc-legacy-db-1", "compose_project": "sc-legacy",
                        "data_volume": "sc_legacy_db_data"},
            "visibility": "read_only_historic",
            "authority": "docs/ops/user_data_production_boundary_v1.md",
            "reason": "preserved in place",
        }]
        with self.assertRaisesRegex(
            identity.DutyIdentityError, "DUTY_IDENTITY_DATABASE_HISTORIC_SOURCE:sc_odoo:only_source"
        ):
            self._resolve("sc_odoo", payload)

    def test_an_unnamed_database_is_refused(self):
        for value in ("", "   ", None):
            with self.assertRaisesRegex(identity.DutyIdentityError, "DUTY_IDENTITY_DATABASE_UNNAMED"):
                self._resolve(value)

    def test_an_undeclared_database_is_refused(self):
        with self.assertRaisesRegex(
            identity.DutyIdentityError, "DUTY_IDENTITY_DATABASE_UNDECLARED:sc_mystery"
        ):
            self._resolve("sc_mystery")

    def _bind(self, duty, database, payload=None):
        return identity.bind_duty_database(
            duty, database, _write(payload or tracked_template(), self.root),
            instances_reader=lambda path: instances_document(),
        )

    def test_naming_the_duty_binds_the_whole_identity(self):
        binding = self._bind("demo", "")
        self.assertEqual(binding["bound_by"], "duty")
        self.assertEqual(binding["database"], "sc_demo")
        self.assertEqual(binding["database_container"], "sc-demo-dev-db-1")
        self.assertEqual(binding["database_volume"], "sc_demo_db_data")
        self.assertEqual(binding["compose_project"], "sc-demo-dev")
        self.assertEqual(binding["dbfilter"], "^sc_demo$")
        self.assertEqual(binding["data_purpose"], "demo")

    def test_a_duty_binding_may_restate_its_own_database(self):
        binding = self._bind("demo", "sc_demo")
        self.assertEqual(binding["database"], "sc_demo")

    def test_a_duty_binding_may_not_name_another_database(self):
        """Naming both and disagreeing is not a preference, it is a stop."""
        with self.assertRaisesRegex(
            identity.DutyIdentityError, "DUTY_IDENTITY_DATABASE_DISAGREES_WITH_DUTY:demo:sc_tenant_sample_dev:sc_demo"
        ):
            self._bind("demo", "sc_tenant_sample_dev")

    def test_the_weak_form_still_works_while_exactly_one_duty_carries_the_name(self):
        binding = self._bind("", "sc_platform_control")
        self.assertEqual(binding["bound_by"], "database")
        self.assertEqual(binding["duty"], "platform_control")

    def test_the_weak_form_stops_once_a_second_carrier_exists(self):
        with self.assertRaisesRegex(identity.DutyIdentityError, "DUTY_IDENTITY_DATABASE_AMBIGUOUS"):
            self._bind("", "sc_demo")

    def test_a_duty_name_that_is_undeclared_is_refused(self):
        with self.assertRaisesRegex(identity.DutyIdentityError, "undeclared duty"):
            self._bind("legacy_demo", "")

    def test_the_refusal_lists_every_carrier(self):
        try:
            self._resolve("sc_demo")
        except identity.DutyIdentityError as error:
            self.assertIn("duty=demo=sc-demo-dev-db-1", str(error))
            self.assertIn(
                "protected_historic_source=pre_governance_shared_cluster=sc-backend-odoo-dev-db-1",
                str(error),
            )
        else:  # pragma: no cover - the refusal above is the assertion
            self.fail("an ambiguous database name must not resolve")


class DutyEnvPathTests(unittest.TestCase):
    """One resolver owns which environment file a duty reads.

    The rebuilt demo duty and the preserved historic source are both called
    ``demo``, and ``demo.env`` still belongs to the pre-governance cluster. An
    entry that derived ``<duty>.env`` on its own read that file, refused itself
    with a carrier disagreement and never saw the correct ``sc-demo-dev.env``
    beside it. These tests pin the shared rule and the refusal that names the
    owner instead of silently writing another carrier's file.
    """

    DEMO = {"duty": "demo", "cluster": {"compose_project": "sc-demo-dev"}}
    LEGACY_MARKER = "sc-backend-odoo-dev"

    def _write(self, root, name, marker):
        path = Path(root) / name
        path.write_text(
            "COMPOSE_PROJECT_NAME=%s\nDB_NAME=sc_demo\n" % (marker,), encoding="utf-8"
        )
        return path

    def test_the_carrier_qualified_file_wins_when_both_exist(self):
        with tempfile.TemporaryDirectory() as root:
            self._write(root, "demo.env", self.LEGACY_MARKER)
            self._write(root, "sc-demo-dev.env", "sc-demo-dev")
            self.assertEqual(
                identity.duty_env_path(self.DEMO, root, reading=True).name,
                "sc-demo-dev.env",
            )

    def test_a_foreign_carrier_file_is_refused_by_name_not_read(self):
        with tempfile.TemporaryDirectory() as root:
            self._write(root, "demo.env", self.LEGACY_MARKER)
            with self.assertRaises(identity.DutyIdentityError) as raised:
                identity.duty_env_path(self.DEMO, root, reading=True)
        message = str(raised.exception)
        self.assertIn("ENV_CARRIER_MISMATCH", message)
        self.assertIn(self.LEGACY_MARKER, message)
        self.assertIn("sc-demo-dev.env", message)

    def test_the_render_side_still_targets_the_qualified_name(self):
        """Creating the duty's file is not the same question as reading one."""
        with tempfile.TemporaryDirectory() as root:
            self._write(root, "demo.env", self.LEGACY_MARKER)
            self.assertEqual(
                identity.duty_env_path(self.DEMO, root).name, "sc-demo-dev.env"
            )

    def test_a_file_without_a_carrier_marker_is_still_the_duty_own_file(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, "platform_control.env").write_text(
                "DB_NAME=sc_platform_control\n", encoding="utf-8"
            )
            duty = {
                "duty": "platform_control",
                "cluster": {"compose_project": "sc-platform-control-dev"},
            }
            self.assertEqual(
                identity.duty_env_path(duty, root, reading=True).name,
                "platform_control.env",
            )

    def test_a_duty_whose_carrier_is_its_own_name_still_reads_that_file(self):
        """The customer duty's file is named after the duty, not the carrier."""
        with tempfile.TemporaryDirectory() as root:
            self._write(root, "customer_tenant_dev.env", "sc-tenant-sample-dev")
            duty = {
                "duty": "customer_tenant_dev",
                "cluster": {"compose_project": "sc-tenant-sample-dev"},
            }
            self.assertEqual(
                identity.duty_env_path(duty, root, reading=True).name,
                "customer_tenant_dev.env",
            )

    def test_the_resolved_identity_shape_resolves_the_same_file(self):
        """``resolve`` hoists ``compose_project``; the resolver must read both shapes.

        The edition-release entry calls the resolver with the *normalized*
        identity, which has no ``cluster`` block. Reading only the nested shape
        silently fell back to the duty's own name -- the first readback of the
        rebuilt carrier asked for ``demo.env`` again.
        """
        with tempfile.TemporaryDirectory() as root:
            self._write(root, "demo.env", self.LEGACY_MARKER)
            self._write(root, "sc-demo-dev.env", "sc-demo-dev")
            hoisted = {"duty": "demo", "compose_project": "sc-demo-dev"}
            self.assertEqual(
                identity.duty_env_path(hoisted, root, reading=True).name,
                "sc-demo-dev.env",
            )
            self.assertEqual(identity.carrier_project(self.DEMO), "sc-demo-dev")
            self.assertEqual(identity.carrier_project(hoisted), "sc-demo-dev")

    def test_an_empty_directory_still_yields_a_creatable_path(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(
                identity.duty_env_path(self.DEMO, root).name, "demo.env"
            )

    def test_the_embedded_carrier_agrees_with_the_resolver(self):
        """The uploaded program cannot import this module, so parity is asserted.

        A second copy of the rule is only safe while a test proves the two
        copies answer the same question the same way.
        """
        with tempfile.TemporaryDirectory() as root:
            self._write(root, "demo.env", self.LEGACY_MARKER)
            namespace = self._embedded_carrier(root)
            shared = identity.duty_env_path(self.DEMO, root)
            embedded = namespace["credentials_path"](self.DEMO)
            self.assertEqual(os.path.basename(embedded), shared.name)
            self._write(root, "sc-demo-dev.env", "sc-demo-dev")
            self.assertEqual(
                os.path.basename(namespace["credentials_path"](self.DEMO)),
                identity.duty_env_path(self.DEMO, root).name,
            )
            self.assertEqual(
                os.path.basename(namespace["credentials_path"](self.DEMO)),
                "sc-demo-dev.env",
            )

    def _embedded_carrier(self, ops_root):
        import contextlib
        import hashlib
        import io

        payload = {
            "mode": "plan",
            "phase": "plan",
            "product_root": "/opt/projects/repos/sce-product-odoo",
            "ops_root": ops_root,
            "platform_admin_database": "sc_platform_control",
            "frontend_build_env_file": os.path.join(ops_root, "absent-build.env"),
            "source_revision": "a" * 40,
            "compose_sha256": hashlib.sha256(b"services:\n").hexdigest(),
            "stack": {"compose_text": "services:\n  db:\n    image: postgres:15\n"},
            "env_template": "DB_NAME=@DB_NAME@\n",
            "data_destination": "/var/lib/postgresql/data",
            "duties": [],
        }
        rendered = duty_entry.render_remote_program(payload)
        namespace = {"__name__": "__parity__"}
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(rendered, "<remote-carrier-parity>", "exec"), namespace)
        return namespace


class RemoteMaterialisationTests(unittest.TestCase):
    """The write path is the one step the product tree cannot perform for itself."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.binding = self.root / "daily_runtime_duty_instances.v1.json"

    def _payload(self, text: str, **overrides) -> dict:
        payload = {
            "mode": "apply",
            "phase": "database",
            "ops_root": str(self.root),
            "stack": {"compose_text": "services: {}\n"},
            "env_template": "DB_NAME=@DB_NAME@\n",
            "data_destination": "/var/lib/postgresql/data",
            "managed_instances": {
                "file": "daily_runtime_duty_instances.v1.json",
                "path": str(self.binding),
                "sha256": _digest(text),
                "text": text,
            },
        }
        payload.update(overrides)
        return payload

    def _materialise(self, payload):
        namespace: dict = {}
        exec(compile(_remote_prefix(payload), "<remote-carrier>", "exec"), namespace)
        return namespace["materialise_managed_instances"]()

    def test_a_plan_writes_nothing(self):
        payload = self._payload(instances_document(), mode="plan")
        entry = self._materialise(payload)
        self.assertFalse(entry["wrote"])
        self.assertEqual(entry["observed_sha256"], "")
        self.assertFalse(self.binding.exists())

    def test_an_apply_writes_the_reviewed_bytes_0600_and_reads_the_digest_back(self):
        text = instances_document()
        entry = self._materialise(self._payload(text))
        self.assertTrue(entry["wrote"], entry)
        self.assertEqual(entry["error"], "")
        self.assertEqual(entry["expected_sha256"], _digest(text))
        self.assertEqual(entry["observed_sha256"], _digest(text))
        self.assertEqual(self.binding.read_text(encoding="utf-8"), text)
        self.assertEqual(stat.S_IMODE(self.binding.stat().st_mode), 0o600)

    def test_an_apply_keeps_the_previous_revision(self):
        first = instances_document()
        self._materialise(self._payload(first))
        second = instances_document(synthetic_instance(tenant_key="sample2"))
        entry = self._materialise(self._payload(second))
        self.assertTrue(entry["wrote"], entry)
        self.assertEqual(entry["previous_sha256"], _digest(first))
        previous = Path(str(self.binding) + ".previous")
        self.assertTrue(previous.exists())
        self.assertEqual(previous.read_text(encoding="utf-8"), first)
        self.assertEqual(stat.S_IMODE(previous.stat().st_mode), 0o600)

    def test_an_apply_over_the_same_revision_writes_nothing(self):
        text = instances_document()
        self._materialise(self._payload(text))
        entry = self._materialise(self._payload(text))
        self.assertFalse(entry["wrote"])
        self.assertEqual(entry["observed_sha256"], _digest(text))
        self.assertFalse(Path(str(self.binding) + ".previous").exists())

    def test_an_entry_without_a_binding_reports_the_refusal(self):
        entry = self._materialise(self._payload("", managed_instances={}))
        self.assertFalse(entry["wrote"])
        self.assertIn("no managed duty binding", entry["error"])


class EntryWiringTests(unittest.TestCase):
    """The duty entry is the caller; the resolver is not a library nobody uses."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        # The resolver's override names a source; a developer shell that happens
        # to export it must not decide which document this test resolves.
        environ = mock.patch.dict(os.environ, {}, clear=True)
        environ.start()
        self.addCleanup(environ.stop)
        # An apply names the mutation it intends; the entry checks it before it
        # reads anything back, so a test that runs an apply must carry it.
        os.environ["SC_CONFIRM_DAILY_RUNTIME_DATABASE_DUTY"] = "PROVISION_DAILY_RUNTIME_DATABASE_DUTY"

    def _entry_reader(self, text: str):
        return mock.patch.object(
            duty_entry.duty_identity, "ssh_instances_reader", lambda host: (lambda path: text)
        )

    def test_the_entry_reads_the_managed_binding_through_the_resolver(self):
        text = instances_document()
        with self._entry_reader(text):
            merged, document = duty_entry.load_managed_declaration(str(DECLARATION), "sc-root")
        self.assertEqual(document["source"], "managed")
        self.assertEqual(document["sha256"], _digest(text))
        self.assertEqual(document["read_from"],
                         "%s/%s" % (merged["ops_root"],
                                    merged["managed_duty_instances"]["file"]))
        self.assertIn("customer_tenant_dev", [row["duty"] for row in merged["duties"]])
        self.assertEqual(
            [row["duty"] for row in document["duties"]], ["customer_tenant_dev"]
        )

    def test_the_entry_uses_the_governed_resolver(self):
        """The entry must consume this module, not a private copy of the rules."""
        self.assertEqual(
            Path(duty_entry.duty_identity.__file__).resolve(), Path(identity.__file__).resolve()
        )

    def test_an_unreadable_managed_binding_stops_the_entry(self):
        def refuse(host):
            def read(path):
                raise duty_entry.duty_identity.DutyIdentityError(
                    "managed duty instances are unreadable at %s" % path
                )
            return read

        with mock.patch.object(duty_entry.duty_identity, "ssh_instances_reader", refuse):
            with self.assertRaisesRegex(duty_entry.DutyError, "MANAGED_INSTANCES_REFUSED"):
                duty_entry.load_managed_declaration(str(DECLARATION), "sc-root")

    def test_an_apply_whose_host_does_not_hold_the_reviewed_binding_is_refused(self):
        """The reviewed revision is what must be on the host, not merely something."""
        text = instances_document()
        seen: dict = {}

        def remote(host, payload):
            seen.update(payload)
            return {"managed_instances": {"observed_sha256": "0" * 64}, "duties": []}

        status, stderr = self._run_main(text, remote)
        self.assertEqual(status, 2)
        self.assertIn("DAILY_DUTY_MANAGED_INSTANCES_READBACK", stderr)
        self.assertIn("is not on the host", stderr)
        self.assertEqual(seen["managed_instances"]["text"], text)
        self.assertEqual(seen["managed_instances"]["path"],
                         "%s/%s" % (tracked_template()["ops_root"],
                                    tracked_template()["managed_duty_instances"]["file"]))

    def test_the_entry_reports_an_unreadable_host_binding_as_a_refusal(self):
        """A remote refusal is reported, never mistaken for a successful plan."""
        status, stderr = self._run_main(
            instances_document(),
            lambda host, payload: {"managed_instances": {"error": "no binding"}, "duties": []},
        )
        self.assertEqual(status, 2)
        self.assertIn("DAILY_DUTY_MANAGED_INSTANCES", stderr)

    def test_the_report_records_the_reviewed_binding_and_its_source(self):
        text = instances_document()
        report_path = self.root / "report.json"

        def remote(host, payload):
            return {
                "managed_instances": {"observed_sha256": payload["managed_instances"]["sha256"]},
                "duties": [],
            }

        status, stderr = self._run_main(text, remote, report=report_path)
        self.assertIn(status, (0, 1), stderr)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["managed_instances"]["source"], "managed")
        self.assertEqual(report["managed_instances"]["sha256"], _digest(text))
        self.assertEqual(report["managed_instances"]["observed"]["observed_sha256"], _digest(text))
        self.assertEqual(report["declaration_digest"], report["plan"]["declaration_sha256"])

    def _run_main(self, text, remote, *, report=None):
        """Run the entry the way a host run does, and keep its diagnostic.

        The entry reports a refusal as exit 2 plus a ``BLOCKED`` line instead of
        raising, so a test that only looked for an exception would pass on a
        success.
        """
        import contextlib
        import io

        captured = io.StringIO()
        with self._entry_reader(text), self._head(), mock.patch.object(
            duty_entry, "remote_duties", remote
        ), contextlib.redirect_stderr(captured), contextlib.redirect_stdout(io.StringIO()):
            status = duty_entry.main(self._argv(text, report=report))
        return status, captured.getvalue()

    def _head(self):
        completed = mock.Mock(returncode=0, stdout=b"a" * 40, stderr=b"")
        return mock.patch.object(duty_entry, "ssh", return_value=completed)

    def _argv(self, text, *, report=None) -> list[str]:
        with self._entry_reader(text):
            merged, document = duty_entry.load_managed_declaration(str(DECLARATION), "sc-root")
        return [
            "--ssh-host", "sc-root",
            "--declaration", str(DECLARATION),
            "--duty", "demo",
            "--apply",
            "--phase", "database",
            "--expect-declaration-digest", duty_entry.declaration_digest(merged),
            "--expect-entry-digest", duty_entry.entry_digest(
                json.loads(ENTRY.read_text(encoding="utf-8"))
            ),
            "--report", str(report or (self.root / "report.json")),
        ]


def _write(payload: dict, directory: Path | None = None) -> Path:
    """One declaration lookalike, written into a directory the caller owns."""
    handle, name = tempfile.mkstemp(suffix=".json", dir=directory)
    os.close(handle)
    path = Path(name)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _digest(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _remote_prefix(payload: dict) -> str:
    """The rendered carrier without its driver section.

    The driver reads the host, and a unit test must not.  Splitting on the marker
    rather than truncating at a line number keeps the split honest: if the
    carrier ever loses that marker this raises instead of silently executing
    nothing.
    """
    text = duty_entry.render_remote_program(payload)
    marker = '\nfor duty in PAYLOAD["duties"]:'
    if marker not in text:
        raise AssertionError("the remote carrier lost its driver section")
    return text.split(marker, 1)[0]


if __name__ == "__main__":
    unittest.main()
