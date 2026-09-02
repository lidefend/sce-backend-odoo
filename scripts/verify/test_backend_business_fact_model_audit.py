#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("backend_business_fact_model_audit.py")
SPEC = importlib.util.spec_from_file_location("backend_business_fact_model_audit", MODULE_PATH)
AUDIT = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(AUDIT)


class BackendBusinessFactModelAuditTest(unittest.TestCase):
    def test_exact_source_extract_proves_each_orm_projection_mode(self):
        expected = {
            "sc.dashboard.cockpit.fact": "runtime_workbench_fact",
            "sc.workbench.item": "runtime_workbench_fact",
            "sc.contract.recon.summary": "computed_runtime_summary",
            "project.cost.ledger": "controlled_generated_ledger",
            "payment.ledger": "controlled_generated_ledger",
            "sc.treasury.ledger": "controlled_generated_ledger",
            "project.boq.summary.component": "controlled_writable_snapshot",
        }
        rows = {row["model"]: row for row in AUDIT.extract_models() if row.get("model") in expected}
        self.assertEqual(set(expected), set(rows))
        for model, mode in expected.items():
            self.assertEqual([mode], rows[model]["projection_semantic_modes"], model)

    def test_traceable_writable_model_is_a_formal_fact(self):
        buckets = AUDIT.classify_model(
            "addons/smart_construction_core/models/core/example.py",
            "sc.example.fact",
            None,
            "Example fact",
            {"source_origin", "legacy_source_model", "legacy_record_id"},
            {},
            True,
        )
        self.assertIn("formal_fact", buckets)

    def test_traceable_sql_view_is_projection_not_formal_fact(self):
        buckets = AUDIT.classify_model(
            "addons/smart_construction_core/models/core/example_ledger.py",
            "sc.example.ledger",
            None,
            "Example ledger",
            {"source_origin", "legacy_source_model", "legacy_record_id"},
            {},
            False,
        )
        self.assertIn("projection", buckets)
        self.assertNotIn("formal_fact", buckets)

    def test_writable_boq_snapshot_remains_a_projection(self):
        buckets = AUDIT.classify_model(
            "addons/smart_construction_core/models/core/boq_analysis.py",
            "project.boq.summary.component",
            None,
            "Published BOQ summary snapshot",
            {"project_id", "quantity"},
            {"quantity": "Float"},
            True,
        )
        self.assertIn("projection", buckets)

    def test_snapshot_source_semantics_only_prove_snapshot_mode(self):
        fields = [{"name": "version_id"}]
        source = '''
class Snapshot:
    def _assert_draft(self):
        if self.version_id.state != "draft":
            raise Exception()
    def write(self, vals):
        self._assert_draft()
    def unlink(self):
        self._assert_draft()
'''
        modes = AUDIT.classify_projection_semantic_modes(
            "project.boq.summary.component", None, fields, "[]", source, True, False
        )
        self.assertEqual(["controlled_writable_snapshot"], modes)

    def test_wrong_orm_projection_mode_fails_closed(self):
        row = {
            "model": "project.boq.summary.component",
            "buckets": ["projection"],
            "projection_storage_kind": "orm_table",
            "projection_semantic_modes": ["controlled_writable_snapshot"],
        }
        item = {
            "model": "project.boq.summary.component",
            "implementation_mode": "runtime_workbench_fact",
            "write_policy": "wrong",
            "source_models": ["project.boq.version"],
            "refresh_owner": "wrong",
            "idempotency_key": "wrong",
            "acceptance_probe": "wrong",
        }
        report = AUDIT.summarize_projection_registry([row], {"projections": [item]})
        self.assertEqual(1, report["projection_registry_implementation_gap_count"])

    def test_abstract_model_remains_in_inventory_without_projection_bucket(self):
        buckets = AUDIT.classify_model(
            "addons/smart_construction_core/models/optional_product_projection.py",
            "sc.optional.product.projection",
            None,
            "Optional projection helper",
            set(),
            {},
            True,
            True,
        )
        self.assertIn("abstract_model", buckets)
        self.assertNotIn("projection", buckets)

    def test_native_references_and_empty_projection_list_are_valid(self):
        report = AUDIT.summarize_ownership_specs(
            [],
            {
                "ownership_specs": [
                    {
                        "spec": "native_support_without_projection",
                        "risk_family": "test",
                        "business_object": "governance",
                        "fact_source_model": "ir.config_parameter",
                        "allowed_support_models": ["ir.attachment", "hr.employee"],
                        "projection_models": [],
                        "boundary_rule": "native authority remains native",
                        "forbidden_drift": "do not duplicate native models",
                        "decision": "reuse native models",
                    }
                ]
            },
        )
        self.assertEqual([], report["ownership_spec_shape_gaps"])
        self.assertEqual([], report["ownership_spec_reference_gaps"])

    def test_projection_mode_must_match_source_storage(self):
        report = AUDIT.summarize_projection_registry(
            [
                {
                    "model": "sc.example.summary",
                    "buckets": ["projection"],
                    "projection_storage_kind": "typed_empty_sql_view",
                    "projection_semantic_modes": ["sql_view"],
                }
            ],
            {
                "projections": [
                    {
                        "model": "sc.example.summary",
                        "implementation_mode": "physical_refresh_table",
                        "write_policy": "table rebuilt",
                        "source_models": ["sc.source"],
                        "refresh_owner": "model init",
                        "idempotency_key": "id",
                        "acceptance_probe": "test",
                    }
                ]
            },
        )
        self.assertTrue(report["projection_registry_implementation_gaps"])

    def test_typed_empty_projection_requires_truthful_policy_and_no_sources(self):
        report = AUDIT.summarize_projection_registry(
            [
                {
                    "model": "sc.empty.summary",
                    "buckets": ["projection"],
                    "projection_storage_kind": "typed_empty_sql_view",
                    "projection_semantic_modes": ["sql_view"],
                }
            ],
            {
                "projections": [
                    {
                        "model": "sc.empty.summary",
                        "implementation_mode": "sql_view",
                        "write_policy": "product-owned typed-empty read-only SQL view",
                        "source_models": [],
                        "refresh_owner": "model init",
                        "idempotency_key": "typed schema",
                        "acceptance_probe": "test",
                    }
                ]
            },
        )
        self.assertEqual([], report["projection_registry_shape_gaps"])
        self.assertEqual([], report["projection_registry_implementation_gaps"])

    def test_empty_active_projection_scripts_require_explicit_retirement(self):
        report = AUDIT.summarize_retired_projection_tooling(
            {"models": [{"model": "sc.example.fact", "projection_scripts": []}]}
        )
        self.assertEqual(
            [{"model": "sc.example.fact", "reason": "empty_projection_scripts_require_explicit_retirement"}],
            report["retired_projection_tooling_gaps"],
        )


if __name__ == "__main__":
    unittest.main()
