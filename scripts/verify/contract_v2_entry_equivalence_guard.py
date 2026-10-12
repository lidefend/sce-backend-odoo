#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The action entry and the model entry must project the same business facts.

`ui.contract.v2` is addressed two ways, and both are real product paths:

* ``loadActionContractV2(actionId)`` — ``op=action_open``.  Menus and windows
  enter here, because only an ``ir.actions.act_window`` carries the domain,
  context, target, menu and ``view_mode`` binding.
* ``loadModelContractV2(model)`` — ``op=model``.  Relationship drill-down and
  action-less record pages enter here, because those paths have no action to
  bind to.

They are not two systems: both are adapters onto one projection core.  What they
*may* differ in is entry fact — action binding, view resolution, requested
``view_type``.  What they may *never* differ in is the business fact:

    same model + same role + same client_type
        => identical head.permissions
        => identical surface_policies.collection_capabilities

A second permission resolver behind one of the entries would produce "the action
page edits, the model page is read-only" with no contract declaring it, and the
frontend would be forced to compensate per entry — business judgement returning
to the renderer.  This guard locks the mechanism that makes the equality
structural rather than accidental:

* one fetch authority and one decode authority in the frontend contract client,
  reached by both loaders;
* one entry branch in the backend, mapping both entry kinds onto one dispatcher;
* the permission fact resolver takes no entry identity at all, so an
  entry-dependent reading is not expressible;
* the collection-capability rule takes only facts (declared actions, effective
  rights, field map, list-view presence), so a per-model or per-entry special
  case is not expressible either.

It deliberately does NOT compare layout, action binding, navigation or domain:
those are entry facts and are allowed to differ.  The runtime parity of
``head.permissions`` / ``collection_capabilities`` across every tree action in
``sc_dev_demo`` (292 probed, 0 violations) is the census evidence; this guard
makes the structural claim falsifiable without a runtime.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLIENT_TS = ROOT / "frontend/apps/web/src/app/contracts/v2/client.ts"
HANDLER_PY = ROOT / "addons/smart_core/handlers/ui_contract_v2.py"
ASSEMBLER_PY = ROOT / "addons/smart_core/core/unified_page_contract_v2_assembler.py"
PERMISSIONS_PY = ROOT / "addons/smart_core/core/unified_page_contract_v2_permissions.py"
CAPABILITY_PY = ROOT / "addons/smart_core/utils/collection_action_capability.py"
PERMISSIONS_MODULE = "unified_page_contract_v2_permissions"

ACTION_LOADER = "loadActionContractV2"
MODEL_LOADER = "loadModelContractV2"
SHARED_LOADER = "loadContractV2"
SINGLE_FETCH = "intentRequestRaw"
SINGLE_DECODE = "decodeContractV2Snapshot"
ENTRY_BRANCH_FN = "_dispatch_native_form_source"
ENTRY_DISPATCHER = "ActionDispatcher"
PERMISSION_FN = "_ui_contract_permission_rights"
PERMISSION_RESOLVER = "resolve_permission_rights"
CAPABILITY_FN = "build_collection_capabilities"

# Identity that would let a projection branch per entry kind.  None of these may
# reach the permission fact resolver or the capability rule.
FORBIDDEN_ENTRY_IDENTIFIERS = frozenset(
    {
        "op",
        "subject",
        "action_id",
        "actionId",
        "menu_id",
        "menuId",
        "entry",
        "entry_kind",
        "entry_source",
        "surface",
        "contract_surface",
        "view_id",
        "viewId",
        "client_type",
        "clientType",
    }
)

CARRIER_RIGHTS = {"read": True, "write": True, "create": True, "unlink": True}
CARRIER_FIELDS = {"id": {}, "name": {"readonly": False}, "note": {"readonly": False}}


def _read(path: Path, errors: list[str]) -> str:
    if not path.is_file():
        errors.append(f"missing file: {path.relative_to(ROOT).as_posix()}")
        return ""
    return path.read_text(encoding="utf-8")


