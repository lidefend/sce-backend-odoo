#!/usr/bin/env python3
"""Validate the source-bound backend authority closure map."""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MAP_PATH = ROOT / "docs/architecture/backend_authority_closure_map_v1.json"

REQUIRED_SAMPLES = {
    "query.daily_contract": {
        "profile": "query",
        "roles": {
            "entry_fact",
            "business_fact",
            "capability_alias",
            "publication",
            "enablement",
            "runtime_filter",
            "page_projection",
            "execution",
        },
    },
    "approval.payment_request": {
        "profile": "approval",
        "roles": {
            "task_fact",
            "task_authorization",
            "page_projection",
            "execution_handler",
            "business_transition",
            "result_readback",
        },
    },
    "platform.duty": {
        "profile": "platform",
        "roles": {
            "namespace",
            "identity",
            "duty_catalog",
            "duty_projection",
            "operation_execution",
            "tenant_business_boundary",
        },
    },
}

NO_AUTHORITY_ROLES = {
    "capability_alias",
    "runtime_filter",
    "page_projection",
    "result_readback",
    "duty_projection",
    "tenant_business_boundary",
}
PROJECTION_ROLES = {"capability_alias", "runtime_filter", "page_projection", "result_readback", "duty_projection"}
EXECUTION_ROLES = {"execution", "task_authorization", "execution_handler", "business_transition", "operation_execution"}
REQUIRED_GAP_OWNERS = {"BE-U02", "BE-U03", "BE-U04", "BE-U05"}
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def _error(errors: list[str], message: str) -> None:
    errors.append(message)


