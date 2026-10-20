#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CORE_PATH = ROOT / "scripts/dev/local_dev_entry_identity_core.py"


def load_core():
    spec = importlib.util.spec_from_file_location("local_dev_entry_identity_core", CORE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


core = load_core()


class LocalDevEntryIdentityCoreTest(unittest.TestCase):
    def test_demo_alias_bound_to_other_database_updates_namespace(self):
        plan = core.plan_binding(
            [{"alias": "demo", "alias_kind": "path", "namespace_id": "ns_000000000002", "retired": False}],
            [{"namespace_id": "ns_000000000002", "database_name": "sc_demo", "lifecycle_state": "active"}],
            "sc_dev_demo",
        )
        self.assertEqual(plan["action"], "update_database")
        self.assertEqual(plan["namespace_id"], "ns_000000000002")

    def test_demo_alias_already_bound_is_noop(self):
        plan = core.plan_binding(
            [{"alias": "demo", "alias_kind": "path", "namespace_id": "ns_000000000002", "retired": False}],
            [{"namespace_id": "ns_000000000002", "database_name": "sc_dev_demo", "lifecycle_state": "active"}],
            "sc_dev_demo",
        )
        self.assertEqual(plan["action"], "noop")

    def test_existing_local_namespace_reassigns_demo_alias(self):
        plan = core.plan_binding(
            [{"alias": "demo", "alias_kind": "path", "namespace_id": "ns_000000000002", "retired": False}],
            [
                {"namespace_id": "ns_000000000002", "database_name": "sc_demo", "lifecycle_state": "active"},
                {"namespace_id": "ns_aaaaaaaaaaaa", "database_name": "sc_dev_demo", "lifecycle_state": "active"},
            ],
            "sc_dev_demo",
        )
        self.assertEqual(plan["action"], "reassign_alias")
        self.assertEqual(plan["namespace_id"], "ns_aaaaaaaaaaaa")

    def test_missing_alias_creates_alias_for_existing_local_namespace(self):
        plan = core.plan_binding(
            [],
            [{"namespace_id": "ns_aaaaaaaaaaaa", "database_name": "sc_dev_demo", "lifecycle_state": "active"}],
            "sc_dev_demo",
        )
        self.assertEqual(plan["action"], "create_alias")
        self.assertEqual(plan["namespace_id"], "ns_aaaaaaaaaaaa")

    def test_missing_alias_and_namespace_creates_stable_namespace(self):
        first = core.plan_binding([], [], "sc_dev_demo")
        second = core.plan_binding([], [], "sc_dev_demo")
        self.assertEqual(first["action"], "create_namespace")
        self.assertEqual(first["namespace_id"], second["namespace_id"])
        self.assertTrue(first["namespace_id"].startswith("ns_"))

    def test_retired_alias_is_reactivated(self):
        plan = core.plan_binding(
            [{"alias": "demo", "alias_kind": "path", "namespace_id": "ns_000000000002", "retired": True}],
            [{"namespace_id": "ns_000000000002", "database_name": "sc_dev_demo", "lifecycle_state": "active"}],
            "sc_dev_demo",
        )
        self.assertEqual(plan["action"], "reactivate_alias")

    def test_multiple_database_namespaces_fail_closed(self):
        with self.assertRaises(ValueError):
            core.plan_binding(
                [],
                [
                    {"namespace_id": "ns_aaaaaaaaaaaa", "database_name": "sc_dev_demo"},
                    {"namespace_id": "ns_bbbbbbbbbbbb", "database_name": "sc_dev_demo"},
                ],
                "sc_dev_demo",
            )


if __name__ == "__main__":
    unittest.main()
