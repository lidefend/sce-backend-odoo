#!/usr/bin/env python3
"""Offline tests for CAP-02C-04 D3 capability impact propagation."""
from __future__ import annotations

import unittest

from scripts.verify import capability_impact_propagation as d3


CTX = {
    "reverse_index": {
        "smart_construction_core": [
            {"capability_key": "project.initiation.create", "provider_type": "odoo_model",
             "provider_ref": "project.project", "disposition": "keep"},
            {"capability_key": "project.list.open", "provider_type": "odoo_action",
             "provider_ref": "smart_construction_core.action_sc_project_list", "disposition": "keep"},
        ],
        "customer_custom": [
            {"capability_key": "project.list.open", "provider_type": "odoo_model",
             "provider_ref": "project.project", "disposition": "keep"},
        ],
        "legacy_module": [
            {"capability_key": "cost.progress.report", "provider_type": "odoo_model",
             "provider_ref": "project.progress.entry", "disposition": "retire"},
        ],
    },
    "mechanism_impact": {
        "base_tier_validation": ["contract.settlement.audit", "finance.payment_request.form"],
    },
    "acceptance_capabilities": {
        "project.initiation.create", "project.list.open", "contract.settlement.audit",
    },
    "capability_to_scenes": {
        "project.initiation.create": ["project.initiation", "project.plan"],
        "project.list.open": ["project.list"],
        "contract.settlement.audit": ["contracts.monitor"],
        "cost.progress.report": ["cost.monitor"],
    },
    "product_scene_keys": {"project.initiation", "project.list", "contracts.monitor"},
    "capability_dependencies": {},
}


def _asset(**overrides):
    asset = {"fact_identity": "field:project.project:x_custom_field", "asset_type": "field",
             "asset_modules": ["smart_construction_core"], "model_owner": "project",
             "model_extensions": ["smart_construction_core"]}
    asset.update(overrides)
    return asset


def _run(*assets, runtime_coverage=True):
    ctx = dict(CTX)
    ctx["runtime_coverage"] = runtime_coverage
    return d3.propagate(list(assets), **ctx)


class PropagationTests(unittest.TestCase):
    def test_multi_module_jointly_provides_capability(self):
        result = _run(_asset(asset_modules=["smart_construction_core", "customer_custom"]))
        cap = next(c for c in result["impacted_capabilities"] if c["capability_key"] == "project.list.open")
        modules = {p["module"] for p in cap["providers"]}
        self.assertEqual(modules, {"smart_construction_core", "customer_custom"})

    def test_single_provider_affects_multiple_capabilities(self):
        result = _run(_asset(asset_modules=["smart_construction_core"]))
        caps = {c["capability_key"] for c in result["impacted_capabilities"]}
        self.assertIn("project.initiation.create", caps)
        self.assertIn("project.list.open", caps)

    def test_capability_relates_multiple_scenes(self):
        result = _run(_asset(asset_modules=["smart_construction_core"]))
        cap = next(c for c in result["impacted_capabilities"] if c["capability_key"] == "project.initiation.create")
        self.assertEqual(cap["scenes"], ["project.initiation", "project.plan"])

    def test_provider_missing_is_unresolved(self):
        result = _run(_asset(asset_modules=["nonexistent_module"]))
        self.assertTrue(any(u["reason"] == "no_association_confirmed" for u in result["unresolved"]))
        self.assertTrue(result["has_unresolved_impact"])

    def test_unregistered_intent_is_unresolved(self):
        result = _run(_asset(asset_type="intent", fact_identity="intent:ui.contract:unregistered",
                             asset_modules=[], model_owner="", model_extensions=[]))
        self.assertTrue(any(u["reason"] == "runtime_unverified" for u in result["unresolved"]))

    def test_model_extension_multi_module_contributes(self):
        result = _run(_asset(model_extensions=["smart_construction_core", "customer_custom"]))
        cap = next(c for c in result["impacted_capabilities"] if c["capability_key"] == "project.list.open")
        modules = {p["module"] for p in cap["providers"]}
        self.assertEqual(modules, {"smart_construction_core", "customer_custom"})

    def test_contract_missing_is_unresolved_but_scene_kept(self):
        result = _run(_asset(asset_modules=["legacy_module"]))
        cap = next(c for c in result["impacted_capabilities"] if c["capability_key"] == "cost.progress.report")
        self.assertFalse(cap["contract"])
        self.assertEqual(cap["scenes"], ["cost.monitor"])
        self.assertTrue(any(u["reason"] == "contract_missing" for u in result["unresolved"]))

    def test_scene_reference_to_historical_capability_is_surfaced(self):
        result = _run(_asset(asset_modules=["legacy_module"]))
        cap = next(c for c in result["impacted_capabilities"] if c["capability_key"] == "cost.progress.report")
        self.assertEqual(cap["scenes"], ["cost.monitor"])
        self.assertTrue(cap["historical"])

    def test_unrelated_module_change_does_not_propagate(self):
        result = _run(_asset(asset_modules=["smart_license_core"], model_owner="",
                             model_extensions=[]))
        self.assertFalse(result["impacted_capabilities"])
        self.assertTrue(any(u["reason"] == "no_association_confirmed" for u in result["unresolved"]))

    def test_incomplete_model_extensions_is_unresolved(self):
        result = _run(_asset(model_extensions_incomplete=True,
                             unaccounted_contributions=["customer_custom"]))
        self.assertTrue(any(u["reason"] == "model_extensions_incomplete" for u in result["unresolved"]))

    def test_provider_association_unresolved_when_incomplete(self):
        result = _run(_asset(asset_modules=["nonexistent_module"]), runtime_coverage=False)
        self.assertTrue(any(u["reason"] == "association_unresolved" for u in result["unresolved"]))

    def test_intent_handler_missing_is_confirmed(self):
        result = _run(_asset(asset_type="intent", fact_identity="intent:ui.contract:x",
                             asset_modules=[], model_owner="", model_extensions=[],
                             handler_missing=True))
        self.assertTrue(any(u["reason"] == "handler_missing" for u in result["unresolved"]))

    def test_intent_handler_resolved_propagates(self):
        asset = _asset(asset_type="intent", fact_identity="intent:ui.contract:describe",
                       asset_modules=["smart_construction_core"], model_owner="",
                       model_extensions=[], value={"intent": "ui.contract",
                                                   "handler": "CapabilityDescribeHandler",
                                                   "module": "smart_construction_core"})
        result = _run(asset)
        self.assertTrue(any(c["capability_key"] == "project.list.open"
                            for c in result["impacted_capabilities"]))


if __name__ == "__main__":
    unittest.main()
