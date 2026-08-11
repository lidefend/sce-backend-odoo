#!/usr/bin/env python3
"""Fail closed when governed business entries drift from their fact owner."""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "docs/architecture/backend_business_model_ownership_specs_v1.json"
MODULE = ROOT / "addons/smart_construction_core"
REQUIRED_OWNERSHIP_FIELDS = {
    "formal_product_layer": "P1",
    "layer_target": "L2_industry_standard",
    "module": "smart_construction_core",
    "standard_vs_user_specific": "construction_industry_standard",
    "frontend_policy": "contract_renderer_only",
}


def _field(node: ET.Element, name: str) -> ET.Element | None:
    return next((item for item in node.findall("field") if item.attrib.get("name") == name), None)


def _field_text(node: ET.Element, name: str) -> str:
    field = _field(node, name)
    return (field.text or "").strip() if field is not None else ""


def _field_ref(node: ET.Element, name: str) -> str:
    field = _field(node, name)
    return field.attrib.get("ref", "") if field is not None else ""


def _field_expression(node: ET.Element, name: str) -> str:
    field = _field(node, name)
    if field is None:
        return ""
    return (field.text or "").strip() or field.attrib.get("eval", "")


def _local_xmlid(xmlid: str) -> str:
    return xmlid.rsplit(".", 1)[-1]


def _xml_records() -> tuple[dict[str, ET.Element], dict[str, ET.Element]]:
    records: dict[str, ET.Element] = {}
    menus: dict[str, ET.Element] = {}
    for path in sorted(MODULE.rglob("*.xml")):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        for node in root.findall(".//record"):
            xmlid = node.attrib.get("id")
            if xmlid:
                records[xmlid] = node
        for node in root.findall(".//menuitem"):
            xmlid = node.attrib.get("id")
            if xmlid:
                menus[xmlid] = node
    return records, menus


def _detected_models() -> set[str]:
    result: set[str] = set()
    pattern = re.compile(r"^\s*_name\s*=\s*['\"]([^'\"]+)['\"]", re.MULTILINE)
    for path in MODULE.rglob("*.py"):
        result.update(pattern.findall(path.read_text(encoding="utf-8")))
    return result


def validate(registry: dict) -> list[str]:
    errors: list[str] = []
    records, menus = _xml_records()
    detected_models = _detected_models()
    governed = [item for item in registry.get("ownership_specs", []) if item.get("entry_bindings")]
    if not governed:
        return ["ownership registry must define at least one governed entry binding"]

    for spec in governed:
        key = spec.get("spec", "<missing>")
        for field, expected in REQUIRED_OWNERSHIP_FIELDS.items():
            if spec.get(field) != expected:
                errors.append(f"{key}.{field} must be {expected!r}")
        bindings = spec.get("entry_bindings") or []
        intents = [item.get("intent") for item in bindings]
        models = [item.get("fact_model") for item in bindings]
        if not all(intents) or len(intents) != len(set(intents)):
            errors.append(f"{key} entry intents must be present and unique")
        if spec.get("separation_policy") == "distinct_fact_models" and len(models) != len(set(models)):
            errors.append(f"{key} requires one distinct fact model per business intent")
        if not spec.get("conservation_invariants"):
            errors.append(f"{key} must declare conservation invariants")
        carriers = spec.get("authority_carriers") or []
        if not carriers or any(str(item).startswith("frontend/") for item in carriers):
            errors.append(f"{key} authority carriers must exist outside frontend")
        for carrier in carriers:
            if not (ROOT / carrier).exists():
                errors.append(f"{key} authority carrier does not exist: {carrier}")

        fact_sources = set(spec.get("fact_source_model") or [])
        for binding in bindings:
            intent = binding.get("intent", "<missing>")
            model = binding.get("fact_model", "")
            if model not in fact_sources:
                errors.append(f"{key}.{intent} fact model is not a declared source: {model}")
            if model not in detected_models:
                errors.append(f"{key}.{intent} fact model is not implemented: {model}")

            action_id = _local_xmlid(binding.get("action_xmlid", ""))
            action = records.get(action_id)
            if action is None or action.attrib.get("model") != "ir.actions.act_window":
                errors.append(f"{key}.{intent} action is missing: {action_id}")
            elif _field_text(action, "res_model") != model:
                errors.append(f"{key}.{intent} action model drifted from {model}")

            menu_id = _local_xmlid(binding.get("menu_xmlid", ""))
            menu = menus.get(menu_id)
            if menu is None:
                errors.append(f"{key}.{intent} menu is missing: {menu_id}")
            elif menu.attrib.get("action") != binding.get("action_xmlid"):
                errors.append(f"{key}.{intent} menu action drifted from ownership registry")

            contract_id = _local_xmlid(binding.get("view_contract_xmlid", ""))
            contract = records.get(contract_id)
            if contract is None or contract.attrib.get("model") != "ui.business.config.contract":
                errors.append(f"{key}.{intent} view contract is missing: {contract_id}")
            else:
                if _field_text(contract, "model") != model:
                    errors.append(f"{key}.{intent} view contract model drifted from {model}")
                if _field_ref(contract, "action_id") != binding.get("action_xmlid"):
                    errors.append(f"{key}.{intent} view contract action drifted from ownership registry")
                if "smart_construction_core.product_release" not in _field_expression(contract, "contract_json"):
                    errors.append(f"{key}.{intent} view contract lacks P1 source authority")
    return errors


def main() -> int:
    try:
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        errors = validate(registry)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[FAIL] business entry ownership guard: {exc}")
        return 1
    if errors:
        print("\n".join(f"[FAIL] {item}" for item in errors))
        return 1
    print("[PASS] governed entries match their P1 fact, action, menu and rendering-contract owners")
    return 0


if __name__ == "__main__":
    sys.exit(main())
