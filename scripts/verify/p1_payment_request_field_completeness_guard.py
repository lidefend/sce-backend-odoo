#!/usr/bin/env python3
"""Validate the P1 payment-request field completeness contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "config/p1_payment_request_field_completeness_v1.json"
MODEL_SOURCES = {
    "payment.request": ROOT / "addons/smart_construction_core/models/core/payment_request.py",
    "sc.payment.execution": ROOT / "addons/smart_construction_core/models/core/payment_execution.py",
}
NATIVE_SOURCES = {
    "payment.request": ROOT / "addons/smart_construction_core/views/core/payment_request_views.xml",
    "sc.payment.execution": ROOT / "addons/smart_construction_core/views/core/payment_execution_views.xml",
}
PRODUCT_CONTRACT = ROOT / "addons/smart_construction_core/data/payment_request_form_productization_contract.xml"
FORMAL_LIST = ROOT / "addons/smart_construction_core/views/support/user_confirmed_formal_list_views.xml"
P1_CORE_EXTENSION = ROOT / "addons/smart_construction_core/core_extension.py"
BROWSER_ACCEPTANCE = ROOT / "scripts/verify/pfl035_payment_request_runtime_acceptance.mjs"
AVAILABLE_ACTIONS = ROOT / "addons/smart_construction_core/handlers/payment_request_available_actions.py"
P1_BACKEND_TEST = ROOT / "addons/smart_construction_core/tests/test_p1_payment_request_capability.py"
WORK_ITEM_TEST = ROOT / "addons/smart_construction_core/tests/test_payment_request_work_item_service.py"
ALLOWED_CLASSIFICATIONS = {"required", "conditional", "derived", "optional", "audit"}
ALLOWED_BENCHMARK_STATUSES = {"implemented", "partial", "gap"}
ALLOWED_JOURNEY_COVERAGE = {"implemented", "partial", "missing"}
ALLOWED_FIELD_ZONES = {"primary", "subordinate"}
FORM_SURFACE_PROFILE_MAPPING = {
    "create_edit": {"create", "edit"},
    "create": {"create"},
    "edit": {"edit"},
    "readonly": {"readonly"},
}
ALLOWED_SURFACES = set(FORM_SURFACE_PROFILE_MAPPING) | {
    "list", "mobile", "execution_create", "execution_readonly",
}
FORM_DECLARATION_SURFACES = set(FORM_SURFACE_PROFILE_MAPPING) | {
    "execution_create", "execution_readonly",
}
REQUIRED_RULE_KEYS = {
    "model", "field", "label", "classification", "source", "applicability",
    "required_gate", "editability", "surfaces", "acceptance",
}


def _model_fields(source: str) -> set[str]:
    return set(re.findall(r"^\s{4}([A-Za-z_][A-Za-z0-9_]*)\s*=\s*fields\.", source, flags=re.MULTILINE))


def form_profiles_for_surfaces(surfaces: list[str]) -> set[str]:
    return {
        profile
        for surface in surfaces
        for profile in FORM_SURFACE_PROFILE_MAPPING.get(surface, set())
    }


def validate() -> list[str]:
    errors: list[str] = []
    payload = json.loads(MATRIX.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "p1_payment_request_field_completeness.v1":
        errors.append("unexpected schema version")
    if payload.get("product_layer") != "P1_construction_industry_standard_product":
        errors.append("field completeness left the P1 standard-product boundary")
    configured_mapping = payload.get("form_surface_profile_mapping") or {}
    expected_mapping = {
        surface: sorted(profiles)
        for surface, profiles in FORM_SURFACE_PROFILE_MAPPING.items()
    }
    if configured_mapping != expected_mapping:
        errors.append("form surface/profile mapping drifted")
    if (payload.get("scope") or {}).get("customer_specific_rules") != "forbidden":
        errors.append("customer-specific field rules must remain forbidden")
    if (payload.get("scope") or {}).get("field_rules_semantics") != (
        "minimum_product_completeness_obligations_not_a_surface_allowlist"
    ):
        errors.append("field completeness rules must not override the P1 product surface authority")

    aggregation = payload.get("list_aggregation_requirements") or {}
    expected_aggregation = {
        "model": "payment.request",
        "display_field": "request_amount_display",
        "value_field": "amount",
        "currency_field": "currency_id",
        "aggregate": "sum",
        "scopes": ["current_page", "filtered_total"],
        "currency_policy": "single_currency_or_fail_closed",
    }
    for key, expected in expected_aggregation.items():
        if aggregation.get(key) != expected:
            errors.append(f"payment list aggregation contract mismatch: {key}")
    formal_list = FORMAL_LIST.read_text(encoding="utf-8")
    if 'name="request_amount_display" string="申请付款金额" sum="申请付款金额合计"' not in formal_list:
        errors.append("payment formal list is missing the native amount sum declaration")
    extension = P1_CORE_EXTENSION.read_text(encoding="utf-8")
    for token in (
        '"display_field": "request_amount_display"',
        '"value_field": "amount"',
        '"aggregation_field": "amount"',
        '"currency_field": "currency_id"',
        '"aggregate": "sum"',
    ):
        if token not in extension:
            errors.append(f"payment normalized aggregation projection missing: {token}")

    benchmarks = payload.get("industry_benchmarks") or {}
    sources = benchmarks.get("sources") or []
    dimensions = benchmarks.get("dimensions") or []
    if len(sources) < 4:
        errors.append("industry benchmark sources are incomplete")
    if len(dimensions) < 10:
        errors.append("industry benchmark dimensions are incomplete")
    benchmark_keys: set[str] = set()
    for index, dimension in enumerate(dimensions):
        required = {"key", "benchmark", "ownership", "status", "source_fields", "decision", "acceptance"}
        missing = sorted(required - set(dimension))
        if missing:
            errors.append(f"industry_benchmarks.dimensions[{index}] missing keys: {missing}")
            continue
        key = str(dimension["key"])
        if key in benchmark_keys:
            errors.append(f"duplicate industry benchmark dimension: {key}")
        benchmark_keys.add(key)
        if dimension["status"] not in ALLOWED_BENCHMARK_STATUSES:
            errors.append(f"invalid industry benchmark status: {key}")
        if dimension["status"] != "gap" and not dimension["source_fields"]:
            errors.append(f"covered industry benchmark has no authoritative source: {key}")
        serialized = json.dumps(dimension, ensure_ascii=False).lower()
        if "customer" in serialized or "客户特例" in serialized:
            errors.append(f"customer-specific benchmark rule is forbidden: {key}")

    rules = payload.get("field_rules") or []
    identities: set[tuple[str, str]] = set()
    model_fields = {model: _model_fields(path.read_text(encoding="utf-8")) for model, path in MODEL_SOURCES.items()}
    native = {model: path.read_text(encoding="utf-8") for model, path in NATIVE_SOURCES.items()}
    product_contract = PRODUCT_CONTRACT.read_text(encoding="utf-8")
    for index, rule in enumerate(rules):
        missing = sorted(REQUIRED_RULE_KEYS - set(rule))
        if missing:
            errors.append(f"field_rules[{index}] missing keys: {missing}")
            continue
        identity = (str(rule["model"]), str(rule["field"]))
        if identity in identities:
            errors.append(f"duplicate field rule: {identity[0]}.{identity[1]}")
        identities.add(identity)
        if identity[0] not in MODEL_SOURCES:
            errors.append(f"unknown model in field rule: {identity[0]}")
            continue
        if identity[1] not in model_fields[identity[0]]:
            errors.append(f"model field missing: {identity[0]}.{identity[1]}")
        if rule["classification"] not in ALLOWED_CLASSIFICATIONS:
            errors.append(f"invalid classification for {identity[0]}.{identity[1]}")
        if rule.get("zone", "primary") not in ALLOWED_FIELD_ZONES:
            errors.append(f"invalid field zone for {identity[0]}.{identity[1]}")
        if not isinstance(rule["surfaces"], list) or not rule["surfaces"]:
            errors.append(f"surfaces missing for {identity[0]}.{identity[1]}")
        unknown_surfaces = sorted(set(rule["surfaces"]) - ALLOWED_SURFACES)
        if unknown_surfaces:
            errors.append(
                f"unknown surfaces for {identity[0]}.{identity[1]}: {unknown_surfaces}"
            )
        if any(surface in FORM_DECLARATION_SURFACES for surface in rule["surfaces"]):
            if f"name=\"{identity[1]}\"" not in native[identity[0]]:
                errors.append(f"native form missing field: {identity[0]}.{identity[1]}")
            if f"'{identity[1]}'" not in product_contract:
                errors.append(f"product contract missing field: {identity[0]}.{identity[1]}")

    minimums = {"payment.request": 25, "sc.payment.execution": 15}
    for model, minimum in minimums.items():
        count = sum(1 for item in identities if item[0] == model)
        if count < minimum:
            errors.append(f"{model} field completeness coverage too small: {count} < {minimum}")

    surfaces = payload.get("surface_requirements") or {}
    for surface_key, surface in surfaces.items():
        source_path = ROOT / str(surface.get("source") or "")
        if not source_path.is_file():
            errors.append(f"{surface_key} source is missing: {source_path}")
            continue
        source = source_path.read_text(encoding="utf-8")
        for field in surface.get("fields") or []:
            if f"name=\"{field}\"" not in source:
                errors.append(f"{surface_key} missing field: {field}")
        for label in surface.get("labels") or []:
            if f"string=\"{label}\"" not in source:
                errors.append(f"{surface_key} missing label: {label}")

    browser = BROWSER_ACCEPTANCE.read_text(encoding="utf-8")
    for token in (
        "normalized_product_fact_evidence", "payee_account_completeness",
        "payee_account_source_display", "payment_execution_status_display",
        "payment_blocking_reason_display", "legal_next_action_display",
        "positive-execution-create", "positive-execution-saved",
        "FIELD_MATRIX", "table_headers", "assertNormalizedFieldSurface",
        "benchmark_dimensions", "requestCreateSaveReopenJourney", "setInputFiles",
        "request-create-save-reopen", "clickAuthoritativeObjectAction",
        "execution-submit-confirm-paid-reconcile", "action_confirm", "action_paid",
        "payment.ledger", "listSearchFilterPageAndReturnJourney",
        "list-search-filter-page-open-return",
        "assertPaymentAmountAggregate", "page_sum", "filtered_total",
    ):
        if token not in browser:
            errors.append(f"browser acceptance missing field evidence anchor: {token}")
    # This P1 guard deliberately does not couple to or mutate the shared My
    # Work browser suite. Reject/correct/resubmit stays partial until its own
    # PFL journey has authenticated evidence; backend action and work-item
    # contracts below are the current static authority.
    rejected_flow_sources = {
        "available_actions": (
            AVAILABLE_ACTIONS.read_text(encoding="utf-8"),
            ('"allowed_states": {"draft", "rejected"}', 'label = "重新提交审批"'),
        ),
        "native_form": (
            native["payment.request"],
            ("state not in ['draft', 'rejected']", 'name="reject_reason"'),
        ),
        "backend_test": (
            P1_BACKEND_TEST.read_text(encoding="utf-8"),
            ("test_rejection_requires_explicit_reason_and_resubmit_preserves_audit",),
        ),
        "work_item_test": (
            WORK_ITEM_TEST.read_text(encoding="utf-8"),
            ("WORK-ITEM-REJECTED-001", "重新提交审批"),
        ),
    }
    for source_name, (source, tokens) in rejected_flow_sources.items():
        for token in tokens:
            if token not in source:
                errors.append(f"rejected correction flow missing {source_name} anchor: {token}")
    journey_gates = payload.get("journey_gates") or []
    if len(journey_gates) < 14:
        errors.append("journey gates are missing")
    for journey in journey_gates:
        if journey.get("coverage_status") not in ALLOWED_JOURNEY_COVERAGE:
            errors.append(f"invalid journey coverage status: {journey.get('key')}")
        if not journey.get("required_assertions"):
            errors.append(f"journey has no assertions: {journey.get('key')}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"[p1-payment-field-completeness] FAIL {error}", file=sys.stderr)
        return 1
    payload = json.loads(MATRIX.read_text(encoding="utf-8"))
    counts = {
        model: sum(1 for rule in payload["field_rules"] if rule["model"] == model)
        for model in MODEL_SOURCES
    }
    print(
        "[p1-payment-field-completeness] PASS "
        + " ".join(f"{model}={count}" for model, count in counts.items())
        + f" journeys={len(payload['journey_gates'])}"
        + f" benchmarks={len(payload['industry_benchmarks']['dimensions'])}"
        + " journey_coverage="
        + "/".join(
            f"{status}:{sum(1 for row in payload['journey_gates'] if row['coverage_status'] == status)}"
            for status in ("implemented", "partial", "missing")
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
