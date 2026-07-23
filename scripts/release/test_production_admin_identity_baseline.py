#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
HELPER_PATH = ROOT / "scripts/release/production_admin_identity_baseline.py"
SPEC = importlib.util.spec_from_file_location(
    "production_admin_identity_baseline", HELPER_PATH
)
assert SPEC and SPEC.loader
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)
POLICY_PATH = ROOT / "addons/smart_construction_core/core_extension_policy_maps.py"
POLICY_SPEC = importlib.util.spec_from_file_location(
    "core_extension_policy_maps", POLICY_PATH
)
assert POLICY_SPEC and POLICY_SPEC.loader
policy = importlib.util.module_from_spec(POLICY_SPEC)
POLICY_SPEC.loader.exec_module(policy)

FORMAL_MODULES = (
    "sc_norm_engine",
    "smart_construction_bootstrap",
    "smart_core",
    "smart_scene",
    "smart_construction_core",
    "smart_construction_portal",
    "smart_construction_scene",
    "smart_license_core",
    "smart_construction_bundle",
    "smart_construction_seed",
)


class FakeRecordset:
    def __init__(self, records):
        self.records = list(records)

    def __len__(self):
        return len(self.records)

    def __iter__(self):
        return iter(self.records)

    def __getattr__(self, name):
        if len(self.records) != 1:
            raise AttributeError(name)
        return getattr(self.records[0], name)


class FakeGroup:
    _name = "res.groups"

    def __init__(self, group_id, xmlid):
        self.id = group_id
        self.xmlid = xmlid


class FakeGroups:
    def __init__(self, groups):
        self.groups = list(groups)

    @property
    def ids(self):
        return [group.id for group in self.groups]

    def get_external_id(self):
        return {group.id: group.xmlid for group in self.groups}


class FakeUser:
    def __init__(self, user_id=2, *, login="admin", active=True, share=False, groups=None):
        self.id = user_id
        self.login = login
        self.active = active
        self.share = share
        self.groups_id = FakeGroups(groups or [])
        self.company_id = type("Company", (), {"id": 1})()
        self.company_ids = type("Companies", (), {"ids": [1]})()
        self.writes = []

    def write(self, values):
        self.writes.append(values)
        for operation, group_id in values["groups_id"]:
            if operation != 4:
                raise AssertionError(operation)
            group = GROUPS_BY_ID[group_id]
            if group.id not in self.groups_id.ids:
                self.groups_id.groups.append(group)
        return True


class FakeUsers:
    def __init__(self, targets, events):
        self.targets = list(targets)
        self.events = events

    def sudo(self):
        return self

    def with_context(self, **_values):
        return self

    def search(self, domain):
        self.events.append("target-user-query")
        if domain != [("login", "=", "admin")]:
            raise AssertionError(domain)
        return FakeRecordset(self.targets)


class FakeModules:
    def __init__(self, events, states=None, pending=0):
        self.events = events
        self.states = states or {name: "installed" for name in FORMAL_MODULES}
        self.pending = pending

    def sudo(self):
        return self

    def search(self, domain):
        self.events.append("formal-module-query")
        names = domain[0][2]
        return FakeRecordset(
            type("Module", (), {"name": name, "state": self.states[name]})()
            for name in names
            if name in self.states
        )

    def search_count(self, domain):
        self.events.append("pending-module-query")
        if domain != [("state", "in", ["to install", "to upgrade", "to remove"])]:
            raise AssertionError(domain)
        return self.pending


class FakeCountModel:
    _fields = {"active": object()}

    def __init__(self, count, active_count):
        self.count = count
        self.active_count = active_count

    def sudo(self):
        return self

    def search_count(self, domain):
        if domain == []:
            return self.count
        if domain == [("active", "=", True)]:
            return self.active_count
        raise AssertionError(domain)


class Savepoint:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class FakeCursor:
    dbname = "sc_production"

    def __init__(self, events, *, show_value="on", set_fails=False):
        self.events = events
        self.show_value = show_value
        self.set_fails = set_fails
        self.read_only = False
        self.last_query = ""
        self.commits = 0
        self.rollbacks = 0

    def execute(self, query):
        normalized = " ".join(str(query).split()).upper()
        self.events.append(f"sql:{normalized}")
        self.last_query = normalized
        if normalized == "SET TRANSACTION READ ONLY":
            if self.set_fails:
                raise RuntimeError("read-only unavailable")
            self.read_only = True
            return
        if normalized == "SHOW TRANSACTION_READ_ONLY":
            return
        if self.read_only and normalized.split(" ", 1)[0] in {
            "INSERT", "UPDATE", "DELETE", "TRUNCATE", "ALTER", "CREATE", "DROP",
        }:
            raise RuntimeError("cannot execute write in a read-only transaction")

    def fetchone(self):
        if self.last_query != "SHOW TRANSACTION_READ_ONLY":
            raise AssertionError(self.last_query)
        return (self.show_value,)

    def savepoint(self):
        return Savepoint()

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


