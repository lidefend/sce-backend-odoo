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

NEGOTIATION_MODULE_PATH = ROOT / "addons/smart_core/core/contract_version_negotiation.py"
NEGOTIATION_SPEC = importlib.util.spec_from_file_location("contract_version_negotiation", NEGOTIATION_MODULE_PATH)
assert NEGOTIATION_SPEC and NEGOTIATION_SPEC.loader
NEGOTIATION_MODULE = importlib.util.module_from_spec(NEGOTIATION_SPEC)
NEGOTIATION_SPEC.loader.exec_module(NEGOTIATION_MODULE)

PAGE_BLOCK_DATA_MODULE_PATH = ROOT / "addons/smart_core/core/page_block_data_contract.py"
PAGE_BLOCK_DATA_SPEC = importlib.util.spec_from_file_location("page_block_data_contract", PAGE_BLOCK_DATA_MODULE_PATH)
assert PAGE_BLOCK_DATA_SPEC and PAGE_BLOCK_DATA_SPEC.loader
PAGE_BLOCK_DATA_MODULE = importlib.util.module_from_spec(PAGE_BLOCK_DATA_SPEC)
PAGE_BLOCK_DATA_SPEC.loader.exec_module(PAGE_BLOCK_DATA_MODULE)


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


class ContractVersionNegotiationTest(unittest.TestCase):
    def negotiate(self, **overrides):
        values = {
            "client_type": "web_pc",
            "accepted_contract_versions": ["2.0.x", "2.1.x", "2.2.x", "2.3.x", "2.4.x", "2.5.x"],
            "client_contract_capabilities": [],
        }
        values.update(overrides)
        return NEGOTIATION_MODULE.negotiate_client_contract(**values)

    def test_known_old_client_without_versions_gets_complete_legacy_projection(self):
        result = self.negotiate(accepted_contract_versions=[])
        self.assertEqual(result["contractVersion"], "2.5.0")
        self.assertEqual(result["pageOrchestrationVersion"], "2.0.0")
        self.assertEqual(result["compatibilityMode"], "known_client_without_versions")
        self.assertFalse(result["carriers"]["page_block_data.v1"]["enabled"])

    def test_client_that_only_accepts_25_gets_complete_legacy_projection(self):
        result = self.negotiate(accepted_contract_versions=["2.5"])
        self.assertEqual(result["contractVersion"], "2.5.0")
        self.assertEqual(result["pageOrchestrationVersion"], "2.0.0")

    def test_client_that_only_accepts_24_fails_closed(self):
        with self.assertRaises(NEGOTIATION_MODULE.ContractNegotiationError) as raised:
            self.negotiate(accepted_contract_versions=["2.4.x"])
        self.assertEqual(raised.exception.reason_code, "CONTRACT_VERSION_UNSUPPORTED")

    def test_client_that_only_accepts_20_fails_closed(self):
        with self.assertRaises(NEGOTIATION_MODULE.ContractNegotiationError) as raised:
            self.negotiate(accepted_contract_versions=["2.0.x"])
        self.assertEqual(raised.exception.reason_code, "CONTRACT_VERSION_UNSUPPORTED")

    def test_mixed_versions_without_25_have_no_common_legacy_version(self):
        with self.assertRaises(NEGOTIATION_MODULE.ContractNegotiationError) as raised:
            self.negotiate(accepted_contract_versions=["2.4.x", "2.6.x"])
        self.assertEqual(raised.exception.reason_code, "CONTRACT_VERSION_UNSUPPORTED")

    def test_26_without_page_block_capability_gets_complete_legacy_projection(self):
        result = self.negotiate(accepted_contract_versions=["2.5.x", "2.6.x"])
        self.assertEqual(result["contractVersion"], "2.5.0")
        self.assertEqual(result["pageOrchestrationVersion"], "2.0.0")
        self.assertEqual(result["compatibilityMode"], "new_version_without_page_block_capability")

    def test_26_only_without_page_block_capability_fails_closed(self):
        with self.assertRaises(NEGOTIATION_MODULE.ContractNegotiationError) as raised:
            self.negotiate(accepted_contract_versions=["2.6.x"])
        self.assertEqual(raised.exception.reason_code, "CONTRACT_VERSION_UNSUPPORTED")

    def test_26_enables_each_declared_current_carrier_independently(self):
        result = self.negotiate(
            accepted_contract_versions=["2.5.x", "2.6.x"],
            client_contract_capabilities=[
                "page_block_data.v1",
                "attachment_fact.v1",
                "page_block_action.v1",
            ],
        )
        self.assertEqual(result["contractVersion"], "2.6.0")
        self.assertEqual(result["pageOrchestrationVersion"], "2.1.0")
        self.assertTrue(result["carriers"]["page_block_data.v1"]["enabled"])
        self.assertFalse(result["carriers"]["attachment_fact.v1"]["enabled"])
        self.assertTrue(result["carriers"]["page_block_action.v1"]["enabled"])
        self.assertEqual(
            result["compatibilityMode"],
            "page_block_data_and_action_v1",
        )

    def test_26_with_only_page_block_action_enables_action_carrier(self):
        result = self.negotiate(
            accepted_contract_versions=["2.5.x", "2.6.x"],
            client_contract_capabilities=["page_block_action.v1"],
        )
        self.assertEqual(result["contractVersion"], "2.6.0")
        self.assertEqual(result["pageOrchestrationVersion"], "2.1.0")
        self.assertFalse(result["carriers"]["page_block_data.v1"]["enabled"])
        self.assertFalse(result["carriers"]["attachment_fact.v1"]["enabled"])
        self.assertTrue(result["carriers"]["page_block_action.v1"]["enabled"])
        self.assertEqual(result["compatibilityMode"], "page_block_action_v1")

    def test_unknown_client_with_version_or_capability_declaration_fails_closed(self):
        with self.assertRaises(NEGOTIATION_MODULE.ContractNegotiationError) as raised:
            self.negotiate(
                client_type="unknown_native",
                accepted_contract_versions=["2.5"],
            )
        self.assertEqual(raised.exception.reason_code, "CONTRACT_VERSION_UNSUPPORTED")

    def test_missing_client_type_with_negotiation_declaration_fails_closed(self):
        with self.assertRaises(NEGOTIATION_MODULE.ContractNegotiationError):
            self.negotiate(client_type="", accepted_contract_versions=["2.6.x"])

    def test_no_common_version_fails_closed(self):
        with self.assertRaises(NEGOTIATION_MODULE.ContractNegotiationError) as raised:
            self.negotiate(accepted_contract_versions=["1.0.x", "2.99.x"])
        self.assertEqual(raised.exception.reason_code, "CONTRACT_VERSION_UNSUPPORTED")

    def test_pre_negotiation_absence_gets_legacy_projection(self):
        result = NEGOTIATION_MODULE.negotiate_client_contract(
            client_type="",
            accepted_contract_versions=None,
            client_contract_capabilities=None,
        )
        self.assertEqual(result["contractVersion"], "2.5.0")
        self.assertEqual(result["clientType"], "")
        self.assertEqual(
            result["compatibilityMode"],
            "pre_negotiation_client_without_identity",
        )

    def test_new_version_never_leaks_unrequested_carriers(self):
        result = self.negotiate(
            accepted_contract_versions=["2.6.x"],
            client_contract_capabilities=["page_block_data.v1"],
        )
        self.assertEqual(
            {key for key, row in result["carriers"].items() if row["enabled"]},
            {"page_block_data.v1"},
        )