def _node_symbols(node: ast.AST) -> dict[str, ast.AST]:
    symbols: dict[str, ast.AST] = {}
    for child in getattr(node, "body", []):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols[child.name] = child
        elif isinstance(child, (ast.Assign, ast.AnnAssign)):
            targets = child.targets if isinstance(child, ast.Assign) else [child.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    symbols[target.id] = child
    return symbols


def _python_symbol_node(tree: ast.AST, symbol: str) -> ast.AST | None:
    current = tree
    node: ast.AST | None = None
    for part in str(symbol or "").split("."):
        if not part:
            return None
        node = _node_symbols(current).get(part)
        if node is None:
            return None
        current = node
    return node


def _resolve_ref(ref: dict[str, Any], root: Path) -> str | None:
    path_value = str(ref.get("path") or "").strip()
    kind = str(ref.get("kind") or "").strip()
    value = str(ref.get("value") or "").strip()
    tokens = ref.get("tokens") or []
    if not path_value or not kind:
        return "reference path and kind are required"
    if path_value.startswith("frontend/"):
        return "frontend paths cannot be backend authority anchors"
    path = (root / path_value).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return "reference escapes repository root"
    if not path.is_file():
        return "reference file does not exist"
    if not value and kind not in {"text"}:
        return "reference value is required"
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        return f"reference cannot be read: {exc}"
    if kind == "text":
        if not tokens or any(not isinstance(token, str) or token not in text for token in tokens):
            return "text tokens are missing"
        return None
    if kind == "xml_record":
        try:
            import xml.etree.ElementTree as ET

            xml_root = ET.fromstring(text)
        except Exception as exc:
            return f"XML cannot be parsed: {exc}"
        found = any(
            node.tag in {"record", "menuitem"} and node.get("id") == value
            for node in xml_root.iter()
        )
        return None if found else "XML record is missing"
    if kind == "json_value":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            return f"JSON cannot be parsed: {exc}"

        def contains(candidate: Any) -> bool:
            if candidate == value:
                return True
            if isinstance(candidate, dict):
                return any(contains(item) for item in candidate.values())
            if isinstance(candidate, list):
                return any(contains(item) for item in candidate)
            return False

        return None if contains(payload) else "JSON value is missing"
    try:
        tree = ast.parse(text, filename=path_value)
    except SyntaxError as exc:
        return f"Python cannot be parsed: {exc}"
    if kind == "model":
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for child in node.body:
                if not isinstance(child, ast.Assign):
                    continue
                if not any(isinstance(target, ast.Name) and target.id == "_name" for target in child.targets):
                    continue
                if isinstance(child.value, ast.Constant) and child.value.value == value:
                    return None
        return "model declaration is missing"
    if kind not in {"python_symbol", "python_symbol_tokens"}:
        return f"unsupported reference kind: {kind}"
    node = _python_symbol_node(tree, value)
    if node is None:
        return "Python symbol is missing"
    if kind == "python_symbol_tokens":
        segment = ast.get_source_segment(text, node) or ""
        if not tokens or any(not isinstance(token, str) or token not in segment for token in tokens):
            return "Python symbol behavior tokens are missing"
    return None


def validate(mapping: dict[str, Any], root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    if mapping.get("schema") != "backend.authority_closure_map.v1":
        _error(errors, "unexpected authority map schema")
    baseline = str(mapping.get("baseline_sha") or "")
    if not FULL_SHA.fullmatch(baseline):
        _error(errors, "baseline_sha must be a full lowercase Git SHA")
    if mapping.get("scope") != "source_mapping_only_no_runtime_or_database_acceptance":
        _error(errors, "scope must explicitly exclude runtime and database acceptance")
    samples = mapping.get("samples")
    if not isinstance(samples, list):
        return errors + ["samples must be a list"]
    by_id = {str(sample.get("id") or ""): sample for sample in samples if isinstance(sample, dict)}
    if set(by_id) != set(REQUIRED_SAMPLES):
        _error(errors, f"sample ids must be exactly {sorted(REQUIRED_SAMPLES)}")
    for sample_id, requirement in REQUIRED_SAMPLES.items():
        sample = by_id.get(sample_id)
        if not isinstance(sample, dict):
            continue
        if sample.get("profile") != requirement["profile"]:
            _error(errors, f"{sample_id}: profile must be {requirement['profile']}")
        stages = sample.get("stages")
        if not isinstance(stages, list) or not stages:
            _error(errors, f"{sample_id}: stages must be a non-empty list")
            continue
        roles = [str(stage.get("role") or "") for stage in stages if isinstance(stage, dict)]
        if set(roles) != requirement["roles"] or len(roles) != len(set(roles)):
            _error(errors, f"{sample_id}: stage roles must be exactly {sorted(requirement['roles'])}")
        required_facts = sample.get("required_facts")
        if not isinstance(required_facts, list) or not required_facts:
            _error(errors, f"{sample_id}: required_facts must be non-empty")
            required_facts = []
        maintained: dict[str, int] = {}
        all_refs: list[dict[str, Any]] = []
        for stage in stages:
            if not isinstance(stage, dict):
                _error(errors, f"{sample_id}: each stage must be an object")
                continue
            role = str(stage.get("role") or "")
            if not str(stage.get("owner") or "").strip():
                _error(errors, f"{sample_id}.{role}: owner is required")
            refs = stage.get("refs")
            if not isinstance(refs, list) or not refs:
                _error(errors, f"{sample_id}.{role}: refs must be non-empty")
                refs = []
            all_refs.extend(ref for ref in refs if isinstance(ref, dict))
            for fact in stage.get("maintains") or []:
                maintained[str(fact)] = maintained.get(str(fact), 0) + 1
            if role in NO_AUTHORITY_ROLES and stage.get("authorizes"):
                _error(errors, f"{sample_id}.{role}: projection or boundary must not authorize")
            if role in NO_AUTHORITY_ROLES and role in {"capability_alias", "runtime_filter", "page_projection", "result_readback", "duty_projection"}:
                if stage.get("projection_only") is not True:
                    _error(errors, f"{sample_id}.{role}: projection_only must be true")
            if role in EXECUTION_ROLES and not stage.get("execution_rechecks"):
                _error(errors, f"{sample_id}.{role}: execution rechecks are required")
        for fact in required_facts:
            count = maintained.get(str(fact), 0)
            if count != 1:
                _error(errors, f"{sample_id}: fact {fact!r} must have exactly one maintainer, got {count}")
        for fact, count in maintained.items():
            if count != 1:
                _error(errors, f"{sample_id}: fact {fact!r} has {count} maintainers")
            if fact not in required_facts:
                _error(errors, f"{sample_id}: maintained fact {fact!r} is not declared in required_facts")
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            for fact in stage.get("consumes") or []:
                if str(fact) not in required_facts:
                    _error(errors, f"{sample_id}.{stage.get('role')}: consumes undeclared fact {fact!r}")
        for ref in all_refs:
            issue = _resolve_ref(ref, root)
            if issue:
                _error(errors, f"{sample_id}: {ref.get('path')}:{ref.get('value')}: {issue}")
    gaps = mapping.get("known_gaps")
    if not isinstance(gaps, list) or not gaps:
        _error(errors, "known_gaps must be a non-empty list")
        return errors
    owners = {str(gap.get("owner_card") or "") for gap in gaps if isinstance(gap, dict)}
    missing_owners = REQUIRED_GAP_OWNERS - owners
    if missing_owners:
        _error(errors, f"known gaps must own follow-up cards {sorted(missing_owners)}")
    for gap in gaps:
        if not isinstance(gap, dict):
            _error(errors, "each known gap must be an object")
            continue
        gap_id = str(gap.get("id") or "<missing>")
        if not str(gap.get("summary") or "").strip():
            _error(errors, f"{gap_id}: summary is required")
        refs = gap.get("refs")
        if not isinstance(refs, list) or not refs:
            _error(errors, f"{gap_id}: refs must be non-empty")
            continue
        for ref in refs:
            if not isinstance(ref, dict):
                _error(errors, f"{gap_id}: each ref must be an object")
                continue
            issue = _resolve_ref(ref, root)
            if issue:
                _error(errors, f"{gap_id}: {ref.get('path')}:{ref.get('value')}: {issue}")
    return errors


def main() -> int:
    try:
        mapping = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[backend_authority_closure_guard] FAIL: {exc}")
        return 2
    errors = validate(mapping)
    if errors:
        print("[backend_authority_closure_guard] FAIL")
        for error in errors:
            print(f" - {error}")
        return 1
    print("[backend_authority_closure_guard] PASS: three source-bound backend authority chains are closed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
