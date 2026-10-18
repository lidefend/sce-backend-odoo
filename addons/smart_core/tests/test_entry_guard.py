# -*- coding: utf-8 -*-
"""Offline tests for the unified ``/api/`` entry guard (ADR-007 batch C).

The guard is what makes an undeclared path namespace impossible to serve: a
public route that never calls the resolver itself still gets refused, because
``ir.http._pre_dispatch`` runs it before any controller.
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


class _Env(dict):
    def __init__(self, dbname, records):
        super().__init__(
            {
                "sc.platform.namespace": _NamespaceModel(records),
                "ir.config_parameter": _Config(
                    {
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


class TestEntryGuard(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        _install_package(root)
        self.errors = _load(
            "smart_core.security.namespace_errors", root / "security" / "namespace_errors.py"
        )
        self.resolver = _load(
            "smart_core.security.namespace_resolver", root / "security" / "namespace_resolver.py"
        )
        self.guard = _load(
            "smart_core.security.entry_guard", root / "security" / "entry_guard.py"
        )
        self.records = {
            "demo": _Record("ns_demo", "sc_demo", audience="tenant"),
            "platform": _Record("ns_platform", "sc_platform_control", audience="platform-admin"),
        }

    def test_only_the_api_surface_is_entry_scoped(self):
        self.assertTrue(self.guard.requires_entry_namespace("/api/runtime-version"))
        self.assertTrue(self.guard.requires_entry_namespace("/api/intent"))
        self.assertFalse(self.guard.requires_entry_namespace("/web/login"))
        self.assertFalse(self.guard.requires_entry_namespace("/report/pdf/x"))

    def test_non_api_paths_keep_their_native_behaviour(self):
        self.assertIsNone(
            self.guard.enforce_entry_namespace(_Env("sc_demo", self.records), "/web/login", {})
        )

    def test_unknown_alias_is_refused_before_the_controller(self):
        env = _Env("sc_demo", self.records)
        with self.assertRaises(self.errors.UnknownNamespace) as raised:
            self.guard.enforce_entry_namespace(
                env, "/api/runtime-version", _headers("sc_undeclared_entry_probe")
            )
        self.assertEqual(raised.exception.code, "NS_UNKNOWN_NAMESPACE")
        self.assertEqual(raised.exception.http_status, 404)

    def test_direct_api_traffic_without_a_stamp_is_refused(self):
        env = _Env("sc_demo", self.records)
        with self.assertRaises(self.errors.NamespaceRequired) as raised:
            self.guard.enforce_entry_namespace(env, "/api/runtime-version", {})
        self.assertEqual(raised.exception.code, "NS_NAMESPACE_REQUIRED")
        self.assertEqual(raised.exception.http_status, 400)

    def test_foreign_target_namespace_is_refused(self):
        env = _Env("sc_demo", self.records)
        with self.assertRaises(self.errors.NamespaceTargetMismatch) as raised:
            self.guard.enforce_entry_namespace(env, "/api/runtime-version", _headers("platform"))
        self.assertEqual(raised.exception.code, "NS_NAMESPACE_TARGET_MISMATCH")
        self.assertEqual(raised.exception.http_status, 421)

    def test_matching_namespace_reaches_the_bound_database(self):
        env = _Env("sc_demo", self.records)
        ref = self.guard.enforce_entry_namespace(env, "/api/runtime-version", _headers("demo"))
        self.assertEqual(ref.namespace_id, "ns_demo")
        self.assertEqual(ref.database_name, "sc_demo")

    def test_error_body_is_stable_json(self):
        body = self.guard.namespace_error_body(self.errors.UnknownNamespace("unknown x"))
        self.assertEqual(body["error"], "NS_UNKNOWN_NAMESPACE")
        self.assertEqual(body["message"], "unknown x")


if __name__ == "__main__":
    unittest.main()
