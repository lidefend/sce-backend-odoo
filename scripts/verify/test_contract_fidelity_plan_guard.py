#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/verify/contract_fidelity_plan_guard.py"
SPEC = importlib.util.spec_from_file_location("contract_fidelity_plan_guard", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ContractFidelityPlanGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.matrix = json.loads((ROOT / MODULE.MATRIX_PATH).read_text(encoding="utf-8"))
        self.plan = json.loads((ROOT / MODULE.PLAN_PATH).read_text(encoding="utf-8"))
        self.guard = json.loads((ROOT / MODULE.GUARD_PATH).read_text(encoding="utf-8"))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self) -> None:
        for relative, content in (
            (MODULE.MATRIX_PATH, self.matrix),
            (MODULE.PLAN_PATH, self.plan),
            (MODULE.GUARD_PATH, self.guard),
        ):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")

    def errors(self) -> list[str]:
        self.write()
        return MODULE.check(self.root)

    def assert_error(self, fragment: str) -> None:
        errors = self.errors()
        self.assertTrue(any(fragment in error for error in errors), errors)

    def test_repository_plan_is_consistent(self) -> None:
        self.assertEqual(MODULE.check(ROOT), [])

    def test_synthetic_baseline_is_clean(self) -> None:
        self.assertEqual(self.errors(), [])

    def test_missing_not_verified_cell_is_detected(self) -> None:
        self.plan["not_verified_cells"].pop()
        self.assert_error("NOT_VERIFIED matrix mismatch")

    def test_my_work_attachment_responsibility_drift_is_detected(self) -> None:
        for cell in self.plan["not_verified_cells"]:
            if cell["id"] == "NV-11":
                cell["gap_probe"] = "CFG-GAP-03"
        self.assert_error("NV-11: gap_probe must be CFG-GAP-04")

    def test_dialog_duration_responsibility_drift_is_detected(self) -> None:
        for cell in self.plan["not_verified_cells"]:
            if cell["id"] == "NV-15":
                cell["gap_probe"] = "CFG-GAP-03"
        self.assert_error("NV-15: gap_probe must be CFG-GAP-07")

    def test_gap_blocks_must_match_cell_ownership(self) -> None:
        for probe in self.plan["contract_gap_probes"]:
            if probe["id"] == "CFG-GAP-03":
                probe["blocks"].append("NV-11")
        self.assert_error("CFG-GAP-03: NV blocks mismatch")

    def test_missing_gap_dependency_edge_is_detected(self) -> None:
        self.plan["dependency_edges"] = [
            edge for edge in self.plan["dependency_edges"]
            if edge["id"] != "DEP-GAP-04-TRANSPORT"
        ]
        self.assert_error("without a matching dependency edge")

    def test_contract_gap_branch_must_redirect_to_p0(self) -> None:
        edge = next(
            edge for edge in self.plan["dependency_edges"]
            if edge.get("kind") == "contract_gate"
        )
        edge["branches"]["contract_gap"] = "unlock"
        self.assert_error("contract_gate branches must be exact")

    def test_first_batch_must_remain_independent(self) -> None:
        self.plan["batches"][0]["depends_on"] = ["CFG-GAP-01"]
        self.assert_error("FCF-02-1 must remain independently startable")

    def test_numeric_clamp_guard_is_required(self) -> None:
        for rule in self.guard["rules"]:
            if rule["id"] == "CFG-003":
                rule["negative_cases"] = ["value looks out of range"]
        self.assert_error("CFG-003 must explicitly cover")

    def test_page_block_feedback_guard_is_required(self) -> None:
        self.guard["rules"] = [rule for rule in self.guard["rules"] if rule["id"] != "CFG-011"]
        self.assert_error("guard rules must be exactly CFG-001..011")

    def test_semantic_carrier_requirement_is_required(self) -> None:
        self.guard["semantic_carrier_requirements"].pop()
        self.assert_error("semantic carrier requirements must be exactly CARRIER-01..06")


