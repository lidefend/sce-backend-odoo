#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


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

    def sudo(self):
        return self

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
        self.fail_after_write = False

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
    def __init__(self, targets):
        self.targets = list(targets)

    def sudo(self):
        return self

    def with_context(self, **_values):
        return self

    def search(self, domain):
        if domain != [("login", "=", "admin")]:
            raise AssertionError(domain)
        return FakeRecordset(self.targets)


class FakeModules:
    def __init__(self, states=None, pending=0):
        self.states = states or {name: "installed" for name in FORMAL_MODULES}
        self.pending = pending

    def sudo(self):
        return self

    def search(self, domain):
        names = domain[0][2]
        return FakeRecordset(
            type("Module", (), {"name": name, "state": self.states[name]})()
            for name in names
            if name in self.states
        )

    def search_count(self, domain):
        if domain != [("state", "in", ["to install", "to upgrade", "to remove"])]:
            raise AssertionError(domain)
        return self.pending


class Savepoint:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class FakeCursor:
    dbname = "sc_production"

    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

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
    def __init__(self, targets, *, states=None, pending=0):
        self.users = FakeUsers(targets)
        self.modules = FakeModules(states, pending)
        self.cr = FakeCursor()

    def __getitem__(self, model):
        if model == "res.users":
            return self.users
        if model == "ir.module.module":
            return self.modules
        raise AssertionError(model)

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
                Path(self.temp.name) / f"{mode}-{len(list(Path(self.temp.name).iterdir()))}.json"
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

    def test_dry_run_is_default_and_writes_nothing(self):
        user = FakeUser(groups=[INTERNAL])
        environment = FakeEnvironment([user])
        active = self.env()
        active.pop("ADMIN_IDENTITY_BASELINE_MODE")
        result = self.call(environment, active)
        self.assertEqual(result["status"], "DRY_RUN")
        self.assertEqual(user.writes, [])
        self.assertEqual(environment.cr.commits, 0)
        self.assertEqual(environment.cr.rollbacks, 1)
        self.assertEqual(
            json.loads(Path(active["ADMIN_IDENTITY_EVIDENCE_OUTPUT"]).read_text())[
                "planned_additions"
            ],
            ["smart_core.group_smart_core_admin"],
        )

    def test_apply_adds_only_canonical_role_and_is_idempotent(self):
        user = FakeUser(groups=[INTERNAL])
        environment = FakeEnvironment([user])
        result = self.call(environment, self.env("apply"))
        self.assertEqual(result["status"], "APPLIED")
        self.assertEqual(user.writes, [{"groups_id": [(4, CANONICAL.id)]}])
        self.assertEqual(result["role_after"], "system_admin")
        self.assertFalse(result["deny_all_navigation_after"])
        self.assertEqual(environment.cr.commits, 1)

        second = self.call(environment, self.env("apply"))
        self.assertEqual(second["status"], "NOOP")
        self.assertEqual(len(user.writes), 1)

    def test_navigation_recovers_without_policy_bypass(self):
        resolver = FakeResolver(None)
        nav = [{"xmlid": "smart_construction_core.menu_sc_root"}]
        restricted = resolver.build_role_surface({"base.group_user"}, nav, set())
        admin = resolver.build_role_surface(
            {"base.group_user", "smart_core.group_smart_core_admin"}, nav, set()
        )
        self.assertEqual(resolver.filter_nav_for_role_surface(nav, restricted), [])
        self.assertEqual(resolver.filter_nav_for_role_surface(nav, admin), nav)

    def test_canonical_role_is_derived_from_authoritative_policy(self):
        self.assertEqual(
            policy.ROLE_GROUPS_EXPLICIT["system_admin"],
            {"smart_core.group_smart_core_admin"},
        )
        self.assertEqual(policy.ROLE_PRECEDENCE[0], "system_admin")
        self.assertTrue(policy.ROLE_SURFACE_OVERRIDES["restricted"]["deny_all_navigation"])
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

    def test_non_admin_login_and_evidence_scope_are_rejected(self):
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

    def test_source_has_no_security_bypass_or_direct_sql(self):
        source = HELPER_PATH.read_text(encoding="utf-8")
        self.assertNotIn(".execute(", source)
        self.assertNotIn("base.group_system", source)
        self.assertNotIn("group_sc_super_admin", source)
        self.assertNotIn("group_sc_business_full", source)
        self.assertNotIn("deny_all_navigation = False", source)
        self.assertNotIn("password", source.casefold())
        self.assertIn('target.write(', source)
        self.assertIn('"groups_id"', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
