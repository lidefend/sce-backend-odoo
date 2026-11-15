#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = Path(__file__).with_name("r10_performance_ab_profile.py")
SPEC = importlib.util.spec_from_file_location("r10_performance_ab_profile", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def load_payload() -> dict:
    return json.loads(module.DEFAULT_PROFILE.read_text(encoding="utf-8"))


def observed_clean(payload: dict) -> dict:
    return {
        "containers": [
            "sc-demo-dev-db-1",
            "sc-demo-dev-redis-1",
            "sc-demo-dev-odoo-1",
            "sc-demo-dev-nginx-1",
        ],
        "volumes": ["sc_demo_db_data", "sc_demo_odoo_data", "sc_demo_redis_data"],
        "networks": ["sc-demo-dev_default", "sc-daily-entry"],
        "listening_ports": [18081, 18082, 18083, 8070],
        "disk_free_bytes": 8 * 1024**3,
        "memory_available_bytes": 4 * 1024**3,
        "paths": {
            "/opt/projects/perf-r10/a/sce-product-odoo": False,
            "/data/perf-r10/a/dist": False,
            "/data/perf-r10/a/logs": False,
            "/opt/projects/perf-r10/b/sce-product-odoo": False,
            "/data/perf-r10/b/dist": False,
            "/data/perf-r10/b/logs": False,
        },
    }


class R10PerformanceProfileTest(unittest.TestCase):
    def test_profile_and_plan_are_identity_bound_and_non_mutating(self):
        payload = module.load_profile()
        plan = module.build_plan(payload)
        self.assertFalse(plan["creates_resources"])
        self.assertEqual(payload["source"]["project_record_id"], 2)
        self.assertEqual(payload["source"]["database"], "sc_demo")
        self.assertEqual(payload["arms"]["a"]["public_port"], 18181)
        self.assertEqual(payload["arms"]["b"]["public_port"], 18182)
        self.assertEqual(payload["runtime"]["max_cron_threads"], 0)
        self.assertFalse(payload["runtime"]["external_egress_allowed"])
        self.assertTrue(payload["runtime"]["readonly_operation_only"])
        self.assertTrue(payload["snapshot"]["paired_restore_drill_required"])
        self.assertFalse(payload["snapshot"]["source_write_allowed"])
        self.assertEqual(payload["measurement"]["cold_samples_per_arm_viewport"], 9)
        self.assertEqual(payload["measurement"]["warm_samples_per_arm"], 9)

    def test_current_duty_continuity_contract_does_not_restate_old_uuid(self):
        payload = module.load_profile()
        contract = json.loads(module.contract_file(module.DEFAULT_PROFILE, payload["snapshot"]["contract"]).read_text())
        self.assertEqual(contract["duty"], "demo")
        self.assertNotIn("backup_root", contract)
        self.assertEqual(payload["snapshot"]["root"], "/data/backups/daily-demo-dev")
        self.assertNotIn("source_database_uuid", contract)
        self.assertFalse(contract["upgrade_contract"]["fixture_write_allowed"])
        self.assertFalse(contract["upgrade_contract"]["demo_data_write_allowed"])

    def test_profile_requires_the_governed_database_name_in_each_cluster(self):
        payload = load_payload()
        payload["arms"]["a"]["database"] = "sc_demo_other"
        payload["arms"]["a"]["database_filter"] = "^sc_demo_other$"
        with self.assertRaisesRegex(module.ProfileError, "governed snapshot database"):
            module.validate_profile(payload)

    def test_profile_rejects_duplicate_arm_ports_volumes_and_networks(self):
        for key in ("public_port", "database_volume", "internal_network"):
            with self.subTest(key=key):
                payload = load_payload()
                payload["arms"]["b"][key] = payload["arms"]["a"][key]
                with self.assertRaisesRegex(module.ProfileError, key):
                    module.validate_profile(payload)

    def test_profile_requires_cron_and_egress_isolation(self):
        payload = load_payload()
        payload["runtime"]["max_cron_threads"] = 2
        with self.assertRaisesRegex(module.ProfileError, "cron"):
            module.validate_profile(payload)
        payload = load_payload()
        payload["runtime"]["external_egress_allowed"] = True
        with self.assertRaisesRegex(module.ProfileError, "egress"):
            module.validate_profile(payload)
        payload = load_payload()
        payload["runtime"]["readonly_operation_only"] = False
        with self.assertRaisesRegex(module.ProfileError, "readonly"):
            module.validate_profile(payload)

    def test_profile_rejects_source_writes_or_wrong_measurement(self):
        payload = load_payload()
        payload["snapshot"]["source_write_allowed"] = True
        with self.assertRaisesRegex(module.ProfileError, "source writes"):
            module.validate_profile(payload)
        payload = load_payload()
        payload["measurement"]["warm_samples_per_arm"] = 8
        with self.assertRaisesRegex(module.ProfileError, "warm sample"):
            module.validate_profile(payload)

    def test_preflight_passes_only_when_resources_and_ports_are_clear(self):
        payload = module.load_profile()
        result = module.evaluate_preflight(payload, observed_clean(payload))
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(all(row["passed"] for row in result["checks"]))
        self.assertFalse(result["creates_resources"])

    def test_preflight_blocks_occupied_port_or_existing_arm_resource(self):
        payload = module.load_profile()
        occupied = observed_clean(payload)
        occupied["listening_ports"].append(18181)
        occupied["containers"].append("sc-perf-b-r10-odoo-1")
        result = module.evaluate_preflight(payload, occupied)
        self.assertEqual(result["status"], "BLOCKED")
        failed = {row["id"] for row in result["checks"] if not row["passed"]}
        self.assertIn("a_port_free", failed)
        self.assertIn("b_containers_absent", failed)

    def test_preflight_requires_current_a_containers_and_resource_headroom(self):
        payload = module.load_profile()
        empty = {
            "containers": [],
            "volumes": [],
            "networks": [],
            "listening_ports": [],
            "disk_free_bytes": 0,
            "memory_available_bytes": 0,
            "paths": {},
        }
        result = module.evaluate_preflight(payload, empty)
        failed = {row["id"] for row in result["checks"] if not row["passed"]}
        self.assertIn("current_a_demo_containers_present", failed)
        self.assertIn("disk_headroom", failed)
        self.assertIn("memory_headroom", failed)


if __name__ == "__main__":
    unittest.main()
