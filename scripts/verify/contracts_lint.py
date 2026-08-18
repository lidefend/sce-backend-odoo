#!/usr/bin/env python3
"""Validate local contract artifacts under contracts/ directory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


REPORT_PATH = Path("artifacts/contracts_lint_report.json")

def fail(msg: str) -> None:
    print(f"[ERROR] {msg}")


def load_yaml(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if data is not None else {}
    except Exception as exc:
        raise RuntimeError(f"{path}: YAML parse failed: {exc}")


def get_json_pointer(document: Any, pointer: str) -> bool:
    if pointer == "":
        return True
    if not pointer.startswith("/"):
        return False

    node = document
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict):
            if token not in node:
                return False
            node = node[token]
        elif isinstance(node, list):
            if not token.isdigit():
                return False
            idx = int(token)
            if idx < 0 or idx >= len(node):
                return False
            node = node[idx]
        else:
            return False
    return True


def normalize_pointer(pointer: str) -> str:
    if pointer == "#":
        return ""
    if pointer.startswith("#/"):
        return pointer[1:]
    return pointer


def validate_ref(
    value: str,
    source: Path,
    docs: Dict[Path, Dict[str, Any]],
    errors: List[str],
    refs: List[Dict[str, Any]],
) -> None:
    if not isinstance(value, str):
        return

    if "#" not in value:
        target = (source.parent / value).resolve()
        if not target.exists():
            errors.append(f"{source}: ref target file not found: {value}")
        elif target.suffix != ".yaml":
            errors.append(f"{source}: ref target extension not supported: {value}")
        return

    file_part, fragment = value.split("#", 1)
    if file_part in ("", "."):
        target = source
    else:
        target = (source.parent / file_part).resolve()

    if not target.exists():
        errors.append(f"{source}: ref target file not found: {value}")
        return

    document = docs.get(target)
    if document is None:
        try:
            document = load_yaml(target)
            docs[target] = document
        except Exception as exc:
            errors.append(str(exc))
            return

    normalized = normalize_pointer(f"#{fragment}")
    if normalized == "#":
        normalized = ""
    if not normalized.startswith("/") and normalized != "":
        errors.append(f"{source}: unsupported ref fragment '{value}'")
        return

    if normalized and not get_json_pointer(document, normalized):
        errors.append(f"{source}: invalid json pointer '{value}' (resolved {target})")
        return

    refs.append({"source": str(source), "ref": value, "resolved": str(target)})


def walk_refs(
    node: Any,
    source: Path,
    docs: Dict[Path, Dict[str, Any]],
    errors: List[str],
    refs: List[Dict[str, Any]],
    local_operation_refs: List[Tuple[str, str, str]],
) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref":
                validate_ref(value, source, docs, errors, refs)
                continue
            if key == "operationRef":
                if not isinstance(value, str):
                    errors.append(f"{source}: operationRef must be string")
                elif not value.startswith("#/paths/"):
                    errors.append(f"{source}: operationRef must point to local path operation, got '{value}'")
                else:
                    local_operation_refs.append((str(source), str(node.get("route", "")) if isinstance(node, dict) and "route" in node else "", value))
                continue
            walk_refs(value, source, docs, errors, refs, local_operation_refs)
    elif isinstance(node, list):
        for item in node:
            walk_refs(item, source, docs, errors, refs, local_operation_refs)


def require_mapping(path: Path, data: Any, required_keys: List[str], errors: List[str]) -> None:
    if not isinstance(data, dict):
        errors.append(f"{path}: content must be YAML mapping")
        return
    for key in required_keys:
        if key not in data:
            errors.append(f"{path}: missing required key '{key}'")


def check_openapi_shape(data: Dict[str, Any], path: Path, errors: List[str], op_ids: List[Tuple[str, str]]) -> None:
    if "openapi" not in data:
        errors.append(f"{path}: missing required key 'openapi'")
    if "paths" not in data or not isinstance(data.get("paths"), dict):
        errors.append(f"{path}: missing or invalid 'paths' object")
        return
    if "info" not in data:
        errors.append(f"{path}: missing required key 'info'")

    seen = set()
    for path_name, path_item in data["paths"].items():
        if not isinstance(path_name, str) or not path_name.startswith("/"):
            errors.append(f"{path_name}: path key should start with '/'")
        if not isinstance(path_item, dict):
            errors.append(f"{path_name}: path definition must be mapping")
            continue
        for method, op in path_item.items():
            if method == "parameters":
                continue
            if method not in {"get", "post", "put", "patch", "delete", "head", "options", "trace"}:
                errors.append(f"{path_name}: unsupported HTTP method '{method}'")
                continue
            if not isinstance(op, dict):
                errors.append(f"{path_name}: operation for '{method}' must be mapping")
                continue
            op_id = op.get("operationId")
            if not op_id:
                errors.append(f"{path_name}: {method} missing operationId")
            elif op_id in seen:
                errors.append(f"{path_name}: duplicate operationId '{op_id}'")
            else:
                seen.add(op_id)
                op_ids.append((path_name, method))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="contracts")
    parser.add_argument("--report", default=str(REPORT_PATH))
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"[ERROR] contracts root not found: {root}")
        return 2

    required_files = [
        root / "product" / "payment-request.yaml",
        root / "domain" / "payment-request.yaml",
        root / "api" / "openapi.yaml",
        root / "api" / "payment-request.yaml",
        root / "schemas" / "common.yaml",
        root / "schemas" / "contract-ref.yaml",
        root / "schemas" / "money.yaml",
        root / "schemas" / "project-ref.yaml",
        root / "schemas" / "payment-request.yaml",
        root / "extensions" / "permission.yaml",
        root / "extensions" / "ui.yaml",
        root / "extensions" / "workflow.yaml",
    ]

    errors: List[str] = []
    docs: Dict[Path, Dict[str, Any]] = {}
    refs: List[Dict[str, Any]] = []
    local_operation_refs: List[Tuple[str, str, str]] = []

    for path in sorted(root.rglob("*.yaml")):
        docs[path.resolve()] = load_yaml(path)

    for req in required_files:
        if req.resolve() not in docs:
            errors.append(f"required contract file missing: {req}")

    for p in (root / "product").glob("*.yaml"):
        require_mapping(p, docs[p.resolve()], ["id", "title", "pages", "capabilities", "roles"], errors)

    for p in (root / "domain").glob("*.yaml"):
        require_mapping(p, docs[p.resolve()], ["id", "title", "entity", "identity", "fields", "states", "transitions"], errors)

    openapi_path = root / "api" / "openapi.yaml"
    if openapi_path.resolve() in docs:
        openapi = docs[openapi_path.resolve()]
        if not isinstance(openapi, dict):
            errors.append(f"{openapi_path}: openapi contract must be YAML mapping")
        else:
            op_ids: List[Tuple[str, str]] = []
            check_openapi_shape(openapi, openapi_path, errors, op_ids)

    split_api = root / "api" / "payment-request.yaml"
    if split_api.resolve() in docs:
        # operationRef must resolve to concrete root openapi operations
        split_doc = docs[split_api.resolve()]
        if not isinstance(split_doc, dict):
            errors.append(f"{split_api}: must be YAML mapping")
        else:
            openapi_docs = docs.get(openapi_path.resolve(), {})
            if not isinstance(openapi_docs, dict) or "paths" not in openapi_docs:
                errors.append(f"{split_api}: openapi.yaml must be loaded before validating operationRef")
            else:
                openapi_paths = openapi_docs.get("paths", {})
                if not isinstance(openapi_paths, dict):
                    errors.append(f"{openapi_path}: paths must be mapping")
                else:
                    split_routes = split_doc.get("paths", split_doc)
                    if not isinstance(split_routes, dict):
                        errors.append(f"{split_api}: split API must contain path map at root or under 'paths'")
                        split_routes = {}

                    for route, route_map in split_routes.items():
                        if not isinstance(route_map, dict):
                            errors.append(f"{split_api}: path '{route}' must be mapping")
                            continue
                        for method, ref_item in route_map.items():
                            if not isinstance(ref_item, dict):
                                errors.append(f"{split_api}: operation for '{route}/{method}' must be mapping")
                                continue
                            op_ref = ref_item.get("operationRef")
                            if not isinstance(op_ref, str):
                                errors.append(f"{split_api}: '{route}/{method}' missing operationRef")
                                continue
                            expected_prefix = "#/paths/" + route.replace("/", "~1") + "/" + method
                            if op_ref != expected_prefix:
                                errors.append(f"{split_api}: operationRef '{op_ref}' expected '{expected_prefix}'")
                            if not get_json_pointer(openapi_docs, op_ref[1:]):
                                errors.append(f"{split_api}: operationRef '{op_ref}' not found in {openapi_path}")

    for p, doc in docs.items():
        if doc is None:
            continue
        walk_refs(doc, p, docs, errors, refs, local_operation_refs)

    # basic duplicate check for local operation refs
    seen_op_refs = set()
    for source, route_label, ref in local_operation_refs:
        if ref in seen_op_refs:
            errors.append(f"{source}: duplicate local operationRef '{ref}' in '{route_label or 'route'}'")
        seen_op_refs.add(ref)

    report = {
        "root": str(root),
        "files": sorted(str(p) for p in docs),
        "refs": refs,
        "issues": errors,
        "total_issues": len(errors),
    }

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if errors:
        for e in errors:
            fail(e)
        print(f"[contracts-lint] FAIL: {len(errors)} issues")
        print(f"[contracts-lint] report: {report_path}")
        return 2

    print(f"[contracts-lint] PASS: parsed {len(docs)} docs, refs {len(refs)}")
    print(f"[contracts-lint] report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