def _ts_function_body(source: str, name: str) -> str:
    """Return the brace-balanced body of a top-level ``function name(...)``.

    The parameter list is skipped first: a default such as ``options = {}``
    contains braces, so searching for the first ``{`` after the name would return
    an empty body for exactly the loaders this guard has to read.
    """
    marker = f"function {name}("
    start = source.find(marker)
    if start < 0:
        return ""
    open_paren = source.find("(", start)
    if open_paren < 0:
        return ""
    depth = 0
    index = open_paren
    while index < len(source):
        char = source[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                break
        index += 1
    brace = source.find("{", index)
    if brace < 0:
        return ""
    depth = 0
    for index in range(brace, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1 : index]
    return ""


def _module_tree(source: str, label: str, errors: list[str]) -> ast.Module | None:
    try:
        return ast.parse(source)
    except SyntaxError as exc:  # a mutation that breaks syntax is a failure too
        errors.append(f"{label}: unparsable python source ({exc.msg} at line {exc.lineno})")
        return None


def _function_arg_names(fn: ast.FunctionDef) -> list[str]:
    """Positional and keyword-only parameter names, in declaration order."""
    args = fn.args
    return [arg.arg for arg in (*getattr(args, "posonlyargs", []), *args.args, *args.kwonlyargs)]


def _function_def(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _identifiers(node: ast.AST) -> list[str]:
    """Every name an expression could branch on: identifiers and string keys."""
    names: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.append(child.id)
        elif isinstance(child, ast.Attribute):
            names.append(child.attr)
        elif isinstance(child, ast.keyword) and child.arg:
            names.append(child.arg)
        elif isinstance(child, ast.Subscript) and isinstance(child.slice, ast.Constant):
            if isinstance(child.slice.value, str):
                names.append(child.slice.value)
    return names


def _forbidden_hits(node: ast.AST) -> list[str]:
    return sorted({name for name in _identifiers(node) if name in FORBIDDEN_ENTRY_IDENTIFIERS})


def _check_frontend(source: str, errors: list[str]) -> None:
    label = CLIENT_TS.name
    fetch_sites = source.count(f"{SINGLE_FETCH}<")
    decode_sites = source.count(f"{SINGLE_DECODE}(")
    if fetch_sites != 1:
        errors.append(
            f"{label}: the contract must have exactly one fetch authority "
            f"(`{SINGLE_FETCH}<` found {fetch_sites} times); a second fetch path lets one entry read a different fact"
        )
    if decode_sites != 1:
        errors.append(
            f"{label}: the contract must have exactly one decode authority "
            f"(`{SINGLE_DECODE}(` found {decode_sites} times); a second decoder can read permissions differently per entry"
        )
    shared = _ts_function_body(source, SHARED_LOADER)
    if not shared:
        errors.append(f"{label}: {SHARED_LOADER} not found")
    else:
        for required in (SINGLE_FETCH, SINGLE_DECODE):
            if required not in shared:
                errors.append(f"{label}: {SHARED_LOADER} must own the {required} step")
    for name in (ACTION_LOADER, MODEL_LOADER):
        body = _ts_function_body(source, name)
        if not body:
            errors.append(f"{label}: {name} not found")
            continue
        if f"{SHARED_LOADER}(" not in body:
            errors.append(f"{label}: {name} must reach the contract only through {SHARED_LOADER}")
        for forbidden in (SINGLE_FETCH, SINGLE_DECODE):
            if forbidden in body:
                errors.append(f"{label}: {name} must not own a private {forbidden} path")


def _check_backend_entry_branch(tree: ast.Module, label: str, errors: list[str]) -> None:
    defs = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == ENTRY_BRANCH_FN
    ]
    if len(defs) != 1:
        errors.append(f"{label}: expected exactly one {ENTRY_BRANCH_FN} definition, found {len(defs)}")
        return
    fn = defs[0]
    module_dispatchers = [
        node for node in ast.walk(tree) if isinstance(node, ast.Call) and _call_name(node) == ENTRY_DISPATCHER
    ]
    if len(module_dispatchers) != 1:
        errors.append(
            f"{label}: the native form source must construct exactly one {ENTRY_DISPATCHER} "
            f"(found {len(module_dispatchers)}); a second dispatcher is a second projection core"
        )
    dispatch_calls = [
        node
        for node in ast.walk(fn)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "dispatch"
    ]
    if len(dispatch_calls) != 1:
        errors.append(
            f"{label}: {ENTRY_BRANCH_FN} must dispatch exactly once (found {len(dispatch_calls)})"
        )
    subject_values: list[str] = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Assign) or not node.targets:
            continue
        target = node.targets[0]
        if (
            isinstance(target, ast.Subscript)
            and isinstance(target.slice, ast.Constant)
            and target.slice.value == "subject"
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            subject_values.append(node.value.value)
    if sorted(subject_values) != ["action", "model"]:
        errors.append(
            f"{label}: {ENTRY_BRANCH_FN} must map both entry kinds onto the one dispatcher "
            f"(expected subject values [action, model], found {sorted(subject_values)})"
        )
    call_sites = [
        node for node in ast.walk(tree) if isinstance(node, ast.Call) and _call_name(node) == ENTRY_BRANCH_FN
    ]
    if len(call_sites) != 1:
        errors.append(
            f"{label}: {ENTRY_BRANCH_FN} must have exactly one call site (found {len(call_sites)}); "
            "an entry that bypasses it reads the page body from a different source"
        )


def _check_permission_facts(
    assembler_tree: ast.Module | None,
    permissions_tree: ast.Module | None,
    errors: list[str],
) -> None:
    label = ASSEMBLER_PY.name
    if assembler_tree is not None:
        imported = [
            alias.name
            for node in ast.walk(assembler_tree)
            if isinstance(node, ast.ImportFrom) and node.module == PERMISSIONS_MODULE
            for alias in node.names
        ]
        if PERMISSION_RESOLVER not in imported:
            errors.append(
                f"{label}: the permission fact must be resolved by {PERMISSIONS_MODULE}.{PERMISSION_RESOLVER}"
            )
        fn = _function_def(assembler_tree, PERMISSION_FN)
        if fn is None:
            errors.append(f"{label}: {PERMISSION_FN} not found")
        else:
            args = _function_arg_names(fn)
            if args != ["source", "ui"]:
                errors.append(
                    f"{label}: {PERMISSION_FN} must take only the contract payload "
                    f"(expected ['source', 'ui'], found {args}); an entry argument makes an entry-dependent reading expressible"
                )
            hits = _forbidden_hits(fn)
            if hits:
                errors.append(
                    f"{label}: {PERMISSION_FN} must not consult entry identity (found {hits})"
                )
    if permissions_tree is not None:
        label = PERMISSIONS_PY.name
        fn = _function_def(permissions_tree, PERMISSION_RESOLVER)
        if fn is None:
            errors.append(f"{label}: {PERMISSION_RESOLVER} not found")
        else:
            args = _function_arg_names(fn)
            if args != ["permission_contract"]:
                errors.append(
                    f"{label}: {PERMISSION_RESOLVER} must take only the permission envelope "
                    f"(expected ['permission_contract'], found {args})"
                )
            hits = _forbidden_hits(fn)
            if hits:
                errors.append(f"{label}: {PERMISSION_RESOLVER} must not consult entry identity (found {hits})")


def _check_capability_rule(tree: ast.Module | None, errors: list[str]) -> None:
    label = CAPABILITY_PY.name
    if tree is None:
        return
    fn = _function_def(tree, CAPABILITY_FN)
    if fn is None:
        errors.append(f"{label}: {CAPABILITY_FN} not found")
        return
    args = _function_arg_names(fn)
    expected = ["selection_actions", "rights", "fields_map", "has_list_view"]
    if args != expected:
        errors.append(
            f"{label}: {CAPABILITY_FN} must take only facts (expected {expected}, found {args}); "
            "any entry/model parameter makes a per-entry special case expressible"
        )
    hits = _forbidden_hits(fn)
    if hits:
        errors.append(f"{label}: {CAPABILITY_FN} must not consult entry identity (found {hits})")


def _check_carrier_independence(resolve_rights, build_caps, errors: list[str]) -> None:
    """The same rights must resolve identically from every supported carrier."""
    if resolve_rights is None or build_caps is None:
        return
    carriers = (
        {"effective": {"rights": CARRIER_RIGHTS}},
        {"effective": CARRIER_RIGHTS},
        {"rights": CARRIER_RIGHTS},
        dict(CARRIER_RIGHTS),
    )
    for index, carrier in enumerate(carriers):
        try:
            resolved = resolve_rights(carrier)
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(f"{PERMISSION_RESOLVER} raised on carrier #{index}: {exc!r}")
            continue
        if resolved != CARRIER_RIGHTS:
            errors.append(
                f"{PERMISSION_RESOLVER} must resolve the same rights from carrier #{index} "
                f"(expected {CARRIER_RIGHTS}, got {resolved})"
            )
    for undeclared in ({"effective": {"rights": {"create": "yes"}}}, {"effective": {"rights": {"create": 1}}}):
        if resolve_rights(undeclared) != {}:
            errors.append(
                f"{PERMISSION_RESOLVER} must not promote a non-boolean right ({undeclared!r})"
            )
    try:
        first = build_caps(
            selection_actions=["export"], rights=CARRIER_RIGHTS, fields_map=CARRIER_FIELDS, has_list_view=True
        )
        second = build_caps(
            selection_actions=["export"], rights=CARRIER_RIGHTS, fields_map=CARRIER_FIELDS, has_list_view=True
        )
    except Exception as exc:  # pragma: no cover - defensive
        errors.append(f"{CAPABILITY_FN} raised on the facts-only signature: {exc!r}")
        return
    if first != second:
        errors.append(f"{CAPABILITY_FN} must be a pure function of its facts, not of call order")


def _load_module(path: Path, name: str):
    if not path.is_file():
        return None
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def probe(
    *,
    client_ts: str | None = None,
    handler_py: str | None = None,
    assembler_py: str | None = None,
    permissions_py: str | None = None,
    capability_py: str | None = None,
    resolve_rights=None,
    build_caps=None,
) -> list[str]:
    errors: list[str] = []
    client_ts = _read(CLIENT_TS, errors) if client_ts is None else client_ts
    handler_py = _read(HANDLER_PY, errors) if handler_py is None else handler_py
    assembler_py = _read(ASSEMBLER_PY, errors) if assembler_py is None else assembler_py
    permissions_py = _read(PERMISSIONS_PY, errors) if permissions_py is None else permissions_py
    capability_py = _read(CAPABILITY_PY, errors) if capability_py is None else capability_py

    if client_ts:
        _check_frontend(client_ts, errors)

    handler_tree = _module_tree(handler_py, HANDLER_PY.name, errors) if handler_py else None
    if handler_tree is not None:
        _check_backend_entry_branch(handler_tree, HANDLER_PY.name, errors)

    assembler_tree = _module_tree(assembler_py, ASSEMBLER_PY.name, errors) if assembler_py else None
    permissions_tree = _module_tree(permissions_py, PERMISSIONS_PY.name, errors) if permissions_py else None
    _check_permission_facts(assembler_tree, permissions_tree, errors)

    capability_tree = _module_tree(capability_py, CAPABILITY_PY.name, errors) if capability_py else None
    _check_capability_rule(capability_tree, errors)

    if resolve_rights is None or build_caps is None:
        module = _load_module(PERMISSIONS_PY, "entry_equivalence_permissions")
        if resolve_rights is None and module is not None:
            resolve_rights = getattr(module, PERMISSION_RESOLVER, None)
        capability_module = _load_module(CAPABILITY_PY, "entry_equivalence_capability")
        if build_caps is None and capability_module is not None:
            build_caps = getattr(capability_module, CAPABILITY_FN, None)
    if resolve_rights is None:
        errors.append(f"cannot import {PERMISSION_RESOLVER} from {PERMISSIONS_PY.name}")
    if build_caps is None:
        errors.append(f"cannot import {CAPABILITY_FN} from {CAPABILITY_PY.name}")
    _check_carrier_independence(resolve_rights, build_caps, errors)
    return errors


def main() -> int:
    errors = probe()
    if errors:
        print("[contract_v2_entry_equivalence_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[contract_v2_entry_equivalence_guard] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