INTERNAL = FakeGroup(10, "base.group_user")
CANONICAL = FakeGroup(20, "smart_core.group_smart_core_admin")
OTHER_ROLE = FakeGroup(
    21, "smart_construction_core.group_sc_role_project_manager"
)
GROUPS_BY_ID = {group.id: group for group in (INTERNAL, CANONICAL, OTHER_ROLE)}


class FakeEnvironment:
    def __init__(
        self,
        targets,
        *,
        states=None,
        pending=0,
        show_value="on",
        set_fails=False,
        flush_fails=False,
    ):
        self.events = []
        self.users = FakeUsers(targets, self.events)
        self.modules = FakeModules(self.events, states, pending)
        self.menus = FakeCountModel(97, 97)
        self.product_policy = FakeCountModel(2, 2)
        self.business_contract = FakeCountModel(73, 73)
        self.cr = FakeCursor(
            self.events, show_value=show_value, set_fails=set_fails
        )
        self.flush_fails = flush_fails
        self.registry = type(
            "Registry",
            (),
            {
                "models": {
                    "ir.module.module": object(),
                    "res.users": object(),
                    "ir.ui.menu": object(),
                    "sc.product.policy": object(),
                    "ui.business.config.contract": object(),
                }
            },
        )()

    def flush_all(self):
        self.events.append("orm-flush")
        if self.flush_fails:
            raise RuntimeError("unexpected pending write")

    def __getitem__(self, model):
        return {
            "res.users": self.users,
            "ir.module.module": self.modules,
            "ir.ui.menu": self.menus,
            "sc.product.policy": self.product_policy,
            "ui.business.config.contract": self.business_contract,
        }[model]

    def ref(self, xmlid, raise_if_not_found=False):
        del raise_if_not_found
        return {
            "base.group_user": INTERNAL,
            "smart_core.group_smart_core_admin": CANONICAL,
        }.get(xmlid)


class FakeResolver:
    _role_groups_explicit = {
        "system_admin": {"smart_core.group_smart_core_admin"},
        "pm": {"smart_construction_core.group_sc_role_project_manager"},
    }
    _role_groups_capability_fallback = {}
    _role_precedence = ("system_admin", "pm")

    def __init__(self, env):
        self.env = env

    def user_group_xmlids(self, user):
        return set(user.groups_id.get_external_id().values())

    def resolve_role_code_with_evidence(self, xmlids):
        hits = []
        for role in self._role_precedence:
            matched = sorted(self._role_groups_explicit[role] & xmlids)
            if matched:
                hits.append((role, matched))
        if not hits:
            return "restricted", {
                "source": "no_authoritative_role",
                "matched_groups": [],
            }
        role, matched = hits[0]
        evidence = {"source": "explicit", "matched_groups": matched}
        if len(hits) > 1:
            evidence["candidate_roles"] = sorted(role for role, _ in hits)
        return role, evidence

    def build_role_surface(self, xmlids, _nav, _scenes):
        role, _evidence = self.resolve_role_code_with_evidence(xmlids)
        return {"deny_all_navigation": role == "restricted"}

    def filter_nav_for_role_surface(self, nav, surface):
        return [] if surface["deny_all_navigation"] else nav


