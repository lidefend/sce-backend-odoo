#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

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
    DESCRIPTOR_SCHEMA_PATH = Path("docs/architecture/p0_contract_producer_01/contract_v2_field_descriptor.schema.json")
    DESCRIPTOR_CASES_PATH = Path("docs/architecture/p0_contract_producer_01/descriptor_cases.json")
    SEMANTIC_REGISTRY_PATH = Path("contracts/registry/semantic.yaml")
    COMPONENT_REGISTRY_PATH = Path("contracts/registry/component.yaml")

    @classmethod
    def setUpClass(cls) -> None:
        cls.design = json.loads((ROOT / cls.DESIGN_PATH).read_text(encoding="utf-8"))
        cls.matrix = json.loads((ROOT / cls.MATRIX_PATH).read_text(encoding="utf-8"))
        cls.report = (ROOT / cls.REPORT_PATH).read_text(encoding="utf-8")
        cls.descriptor_schema = json.loads((ROOT / cls.DESCRIPTOR_SCHEMA_PATH).read_text(encoding="utf-8"))
        cls.descriptor_cases = json.loads((ROOT / cls.DESCRIPTOR_CASES_PATH).read_text(encoding="utf-8"))
        cls.semantic_registry = yaml.safe_load((ROOT / cls.SEMANTIC_REGISTRY_PATH).read_text(encoding="utf-8"))
        cls.component_registry = yaml.safe_load((ROOT / cls.COMPONENT_REGISTRY_PATH).read_text(encoding="utf-8"))
        cls.packages = {item["id"]: item for item in cls.design["work_packages"]}

    def descriptor_field_semantics(self) -> dict[str, dict]:
        semantics = self.semantic_registry["semantics"]
        components = self.component_registry["components"]
        field_semantics: dict[str, dict] = {}
        for semantic_type, declaration in semantics.items():
            component_key = declaration.get("component")
            component = components.get(component_key)
            if not isinstance(component, dict) or component.get("kind"):
                continue
            supported = component.get("field_types", [])
            if "*" in supported or any(field_type != "action" for field_type in supported):
                field_semantics[semantic_type] = {
                    "component": component_key,
                    "supported_field_types": supported,
                }
        return field_semantics

    def descriptor_widget_statuses(self) -> dict[str, str]:
        return {
            widget_type: str(declaration["status"])
            for widget_type, declaration in self.semantic_registry["native_widgets"].items()
        }

    def descriptor_registry_errors(self, descriptor: dict) -> list[str]:
        errors: list[str] = []
        semantic_type = descriptor.get("semanticType")
        component_key = descriptor.get("componentKey")
        field_type = descriptor.get("fieldType")
        semantics = self.semantic_registry["semantics"]
        components = self.component_registry["components"]
        field_semantics = self.descriptor_field_semantics()
        component = components.get(component_key)
        if semantic_type in semantics and semantic_type not in field_semantics:
            errors.append(f"semanticType {semantic_type!r} is an action-only semantic owned by P0-C")
        elif semantic_type not in field_semantics:
            errors.append(f"semanticType {semantic_type!r} is not declared")
        elif field_semantics[semantic_type]["component"] != component_key:
            errors.append(f"semanticType {semantic_type!r} does not resolve to {component_key!r}")
        if not isinstance(component, dict) or component.get("kind"):
            errors.append(f"componentKey {component_key!r} is not a registered field component")
        else:
            supported = component.get("field_types", [])
            if "*" not in supported and field_type not in supported:
                errors.append(f"componentKey {component_key!r} does not support fieldType {field_type!r}")
        widget_type = descriptor.get("widgetType")
        if widget_type not in self.descriptor_widget_statuses():
            errors.append(f"widgetType {widget_type!r} is not declared by semantic.yaml.native_widgets")
        digits = descriptor.get("digits")
        if isinstance(digits, list) and len(digits) == 2 and all(isinstance(item, int) for item in digits):
            if digits[0] < 1 or digits[1] < 0 or digits[1] > digits[0]:
                errors.append(f"digits {digits!r} do not satisfy total > 0, scale >= 0 and scale <= total")
        return errors

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
        missing = strategy["accepted_contract_versions_extension"]["missing_declaration_policy"]
        self.assertEqual(
            missing["known_client_without_versions"],
            "serve the complete legacy projection",
        )
        self.assertEqual(
            missing["unknown_or_missing_client_type"],
            "fail closed with CONTRACT_VERSION_UNSUPPORTED",
        )
        self.assertFalse(missing["new_carriers_allowed"])
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
        self.assertEqual(
            pending,
            {"DEC-05", "DEC-06", "NEG-01", "NEG-02", "NEG-03", "NEG-04", "VER-05", "VER-06"},
        )
        design_asserted = {
            row["id"] for row in self.matrix["cases"]
            if row["evidence"] == "executed_design_assertion"
        }
        self.assertEqual(
            design_asserted,
            {"SEC-01", "SEC-02", "FIELD-01", "FIELD-02", "FIELD-03", "FIELD-04", "FIELD-05"},
        )

    def test_p0_a_reuses_contract_v2_field_descriptor(self) -> None:
        contract = self.packages["P0-A"]["schema_contract"]
        self.assertNotIn("fields", contract)
        self.assertIn("fieldRefs", contract["required"])
        source = contract["descriptor_source"]
        self.assertEqual(source["type"], "ContractV2FieldDescriptor")
        self.assertEqual(source["widget_backed"]["referenceKind"], "widget")
        self.assertEqual(source["non_widget_backed"]["referenceKind"], "descriptor")
        self.assertEqual(
            source["non_widget_backed"]["registry"],
            "page_orchestration.block_field_descriptors[descriptorId]",
        )
        self.assertFalse(source["non_widget_backed"]["fake_widget_creation_allowed"])
        self.assertTrue(source["no_parallel_descriptor_map"])
        self.assertIn("kind", contract["fieldRefs"]["<slot-key>"])
        self.assertIn("descriptorId", contract["fieldRefs"]["<slot-key>"])
        self.assertIn("block_field_descriptors", contract)
        self.assertIn("does not define a parallel field descriptor", " ".join(self.packages["P0-A"]["rules"]))
        schema_contract = contract["descriptor_schema"]
        self.assertEqual(schema_contract["decoder_id"], "decodeContractV2FieldDescriptor")
        self.assertIn("same normalized ContractV2FieldDescriptor", schema_contract["decode_equivalence"])
        self.assertEqual(
            set(schema_contract["shared_by"]),
            {
                "decodeContractV2Widget.fieldDescriptor",
                "decodePageOrchestration.block_field_descriptors",
            },
        )
        self.assertEqual(schema_contract["unknown_keys"], "reject")
        self.assertIn("FIELD_DESCRIPTOR_UNKNOWN_KEY", schema_contract["error_codes"])
        self.assertEqual(
            set(schema_contract["validation_layers"]),
            {
                "structural_schema",
                "field_semantic_scope",
                "native_widget_vocabulary",
                "semantic_registry",
            },
        )
        self.assertEqual(
            schema_contract["semantic_registry_source"]["semantic_declaration"],
            "contracts/registry/semantic.yaml",
        )
        self.assertEqual(
            schema_contract["semantic_registry_source"]["component_declaration"],
            "contracts/registry/component.yaml",
        )
        self.assertIn("validated projection", schema_contract["semantic_registry_source"]["schema_enum_role"])
        self.assertEqual(
            set(schema_contract["field_semantic_scope"]["action_only_semantics"]),
            {"action", "support_action"},
        )
        self.assertTrue(schema_contract["field_semantic_scope"]["field_descriptor_cannot_define_actions"])
        self.assertEqual(
            schema_contract["widget_type_authority"]["property"],
            "native_widgets",
        )
        self.assertIn("every key", schema_contract["widget_type_authority"]["admissible_vocabulary"])
        self.assertEqual(schema_contract["widget_type_authority"]["unknown_widget_type"], "reject")
        self.assertIn("FIELD_DESCRIPTOR_WIDGET_UNKNOWN", schema_contract["error_codes"])
        self.assertIn(
            "const fieldDescriptor = optionalRecord(raw, 'fieldDescriptor'",
            (ROOT / "frontend/apps/web/src/app/contracts/v2/schema.ts").read_text(encoding="utf-8"),
        )

    def test_descriptor_schema_is_strict_and_cases_match(self) -> None:
        Draft202012Validator.check_schema(self.descriptor_schema)
        validator = Draft202012Validator(self.descriptor_schema)
        self.assertFalse(self.descriptor_schema["additionalProperties"])
        field_semantics = self.descriptor_field_semantics()
        action_only_semantics = set(self.semantic_registry["semantics"]) - set(field_semantics)
        self.assertEqual(action_only_semantics, {"action", "support_action"})
        schema_field_types = set(self.descriptor_schema["properties"]["fieldType"]["enum"])
        self.assertNotIn("action", schema_field_types)
        self.assertEqual(
            set(self.descriptor_schema["properties"]["semanticType"]["enum"]),
            set(field_semantics),
        )
        registry_field_types = {
            field_type
            for component in self.component_registry["components"].values()
            if isinstance(component, dict) and not component.get("kind")
            for field_type in component.get("field_types", [])
            if field_type not in {"action", "*"}
        }
        for semantic_type, declaration in field_semantics.items():
            supported = set(declaration["supported_field_types"])
            if "*" not in supported:
                self.assertTrue(supported & schema_field_types, semantic_type)
        self.assertTrue(
            registry_field_types.issubset(schema_field_types),
        )
        self.assertEqual(
            set(self.descriptor_schema["properties"]["widgetType"]["enum"]),
            set(self.descriptor_widget_statuses()),
        )
        self.assertEqual(
            set(self.descriptor_schema["required"]),
            {"schemaVersion", "fieldCode", "label", "fieldType", "widgetType", "componentKey", "semanticType"},
        )
        seen = set()
        expected: dict[str, str] = {}
        for case in self.descriptor_cases["cases"]:
            self.assertNotIn(case["id"], seen)
            seen.add(case["id"])
            errors = list(validator.iter_errors(case["descriptor"]))
            registry_errors = self.descriptor_registry_errors(case["descriptor"])
            failed_by = case.get("failed_by", ["structural_schema"] if errors else [])
            if "structural_schema" in failed_by:
                self.assertTrue(errors, case["id"])
            if "semantic_registry" in failed_by:
                self.assertTrue(registry_errors, case["id"])
                self.assertEqual(errors, [], case["id"])
            if case["expect"] == "valid":
                self.assertEqual(registry_errors, [], case["id"])
            actual = "invalid" if errors or registry_errors else "valid"
            self.assertEqual(actual, case["expect"], f"{case['id']}: {errors[:1]}")
            expected[case["id"]] = case["expect"]
        schema_matrix = {
            row["id"]: row["expectation"]
            for row in self.matrix["cases"]
            if row["evidence"] == "executed_schema_validation"
        }
        self.assertEqual(len(expected), 22)
        self.assertEqual(schema_matrix, expected)

    def test_p0_b_keeps_attachment_identities_separate(self) -> None:
        contract = self.packages["P0-B"]["schema_contract"]
        fact = contract["fact"]
        self.assertIn("storageOwner", fact)
        self.assertIn("businessOwner", fact)
        self.assertNotIn("owner", fact)
        self.assertNotIn("authorizationSubject", fact)
        subject = contract["server_only_identities"]["authorizationSubject"]
        self.assertFalse(subject["publicCarrier"])
        self.assertFalse(subject["clientInputAllowed"])
        self.assertEqual(subject["valueLocation"], "server execution authorization")
        action_contract = self.packages["P0-C"]["schema_contract"]
        self.assertNotIn("authorization.subject", action_contract["declaration"])
        self.assertFalse(action_contract["server_only_identities"]["authorizationSubject"]["publicCarrier"])
        self.assertFalse(action_contract["server_only_identities"]["authorizationSubject"]["clientInputAllowed"])
        public_payload = {"fact": fact, "declaration": action_contract["declaration"]}
        self.assertNotIn("authorizationSubject", str(public_payload))
        self.assertNotIn("authorization.subject", str(public_payload))

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
        self.assertIn("ContractV2FieldDescriptor", self.report)
        self.assertIn("block_field_descriptors", self.report)
        self.assertIn("fake UI Widget", self.report)
        self.assertIn("ContractV2ActionRule.target", self.report)


if __name__ == "__main__":
    unittest.main()
