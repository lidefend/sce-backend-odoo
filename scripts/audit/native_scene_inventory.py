#!/usr/bin/env python3
"""Deterministic, read-only NATIVE-SCENE source inventory.

The generated files are evidence about module source declarations. They do not
claim effective runtime ACL, installed state, inherited-view merging or browser
delivery. Runtime evidence is hashed and linked from the manifest separately.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable
from xml.parsers import expat


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "docs/audit/native-scene-01/inventories"
EVIDENCE_DIR = ROOT / "docs/audit/native-scene-01/evidence"
RAW_REGISTRY = EVIDENCE_DIR / "navigation_capability_inventory_v1.json"
CURRENT_NATIVE_LOG = ROOT / "docs/audit/capability-explorer-05/evidence/current-native.log"
MANIFEST_GLOBS = (
    "addons/*/__manifest__.py",
    "addons_external/*/*/__manifest__.py",
    "customer_addons/*/__manifest__.py",
    "demo_addons/*/__manifest__.py",
)
ACTION_MODELS = {
    "ir.actions.act_window",
    "ir.actions.server",
    "ir.actions.client",
    "ir.actions.report",
    "ir.actions.act_url",
}
VIEW_TAGS = {
    "form",
    "tree",
    "list",
    "kanban",
    "search",
    "pivot",
    "graph",
    "calendar",
    "gantt",
    "activity",
    "dashboard",
    "qweb",
}
XMLID_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z0-9_.]+\b")
REF_CALL_RE = re.compile(r"\bref\(\s*['\"]([^'\"]+)['\"]\s*\)")
ACTION_CALL_RE = re.compile(r"%\(\s*([^)\s]+)\s*\)d")
RELATIONAL_TYPES = {"Many2one", "One2many", "Many2many", "Reference"}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def _manifest(path: Path) -> dict[str, Any]:
    value = ast.literal_eval(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: manifest is not a dictionary")
    return value


def _module_scope(name: str) -> str:
    if name in {"base_tier_validation", "base_tier_validation_server_action"}:
        return "oca"
    if name in {
        "smart_construction_demo",
        "smart_construction_seed",
        "smart_construction_bootstrap",
        "smart_construction_acceptance_fixture",
    }:
        return "p4"
    if name.startswith("sce_customer_"):
        return "p2"
    if name in {
        "smart_core",
        "smart_scene",
        "smart_license_core",
        "smart_owner_core",
        "smart_owner_bundle",
    }:
        return "p0"
    return "p1"


@dataclass
class XmlNode:
    tag: str
    attrs: dict[str, str]
    line: int
    parent: "XmlNode | None" = None
    children: list["XmlNode"] = field(default_factory=list)
    text: str = ""


def _parse_xml(path: Path) -> XmlNode:
    parser = expat.ParserCreate()
    stack: list[XmlNode] = []
    root_holder: list[XmlNode] = []

    def start(name: str, attrs: dict[str, str]) -> None:
        parent = stack[-1] if stack else None
        node = XmlNode(name, dict(attrs), parser.CurrentLineNumber, parent)
        if parent:
            parent.children.append(node)
        else:
            root_holder.append(node)
        stack.append(node)

    def end(_name: str) -> None:
        stack.pop()

    def chars(value: str) -> None:
        if stack:
            stack[-1].text += value

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = chars
    parser.Parse(path.read_bytes(), True)
    if len(root_holder) != 1:
        raise ValueError(f"{path}: expected one XML root")
    return root_holder[0]


def _iter_nodes(node: XmlNode) -> Iterable[XmlNode]:
    yield node
    for child in node.children:
        yield from _iter_nodes(child)


def _field_nodes(node: XmlNode, name: str) -> list[XmlNode]:
    return [child for child in node.children if child.tag == "field" and child.attrs.get("name") == name]


def _field_values(node: XmlNode, name: str) -> list[str]:
    values: list[str] = []
    for field_node in _field_nodes(node, name):
        value = field_node.attrs.get("ref") or field_node.attrs.get("eval") or field_node.text.strip()
        if value:
            values.append(str(value).strip())
    return values


def _declared_xmlid(module: str, value: str) -> str:
    raw = str(value or "").strip().strip("'\"")
    return raw if "." in raw else f"{module}.{raw}" if raw else ""


def _extract_ref(raw: str, module: str) -> str:
    value = str(raw or "").strip()
    if not value or value.strip("'\" ") in {"False", "false", "None", "null", "0"}:
        return ""
    refs = REF_CALL_RE.findall(value)
    if refs:
        return _declared_xmlid(module, refs[0])
    call_refs = ACTION_CALL_RE.findall(value)
    if call_refs:
        return _declared_xmlid(module, call_refs[0])
    if value.startswith("ir.actions.") and "," in value:
        return value
    return _declared_xmlid(module, value)


def _extract_refs(raw: str, module: str) -> list[str]:
    value = str(raw or "").strip()
    if not value or value.strip("'\" ") in {"False", "false", "None", "null", "0"}:
        return []
    refs = REF_CALL_RE.findall(value)
    refs.extend(ACTION_CALL_RE.findall(value))
    refs.extend(XMLID_RE.findall(value))
    resolved = []
    for ref in refs:
        xmlid = _declared_xmlid(module, ref)
        if xmlid and not xmlid.startswith("ir.actions."):
            resolved.append(xmlid)
    return sorted(set(resolved))


def _raw_values(node: XmlNode, name: str) -> list[str]:
    values = []
    for field_node in _field_nodes(node, name):
        value = field_node.attrs.get("ref") or field_node.attrs.get("eval") or field_node.text.strip()
        if value:
            values.append(str(value).strip())
    return values


def _merge_value(row: dict[str, Any], key: str, value: Any) -> None:
    if value is None or value == "" or value == []:
        return
    row[key] = value


def _line_declaration(path: str, line: int, tag: str, xmlid: str) -> dict[str, Any]:
    return {"path": path, "line": line, "tag": tag, "xmlid": xmlid}


def _literal_constraint_count(node: ast.Assign) -> int:
    try:
        value = ast.literal_eval(node.value)
    except Exception:
        return 0
    return len(value) if isinstance(value, (list, tuple)) else 0


def _field_row(module: str, model: str, file_path: str, node: ast.Assign, name: str, call: ast.Call) -> dict[str, Any]:
    keywords: dict[str, Any] = {}
    for keyword in call.keywords:
        if not keyword.arg:
            continue
        try:
            keywords[keyword.arg] = ast.literal_eval(keyword.value)
        except Exception:
            keywords[keyword.arg] = ast.unparse(keyword.value)
    relation = ""
    if call.args:
        try:
            relation = str(ast.literal_eval(call.args[0]))
        except Exception:
            relation = ast.unparse(call.args[0])
    return {
        "name": name,
        "type": call.func.attr,
        "relation": relation,
        "required": bool(keywords.get("required", False)),
        "readonly": bool(keywords.get("readonly", False)),
        "compute": str(keywords.get("compute") or ""),
        "related": str(keywords.get("related") or ""),
        "store": keywords.get("store"),
        "index": keywords.get("index"),
        "comodel_field": str(keywords.get("comodel_name") or keywords.get("relation") or relation),
        "path": file_path,
        "line": node.lineno,
    }


def _model_declarations(root: Path, modules: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    scanned_files: list[str] = []
    for module in modules:
        module_dir = root / module["directory"]
        for path in sorted(module_dir.rglob("*.py")):
            if "tests" in path.parts or "__pycache__" in path.parts:
                continue
            relative = _relative(root, path)
            scanned_files.append(relative)
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for class_node in ast.walk(tree):
                if not isinstance(class_node, ast.ClassDef):
                    continue
                model_values: dict[str, Any] = {}
                for statement in class_node.body:
                    if not isinstance(statement, ast.Assign):
                        continue
                    for target in statement.targets:
                        if not isinstance(target, ast.Name) or target.id not in {"_name", "_inherit"}:
                            continue
                        try:
                            model_values[target.id] = ast.literal_eval(statement.value)
                        except Exception:
                            pass
                inherits = model_values.get("_inherit") or []
                if isinstance(inherits, str):
                    inherits = [inherits]
                technical_name = model_values.get("_name") or (inherits[0] if len(inherits) == 1 else "")
                if not technical_name:
                    continue
                base_names = [
                    ast.unparse(base).split(".")[-1]
                    for base in class_node.bases
                    if isinstance(base, (ast.Name, ast.Attribute))
                ]
                fields: list[dict[str, Any]] = []
                constraints: list[dict[str, Any]] = []
                onchanges: list[dict[str, Any]] = []
                sql_constraints: list[dict[str, Any]] = []
                methods: list[dict[str, Any]] = []
                for statement in class_node.body:
                    if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
                        target_name = statement.targets[0].id
                        value = statement.value
                        if (
                            isinstance(value, ast.Call)
                            and isinstance(value.func, ast.Attribute)
                            and isinstance(value.func.value, ast.Name)
                            and value.func.value.id == "fields"
                        ):
                            fields.append(_field_row(module["technical_name"], technical_name, relative, statement, target_name, value))
                        if target_name == "_sql_constraints":
                            sql_constraints.append(
                                {
                                    "path": relative,
                                    "line": statement.lineno,
                                    "constraint_count": _literal_constraint_count(statement),
                                }
                            )
                    if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        decorators = [ast.unparse(item) for item in statement.decorator_list]
                        if any(item.startswith("api.constrains") for item in decorators):
                            constraints.append(
                                {
                                    "method": statement.name,
                                    "path": relative,
                                    "line": statement.lineno,
                                    "decorators": decorators,
                                }
                            )
                        if any(item.startswith("api.onchange") for item in decorators):
                            onchanges.append(
                                {
                                    "method": statement.name,
                                    "path": relative,
                                    "line": statement.lineno,
                                    "decorators": decorators,
                                }
                            )
                        if not statement.name.startswith("_"):
                            methods.append(
                                {
                                    "name": statement.name,
                                    "path": relative,
                                    "line": statement.lineno,
                                    "decorators": decorators,
                                }
                            )
                rows.append(
                    {
                        "technical_name": str(technical_name),
                        "module": module["technical_name"],
                        "module_scope": module["scope"],
                        "class_name": class_node.name,
                        "path": relative,
                        "line": class_node.lineno,
                        "kind": "extension" if model_values.get("_name") is None or technical_name in inherits else "new",
                        "inherits": inherits,
                        "abstract": "AbstractModel" in base_names,
                        "transient": "TransientModel" in base_names,
                        "fields": fields,
                        "constraints": constraints,
                        "onchanges": onchanges,
                        "sql_constraints": sql_constraints,
                        "business_methods": methods,
                    }
                )
    return rows, sorted(set(scanned_files))


def _discover_xml(root: Path, modules: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    documents: list[dict[str, Any]] = []
    scanned_files: list[str] = []
    for module in modules:
        module_dir = root / module["directory"]
        for group in ("data", "demo"):
            for rel in module[group]:
                path = module_dir / rel
                if path.suffix != ".xml" or not path.exists():
                    continue
                relative = _relative(root, path)
                scanned_files.append(relative)
                documents.append(
                    {
                        "module": module["technical_name"],
                        "scope": module["scope"],
                        "path": relative,
                        "group": group,
                        "root": _parse_xml(path),
                    }
                )
    return documents, sorted(set(scanned_files))


def _record_rows(documents: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    rows: list[dict[str, Any]] = []
    unkeyed: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for document in documents:
        for node in _iter_nodes(document["root"]):
            if node.tag == "record":
                model = node.attrs.get("model", "")
                ident = node.attrs.get("id", "")
                if not ident:
                    unkeyed.append({"path": document["path"], "line": node.line, "tag": "record", "model": model})
                    continue
                xmlid = _declared_xmlid(document["module"], ident)
                fields = {
                    field_node.attrs["name"]: {
                        "ref": field_node.attrs.get("ref"),
                        "eval": field_node.attrs.get("eval"),
                        "text": field_node.text.strip(),
                        "line": field_node.line,
                        "root_tags": [
                            child.tag
                            for child in _iter_nodes(field_node)
                            if child is not field_node and child.tag in VIEW_TAGS
                        ],
                    }
                    for field_node in node.children
                    if field_node.tag == "field" and field_node.attrs.get("name")
                }
                rows.append(
                    {
                        "xmlid": xmlid,
                        "module": document["module"],
                        "module_scope": document["scope"],
                        "model": model,
                        "path": document["path"],
                        "line": node.line,
                        "fields": fields,
                        "node": node,
                    }
                )
                counts[model] += 1
            elif node.tag == "menuitem":
                ident = node.attrs.get("id", "")
                if not ident:
                    unkeyed.append({"path": document["path"], "line": node.line, "tag": "menuitem", "model": "ir.ui.menu"})
                    continue
                rows.append(
                    {
                        "xmlid": _declared_xmlid(document["module"], ident),
                        "module": document["module"],
                        "module_scope": document["scope"],
                        "model": "ir.ui.menu",
                        "path": document["path"],
                        "line": node.line,
                        "fields": {},
                        "node": node,
                    }
                )
                counts["ir.ui.menu"] += 1
            elif node.tag in {"template", "report"}:
                ident = node.attrs.get("id", "")
                if not ident:
                    unkeyed.append({"path": document["path"], "line": node.line, "tag": node.tag, "model": ""})
                    continue
                model = "ir.ui.view" if node.tag == "template" else "ir.actions.report"
                rows.append(
                    {
                        "xmlid": _declared_xmlid(document["module"], ident),
                        "module": document["module"],
                        "module_scope": document["scope"],
                        "model": model,
                        "path": document["path"],
                        "line": node.line,
                        "fields": {},
                        "node": node,
                    }
                )
                counts[model] += 1
    return rows, unkeyed, dict(counts)


def _non_xml_action_references(
    root: Path,
    modules: list[dict[str, Any]],
    action_ids: set[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for module in modules:
        module_dir = root / module["directory"]
        for path in sorted(module_dir.rglob("*.py")):
            if "tests" in path.parts or "__pycache__" in path.parts:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            parents: dict[ast.AST, ast.AST] = {}
            for parent in ast.walk(tree):
                for child in ast.iter_child_nodes(parent):
                    parents[child] = parent
            for node in ast.walk(tree):
                if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                    continue
                refs = set(_extract_refs(node.value, module["technical_name"]))
                if not refs:
                    continue
                owner = node
                owner_name = ""
                while owner in parents:
                    owner = parents[owner]
                    if isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        owner_name = owner.name
                        break
                for ref in sorted(refs & action_ids):
                    rows.append(
                        {
                            "action_xmlid": ref,
                            "kind": "python_reference",
                            "owner_xmlid": "",
                            "owner_model": "",
                            "owner": owner_name,
                            "path": _relative(root, path),
                            "line": node.lineno,
                            "tag": "string",
                            "raw": node.value.strip(),
                        }
                    )
        for group in ("data", "demo"):
            for rel in module[group]:
                path = module_dir / rel
                if not path.is_file() or path.suffix not in {".json", ".csv", ".yaml", ".yml", ".txt"}:
                    continue
                for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    for ref in sorted(set(_extract_refs(line, module["technical_name"])) & action_ids):
                        rows.append(
                            {
                                "action_xmlid": ref,
                                "kind": "data_reference",
                                "owner_xmlid": "",
                                "owner_model": "",
                                "owner": "",
                                "path": _relative(root, path),
                                "line": line_number,
                                "tag": path.suffix.lstrip("."),
                                "raw": line.strip()[:500],
                            }
                        )
    return rows


def _actions_and_menus(
    root: Path,
    modules: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    action_rows: dict[str, dict[str, Any]] = {}
    menu_rows: dict[str, dict[str, Any]] = {}
    bindings: dict[str, dict[str, Any]] = {}
    for row in rows:
        model = row["model"]
        xmlid = row["xmlid"]
        node = row["node"]
        declaration = _line_declaration(row["path"], row["line"], node.tag, xmlid)
        if model in ACTION_MODELS:
            action = action_rows.setdefault(
                xmlid,
                {
                    "xmlid": xmlid,
                    "module": row["module"],
                    "module_scope": row["module_scope"],
                    "action_type": model,
                    "source_declarations": [],
                    "fields": {},
                    "references": [],
                },
            )
            action["source_declarations"].append(declaration)
            for key, values in row["fields"].items():
                _merge_value(action["fields"], key, values)
            if model == "ir.actions.act_window":
                raw_mode = action["fields"].get("view_mode")
                if isinstance(raw_mode, dict):
                    raw_mode = raw_mode.get("eval") or raw_mode.get("text") or ""
                action["view_modes"] = [item.strip("'\" ") for item in str(raw_mode or "").split(",") if item.strip("'\" ")]
        elif model == "ir.actions.act_window.view":
            bindings[xmlid] = {
                "xmlid": xmlid,
                "module": row["module"],
                "source_declarations": [declaration],
                "fields": row["fields"],
            }
        elif model == "ir.ui.menu":
            menu = menu_rows.setdefault(
                xmlid,
                {
                    "xmlid": xmlid,
                    "module": row["module"],
                    "module_scope": row["module_scope"],
                    "name": "",
                    "parent_xmlid": "",
                    "action_xmlid": "",
                    "action_raw": "",
                    "action_type": "",
                    "groups": [],
                    "sequence": None,
                    "active": True,
                    "source_declarations": [],
                    "other_entry_references": [],
                },
            )
            menu["source_declarations"].append(declaration)
            if node.tag == "menuitem":
                _merge_value(menu, "name", node.attrs.get("name", ""))
                raw_parent = node.attrs.get("parent", "")
                raw_action = node.attrs.get("action", "")
                raw_groups = node.attrs.get("groups", "")
                _merge_value(menu, "parent_xmlid", _extract_ref(raw_parent, row["module"]))
                _merge_value(menu, "action_xmlid", _extract_ref(raw_action, row["module"]))
                _merge_value(menu, "action_raw", raw_action)
                if raw_groups:
                    menu["groups"] = sorted(set(item.strip() for item in raw_groups.split(",") if item.strip()))
                if node.attrs.get("sequence"):
                    try:
                        menu["sequence"] = int(node.attrs["sequence"])
                    except ValueError:
                        pass
                if node.attrs.get("active") in {"0", "False", "false"}:
                    menu["active"] = False
            else:
                values = row["fields"]
                _merge_value(menu, "name", values.get("name", {}).get("text", ""))
                raw_parent = values.get("parent_id", {}).get("ref") or values.get("parent_id", {}).get("eval") or ""
                raw_action = values.get("action", {}).get("ref") or values.get("action", {}).get("eval") or ""
                raw_groups = values.get("groups_id", {}).get("eval") or values.get("groups_id", {}).get("ref") or ""
                _merge_value(menu, "parent_xmlid", _extract_ref(raw_parent, row["module"]))
                _merge_value(menu, "action_xmlid", _extract_ref(raw_action, row["module"]))
                _merge_value(menu, "action_raw", raw_action)
                if raw_groups:
                    menu["groups"] = _extract_refs(raw_groups, row["module"])
                sequence_raw = values.get("sequence", {}).get("eval") or values.get("sequence", {}).get("text") or ""
                try:
                    menu["sequence"] = int(str(sequence_raw).strip("'\" "))
                except ValueError:
                    pass
                active_raw = values.get("active", {}).get("eval") or values.get("active", {}).get("text") or ""
                if str(active_raw).strip("'\" ") in {"0", "False", "false"}:
                    menu["active"] = False

    actions_by_id = set(action_rows)
    for action_id, action in action_rows.items():
        action["fields"] = {
            key: (value.get("ref") or value.get("eval") or value.get("text"))
            for key, value in action["fields"].items()
        }
        if action["action_type"] == "ir.actions.act_window":
            raw_mode = str(action["fields"].get("view_mode") or "")
            action["view_modes"] = [item.strip("'\" ") for item in raw_mode.split(",") if item.strip("'\" ")]
    for menu in menu_rows.values():
        action = action_rows.get(menu["action_xmlid"])
        if action:
            menu["action_type"] = action["action_type"]

    # References are derived from declaration values, not from runtime callers.
    reference_rows: list[dict[str, Any]] = []
    for row in rows:
        owner = row
        for node in _iter_nodes(row["node"]):
            raw_values = list(node.attrs.values())
            if node.text.strip():
                raw_values.append(node.text.strip())
            refs: set[str] = set()
            for raw in raw_values:
                refs.update(_extract_refs(raw, row["module"]))
            if not refs:
                continue
            for ref in refs:
                if ref not in actions_by_id:
                    continue
                kind = "menu" if owner["model"] == "ir.ui.menu" else "action_button" if node.tag == "button" and node.attrs.get("type") in {"action", "server", "server_action"} else "view" if owner["model"] == "ir.ui.view" else "other"
                reference_rows.append(
                    {
                        "action_xmlid": ref,
                        "kind": kind,
                        "owner_xmlid": owner["xmlid"],
                        "owner_model": owner["model"],
                        "path": row["path"],
                        "line": node.line,
                        "tag": node.tag,
                        "raw": " | ".join(raw_values),
                    }
                )
    reference_rows.extend(_non_xml_action_references(root, modules, actions_by_id))
    by_action: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for reference in reference_rows:
        by_action[reference["action_xmlid"]].append(reference)
    for action_id, references in by_action.items():
        action_rows[action_id]["references"] = sorted(
            references,
            key=lambda item: (item["path"], item["line"], item["kind"], item["owner_xmlid"]),
        )
    for menu in menu_rows.values():
        menu["other_entry_references"] = [
            reference
            for reference in action_rows.get(menu["action_xmlid"], {}).get("references", [])
            if reference["kind"] != "menu"
        ]
        menu["action_type"] = action_rows.get(menu["action_xmlid"], {}).get("action_type", "")

    known_ids = set(menu_rows)
    children: dict[str, list[str]] = defaultdict(list)
    for menu in menu_rows.values():
        if menu["parent_xmlid"]:
            children[menu["parent_xmlid"]].append(menu["xmlid"])
    for menu in menu_rows.values():
        child_ids = sorted(children.get(menu["xmlid"], []))
        menu["children"] = child_ids
        menu["is_container"] = bool(child_ids)
        menu["is_leaf"] = not child_ids

    return (
        sorted(action_rows.values(), key=lambda row: row["xmlid"]),
        sorted(menu_rows.values(), key=lambda row: row["xmlid"]),
        sorted(bindings.values(), key=lambda row: row["xmlid"]),
    )


def _view_inventory(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    views: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row["model"] != "ir.ui.view":
            continue
        node = row["node"]
        values = row["fields"]
        declaration = _line_declaration(row["path"], row["line"], node.tag, row["xmlid"])
        view = views.setdefault(
            row["xmlid"],
            {
                "xmlid": row["xmlid"],
                "module": row["module"],
                "module_scope": row["module_scope"],
                "model": "",
                "declared_type": "",
                "resolved_type": "",
                "inherit_id": "",
                "priority": None,
                "groups": [],
                "root_tags": [],
                "js_class": "",
                "widgets": [],
                "source_declarations": [],
            },
        )
        view["source_declarations"].append(declaration)
        for item in _iter_nodes(node):
            if item.tag != "field" or not item.attrs.get("name"):
                continue
            widget = item.attrs.get("widget")
            if not widget:
                widget_nodes = [child for child in item.children if child.tag == "widget"]
                widget = widget_nodes[0].attrs.get("name", "") if widget_nodes else ""
            if widget:
                view["widgets"].append(
                    {"name": item.attrs["name"], "widget": widget, "path": row["path"], "line": item.line}
                )
        if node.tag == "template":
            view["declared_type"] = "qweb"
            view["resolved_type"] = "qweb"
            continue
        for field_name in ("model", "type", "inherit_id", "groups_id"):
            value = values.get(field_name, {})
            raw = value.get("ref") or value.get("eval") or value.get("text") or ""
            if field_name == "groups_id" and raw:
                view["groups"] = _extract_refs(raw, row["module"])
            elif field_name == "inherit_id" and raw:
                view["inherit_id"] = _extract_ref(raw, row["module"])
            elif field_name == "type" and raw:
                view["declared_type"] = str(raw).strip("'\" ")
            elif field_name == "model" and raw:
                view["model"] = str(raw).strip("'\" ")
        priority = values.get("priority", {})
        raw_priority = priority.get("eval") or priority.get("text") or ""
        try:
            view["priority"] = int(str(raw_priority).strip("'\" "))
        except ValueError:
            pass
        arch_nodes = [
            child
            for child in node.children
            if child.tag == "field" and child.attrs.get("name") == "arch"
        ]
        view["root_tags"] = sorted(
            {
                item.tag
                for arch in arch_nodes
                for item in _iter_nodes(arch)
                if item is not arch and item.tag in VIEW_TAGS
            }
        )
        for arch in arch_nodes:
            for item in _iter_nodes(arch):
                if item.attrs.get("js_class"):
                    view["js_class"] = item.attrs["js_class"]
        if not view["declared_type"] and view["root_tags"]:
            view["declared_type"] = view["root_tags"][0]

    def resolve(view: dict[str, Any], seen: set[str] | None = None) -> str:
        if view["declared_type"]:
            return view["declared_type"]
        if not view["inherit_id"]:
            return ""
        seen = set(seen or ())
        if view["xmlid"] in seen:
            return ""
        seen.add(view["xmlid"])
        parent = views.get(view["inherit_id"])
        return resolve(parent, seen) if parent else ""

    for view in views.values():
        view["resolved_type"] = resolve(view)
        view["inherited"] = bool(view["inherit_id"])
        view["external_parent_unresolved"] = bool(view["inherit_id"] and not view["resolved_type"])
        view["widgets"] = sorted(view["widgets"], key=lambda item: (item["path"], item["line"], item["name"], item["widget"]))
        view["source_declarations"] = sorted(view["source_declarations"], key=lambda item: (item["path"], item["line"]))
    return sorted(views.values(), key=lambda row: row["xmlid"])


def _dynamic_actions(root: Path, modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for module in modules:
        module_dir = root / module["directory"]
        for path in sorted(module_dir.rglob("*.py")):
            if "tests" in path.parts or "__pycache__" in path.parts:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            parents: dict[ast.AST, ast.AST] = {}
            for parent in ast.walk(tree):
                for child in ast.iter_child_nodes(parent):
                    parents[child] = parent
            for node in ast.walk(tree):
                if not isinstance(node, ast.Dict):
                    continue
                values: dict[str, Any] = {}
                for key, value in zip(node.keys, node.values):
                    if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                        continue
                    try:
                        values[key.value] = ast.literal_eval(value)
                    except Exception:
                        values[key.value] = ast.unparse(value)
                action_type = values.get("type")
                if not isinstance(action_type, str) or not action_type.startswith("ir.actions."):
                    continue
                owner = node
                owner_name = ""
                while owner in parents:
                    owner = parents[owner]
                    if isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        owner_name = owner.name
                        break
                rows.append(
                    {
                        "action_type": action_type,
                        "module": module["technical_name"],
                        "module_scope": module["scope"],
                        "path": _relative(root, path),
                        "line": node.lineno,
                        "source_method": owner_name,
                        "name": values.get("name", ""),
                        "res_model": values.get("res_model", ""),
                        "view_mode": values.get("view_mode", ""),
                        "tag": values.get("tag", ""),
                        "url": values.get("url", ""),
                    }
                )
    return sorted(rows, key=lambda row: (row["path"], row["line"], row["action_type"]))


def _input_fingerprint(root: Path, files: list[str]) -> str:
    digest = hashlib.sha256()
    for item in sorted(set(files)):
        path = root / item
        digest.update(item.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n"))
        digest.update(b"\0")
    return digest.hexdigest()


def _runtime_evidence(root: Path) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "registry_snapshot": None,
        "current_native_log": None,
    }
    raw = root / RAW_REGISTRY.relative_to(ROOT)
    if raw.is_file():
        payload = json.loads(raw.read_text(encoding="utf-8"))
        evidence["registry_snapshot"] = {
            "path": _relative(root, raw),
            "sha256": _sha256_file(raw),
            "schema": payload.get("schema"),
            "generated_at": payload.get("generated_at"),
            "identity": payload.get("identity"),
            "summary": {
                "menu_count": payload.get("native_capability_facts", {}).get("all", {}).get("menu_count"),
                "action_counts": payload.get("native_capability_facts", {}).get("action_registry", {}).get("all_record_counts"),
            },
        }
    current_log = root / CURRENT_NATIVE_LOG.relative_to(ROOT)
    if current_log.is_file():
        evidence["current_native_log"] = {
            "path": _relative(root, current_log),
            "sha256": _sha256_file(current_log),
        }
    return evidence


def build_inventory(
    root: Path,
    *,
    source_revision: str,
    source_tree: str,
    source_commit_time: str,
    dirty_paths: list[str],
    output_dir: Path,
) -> dict[str, Any]:
    manifest_paths = sorted(path for pattern in MANIFEST_GLOBS for path in root.glob(pattern))
    modules = []
    for path in manifest_paths:
        value = _manifest(path)
        modules.append(
            {
                "technical_name": path.parent.name,
                "name": value.get("name", path.parent.name),
                "version": value.get("version", ""),
                "depends": value.get("depends", []),
                "scope": _module_scope(path.parent.name),
                "directory": _relative(root, path.parent),
                "data": list(value.get("data", [])),
                "demo": list(value.get("demo", [])),
                "manifest_path": _relative(root, path),
            }
        )
    models, model_files = _model_declarations(root, modules)
    documents, xml_files = _discover_xml(root, modules)
    records, unkeyed, record_counts = _record_rows(documents)
    actions, menus, view_bindings = _actions_and_menus(root, modules, records)
    views = _view_inventory(records)
    dynamic_actions = _dynamic_actions(root, modules)

    model_summary = {
        "class_declarations": len(models),
        "distinct_models": len({row["technical_name"] for row in models}),
        "field_declarations": sum(len(row["fields"]) for row in models),
        "relation_declarations": sum(
            len([field for field in row["fields"] if field["type"] in RELATIONAL_TYPES])
            for row in models
        ),
        "computed_fields": sum(len([field for field in row["fields"] if field["compute"]]) for row in models),
        "related_fields": sum(len([field for field in row["fields"] if field["related"]]) for row in models),
        "constraint_methods": sum(len(row["constraints"]) for row in models),
        "onchange_methods": sum(len(row["onchanges"]) for row in models),
        "sql_constraint_declarations": sum(len(row["sql_constraints"]) for row in models),
        "sql_constraint_entries": sum(
            entry["constraint_count"] for row in models for entry in row["sql_constraints"]
        ),
        "transient_models": len({row["technical_name"] for row in models if row["transient"]}),
        "abstract_models": len({row["technical_name"] for row in models if row["abstract"]}),
        "abstract_declarations": sum(row["abstract"] for row in models),
        "transient_declarations": sum(row["transient"] for row in models),
        "extension_declarations": sum(row["kind"] == "extension" for row in models),
        "extension_model_identities": len({row["technical_name"] for row in models if row["kind"] == "extension"}),
    }
    menu_summary = {
        "declarations": sum(record_counts.get(model, 0) for model in ("ir.ui.menu",)),
        "unique_menu_xmlids": len(menus),
        "with_action": sum(bool(row["action_xmlid"]) for row in menus),
        "without_action": sum(not row["action_xmlid"] for row in menus),
        "containers": sum(row["is_container"] for row in menus),
        "actionless_containers": sum(row["is_container"] and not row["action_xmlid"] for row in menus),
        "actionless_leaves": sum(row["is_leaf"] and not row["action_xmlid"] for row in menus),
        "with_parent": sum(bool(row["parent_xmlid"]) for row in menus),
        "with_groups": sum(bool(row["groups"]) for row in menus),
        "with_non_menu_action_references": sum(bool(row["other_entry_references"]) for row in menus),
    }
    action_summary = {
        "declarations": sum(record_counts.get(model, 0) for model in ACTION_MODELS),
        "unique_action_xmlids": len(actions),
        "by_type": dict(sorted(Counter(row["action_type"] for row in actions).items())),
        "view_binding_xmlids": len(view_bindings),
        "dynamic_action_declarations": len(dynamic_actions),
        "dynamic_by_type": dict(sorted(Counter(row["action_type"] for row in dynamic_actions).items())),
        "with_menu_reference": sum(
            any(reference["kind"] == "menu" for reference in row["references"]) for row in actions
        ),
        "with_non_menu_reference": sum(
            any(reference["kind"] != "menu" for reference in row["references"]) for row in actions
        ),
        "without_static_xml_reference": sum(not row["references"] for row in actions),
    }
    view_summary = {
        "declarations": sum(record_counts.get("ir.ui.view", 0) for _ in (0,)),
        "unique_view_xmlids": len(views),
        "by_resolved_type": dict(sorted(Counter(row["resolved_type"] or "external_parent_unresolved" for row in views).items())),
        "inherited": sum(row["inherited"] for row in views),
        "external_parent_unresolved": sum(row["external_parent_unresolved"] for row in views),
        "with_js_class": sum(bool(row["js_class"]) for row in views),
        "widget_declarations": sum(len(row["widgets"]) for row in views),
        "unique_widgets": sorted({item["widget"] for row in views for item in row["widgets"]}),
    }

    common = {
        "source_revision": source_revision,
        "source_tree": source_tree,
        "modules": [row["technical_name"] for row in modules],
    }
    outputs = {
        "native_model_inventory.json": {
            "schema": "native_scene.model_inventory.v1",
            "scope": common,
            "summary": model_summary,
            "modules": modules,
            "models": models,
        },
        "native_menu_inventory.json": {
            "schema": "native_scene.menu_inventory.v1",
            "scope": common,
            "summary": menu_summary,
            "menus": menus,
        },
        "native_action_inventory.json": {
            "schema": "native_scene.action_inventory.v1",
            "scope": common,
            "summary": action_summary,
            "actions": actions,
            "view_bindings": view_bindings,
            "dynamic_actions": dynamic_actions,
            "unkeyed_declarations": unkeyed,
        },
        "native_view_inventory.json": {
            "schema": "native_scene.view_inventory.v1",
            "scope": common,
            "summary": view_summary,
            "views": views,
        },
    }
    serialized = {name: _json(payload) for name, payload in outputs.items()}
    tool_path = Path(__file__).resolve()
    tool_input = _relative(root, tool_path) if tool_path.is_relative_to(root) else ""
    inputs = [
        *model_files,
        *xml_files,
        *[row["manifest_path"] for row in modules],
        tool_input,
        *[
            _relative(root, root / module["directory"] / rel)
            for module in modules
            for group in ("data", "demo")
            for rel in module[group]
            if (root / module["directory"] / rel).is_file()
            and (root / module["directory"] / rel).suffix in {".json", ".csv", ".yaml", ".yml", ".txt"}
        ],
        _relative(root, ROOT / RAW_REGISTRY.relative_to(ROOT)) if (root / RAW_REGISTRY.relative_to(ROOT)).is_file() else "",
        _relative(root, ROOT / CURRENT_NATIVE_LOG.relative_to(ROOT)) if (root / CURRENT_NATIVE_LOG.relative_to(ROOT)).is_file() else "",
    ]
    inputs = sorted({item for item in inputs if item})
    relevant_dirty_paths = sorted(set(dirty_paths) & set(inputs))
    manifest = {
        "schema": "native_scene.inventory_manifest.v1",
        "source": {
            "root": ".",
            "revision": source_revision,
            "tree": source_tree,
            "commit_time": source_commit_time,
            "dirty_paths": relevant_dirty_paths,
        },
        "scope": {
            "modules": [row["technical_name"] for row in modules],
            "manifest_globs": list(MANIFEST_GLOBS),
            "xml_loading": "manifest data and demo files only",
            "python_loading": "all non-tests Python files under each module",
            "claims": [
                "source declaration identity",
                "static source reference topology",
                "explicitly not runtime installed state",
                "explicitly not effective inherited View merging",
                "explicitly not ACL/record-rule/browser delivery",
            ],
        },
        "command": {
            "write": "python3 scripts/audit/native_scene_inventory.py",
            "check": "python3 scripts/audit/native_scene_inventory.py --check",
            "test": "python3 -m unittest scripts.audit.test_native_scene_inventory",
        },
        "inputs": {
            "file_count": len(inputs),
            "sha256": _input_fingerprint(root, inputs),
            "files": inputs,
        },
        "tool": {
            "path": "scripts/audit/native_scene_inventory.py",
            "sha256": _sha256_file(tool_path),
        },
        "statistics": {
            "models": model_summary,
            "menus": menu_summary,
            "actions": action_summary,
            "views": view_summary,
            "record_declaration_counts": dict(sorted(record_counts.items())),
        },
        "runtime_evidence": _runtime_evidence(root),
        "outputs": {
            name: {
                "path": f"docs/audit/native-scene-01/inventories/{name}",
                "sha256": _sha256_bytes(content.encode("utf-8")),
                "primary_row_count": (
                    len(outputs[name]["models"])
                    if "models" in outputs[name]
                    else len(outputs[name]["menus"])
                    if "menus" in outputs[name]
                    else len(outputs[name]["actions"])
                    if "actions" in outputs[name]
                    else len(outputs[name]["views"])
                ),
            }
            for name, content in serialized.items()
        },
        "limitations": [
            "Source declarations are not proof that a module is installed or that a View is effective.",
            "Static XMLID references do not prove actor-specific runtime reachability.",
            "Runtime model/action/menu totals come only from the hashed external evidence file.",
            "Dynamic Python Action dictionaries have no stable XMLID and remain context actions.",
        ],
    }
    serialized["inventory_manifest.json"] = _json(manifest)
    return {
        "payloads": outputs,
        "manifest": manifest,
        "serialized": serialized,
        "output_dir": output_dir,
    }


def _git_context(root: Path, source_revision: str | None = None) -> tuple[str, str, str, list[str]]:
    try:
        revision = source_revision or _git(root, "rev-parse", "HEAD")
        tree = _git(root, "rev-parse", f"{revision}^{{tree}}")
        commit_time = _git(root, "show", "-s", "--format=%cI", revision)
        status = _git(root, "status", "--porcelain=v2", "--untracked-files=all")
    except (subprocess.CalledProcessError, FileNotFoundError):
        if source_revision:
            return source_revision, "", "", []
        raise
    dirty_paths = []
    for line in status.splitlines():
        fields = line.split()
        if fields:
            dirty_paths.append(fields[-1])
    return revision, tree, commit_time, dirty_paths


def _filtered_dirty_paths(root: Path, output_dir: Path, dirty_paths: list[str]) -> list[str]:
    output_rel = _relative(root, output_dir)
    return sorted(
        path
        for path in dirty_paths
        if not path.startswith(f"{output_rel}/")
        and path != output_rel
    )


def write_outputs(root: Path, output_dir: Path, source_revision: str | None = None) -> dict[str, Any]:
    revision, tree, commit_time, dirty = _git_context(root, source_revision)
    built = build_inventory(
        root,
        source_revision=revision,
        source_tree=tree,
        source_commit_time=commit_time,
        dirty_paths=_filtered_dirty_paths(root, output_dir, dirty),
        output_dir=output_dir,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in built["serialized"].items():
        (output_dir / name).write_text(content, encoding="utf-8")
    return built


def check_outputs(root: Path, output_dir: Path) -> list[str]:
    manifest_path = output_dir / "inventory_manifest.json"
    if not manifest_path.is_file():
        return [f"missing {_relative(root, manifest_path)}"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = manifest.get("source", {})
    built = build_inventory(
        root,
        source_revision=source.get("revision", ""),
        source_tree=source.get("tree", ""),
        source_commit_time=source.get("commit_time", ""),
        dirty_paths=_filtered_dirty_paths(
            root,
            output_dir,
            _git_context(root, source.get("revision"))[3],
        ),
        output_dir=output_dir,
    )
    errors = []
    for name, content in built["serialized"].items():
        path = output_dir / name
        if not path.is_file():
            errors.append(f"missing {_relative(root, path)}")
        elif path.read_text(encoding="utf-8") != content:
            errors.append(f"stale {_relative(root, path)}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--source-revision")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    if args.check:
        errors = check_outputs(root, output_dir)
        if errors:
            print("[FAIL] native_scene_inventory")
            for error in errors:
                print(f"- {error}")
            return 1
        print("[OK] native_scene_inventory --check")
        return 0
    built = write_outputs(root, output_dir, args.source_revision)
    print(
        json.dumps(
            {
                "status": "written",
                "output_dir": _relative(root, output_dir),
                "source_revision": built["manifest"]["source"]["revision"],
                "inputs_sha256": built["manifest"]["inputs"]["sha256"],
                "statistics": {
                    "models": built["payloads"]["native_model_inventory.json"]["summary"],
                    "menus": built["payloads"]["native_menu_inventory.json"]["summary"],
                    "actions": built["payloads"]["native_action_inventory.json"]["summary"],
                    "views": built["payloads"]["native_view_inventory.json"]["summary"],
                },
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