def resolver_factory(env):
    return FakeResolver(env)


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.previous_root = helper.EVIDENCE_ROOT
        helper.EVIDENCE_ROOT = Path(self.temp.name).resolve()
        self.addCleanup(setattr, helper, "EVIDENCE_ROOT", self.previous_root)

    def env(self, mode="dry-run", **updates):
        values = {
            "ENV": "prod",
            "TARGET_DB": "sc_production",
            "ADMIN_IDENTITY_BASELINE_MODE": mode,
            "ADMIN_IDENTITY_LOGIN": "admin",
            "ADMIN_IDENTITY_EXPECTED_USER_COUNT": "1",
            "ADMIN_IDENTITY_EXPECTED_CURRENT_ROLE": "restricted",
            "FORMAL_MODULE_CONTRACT": ",".join(FORMAL_MODULES),
            "ADMIN_IDENTITY_EVIDENCE_OUTPUT": str(
                Path(self.temp.name)
                / f"{mode}-{len(list(Path(self.temp.name).iterdir()))}.json"
            ),
        }
        if mode == "apply":
            values.update(
                {
                    "PROD_DANGER": "1",
                    "CONFIRM_ADMIN_IDENTITY_BASELINE": helper.CONFIRMATION,
                }
            )
        values.update(updates)
        return values

    def call(self, environment, active_env):
        return helper.baseline_admin_identity(
            environment, active_env, resolver_factory=resolver_factory
        )

    def test_dry_run_sets_and_verifies_read_only_before_target_queries(self):
        environment = FakeEnvironment([FakeUser(groups=[INTERNAL])])
        result = self.call(environment, self.env())
        self.assertEqual(result["transaction"]["transaction_read_only"], "on")
        set_index = environment.events.index("sql:SET TRANSACTION READ ONLY")
        show_index = environment.events.index("sql:SHOW TRANSACTION_READ_ONLY")
        target_index = environment.events.index("target-user-query")
        module_index = environment.events.index("formal-module-query")
        self.assertLess(set_index, show_index)
        self.assertLess(show_index, target_index)
        self.assertLess(show_index, module_index)

    def test_dry_run_current_plan_and_observed_states_are_separate(self):
        environment = FakeEnvironment([FakeUser(groups=[INTERNAL])])
        result = self.call(environment, self.env())
        self.assertEqual(result["current"]["role_code"], "restricted")
        self.assertEqual(
            result["current"]["role_evidence"], "no_authoritative_role"
        )
        self.assertTrue(result["current"]["deny_all_navigation"])
        self.assertEqual(
            result["expected_after_apply"]["role_code"], "system_admin"
        )
        self.assertEqual(
            result["expected_after_apply"]["role_evidence"],
            "explicit:smart_core.group_smart_core_admin",
        )
        self.assertFalse(
            result["expected_after_apply"]["deny_all_navigation"]
        )
        self.assertEqual(result["observed_after_dry_run"], result["current"])

    def test_dry_run_plan_is_exact_and_write_audit_is_zero(self):
        environment = FakeEnvironment([FakeUser(groups=[INTERNAL])])
        result = self.call(environment, self.env())
        self.assertEqual(result["plan"]["action"], "ADD_MISSING_CANONICAL_ROLE")
        self.assertTrue(result["plan"]["canonical_role_record_present"])
        self.assertFalse(result["plan"]["canonical_relation_present_before"])
        self.assertEqual(
            result["plan"]["planned_write_model"], "res_users_groups_rel"
        )
        self.assertEqual(result["plan"]["planned_relation_append_count"], 1)
        self.assertEqual(result["plan"]["planned_unrelated_write_count"], 0)
        self.assertEqual(
            result["write_audit"],
            {
                "database_write_statement_count": 0,
                "orm_write_method_count": 0,
                "relation_rows_added": 0,
                "database_transaction_read_only": "PASS",
                "database_changed": False,
            },
        )

    def test_dry_run_fingerprints_are_observed_twice_and_unchanged(self):
        result = self.call(
            FakeEnvironment([FakeUser(groups=[INTERNAL])]), self.env()
        )
        fingerprints = result["fingerprints"]
        self.assertTrue(fingerprints["unchanged"])
        self.assertEqual(fingerprints["before"], fingerprints["after_observed"])
        self.assertIn("menu_definition_sha256", fingerprints["before"])
        self.assertIn("product_configuration_sha256", fingerprints["before"])

    def test_read_only_setup_or_verification_failure_stops_before_user_query(self):
        for kwargs in ({"set_fails": True}, {"show_value": "off"}):
            with self.subTest(kwargs=kwargs):
                environment = FakeEnvironment(
                    [FakeUser(groups=[INTERNAL])], **kwargs
                )
                with self.assertRaises(helper.AdminIdentityBaselineError):
                    self.call(environment, self.env())
                self.assertNotIn("target-user-query", environment.events)

    def test_read_only_database_rejects_an_accidental_write(self):
        environment = FakeEnvironment([FakeUser(groups=[INTERNAL])])
        helper._enable_dry_run_read_only(environment)
        with self.assertRaises(RuntimeError):
            environment.cr.execute("UPDATE res_users SET active = false")

    def test_unexpected_orm_flush_is_caught_before_pass_evidence(self):
        environment = FakeEnvironment(
            [FakeUser(groups=[INTERNAL])], flush_fails=True
        )
        active = self.env()
        with self.assertRaises(helper.AdminIdentityBaselineError):
            self.call(environment, active)
        self.assertFalse(Path(active["ADMIN_IDENTITY_EVIDENCE_OUTPUT"]).exists())

    def test_atomic_evidence_failure_leaves_no_partial_pass(self):
        path = Path(self.temp.name) / "atomic.json"
        with mock.patch.object(helper.os, "replace", side_effect=OSError("fail")):
            with self.assertRaises(OSError):
                helper._write_evidence(path, {"result": "PASS"})
        self.assertFalse(path.exists())
        self.assertEqual(list(Path(self.temp.name).glob(".atomic.json.*")), [])

    def test_evidence_is_redacted_and_contains_no_complete_group_membership(self):
        active = self.env()
        self.call(FakeEnvironment([FakeUser(groups=[INTERNAL])]), active)
        content = Path(active["ADMIN_IDENTITY_EVIDENCE_OUTPUT"]).read_text()
        for token in ("password", "cookie", "token", "connection_string"):
            self.assertNotIn(token, content.casefold())
        payload = json.loads(content)
        self.assertNotIn("xmlids", payload["current"])

    def test_apply_adds_only_canonical_relation_and_remains_idempotent(self):
        user = FakeUser(groups=[INTERNAL])
        environment = FakeEnvironment([user])
        first = self.call(environment, self.env("apply"))
        self.assertEqual(first["status"], "APPLIED")
        self.assertEqual(user.writes, [{"groups_id": [(4, CANONICAL.id)]}])
        self.assertEqual(first["write_audit"]["orm_write_method_count"], 1)
        self.assertEqual(first["write_audit"]["relation_rows_added"], 1)
        self.assertEqual(environment.cr.commits, 1)

        second = self.call(environment, self.env("apply"))
        self.assertEqual(second["status"], "NOOP")
        self.assertEqual(second["plan"]["planned_relation_append_count"], 0)
        self.assertEqual(len(user.writes), 1)

    def test_apply_does_not_enable_read_only(self):
        environment = FakeEnvironment([FakeUser(groups=[INTERNAL])])
        self.call(environment, self.env("apply"))
        self.assertNotIn("sql:SET TRANSACTION READ ONLY", environment.events)

    def test_navigation_recovers_from_shared_policy_without_bypass(self):
        resolver = FakeResolver(None)
        nav = [{"xmlid": "smart_construction_core.menu_sc_root"}]
        restricted = resolver.build_role_surface({"base.group_user"}, nav, set())
        admin = resolver.build_role_surface(
            {"base.group_user", "smart_core.group_smart_core_admin"}, nav, set()
        )
        self.assertEqual(resolver.filter_nav_for_role_surface(nav, restricted), [])
        self.assertGreater(
            len(resolver.filter_nav_for_role_surface(nav, admin)), 0
        )

    def test_canonical_role_is_derived_from_authoritative_policy(self):
        self.assertEqual(
            policy.ROLE_GROUPS_EXPLICIT["system_admin"],
            {"smart_core.group_smart_core_admin"},
        )
        self.assertEqual(policy.ROLE_PRECEDENCE[0], "system_admin")
        self.assertTrue(
            policy.ROLE_SURFACE_OVERRIDES["restricted"]["deny_all_navigation"]
        )
        self.assertFalse(
            policy.ROLE_SURFACE_OVERRIDES["system_admin"].get(
                "deny_all_navigation", False
            )
        )

    def test_target_uniqueness_and_internal_identity_are_guarded(self):
        cases = (
            [],
            [FakeUser(), FakeUser(3)],
            [FakeUser(active=False, groups=[INTERNAL])],
            [FakeUser(share=True, groups=[INTERNAL])],
            [FakeUser(groups=[])],
        )
        for index, users in enumerate(cases):
            with self.subTest(index=index):
                with self.assertRaises(helper.AdminIdentityBaselineError):
                    self.call(FakeEnvironment(users), self.env())

    def test_database_module_and_pending_drift_are_guarded(self):
        user = FakeUser(groups=[INTERNAL])
        environment = FakeEnvironment([user])
        environment.cr.dbname = "other"
        with self.assertRaises(helper.AdminIdentityBaselineError):
            self.call(environment, self.env())

        states = {name: "installed" for name in FORMAL_MODULES}
        states[FORMAL_MODULES[0]] = "to upgrade"
        with self.assertRaises(helper.AdminIdentityBaselineError):
            self.call(FakeEnvironment([user], states=states), self.env())
        with self.assertRaises(helper.AdminIdentityBaselineError):
            self.call(FakeEnvironment([user], pending=1), self.env())

    def test_conflicting_role_is_rejected(self):
        user = FakeUser(groups=[INTERNAL, OTHER_ROLE])
        with self.assertRaises(helper.AdminIdentityBaselineError):
            self.call(FakeEnvironment([user]), self.env("apply"))
        self.assertEqual(user.writes, [])

    def test_missing_xmlid_and_policy_drift_are_rejected(self):
        user = FakeUser(groups=[INTERNAL])
        environment = FakeEnvironment([user])
        original = environment.ref
        environment.ref = lambda xmlid, raise_if_not_found=False: (
            None
            if xmlid == "smart_core.group_smart_core_admin"
            else original(xmlid, raise_if_not_found=raise_if_not_found)
        )
        with self.assertRaises(helper.AdminIdentityBaselineError):
            self.call(environment, self.env())

        class DriftResolver(FakeResolver):
            _role_groups_explicit = {
                "system_admin": {
                    "smart_core.group_smart_core_admin",
                    "smart_construction_core.group_sc_role_project_manager",
                }
            }

        with self.assertRaises(helper.AdminIdentityBaselineError):
            helper.baseline_admin_identity(
                FakeEnvironment([user]),
                self.env(),
                resolver_factory=DriftResolver,
            )

    def test_apply_requires_explicit_danger_and_confirmation(self):
        for key in ("PROD_DANGER", "CONFIRM_ADMIN_IDENTITY_BASELINE"):
            active = self.env("apply")
            active.pop(key)
            with self.assertRaises(helper.AdminIdentityBaselineError):
                helper.validate_control_plane(active)

    def test_dry_run_is_default_and_input_scope_is_guarded(self):
        active = self.env()
        active.pop("ADMIN_IDENTITY_BASELINE_MODE")
        result = self.call(
            FakeEnvironment([FakeUser(groups=[INTERNAL])]), active
        )
        self.assertEqual(result["mode"], "dry-run")

        active = self.env()
        active["ADMIN_IDENTITY_LOGIN"] = "other"
        with self.assertRaises(helper.AdminIdentityBaselineError):
            helper.validate_control_plane(active)

        active = self.env()
        active["ADMIN_IDENTITY_EVIDENCE_OUTPUT"] = "/tmp/evidence.json"
        with self.assertRaises(helper.AdminIdentityBaselineError):
            helper.validate_control_plane(active)

    def test_unrelated_user_fields_are_unchanged(self):
        user = FakeUser(groups=[INTERNAL])
        before = helper._safe_snapshot(user)
        self.call(FakeEnvironment([user]), self.env("apply"))
        self.assertEqual(helper._safe_snapshot(user), before)

    def test_post_write_validation_failure_rolls_back_without_commit(self):
        user = FakeUser(groups=[INTERNAL])
        environment = FakeEnvironment([user])
        calls = 0

        class InvalidAfterResolver(FakeResolver):
            def resolve_role_code_with_evidence(self, xmlids):
                if CANONICAL.xmlid in xmlids:
                    return "restricted", {
                        "source": "no_authoritative_role",
                        "matched_groups": [],
                    }
                return super().resolve_role_code_with_evidence(xmlids)

        def changing_factory(env):
            nonlocal calls
            calls += 1
            return FakeResolver(env) if calls == 1 else InvalidAfterResolver(env)

        with self.assertRaises(helper.AdminIdentityBaselineError):
            helper.baseline_admin_identity(
                environment,
                self.env("apply"),
                resolver_factory=changing_factory,
            )
        self.assertEqual(environment.cr.commits, 0)
        self.assertEqual(environment.cr.rollbacks, 1)

    def test_source_has_only_controlled_sql_and_no_security_bypass(self):
        source = HELPER_PATH.read_text(encoding="utf-8")
        self.assertEqual(source.count("odoo_env.cr.execute("), 2)
        self.assertIn('odoo_env.cr.execute("SET TRANSACTION READ ONLY")', source)
        self.assertIn('odoo_env.cr.execute("SHOW transaction_read_only")', source)
        for statement in ("INSERT ", "UPDATE ", "DELETE ", "TRUNCATE "):
            self.assertNotIn(statement, source)
        self.assertNotIn("base.group_system", source)
        self.assertNotIn("group_sc_super_admin", source)
        self.assertNotIn("group_sc_business_full", source)
        self.assertNotIn("deny_all_navigation = False", source)
        self.assertNotIn("password", source.casefold())
        self.assertIn("target.write(", source)
        self.assertNotIn("target.create(", source)
        self.assertNotIn("target.unlink(", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
