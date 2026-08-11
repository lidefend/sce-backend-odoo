from __future__ import annotations

import copy
import json
import unittest

from scripts.verify import business_entry_ownership_guard as guard
from scripts.verify import backend_business_fact_model_audit as model_audit


class BusinessEntryOwnershipGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(guard.REGISTRY.read_text(encoding="utf-8"))

    def test_repository_registry_passes(self):
        self.assertEqual(guard.validate(self.registry), [])

    def test_shared_fact_model_drift_fails_closed(self):
        registry = copy.deepcopy(self.registry)
        spec = next(item for item in registry["ownership_specs"] if item.get("entry_bindings"))
        spec["entry_bindings"][1]["fact_model"] = spec["entry_bindings"][0]["fact_model"]
        errors = guard.validate(registry)
        self.assertTrue(any("distinct fact model" in item for item in errors), errors)

    def test_frontend_fact_authority_fails_closed(self):
        registry = copy.deepcopy(self.registry)
        spec = next(item for item in registry["ownership_specs"] if item.get("entry_bindings"))
        spec["authority_carriers"].append("frontend/apps/web/src/fake.ts")
        errors = guard.validate(registry)
        self.assertTrue(any("outside frontend" in item for item in errors), errors)

    def test_dispatch_workspace_cannot_become_fact_owner(self):
        registry = copy.deepcopy(self.registry)
        spec = next(item for item in registry["ownership_specs"] if item.get("separation_policy") == "transient_dispatch_only")
        binding = spec["entry_bindings"][0]
        binding["entry_model"] = binding["fact_models"][0]
        errors = guard.validate(registry)
        self.assertTrue(any("must not own a business fact" in item for item in errors), errors)

    def test_contract_source_isolation_action_is_governed(self):
        registry = copy.deepcopy(self.registry)
        spec = next(item for item in registry["ownership_specs"] if item.get("source_isolation_actions"))
        spec["source_isolation_actions"][0]["required_domain_tokens"].append("missing_source_token")
        errors = guard.validate(registry)
        self.assertTrue(any("source-isolation action definition drifted" in item for item in errors), errors)

    def test_explicit_family_owner_precedes_heuristic_classifier(self):
        rows = [
            {
                "path": "addons/smart_construction_core/models/core/example.py",
                "model": "sc.example.payment",
                "inherit": None,
                "fields": [],
                "buckets": ["core"],
                "model_family": "unclassified",
                "universal_carrier_fit": "review_required",
            }
        ]
        family_registry = {
            "families": [
                {
                    "family": "document admin payroll and office operations",
                    "owned_models": ["sc.example.payment"],
                }
            ]
        }
        model_audit.apply_registered_family_ownership(rows, family_registry)
        self.assertEqual(
            rows[0]["model_family"],
            "document admin payroll and office operations",
        )


if __name__ == "__main__":
    unittest.main()
