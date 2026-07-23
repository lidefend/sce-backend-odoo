#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import importlib.util
import io
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HELPER_PATH = ROOT / "scripts/release/production_admin_harden.py"
SPEC = importlib.util.spec_from_file_location("production_admin_harden", HELPER_PATH)
assert SPEC and SPEC.loader
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)

SECRET = "Unique-Production-Admin-42!"


def valid_env() -> dict[str, str]:
    return {
        "ENV": "prod",
        "PROD_DANGER": "1",
        "TARGET_DB": "sc_production",
        "CONFIRM_ADMIN_HARDEN": "YES_HARDEN_FRESH_PRODUCTION_ADMIN",
        "SC_BOOTSTRAP_ADMIN_PASSWORD": SECRET,
    }


class FakeRecordset:
    def __init__(self, records):
        self.records = list(records)

    def __len__(self):
        return len(self.records)

    @property
    def id(self):
        return self.records[0].id if len(self.records) == 1 else False

    @property
    def active(self):
        return self.records[0].active if len(self.records) == 1 else False

    def filtered(self, predicate):
        return FakeRecordset(record for record in self.records if predicate(record))

    def write(self, values):
        if len(self.records) != 1:
            raise AssertionError("write requires one record")
        return self.records[0].write(values)


class FakeUser:
    def __init__(self, user_id: int, *, active: bool = True):
        self.id = user_id
        self.active = active
        self.writes = []

    def write(self, values):
        self.writes.append(values)
        return True


class FakeUsers:
    def __init__(self, targets):
        self.targets = targets
        self.used_sudo = False
        self.context = None
        self.domain = None

    def sudo(self):
        self.used_sudo = True
        return self

    def with_context(self, **values):
        self.context = values
        return self

    def search(self, domain):
        self.domain = domain
        return FakeRecordset(self.targets)


class FakeCursor:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


class FakeEnvironment:
    def __init__(self, targets, system_users):
        self.users = FakeUsers(targets)
        self.group = type("Group", (), {"users": FakeRecordset(system_users)})()
        self.cr = FakeCursor()

    def __getitem__(self, model):
        if model != "res.users":
            raise AssertionError(model)
        return self.users

    def ref(self, xml_id):
        if xml_id != "base.group_system":
            raise AssertionError(xml_id)
        return self.group


class ControlPlaneTests(unittest.TestCase):
    def test_valid_control_plane(self):
        helper.validate_control_plane(valid_env())

    def test_missing_danger_is_rejected(self):
        active = valid_env()
        active.pop("PROD_DANGER")
        with self.assertRaises(helper.AdminHardenError):
            helper.validate_control_plane(active)

    def test_wrong_confirmation_is_rejected(self):
        active = valid_env()
        active["CONFIRM_ADMIN_HARDEN"] = "yes"
        with self.assertRaises(helper.AdminHardenError):
            helper.validate_control_plane(active)

    def test_missing_dedicated_secret_is_rejected(self):
        active = valid_env()
        active.pop("SC_BOOTSTRAP_ADMIN_PASSWORD")
        with self.assertRaises(helper.AdminHardenError):
            helper.validate_control_plane(active)

    def test_database_drift_is_rejected(self):
        active = valid_env()
        active["TARGET_DB"] = "other"
        with self.assertRaises(helper.AdminHardenError):
            helper.validate_control_plane(active)

    def test_default_and_weak_secrets_are_rejected(self):
        for value in ("admin", "alllowercasebutlongenough"):
            active = valid_env()
            active["SC_BOOTSTRAP_ADMIN_PASSWORD"] = value
            with self.assertRaises(helper.AdminHardenError):
                helper.validate_control_plane(active)


class OrmHardenTests(unittest.TestCase):
    def test_password_is_changed_through_orm_and_committed(self):
        admin = FakeUser(2)
        active_env = valid_env()
        odoo_env = FakeEnvironment([admin], [admin])

        result = helper.harden_admin(odoo_env, active_env)

        self.assertEqual(result, {"status": "PASS", "login": "admin", "user_id": 2})
        self.assertTrue(odoo_env.users.used_sudo)
        self.assertEqual(odoo_env.users.context, {"active_test": False})
        self.assertEqual(odoo_env.users.domain, [("login", "=", "admin")])
        self.assertEqual(admin.writes, [{"password": SECRET}])
        self.assertEqual(odoo_env.cr.commits, 1)

    def test_target_admin_drift_is_rejected(self):
        for targets in ([], [FakeUser(2), FakeUser(3)], [FakeUser(2, active=False)]):
            with self.subTest(count=len(targets)):
                odoo_env = FakeEnvironment(targets, targets)
                with self.assertRaises(helper.AdminHardenError):
                    helper.harden_admin(odoo_env, valid_env())

    def test_another_active_system_admin_is_rejected(self):
        admin = FakeUser(2)
        other = FakeUser(3)
        with self.assertRaises(helper.AdminHardenError):
            helper.harden_admin(
                FakeEnvironment([admin], [admin, other]),
                valid_env(),
            )

    def test_safe_output_never_contains_secret(self):
        admin = FakeUser(2)
        result = helper.harden_admin(FakeEnvironment([admin], [admin]), valid_env())
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            print(result)
        self.assertNotIn(SECRET, output.getvalue())

    def test_source_has_no_fallback_or_direct_sql(self):
        source = HELPER_PATH.read_text(encoding="utf-8")
        self.assertNotIn("FORMAL_ACCEPTANCE_PASSWORD", source)
        self.assertNotIn("ADMIN_PASSWD", source)
        self.assertNotIn(".execute(", source)
        self.assertNotIn("password_crypt", source)
        self.assertIn('target.write({"password": password})', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