class P0ContractProducerDesignTest(unittest.TestCase):
    DESIGN_PATH = Path("docs/architecture/p0_contract_producer_01/remediation_design.json")
    MATRIX_PATH = Path("docs/architecture/p0_contract_producer_01/compatibility_matrix.json")
    REPORT_PATH = Path("docs/architecture/p0_contract_producer_01_contract_remediation_design_20261123.md")

    @classmethod
    def setUpClass(cls) -> None:
        cls.design = json.loads((ROOT / cls.DESIGN_PATH).read_text(encoding="utf-8"))
        cls.matrix = json.loads((ROOT / cls.MATRIX_PATH).read_text(encoding="utf-8"))
        cls.report = (ROOT / cls.REPORT_PATH).read_text(encoding="utf-8")
        cls.packages = {item["id"]: item for item in cls.design["work_packages"]}

    def test_product_implementation_remains_unauthorized(self) -> None:
        self.assertFalse(self.design["product_implementation_authorized"])
        self.assertEqual(self.design["status"], "design_candidate")

    def test_source_hashes_match_current_baseline(self) -> None:
        for relative, expected in self.design["source_evidence"].items():
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, relative)

    def test_accepted_versions_and_capabilities_are_real_negotiation_inputs(self) -> None:
        strategy = self.design["version_strategy"]
        self.assertIn("2.6.x", strategy["accepted_contract_versions_extension"]["target_values"])
        self.assertEqual(
            set(strategy["client_contract_capabilities_extension"]["required_new_capabilities"]),
            {"page_block_data.v1", "attachment_fact.v1", "page_block_action.v1"},
        )
        self.assertEqual(
            strategy["accepted_contract_versions_extension"]["server_request_field"],
            "accepted_contract_versions",
        )
        self.assertIn("does not preserve", strategy["current_state"]["backend_request_normalizer"])
        self.assertIn("not frontend decoder evidence", strategy["current_state"]["contract_compatibility_core"])
        client_source = (ROOT / "frontend/apps/web/src/app/contracts/v2/client.ts").read_text(encoding="utf-8")
        schema_source = (ROOT / "frontend/apps/web/src/app/contracts/v2/schema.ts").read_text(encoding="utf-8")
        payload_source = (ROOT / "addons/smart_core/app_config_engine/utils/payload.py").read_text(encoding="utf-8")
        workbench_source = (ROOT / "frontend/apps/web/src/views/WorkbenchView.vue").read_text(encoding="utf-8")
        self.assertNotIn("2.6.x", client_source)
        self.assertIn(r"/^2\.(0|1|2|3|4|5)\.\d+$/", schema_source)
        self.assertNotIn("accepted_contract_versions", payload_source)
        self.assertIn("asText(contract.contract_version) === '2.0.0'", workbench_source)

    def test_decoder_evidence_distinguishes_executed_and_pending(self) -> None:
        cases = {row["case"]: row for row in self.design["version_strategy"]["real_decoder_acceptance"]}
        self.assertEqual(cases["old_decoder_old_projection"]["evidence_status"], "executed")
        self.assertEqual(cases["old_decoder_new_outer_version"]["expected"], "REJECT")
        self.assertEqual(cases["old_decoder_undeclared_carrier"]["expected"], "REJECT")
        self.assertEqual(
            cases["new_decoder_new_projection"]["evidence_status"],
            "required_not_run_pending_implementation",
        )
        executed = {row["id"] for row in self.matrix["cases"] if row["evidence"] == "executed"}
        self.assertEqual(executed, {"DEC-01", "DEC-02", "DEC-03", "DEC-04", "NEG-05"})
        pending = {row["id"] for row in self.matrix["cases"] if row["evidence"] == "not_run_pending_implementation"}
        self.assertEqual(pending, {"DEC-05", "DEC-06", "NEG-01", "NEG-02", "NEG-03", "NEG-04"})

    def test_p0_a_reuses_contract_v2_field_descriptor(self) -> None:
        contract = self.packages["P0-A"]["schema_contract"]
        self.assertNotIn("fields", contract)
        self.assertIn("fieldRefs", contract["required"])
        source = contract["descriptor_source"]
        self.assertEqual(source["field_descriptor"], "ContractV2Widget.fieldDescriptor")
        self.assertEqual(source["component_config"], "ContractV2Widget.componentConfig")
        self.assertTrue(source["no_parallel_descriptor_map"])
        self.assertIn("does not define a parallel field descriptor", " ".join(self.packages["P0-A"]["rules"]))

    def test_p0_b_keeps_attachment_identities_separate(self) -> None:
        fact = self.packages["P0-B"]["schema_contract"]["fact"]
        self.assertIn("storageOwner", fact)
        self.assertIn("businessOwner", fact)
        self.assertIn("authorizationSubject", fact)
        self.assertNotIn("owner", fact)
        subject = fact["authorizationSubject"]
        self.assertFalse(subject["clientInputAllowed"])
        self.assertEqual(subject["source"], "server-only action resolution")
        self.assertIn("resolve_file_download_auth_subject", subject["resolvedBy"])

    def test_p0_c_reuses_action_rule_and_target_schema(self) -> None:
        contract = self.packages["P0-C"]["schema_contract"]
        source = contract["action_rule_source"]
        self.assertEqual(source["type"], "ContractV2ActionRule")
        self.assertEqual(source["identity"], "actionId")
        self.assertEqual(source["target_source"], "ContractV2ActionRule.target")
        self.assertTrue(source["no_parallel_action_target_schema"])
        declaration = contract["declaration"]
        self.assertEqual(
            declaration["target"]["existing_static_kinds"],
            ["scene.key", "route.path", "page.refresh", "menu.first_reachable"],
        )
        self.assertFalse(declaration["target"]["frontend_translation_allowed"])
        self.assertIn("compatibility aggregate", declaration["permission.allowed"])
        self.assertIn("actor authorization result only", declaration["permission.authorizationAllowed"])
        self.assertIn("business/workflow state availability only", declaration["permission.businessAvailable"])
        self.assertIn("enabled=true requires allowed=true", declaration["state.enabled"])

    def test_report_uses_decoder_and_identity_boundaries(self) -> None:
        self.assertIn("Real Decoder acceptance is mandatory", self.report)
        self.assertIn("storageOwner", self.report)
        self.assertIn("businessOwner", self.report)
        self.assertIn("authorizationSubject", self.report)
        self.assertIn("ContractV2Widget.fieldDescriptor", self.report)
        self.assertIn("ContractV2ActionRule.target", self.report)


if __name__ == "__main__":
    unittest.main()
