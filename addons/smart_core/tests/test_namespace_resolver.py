# -*- coding: utf-8 -*-
"""Offline tests for the Batch C path-namespace resolver.

The resolver is the only place that turns an entry stamp into a database.  These
tests prove it fails closed for a missing signature, a route-version drift, an
audience mismatch, an unknown alias, and — critically — a namespace bound to a
different database than the instance serving the request.
"""

import importlib.util
import sys
import types
import unittest
from pathlib import Path


def _install_package(root: Path):
    pkg = types.ModuleType("smart_core")
    pkg.__path__ = [str(root)]
    security_pkg = types.ModuleType("smart_core.security")
    security_pkg.__path__ = [str(root / "security")]
    sys.modules["smart_core"] = pkg
    sys.modules["smart_core.security"] = security_pkg


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class _Cr:
    def __init__(self, dbname):
        self.dbname = dbname


class _Config:
    def __init__(self, params):
        self._params = dict(params)

    def sudo(self):
        return self

    def get_param(self, key, default=""):
        return self._params.get(key, default)


class _Record:
    def __init__(self, namespace_id, database_name, audience="tenant", duty_key="demo"):
        self.namespace_id = namespace_id
        self.database_name = database_name
        self.audience = audience
        self.duty_key = duty_key
        self.lifecycle_state = "active"


class _NamespaceModel:
    def __init__(self, records):
        self._records = records

    def sudo(self):
        return self

    def resolve_alias(self, alias):
        record = self._records.get(alias)
        if record is None:
            raise sys.modules["smart_core.security.namespace_errors"].UnknownNamespace(alias)
        return record

    def resolve_for_database(self, database):
        for record in self._records.values():
            if record.database_name == database:
                return record
        raise sys.modules["smart_core.security.namespace_errors"].UnknownNamespace(database)


class _Env(dict):
    def __init__(self, dbname, records, params=None):
        super().__init__(
            {
                "sc.platform.namespace": _NamespaceModel(records),
                "ir.config_parameter": _Config(
                    params
                    or {
                        "sc.entry.shared_secret": "entry-secret",
                        "sc.entry.route_version": "v1",
                    }
                ),
            }
        )
        self.cr = _Cr(dbname)


def _headers(alias="demo", **overrides):
    values = {
        "X-SC-Namespace": alias,
        "X-SC-Audience": "platform-admin" if alias == "platform" else "tenant",
        "X-SC-Entry-Secret": "entry-secret",
        "X-SC-Route-Version": "v1",
    }
    values.update(overrides)
    return values


class TestNamespaceResolver(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        _install_package(root)
        self.errors = _load(
            "smart_core.security.namespace_errors", root / "security" / "namespace_errors.py"
        )
        self.resolver = _load(
            "smart_core.security.namespace_resolver", root / "security" / "namespace_resolver.py"
        )
        self.records = {
            "demo": _Record("ns_demo", "sc_demo", audience="tenant"),
            "platform": _Record("ns_platform", "sc_platform_control", audience="platform-admin"),
        }

    def test_path_prefix_selects_namespace(self):
        self.assertEqual(self.resolver.parse_path_namespace("/t/demo/api/x"), "demo")
        self.assertEqual(self.resolver.parse_path_namespace("/platform-admin/login"), "platform")
        self.assertEqual(self.resolver.parse_path_namespace("/api/x"), "")

    def test_matching_namespace_resolves_the_bound_database(self):
        ref = self.resolver.resolve_entry(_Env("sc_demo", self.records), _headers("demo"))
        self.assertEqual(ref.namespace_id, "ns_demo")
        self.assertEqual(ref.database_name, "sc_demo")

    def test_namespace_bound_to_another_database_is_refused(self):
        env = _Env("sc_demo", self.records)
        with self.assertRaises(self.errors.NamespaceTargetMismatch) as raised:
            self.resolver.resolve_entry(env, _headers("platform"))
        self.assertEqual(raised.exception.code, "NS_NAMESPACE_TARGET_MISMATCH")
        self.assertEqual(raised.exception.http_status, 421)

    def test_missing_secret_is_refused(self):
        env = _Env("sc_demo", self.records)
        with self.assertRaises(self.errors.EntrySignatureInvalid):
            self.resolver.resolve_entry(
                env, _headers("demo", **{"X-SC-Entry-Secret": "wrong"})
            )

    def test_route_version_drift_is_refused(self):
        env = _Env("sc_demo", self.records)
        with self.assertRaises(self.errors.RouteVersionMismatch):
            self.resolver.resolve_entry(
                env, _headers("demo", **{"X-SC-Route-Version": "v0"})
            )

    def test_audience_must_match_the_namespace(self):
        env = _Env("sc_demo", self.records)
        with self.assertRaises(self.errors.EntrySignatureInvalid):
            self.resolver.resolve_entry(
                env, _headers("demo", **{"X-SC-Audience": "platform-admin"})
            )

    def test_unknown_alias_is_refused(self):
        env = _Env("sc_demo", self.records)
        with self.assertRaises(self.errors.UnknownNamespace):
            self.resolver.resolve_entry(env, _headers("unknown"))

    def test_missing_namespace_header_is_refused(self):
        env = _Env("sc_demo", self.records)
        with self.assertRaises(self.errors.NamespaceRequired):
            self.resolver.resolve_entry(env, _headers(""))

    def test_instance_resolution_uses_its_own_database(self):
        ref = self.resolver.resolve_instance(_Env("sc_platform_control", self.records))
        self.assertEqual(ref.namespace_id, "ns_platform")
        self.assertEqual(ref.database_name, "sc_platform_control")


if __name__ == "__main__":
    unittest.main()
