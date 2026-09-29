# -*- coding: utf-8 -*-
"""P0 boundary for workflow projection profiles owned outside `smart_core`.

`smart_construction_core` owns the construction-industry projection only.  A
model owned by a user or product module publishes its own profile through this
registry, and the workflow service merges it at read time.  These tests pin the
two behaviours that keep a capability gap visible instead of silently filled:
a structurally incomplete profile is refused at registration, and callers read
isolated copies so one consumer cannot mutate the registered projection.
"""
import importlib.util
import sys
import unittest
from pathlib import Path


REGISTRY_PATH = Path(__file__).resolve().parents[1] / "utils" / "contract_governance_registry.py"


def _load_registry():
    spec = importlib.util.spec_from_file_location("contract_governance_registry", REGISTRY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["contract_governance_registry"] = module
    spec.loader.exec_module(module)
    return module


def _valid_profile():
    return {
        "state_field": "review_state",
        "state_phase": {"candidate": "draft", "resolved": "done"},
        "state_actions": {"candidate": ["submit"]},
        "method_by_action": {"submit": "action_resolve_customer"},
    }


class TestWorkflowContractProfileRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = _load_registry()

    def test_a_registered_profile_is_readable_by_its_owner(self):
        self.assertTrue(
            self.registry.register_workflow_contract_profile(
                "sc.partner.import.review", _valid_profile(), source="unit.test",
            )
        )
        profiles = self.registry.workflow_contract_profiles()
        self.assertIn("sc.partner.import.review", profiles)
        self.assertEqual(profiles["sc.partner.import.review"]["state_field"], "review_state")
        self.assertEqual(
            self.registry.workflow_contract_profile_sources()["sc.partner.import.review"],
            "unit.test",
        )

    def test_a_profile_missing_a_read_key_is_refused_instead_of_degraded(self):
        for missing in ("state_field", "state_phase", "state_actions", "method_by_action"):
            profile = _valid_profile()
            profile.pop(missing)
            with self.subTest(missing=missing):
                self.assertFalse(
                    self.registry.register_workflow_contract_profile("sc.gap.model", profile)
                )
                self.assertNotIn("sc.gap.model", self.registry.workflow_contract_profiles())

    def test_a_blank_model_name_is_refused(self):
        self.assertFalse(self.registry.register_workflow_contract_profile("  ", _valid_profile()))

    def test_readers_get_isolated_copies(self):
        self.registry.register_workflow_contract_profile("sc.isolated.model", _valid_profile())
        first = self.registry.workflow_contract_profiles()
        first["sc.isolated.model"]["state_field"] = "mutated"
        second = self.registry.workflow_contract_profiles()
        self.assertEqual(second["sc.isolated.model"]["state_field"], "review_state")


if __name__ == "__main__":
    unittest.main()
