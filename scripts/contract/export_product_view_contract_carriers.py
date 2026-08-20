#!/usr/bin/env python3
"""Collect final LoadContractHandler carriers inside governed Odoo shell."""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from odoo import SUPERUSER_ID
from odoo.addons.smart_core.handlers.load_contract import LoadContractHandler

try:
    ROOT = Path(__file__).resolve().parents[2]
except NameError:
    ROOT = Path("/mnt")
sys.path.insert(0, str(ROOT / "scripts" / "contract"))

from complete_worktree_fingerprint import validate_fingerprint  # noqa: E402
from product_view_contract_carriers_common import (  # noqa: E402
    TYPE_REQUIRED_KEYS,
    assert_system_identity,
    atomic_write_json,
    expected_normalized_selectors,
    file_sha256,
    normalized_value_errors,
    sha256_json,
    stable_selector_payload,
    with_manifest,
)


SCHEMA = "product_view_contract_carriers/v1"
STRUCTURE_SCHEMA = "product_view_structure_contract/v1"
EXPECTED_DB = "sc_clean"
def _required_path(name: str) -> Path:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"missing {name}")
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def _surfaces(structure: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [surface for entry in structure.get("entries", []) for surface in entry.get("surfaces", [])]
    rows.sort(key=lambda item: item["contract_ref"])
    return rows


def _external_id(record: Any) -> str:
    values = record.get_external_id()
    return str(values.get(record.id) or "")


def _runtime_authority(runtime_env: Any, structure: dict[str, Any], fingerprint: dict[str, Any]) -> dict[str, Any]:
    source = structure["authority"]
    if runtime_env.cr.dbname != EXPECTED_DB:
        raise ValueError(f"carrier collector requires database {EXPECTED_DB}")
    if "app.contract.service" in runtime_env.registry.models:
        raise ValueError("unproven app.contract.service is registered")
    modules = runtime_env["ir.module.module"].sudo().search([("state", "=", "installed")])
    module_set = sorted(
        ({"name": row.name, "installed_version": str(row.latest_version or "")} for row in modules),
        key=lambda item: item["name"],
    )
    if sha256_json(module_set) != source["module_set_sha256"]:
        raise ValueError("runtime module set differs from structure input")
    assert_system_identity(runtime_env.uid, SUPERUSER_ID, source["user"])
    if source["language"] != "en_US" or runtime_env.context.get("lang") != source["language"]:
        raise ValueError("runtime user or language differs from structure input")
    company = _external_id(runtime_env.company)
    if company != source["company"]:
        raise ValueError("runtime company differs from structure input")
    group_profile = sorted(value for value in runtime_env.user.groups_id.get_external_id().values() if value)
    if group_profile != source["group_profile"]:
        raise ValueError("runtime group profile differs from structure input")
    return {
        "branch": fingerprint["branch"],
        "candidate_fingerprint": {key: fingerprint[key] for key in ("algorithm", "git_head", "baseline_sha", "scope_manifest_sha256", "digest")},
        "runtime_profile": "local.clean",
        "compose_project": "sc-local-clean",
        "database": EXPECTED_DB,
        "database_filter": "^sc_clean$",
        "demo_data": False,
        "module_set": module_set,
        "module_set_sha256": source["module_set_sha256"],
        "user": source["user"],
        "company": company,
        "language": source["language"],
        "group_profile": group_profile,
        "handler": "odoo.addons.smart_core.handlers.load_contract.LoadContractHandler",
        "capture_mode": "final_response_rollback_sandbox",
        "force_refresh": True,
        "external_contract_service_absent": True,
        "capture_transaction_strategy": "dedicated_cursor_rollback",
        "exporter_version": SCHEMA,
    }


def _carrier(source_selector: str, artifact_selector: str, source_authority: str, value: Any) -> dict[str, Any]:
    return {
        "source_selector": source_selector,
        "artifact_selector": artifact_selector,
        "source_authority": source_authority,
        "value": value,
        "value_hash": sha256_json(value),
    }


def _capture_surface(runtime_env: Any, surface: dict[str, Any], authority: dict[str, Any], index: int) -> dict[str, Any]:
    view_type = surface["view_type"]
    if view_type not in TYPE_REQUIRED_KEYS or view_type == "list":
        raise ValueError(f"unsupported canonical view type: {view_type}")
    menu_id = runtime_env.ref(surface["menu_xmlid"]).id
    action_id = runtime_env.ref(surface["action_xmlid"]).id
    requested_view_id = 0
    request_context: dict[str, Any] = {}
    if surface["source_kind"] == "database_view":
        requested_view_id = runtime_env.ref(surface["view_ref"]).id
        request_context["requested_view_id"] = requested_view_id
    elif surface["source_kind"] != "synthetic_default_view":
        raise ValueError(f"unsupported source kind: {surface['source_kind']}")
    request = {
        "menu_id": menu_id,
        "action_id": action_id,
        "model": surface["model"],
        "view_type": view_type,
        "include": "all",
        "force_refresh": True,
        "context": request_context,
    }
    params = dict(request)
    params["context"] = request_context
    result = LoadContractHandler(env=runtime_env).handle(payload={"params": params}, ctx=dict(runtime_env.context or {}))
    status = str(result.get("status") or "").lower() if isinstance(result, dict) else ""
    code = int(result.get("code") or 0) if isinstance(result, dict) else 0
    data = result.get("data") if isinstance(result, dict) else None
    if status != "success" or code != 200 or not isinstance(data, dict):
        raise ValueError(f"{surface['contract_ref']} handler failed status={status} code={code}")
    if data.get("degraded") is not False:
        raise ValueError(f"{surface['contract_ref']} degraded response")
    warnings = data.get("warnings") or []
    if not isinstance(warnings, list) or any(str(item).startswith("view_contract_fallback:") for item in warnings):
        raise ValueError(f"{surface['contract_ref']} ungoverned fallback warning")
    views = data.get("views")
    view_value = views.get(view_type) if isinstance(views, dict) else None
    if not isinstance(view_value, dict):
        raise ValueError(f"{surface['contract_ref']} missing data.views.{view_type}")
    if view_value.get("model") != surface["model"] or view_value.get("view_type") != view_type:
        raise ValueError(f"{surface['contract_ref']} normalized identity mismatch")
    value_errors = normalized_value_errors(view_type, surface["model"], f"/data/views/{view_type}", view_value)
    if value_errors:
        raise ValueError(f"{surface['contract_ref']} {'; '.join(value_errors)}")

    normalized_values = [(f"/data/views/{view_type}", view_value)]
    if view_type == "search":
        search_value = data.get("search")
        if not isinstance(search_value, dict):
            raise ValueError(f"{surface['contract_ref']} missing data.search")
        normalized_values.append(("/data/search", search_value))
    if tuple(selector for selector, _value in normalized_values) != expected_normalized_selectors(view_type):
        raise ValueError(f"{surface['contract_ref']} normalized selector set mismatch")
    normalized = [
        _carrier(selector, f"/entries/{index}/normalized_carriers/{offset}/value", "normalized_contract", value)
        for offset, (selector, value) in enumerate(normalized_values)
    ]

    semantic_values: list[dict[str, Any]] = []
    semantic_page = data.get("semantic_page")
    outcome = {"status": "normalized_only", "reason_code": "CAPABILITY_SEMANTIC_CARRIER_MISSING"}
    if isinstance(semantic_page, dict) and semantic_page.get("version") == "v1" and semantic_page.get("source") == "load_contract":
        if semantic_page.get("model") != surface["model"] or semantic_page.get("view_type") != view_type:
            raise ValueError(f"{surface['contract_ref']} semantic identity mismatch")
        semantic_values.append(
            _carrier("/data/semantic_page", f"/entries/{index}/semantic_carriers/0/value", "semantic_page", semantic_page)
        )
        outcome = {"status": "complete", "reason_code": ""}

    metadata = result.get("meta") if isinstance(result.get("meta"), dict) else {}
    entry = {
        "contract_ref": surface["contract_ref"],
        "menu_xmlid": surface["menu_xmlid"],
        "action_xmlid": surface["action_xmlid"],
        "model": surface["model"],
        "view_type": view_type,
        "view_ref": surface["view_ref"],
        "source_kind": surface["source_kind"],
        "hashes": dict(surface["hashes"]),
        "runtime_binding": {"menu_id": menu_id, "action_id": action_id, "requested_view_id": requested_view_id, "selector_sha256": ""},
        "request": request,
        "response": {
            "status": status,
            "code": code,
            "source_authority": "load_contract_final_response",
            "etag": str(result.get("etag") or metadata.get("etag") or ""),
            "degraded": False,
            "warnings": sorted(str(item) for item in warnings),
        },
        "normalized_carriers": normalized,
        "semantic_carriers": semantic_values,
        "capture_outcome": outcome,
    }
    entry["runtime_binding"]["selector_sha256"] = sha256_json(stable_selector_payload(entry, authority))
    return entry


def capture(runtime_env: Any, structure_path: Path, fingerprint_path: Path) -> dict[str, Any]:
    structure = _load(structure_path)
    fingerprint = _load(fingerprint_path)
    if structure.get("schema") != STRUCTURE_SCHEMA:
        raise ValueError("structure input schema mismatch")
    fingerprint_errors = validate_fingerprint(fingerprint)
    if fingerprint_errors:
        raise ValueError("; ".join(fingerprint_errors))
    source_fp = structure.get("authority", {}).get("candidate_fingerprint", {})
    if source_fp != {key: fingerprint[key] for key in ("algorithm", "git_head", "baseline_sha", "scope_manifest_sha256", "digest")}:
        raise ValueError("structure input candidate fingerprint mismatch")
    authority = _runtime_authority(runtime_env, structure, fingerprint)
    surfaces = _surfaces(structure)
    expected = int(structure["summary"]["resolved_surface_count"])
    if not surfaces or len(surfaces) != expected:
        raise ValueError("structure surface count mismatch")
    entries = [_capture_surface(runtime_env, surface, authority, index) for index, surface in enumerate(surfaces)]
    view_type_counts = dict(sorted(Counter(row["view_type"] for row in entries).items()))
    complete_count = sum(row["capture_outcome"]["status"] == "complete" for row in entries)
    payload = {
        "schema": SCHEMA,
        "authority": authority,
        "structure_input": {
            "path": "artifacts/contract/product_view_structure_contract.json",
            "sha256": file_sha256(structure_path),
            "manifest_sha256": structure["manifest_sha256"],
            "candidate_fingerprint": authority["candidate_fingerprint"],
            "formal_menu_policy_sha256": structure["authority"]["formal_menu_policy_sha256"],
            "expected_formal_menu_count": structure["summary"]["formal_menu_count"],
            "expected_model_count": structure["summary"]["model_count"],
            "expected_surface_count": expected,
        },
        "summary": {
            "formal_menu_count": structure["summary"]["formal_menu_count"],
            "model_count": structure["summary"]["model_count"],
            "surface_count": len(entries),
            "complete_count": complete_count,
            "normalized_only_count": len(entries) - complete_count,
            "error_count": 0,
            "normalized_carrier_count": sum(len(row["normalized_carriers"]) for row in entries),
            "semantic_carrier_count": sum(len(row["semantic_carriers"]) for row in entries),
            "view_type_counts": view_type_counts,
        },
        "entries": entries,
    }
    return with_manifest(payload)


structure_input = _required_path("PRODUCT_VIEW_CARRIER_STRUCTURE_INPUT")
fingerprint_input = _required_path("PRODUCT_VIEW_CARRIER_FINGERPRINT")
output = _required_path("PRODUCT_VIEW_CARRIER_OUTPUT")
if output.resolve() in {structure_input.resolve(), fingerprint_input.resolve()}:
    raise ValueError("carrier output must not overwrite an input")
output.unlink(missing_ok=True)
captured = None
with env.registry.cursor() as capture_cr:
    try:
        runtime = env(cr=capture_cr, context={**dict(env.context or {}), "lang": "en_US"})
        captured = capture(runtime, structure_input, fingerprint_input)
    finally:
        capture_cr.rollback()
if captured is not None:
    atomic_write_json(output, captured)
    print(json.dumps({"status": "PASS", "surface_count": captured["summary"]["surface_count"], "manifest_sha256": captured["manifest_sha256"]}, sort_keys=True))