class PageBlockDataContractTest(unittest.TestCase):
    def test_non_widget_business_value_preserves_raw_type_and_semantics(self):
        descriptor = PAGE_BLOCK_DATA_MODULE.field_descriptor(
            field_code="payment.pending_amount",
            label="待付款金额",
            field_type="monetary",
            widget_type="monetary",
            component_key="sc.value.money",
            semantic_type="money",
            digits=[16, 2],
            currencyField="currency_id",
        )
        data = PAGE_BLOCK_DATA_MODULE.build_data_contract(
            rows=[
                {"rowKey": "pending", "values": {"value": "0.00", "currency_id": 7}},
                {"rowKey": "missing", "values": {}},
            ],
            field_refs={
                "value": PAGE_BLOCK_DATA_MODULE.descriptor_ref(
                    descriptor_id="payment.pending_amount.value",
                    raw_value_path="value",
                ),
                "currency_id": PAGE_BLOCK_DATA_MODULE.descriptor_ref(
                    descriptor_id="payment.pending_amount.currency",
                    raw_value_path="currency_id",
                ),
            },
            currencies={"7": {"id": 7, "code": "CNY", "symbol": "¥"}},
            timezone="Asia/Shanghai",
        )
        carrier = PAGE_BLOCK_DATA_MODULE.build_page_orchestration_page_block_data(
            descriptors={"payment.pending_amount.value": descriptor},
            data_contracts={"ds_pending_amount": data},
            enabled=True,
        )
        self.assertEqual(carrier["contract_version"], "2.1.0")
        self.assertEqual(carrier["schema_version"], "2.1.0")
        self.assertEqual(carrier["block_data_contracts"]["ds_pending_amount"]["rows"][0]["values"]["value"], "0.00")
        self.assertEqual(
            carrier["block_data_contracts"]["ds_pending_amount"]["rows"][0]["values"]["currency_id"],
            7,
        )
        self.assertNotIn("value", carrier["block_data_contracts"]["ds_pending_amount"]["rows"][1]["values"])
        self.assertEqual(carrier["block_field_descriptors"]["payment.pending_amount.value"], descriptor)
        self.assertEqual(carrier["block_data_contracts"]["ds_pending_amount"]["context"]["timezone"], "Asia/Shanghai")
        self.assertEqual(
            carrier["block_data_contracts"]["ds_pending_amount"]["context"]["currencies"]["7"]["code"],
            "CNY",
        )

    def test_currency_context_rejects_unknown_fields_and_identity_mismatch(self):
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            PAGE_BLOCK_DATA_MODULE.normalize_currency_context({
                "7": {"id": 7, "code": "CNY", "unexpected": True},
            })
        with self.assertRaisesRegex(ValueError, "does not match its key"):
            PAGE_BLOCK_DATA_MODULE.normalize_currency_context({
                "7": {"id": 8, "code": "CNY"},
            })

    def test_legacy_projection_has_no_new_carriers(self):
        carrier = PAGE_BLOCK_DATA_MODULE.build_page_orchestration_page_block_data(
            descriptors={},
            data_contracts={},
            enabled=False,
        )
        self.assertEqual(carrier, {"contract_version": "2.0.0", "schema_version": "2.0.0"})

    def test_distinct_falsy_values_remain_distinct(self):
        data = PAGE_BLOCK_DATA_MODULE.build_data_contract(
            rows=[{
                "rowKey": "combined",
                "values": {
                    "zero": 0,
                    "false_value": False,
                    "null_value": None,
                    "empty": "",
                },
            }],
            field_refs={
                "zero": PAGE_BLOCK_DATA_MODULE.descriptor_ref(descriptor_id="d.zero", raw_value_path="zero"),
                "false": PAGE_BLOCK_DATA_MODULE.descriptor_ref(descriptor_id="d.false", raw_value_path="false_value"),
                "null": PAGE_BLOCK_DATA_MODULE.descriptor_ref(descriptor_id="d.null", raw_value_path="null_value"),
                "empty": PAGE_BLOCK_DATA_MODULE.descriptor_ref(descriptor_id="d.empty", raw_value_path="empty"),
            },
            timezone="UTC",
        )
        values = data["rows"][0]["values"]
        self.assertIs(values["zero"], 0)
        self.assertIs(values["false_value"], False)
        self.assertIsNone(values["null_value"])
        self.assertEqual(values["empty"], "")

    def test_missing_raw_value_is_not_invented_at_producer(self):
        data = PAGE_BLOCK_DATA_MODULE.build_data_contract(
            rows=[{"rowKey": "r1", "values": {}}],
            field_refs={"value": PAGE_BLOCK_DATA_MODULE.descriptor_ref(
                descriptor_id="d.value",
                raw_value_path="value",
            )},
            timezone="UTC",
        )
        self.assertNotIn("value", data["rows"][0]["values"])


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
        widget_declaration = self.semantic_registry["native_widgets"].get(widget_type)
        if not isinstance(widget_declaration, dict):
            errors.append(f"widgetType {widget_type!r} is not declared by semantic.yaml.native_widgets")
        else:
            widget_status = widget_declaration.get("status")
            reason_code = str(widget_declaration.get("reason_code") or "").strip()
            if widget_status == "unsupported":
                errors.append(f"widgetType {widget_type!r} is declared unsupported")
            elif widget_status == "fallback" and not reason_code:
                errors.append(f"widgetType {widget_type!r} requires a declared fallback reason_code")
            elif widget_status not in {"ready", "fallback"}:
                errors.append(f"widgetType {widget_type!r} has unknown status {widget_status!r}")
        digits = descriptor.get("digits")
        if isinstance(digits, list) and len(digits) == 2 and all(isinstance(item, int) for item in digits):
            if digits[0] < 1 or digits[1] < 0 or digits[1] > digits[0]:
                errors.append(f"digits {digits!r} do not satisfy total > 0, scale >= 0 and scale <= total")
        return errors

    def descriptor_registry_resolution(self, descriptor: dict) -> dict:
        errors = self.descriptor_registry_errors(descriptor)
        if errors:
            raise ValueError("; ".join(errors))
        widget_type = descriptor["widgetType"]
        declaration = self.semantic_registry["native_widgets"][widget_type]
        widget_status = declaration["status"]
        return {
            "widget": {
                "widgetType": widget_type,
                "widgetStatus": widget_status,
                "fallbackReasonCode": declaration.get("reason_code") if widget_status == "fallback" else None,
            },
        }

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
        self.assertIn("2.6.x", client_source)
        self.assertIn(r"/^2\.(0|1|2|3|4|5|6)\.\d+$/", schema_source)
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
        self.assertEqual(executed, {"DEC-01", "DEC-02", "DEC-03", "DEC-04", "NEG-05", "VER-07"})
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
            {
                "SEC-01",
                "SEC-02",
                "FIELD-01",
                "FIELD-02",
                "FIELD-03",
                "FIELD-04",
                "FIELD-05",
                "RES-WIDGET-READY",
                "RES-WIDGET-FALLBACK",
                "RES-WIDGET-FALLBACK-MISSING",
                "RES-WIDGET-FALLBACK-EMPTY",
                "RES-WIDGET-STATUS-INVALID",
            },
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
        self.assertIn("every key", schema_contract["widget_type_authority"]["known_vocabulary"])
        self.assertEqual(
            schema_contract["widget_type_authority"]["status_policy"]["unsupported"],
            "reject as a normal Field Descriptor",
        )
        self.assertEqual(schema_contract["widget_type_authority"]["unknown_widget_type"], "reject")
        self.assertIn("FIELD_DESCRIPTOR_WIDGET_UNKNOWN", schema_contract["error_codes"])
        self.assertIn("FIELD_DESCRIPTOR_WIDGET_UNSUPPORTED", schema_contract["error_codes"])
        self.assertIn("FIELD_DESCRIPTOR_WIDGET_FALLBACK_REASON_MISSING", schema_contract["error_codes"])
        decode_result = schema_contract["decode_result_contract"]
        self.assertEqual(decode_result["type"], "ContractV2FieldDescriptorDecodeResult")
        self.assertEqual(
            decode_result["registryResolution"]["widget"]["sourceAuthority"],
            "contracts/registry/semantic.yaml#native_widgets",
        )
        self.assertEqual(
            set(decode_result["descriptor_forbidden_runtime_fields"]),
            {"widgetStatus", "fallbackReasonCode"},
        )
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
        fallback_widgets = {
            widget_type: declaration
            for widget_type, declaration in self.semantic_registry["native_widgets"].items()
            if declaration["status"] == "fallback"
        }
        self.assertTrue(fallback_widgets)
        for widget_type, declaration in fallback_widgets.items():
            self.assertTrue(declaration.get("reason_code"), widget_type)
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
        self.assertEqual(len(expected), 24)
        self.assertEqual(schema_matrix, expected)

    def test_decode_result_keeps_registry_widget_metadata_outside_descriptor(self) -> None:
        cases = {case["id"]: case["descriptor"] for case in self.descriptor_cases["cases"]}
        ready_descriptor = cases["DESC-MONEY-VALID"]
        fallback_descriptor = cases["DESC-FALLBACK-WIDGET-VALID"]
        self.assertNotIn("widgetStatus", self.descriptor_schema["properties"])
        self.assertNotIn("fallbackReasonCode", self.descriptor_schema["properties"])
        self.assertNotIn("widgetStatus", ready_descriptor)
        self.assertNotIn("fallbackReasonCode", ready_descriptor)
        self.assertNotIn("widgetStatus", fallback_descriptor)
        self.assertNotIn("fallbackReasonCode", fallback_descriptor)
        self.assertEqual(
            self.descriptor_registry_resolution(ready_descriptor)["widget"],
            {
                "widgetType": "number",
                "widgetStatus": "ready",
                "fallbackReasonCode": None,
            },
        )
        fallback = self.semantic_registry["native_widgets"]["boolean_toggle"]
        self.assertEqual(
            self.descriptor_registry_resolution(fallback_descriptor)["widget"],
            {
                "widgetType": "boolean_toggle",
                "widgetStatus": "fallback",
                "fallbackReasonCode": fallback["reason_code"],
            },
        )

    def test_widget_registry_status_resolution_fails_closed(self) -> None:
        descriptor = {
            "schemaVersion": "1.0.0",
            "fieldCode": "project.is_favorite",
            "label": "收藏",
            "fieldType": "boolean",
            "widgetType": "boolean_toggle",
            "componentKey": "sc.input.boolean",
            "semanticType": "boolean",
        }
        original_registry = self.semantic_registry
        try:
            for mutation, expected in (
                ("missing_reason", "fallback reason_code"),
                ("empty_reason", "fallback reason_code"),
                ("invalid_status", "unknown status"),
            ):
                self.semantic_registry = copy.deepcopy(original_registry)
                widget = self.semantic_registry["native_widgets"]["boolean_toggle"]
                if mutation == "missing_reason":
                    widget.pop("reason_code", None)
                elif mutation == "empty_reason":
                    widget["reason_code"] = ""
                else:
                    widget["status"] = "degraded"
                errors = self.descriptor_registry_errors(descriptor)
                self.assertTrue(
                    any(expected in error for error in errors),
                    f"{mutation}: {errors}",
                )
        finally:
            self.semantic_registry = original_registry

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
