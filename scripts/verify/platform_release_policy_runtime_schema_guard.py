#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
REPORT_JSON = ROOT / "artifacts" / "backend" / "platform_release_policy_runtime_probe.json"
REPORT_MD = ROOT / "artifacts" / "backend" / "platform_release_policy_runtime_probe.md"
PRODUCT_KEYS = {"construction.standard", "construction.preview"}


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _check_counts(prefix: str, value: object, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{prefix} must be object")
        return
    for key in ("menu_group_count", "menu_count", "scene_count", "capability_count"):
        if not isinstance(value.get(key), int):
            errors.append(f"{prefix}.{key} must be int")


def _check_delivery(prefix: str, value: object, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{prefix} must be object")
        return
    for key in (
        "product_key",
        "policy_source_kind",
        "nav_source_authority_kind",
        "capability_source_authority_kind",
    ):
        if not isinstance(value.get(key), str):
            errors.append(f"{prefix}.{key} must be string")
    for key in ("policy_empty",):
        if not isinstance(value.get(key), bool):
            errors.append(f"{prefix}.{key} must be bool")
    for key in (
        "menu_key_count",
        "scene_key_count",
        "capability_key_count",
        "nav_leaf_count",
        "stable_leaf_count",
        "native_preview_leaf_count",
        "delivered_menu_leaf_count",
        "group_count",
    ):
        if not isinstance(value.get(key), int):
            errors.append(f"{prefix}.{key} must be int")


def main() -> int:
    payload = _load_json(REPORT_JSON)
    errors: list[str] = []

    if not payload:
        errors.append(f"missing or invalid json: {REPORT_JSON.relative_to(ROOT).as_posix()}")
    else:
        if not isinstance(payload.get("ok"), bool):
            errors.append("ok must be bool")
        for key in ("db", "probe_user_login"):
            if not isinstance(payload.get(key), str) or not payload.get(key):
                errors.append(f"{key} must be non-empty string")
        if not isinstance(payload.get("native_authorized_leaf_count"), int):
            errors.append("native_authorized_leaf_count must be int")
        if not isinstance(payload.get("customer_specific_product_view_count"), int):
            errors.append("customer_specific_product_view_count must be int")
        customer_view_xmlids = payload.get("customer_specific_product_view_xmlids")
        if not isinstance(customer_view_xmlids, list) or not all(
            isinstance(item, str) for item in customer_view_xmlids
        ):
            errors.append("customer_specific_product_view_xmlids must be string list")
            customer_view_xmlids = []
        if payload.get("customer_specific_product_view_count") != len(customer_view_xmlids):
            errors.append("customer-specific product view count must match XML-ID list")
        if customer_view_xmlids:
            errors.append("customer-specific product view XML-ID list must be empty")
        material_plan_boundary = payload.get("material_plan_customer_field_boundary")
        if not isinstance(material_plan_boundary, dict):
            errors.append("material_plan_customer_field_boundary must be object")
        else:
            for key in ("registered_field_count", "remaining_physical_column_count"):
                if not isinstance(material_plan_boundary.get(key), int):
                    errors.append(f"material_plan_customer_field_boundary.{key} must be int")
            for key in ("registered_fields", "remaining_physical_columns"):
                value = material_plan_boundary.get(key)
                if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                    errors.append(f"material_plan_customer_field_boundary.{key} must be string list")
            if material_plan_boundary.get("registered_field_count") != len(
                material_plan_boundary.get("registered_fields") or []
            ):
                errors.append("material-plan registered field count must match field list")
            if material_plan_boundary.get("remaining_physical_column_count") != len(
                material_plan_boundary.get("remaining_physical_columns") or []
            ):
                errors.append("material-plan remaining column count must match column list")
            if material_plan_boundary.get("registered_fields"):
                errors.append("material-plan P2 legacy-visible registered field list must be empty")
            if material_plan_boundary.get("remaining_physical_columns"):
                errors.append("material-plan P2 legacy-visible physical column list must be empty")
        material_rfq_boundary = payload.get("material_rfq_customer_field_boundary")
        if not isinstance(material_rfq_boundary, dict):
            errors.append("material_rfq_customer_field_boundary must be object")
        else:
            for key in ("registered_field_count", "remaining_physical_column_count"):
                if not isinstance(material_rfq_boundary.get(key), int):
                    errors.append(f"material_rfq_customer_field_boundary.{key} must be int")
            for key in ("registered_fields", "remaining_physical_columns"):
                value = material_rfq_boundary.get(key)
                if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                    errors.append(f"material_rfq_customer_field_boundary.{key} must be string list")
            if material_rfq_boundary.get("registered_field_count") != len(
                material_rfq_boundary.get("registered_fields") or []
            ):
                errors.append("RFQ registered field count must match field list")
            if material_rfq_boundary.get("remaining_physical_column_count") != len(
                material_rfq_boundary.get("remaining_physical_columns") or []
            ):
                errors.append("RFQ remaining column count must match column list")
            if material_rfq_boundary.get("registered_fields"):
                errors.append("RFQ P2 legacy-visible registered field list must be empty")
            if material_rfq_boundary.get("remaining_physical_columns"):
                errors.append("RFQ P2 legacy-visible physical column list must be empty")
        material_inbound_boundary = payload.get("material_inbound_customer_field_boundary")
        if not isinstance(material_inbound_boundary, dict):
            errors.append("material_inbound_customer_field_boundary must be object")
        else:
            for key in ("registered_field_count", "remaining_physical_column_count"):
                if not isinstance(material_inbound_boundary.get(key), int):
                    errors.append(f"material_inbound_customer_field_boundary.{key} must be int")
            for key in ("registered_fields", "remaining_physical_columns"):
                value = material_inbound_boundary.get(key)
                if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                    errors.append(f"material_inbound_customer_field_boundary.{key} must be string list")
            if material_inbound_boundary.get("registered_field_count") != len(material_inbound_boundary.get("registered_fields") or []):
                errors.append("inbound registered field count must match field list")
            if material_inbound_boundary.get("remaining_physical_column_count") != len(material_inbound_boundary.get("remaining_physical_columns") or []):
                errors.append("inbound remaining column count must match column list")
            if material_inbound_boundary.get("registered_fields"):
                errors.append("inbound P2 legacy-visible registered field list must be empty")
            if material_inbound_boundary.get("remaining_physical_columns"):
                errors.append("inbound P2 legacy-visible physical column list must be empty")
        pass_through_boundaries = payload.get("pass_through_customer_field_boundaries")
        subcontract_boundary = payload.get("subcontract_request_customer_field_boundary")
        if not isinstance(subcontract_boundary, dict):
            errors.append("subcontract_request_customer_field_boundary must be object")
        else:
            registered = subcontract_boundary.get("registered_fields")
            physical = subcontract_boundary.get("remaining_physical_columns")
            if registered or physical:
                errors.append("subcontract request P2 boundary must be empty")
            if subcontract_boundary.get("registered_field_count") != len(registered or []):
                errors.append("subcontract request registered count mismatch")
            if subcontract_boundary.get("remaining_physical_column_count") != len(physical or []):
                errors.append("subcontract request physical count mismatch")
        diary_boundary = payload.get("construction_diary_customer_field_boundary")
        if not isinstance(diary_boundary, dict):
            errors.append("construction_diary_customer_field_boundary must be object")
        else:
            registered = diary_boundary.get("registered_fields")
            physical = diary_boundary.get("remaining_physical_columns")
            if registered or physical:
                errors.append("construction diary P2 boundary must be empty")
            if diary_boundary.get("registered_field_count") != len(registered or []):
                errors.append("construction diary registered count mismatch")
            if diary_boundary.get("remaining_physical_column_count") != len(physical or []):
                errors.append("construction diary physical count mismatch")
        expected_pass_through_models = {
            "sc.fund.account.operation",
            "sc.receipt.income",
            "sc.invoice.registration",
            "construction.contract.expense",
        }
        if not isinstance(pass_through_boundaries, dict):
            errors.append("pass_through_customer_field_boundaries must be object")
        elif set(pass_through_boundaries) != expected_pass_through_models:
            errors.append("pass-through customer field boundary model set mismatch")
        else:
            for model_name, boundary in pass_through_boundaries.items():
                if not isinstance(boundary, dict):
                    errors.append(f"pass-through boundary must be object: {model_name}")
                    continue
                registered = boundary.get("registered_fields")
                physical = boundary.get("remaining_physical_columns")
                if registered or physical:
                    errors.append(f"pass-through P2 boundary must be empty: {model_name}")
                if boundary.get("registered_field_count") != len(registered or []):
                    errors.append(f"pass-through registered count mismatch: {model_name}")
                if boundary.get("remaining_physical_column_count") != len(physical or []):
                    errors.append(f"pass-through physical count mismatch: {model_name}")
        failures = payload.get("failures")
        if not isinstance(failures, list) or not all(isinstance(item, str) for item in failures):
            errors.append("failures must be string list")
            failures = []
        if payload.get("ok") is True and failures:
            errors.append("ok=true report must not contain failures")
        if payload.get("ok") is False and not failures:
            errors.append("ok=false report must contain failures")

        artifacts = payload.get("artifacts")
        if not isinstance(artifacts, dict):
            errors.append("artifacts must be object")
        else:
            for key in ("json", "markdown"):
                if not isinstance(artifacts.get(key), str) or not artifacts.get(key):
                    errors.append(f"artifacts.{key} must be non-empty string")

        products = payload.get("products")
        if not isinstance(products, list):
            errors.append("products must be list")
            products = []
        seen_products: set[str] = set()
        for idx, product in enumerate(products):
            prefix = f"products[{idx}]"
            if not isinstance(product, dict):
                errors.append(f"{prefix} must be object")
                continue
            product_key = str(product.get("product_key") or "").strip()
            if product_key not in PRODUCT_KEYS:
                errors.append(f"{prefix}.product_key must be one of {sorted(PRODUCT_KEYS)}")
            seen_products.add(product_key)
            if not isinstance(product.get("policy_source_kind"), str) or not product.get("policy_source_kind"):
                errors.append(f"{prefix}.policy_source_kind must be non-empty string")
            _check_counts(f"{prefix}.policy_counts", product.get("policy_counts"), errors)
            _check_counts(f"{prefix}.catalog_counts", product.get("catalog_counts"), errors)
            runtime = product.get("runtime")
            if not isinstance(runtime, dict):
                errors.append(f"{prefix}.runtime must be object")
            else:
                for key in ("user_delivery", "no_native_delivery", "subset_delivery", "admin_delivery"):
                    _check_delivery(f"{prefix}.runtime.{key}", runtime.get(key), errors)
        if seen_products != PRODUCT_KEYS:
            errors.append(f"products must cover {sorted(PRODUCT_KEYS)}")

    if not REPORT_MD.is_file():
        errors.append(f"missing markdown report: {REPORT_MD.relative_to(ROOT).as_posix()}")
    else:
        text = REPORT_MD.read_text(encoding="utf-8")
        for token in ("# Platform Release Policy Runtime Probe", "- ok:", "## Products", "## Failures"):
            if token not in text:
                errors.append(f"markdown report missing token: {token}")

    if errors:
        print("[platform_release_policy_runtime_schema_guard] FAIL")
        for error in errors:
            print(error)
        return 2

    print("[platform_release_policy_runtime_schema_guard] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
