#!/usr/bin/env python3
"""Prove the backend's own action-declaration side is complete.

A transition the backend lets a user execute must carry a published business
purpose, because the Web is not allowed to infer one from a method name, a
label or a button position.  This guard reads the declaration authorities
(instead of a rendered page) and fails when any of them can hand the Web a
reachable action whose meaning is missing or outside the published vocabulary.

The registry is read by static evaluation, not by importing Odoo: a value is
resolved when it is a literal, a small comprehension over a literal model list,
or a call to another declaration helper in the same file.  Anything else is
reported instead of silently skipped.

Whether an action is reachable is also decided by permission and role, so the
same guard proves the authorization side: an action the backend offers must
resolve a runtime authorization verdict and, when it declares a role gate, that
gate must name a role from the published role vocabulary and a group the module
actually declares.  A dangling or invented gate is a failure, not a warning.

This proves the *declaration* side only.  A native view may still contain
buttons no authority registered; that remainder is reported by the runtime
occurrence audit, not here.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json"
WORKFLOW_SERVICE = ROOT / "addons/smart_construction_core/models/support/workflow_contract_service.py"
PAYMENT_ACTIONS = ROOT / "addons/smart_construction_core/handlers/payment_request_available_actions.py"
FINANCIAL_WORKSPACE = ROOT / "addons/smart_construction_core/services/financial_workspace_contract.py"
CAPABILITY_REGISTRY = ROOT / "addons/smart_construction_core/services/capability_registry.py"
ACTOR_ROLES = ROOT / "addons/smart_construction_core/core_extension_actor_roles.py"
SECURITY_DIR = ROOT / "addons/smart_construction_core/security"
SECURITY_MODULE = "smart_construction_core"
# The one authority for the declared `(kind, purpose, executor)` vocabulary.
# Checking the three parts against three independent enums would accept a
# combination every terminal drops - the failure this guard exists to catch -
# so the pairing itself is read from the authority.
ACTION_SEMANTICS_AUTHORITY = "addons/smart_core/core/action_semantics_vocabulary.py"

# The verdict the workflow contract must consult before it publishes an
# approval action; removing it would leave the Web as the only decider.
APPROVAL_VERDICT_MARKER = "can_review"
ROLE_VOCABULARY_MAP = "ROLE_SUFFIX_MAP"
GROUP_ROLE_MAP = "CAPABILITY_GROUP_ROLE_MAP"
ROLE_GROUP_PREFIX = "ROLE_GROUP_PREFIX_CORE"

# Actions whose method is owned by platform persistence instead of a business
# authority.  They keep the platform's own declaration (`record.save`), so they
# are the only keys allowed to resolve no method and declare no purpose.
PLATFORM_PERSISTENCE_KEYS = {"save_draft"}

# A method-binding action the Web may execute must be classified: it either
# declares a published business purpose, or it is registered here as navigation
# with a reason.  The registry is not a bypass -- the guard fails when a
# registered key is no longer declared and when a declared method-binding action
# is neither classified nor registered, so a new object-method action cannot
# inherit this exception silently.
NAVIGATION_METHOD_ACTIONS = {
    "view_payment_execution": (
        "hands the Web the related payment-execution record; it reads a related "
        "record and does not transition this one"
    ),
}

UNRESOLVED = object()


class Unresolved(Exception):
    def __init__(self, node: ast.AST):
        super().__init__(f"cannot statically resolve {type(node).__name__} at line {getattr(node, 'lineno', '?')}")
        self.node = node


def _comprehension_source(node: ast.DictComp, env: dict[str, Any]) -> Any:
    if len(node.generators) != 1:
        raise Unresolved(node)
    generator = node.generators[0]
    if not isinstance(generator.target, ast.Name) or generator.ifs:
        raise Unresolved(node)
    source = eval_node(generator.iter, {}, env)
    if not isinstance(source, (list, tuple)):
        raise Unresolved(node)
    return source


def eval_node(node: ast.AST, funcs: dict[str, ast.AST], env: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        raise Unresolved(node)
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        values = []
        for element in node.elts:
            if isinstance(element, ast.Starred):
                raise Unresolved(node)
            values.append(eval_node(element, funcs, env))
        return tuple(values) if isinstance(node, ast.Tuple) else list(values)
    if isinstance(node, ast.Dict):
        result: dict[Any, Any] = {}
        for key, value in zip(node.keys, node.values):
            if key is None:
                merged = eval_node(value, funcs, env)
                if not isinstance(merged, dict):
                    raise Unresolved(node)
                result.update(merged)
                continue
            result[eval_node(key, funcs, env)] = eval_node(value, funcs, env)
        return result
    if isinstance(node, ast.DictComp):
        source = _comprehension_source(node, env)
        result = {}
        for item in source:
            local = dict(env)
            local[node.generators[0].target.id] = item
            result[eval_node(node.key, funcs, local)] = eval_node(node.value, funcs, local)
        return result
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        name = node.func.id
        args = [eval_node(arg, funcs, env) for arg in node.args]
        if name == "dict":
            return dict(args[0]) if args else {}
        if name in funcs:
            body = funcs[name]
            if not isinstance(body, ast.FunctionDef):
                raise Unresolved(node)
            local = {arg.arg: value for arg, value in zip(body.args.args, args)}
            return eval_function_body(body, funcs, local)
    raise Unresolved(node)


def eval_function_body(body: ast.FunctionDef, funcs: dict[str, ast.AST], local: dict[str, Any]) -> Any:
    """Evaluate a declaration helper: bind its locals in order, then its return.

    Declaration helpers build a profile into a local name and hand back copies
    of it, so a resolver that only understands module-level literals would
    report the registry as unresolvable - and a guard that cannot read the
    registry cannot prove anything about it.
    """
    for statement in body.body:
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name):
                    local[target.id] = eval_node(statement.value, funcs, local)
            continue
        if isinstance(statement, ast.Return):
            if statement.value is None:
                return None
            return eval_node(statement.value, funcs, local)
        if isinstance(statement, (ast.Expr, ast.Pass, ast.If, ast.AugAssign)):
            continue
        raise Unresolved(statement)
    raise Unresolved(body)


def _string_literals(node: ast.AST) -> set[str]:
    values: set[str] = set()
    for element in getattr(node, "elts", []) or [node]:
        if isinstance(element, ast.Constant) and isinstance(element.value, str):
            values.add(element.value)
    return values


def verdict_keys(path: Path, function_name: str, subject: str) -> tuple[set[str], list[str]]:
    """Read which actions a runtime authorization verdict actually covers.

    A spec key the verdict never examines is an action the backend offers but
    does not authorize, which leaves the Web deciding who may act.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    target = next(
        (node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == function_name),
        None,
    )
    if target is None:
        return set(), [f"{path.name}:{function_name} is missing; the authorization verdict cannot be read"]
    keys: set[str] = set()
    for node in ast.walk(target):
        if not isinstance(node, ast.Compare):
            continue
        operands = [node.left, *node.comparators]
        if not any(isinstance(operand, ast.Name) and operand.id == subject for operand in operands):
            continue
        for operand in operands:
            if isinstance(operand, ast.Name):
                continue
            keys |= _string_literals(operand)
    return keys, []


def _resolver_role_literals(path: Path, function_name: str) -> tuple[set[str], list[str]]:
    """Read the role codes a runtime resolver can actually produce."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    target = next(
        (node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == function_name),
        None,
    )
    if target is None:
        return set(), [f"{path.name}:{function_name} is missing; the runtime role vocabulary cannot be read"]
    codes: set[str] = set()
    for node in ast.walk(target):
        if isinstance(node, ast.Return) and node.value is not None:
            codes |= _string_literals(node.value)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"add", "update"}
            and node.args
        ):
            codes |= _string_literals(node.args[0])
    return codes, []


def role_vocabulary(
    registry_path: Path, actor_roles_path: Path
) -> tuple[set[str], set[str], list[str]]:  # noqa: D401 - see resolve_role_code
    """Derive the role vocabulary from the authorities that produce it.

    Hardcoding it here would let the guard agree with itself while the runtime
    resolves a different set of roles, so every code is read from the group map
    and from the resolvers that hand role codes to the capability checks.
    """
    found, unresolved = literal_assignments(
        registry_path, {ROLE_VOCABULARY_MAP, GROUP_ROLE_MAP, ROLE_GROUP_PREFIX}
    )
    suffix_map = found.get(ROLE_VOCABULARY_MAP)
    if not isinstance(suffix_map, dict):
        return set(), set(), [*unresolved, f"{registry_path.name}:{ROLE_VOCABULARY_MAP} could not be read"]
    errors = list(unresolved)
    group_map = found
    vocabulary = {str(key) for key in suffix_map} | {str(value) for value in suffix_map.values()}
    group_role_map = group_map.get(GROUP_ROLE_MAP)
    if isinstance(group_role_map, dict):
        vocabulary |= {str(value) for value in group_role_map.values()}
    for path, function_name in (
        (registry_path, "_resolve_role_codes_for_user"),
        (actor_roles_path, "resolve_release_actor_role_codes"),
    ):
        codes, code_errors = _resolver_role_literals(path, function_name)
        vocabulary |= codes
        errors += code_errors

    tree = ast.parse(registry_path.read_text(encoding="utf-8"), filename=str(registry_path))
    declared: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg != "required_roles":
                continue
            if not isinstance(keyword.value, (ast.List, ast.Tuple, ast.Set)):
                errors.append(
                    f"{registry_path.name}: a required_roles value is not a literal at line {keyword.value.lineno}"
                )
                continue
            declared |= _string_literals(keyword.value)
    return vocabulary, declared, errors


def group_role_maps(registry_path: Path) -> tuple[dict[str, Any], dict[str, Any], str, list[str]]:
    """Read the group -> role authority the runtime resolution uses."""
    found, unresolved = literal_assignments(
        registry_path, {ROLE_VOCABULARY_MAP, GROUP_ROLE_MAP, ROLE_GROUP_PREFIX}
    )
    suffix_map = found.get(ROLE_VOCABULARY_MAP)
    group_role_map = found.get(GROUP_ROLE_MAP)
    prefix = found.get(ROLE_GROUP_PREFIX)
    errors = list(unresolved)
    if not isinstance(suffix_map, dict):
        errors.append(f"{registry_path.name}:{ROLE_VOCABULARY_MAP} could not be read")
        suffix_map = {}
    if not isinstance(group_role_map, dict):
        errors.append(f"{registry_path.name}:{GROUP_ROLE_MAP} could not be read")
        group_role_map = {}
    if not isinstance(prefix, str):
        errors.append(f"{registry_path.name}:{ROLE_GROUP_PREFIX} could not be read")
        prefix = ""
    return suffix_map, group_role_map, prefix, errors


def resolve_role_code(
    group_xmlid: str, suffix_map: dict[str, Any], group_role_map: dict[str, Any], prefix: str
) -> str:
    """Resolve a gate group to its published role code, or ``''``."""
    text = str(group_xmlid or "").strip()
    if not text:
        return ""
    mapped = group_role_map.get(text)
    if mapped:
        return str(mapped)
    if prefix and text.startswith(prefix):
        suffix = text[len(prefix):]
        return str(suffix_map.get(suffix, suffix))
    return ""


def declared_group_xmlids(path: Path) -> set[str]:
    """Collect the res.groups records the module security files really declare."""
    import xml.etree.ElementTree as ET

    xmlids: set[str] = set()
    for xml_file in sorted(path.glob("*.xml")):
        try:
            root = ET.fromstring(xml_file.read_text(encoding="utf-8"))
        except ET.ParseError:
            continue
        for element in root.iter():
            tag = element.tag.rsplit("}", 1)[-1]
            if tag != "record" or element.get("model") != "res.groups":
                continue
            record_id = str(element.get("id") or "").strip()
            if record_id:
                xmlids.add(f"{SECURITY_MODULE}.{record_id}")
    return xmlids


def literal_assignments(path: Path, wanted: set[str]) -> tuple[dict[str, Any], list[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    funcs = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    found: dict[str, Any] = {}
    unresolved: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            name = target.id if isinstance(target, ast.Name) else None
            if name not in wanted:
                continue
            try:
                found[name] = eval_node(node.value, funcs, {})
            except Unresolved as exc:
                unresolved.append(f"{path.name}:{name} {exc}")
    return found, unresolved


def financial_workspace_action_declarations(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Read the action dicts the financial workspace authority literally declares.

    The authority assembles most of its list from workflow rows at runtime, so a
    literal dict is the only declaration a static guard can bind to.  A dict that
    spreads a conditional ``action_semantics`` copies it from the workflow
    registry, which :func:`validate` already checks; that is reported as
    propagated rather than silently skipped.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except OSError as exc:
        return [], [f"{path.name}: cannot read the financial workspace authority ({exc})"]

    records: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        candidates: list[ast.AST] = []
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "append"
        ):
            candidates = list(node.args)
        elif isinstance(node, ast.Return) and isinstance(node.value, ast.List):
            candidates = list(node.value.elts)
        for candidate in candidates:
            if not isinstance(candidate, ast.Dict):
                continue
            literal: dict[str, Any] = {}
            propagated = False
            binds_method = False
            for key, value in zip(candidate.keys, candidate.values):
                if key is None:
                    # A spread that mentions action_semantics copies it from the
                    # workflow registry instead of declaring it here.
                    if "action_semantics" in ast.dump(value):
                        propagated = True
                    continue
                if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                    continue
                if key.value == "method":
                    # An unresolved method still binds one: dropping the dict
                    # would hide exactly the declaration this guard checks.
                    binds_method = True
                try:
                    literal[key.value] = eval_node(value, {}, {})
                except Unresolved:
                    continue
            if not binds_method and "action_semantics" not in literal:
                continue
            records.append(
                {
                    "key": str(literal.get("key") or f"<dict@{candidate.lineno}>"),
                    "method": literal.get("method"),
                    "binds_method": binds_method,
                    "action_semantics": literal.get("action_semantics"),
                    "required_params": literal.get("required_params"),
                    "requires_reason": literal.get("requires_reason"),
                    "action_safety": literal.get("action_safety"),
                    "propagates_semantics": propagated,
                    "line": candidate.lineno,
                }
            )
    return records, []


def validate_navigation_exception(key: str, item: dict[str, Any]) -> list[str]:
    """A navigation exception must not excuse an action that takes business input.

    The registry records a classification a human made; this check removes the
    most dangerous misuse of it, where a real transition (reason prompt, required
    parameters or a destructive classification) is excused as navigation.
    """
    errors: list[str] = []
    required = item.get("required_params") or []
    if item.get("requires_reason") or (isinstance(required, list) and required):
        errors.append(
            f"navigation exception {key!r} excuses an action that collects business input "
            f"(required_params={required!r}, requires_reason={item.get('requires_reason')!r}); "
            f"declare a published purpose instead"
        )
    safety = item.get("action_safety")
    classification = str((safety or {}).get("classification") or "").strip().lower() if isinstance(safety, dict) else ""
    if classification in {"danger", "destructive"}:
        errors.append(
            f"navigation exception {key!r} excuses a destructive action "
            f"(action_safety.classification={classification!r}); declare a published purpose instead"
        )
    return errors


def validate_financial_workspace_actions(
    *,
    vocabulary: set[str],
    authority: Any,
    declarations: list[dict[str, Any]],
    registered_navigation: dict[str, str],
) -> list[str]:
    """Prove every method-binding action of the workspace authority is classified."""
    errors: list[str] = []
    if not declarations:
        return [
            "no financial workspace action declaration was read; the check would be vacuous"
        ]

    declared_keys = {str(item.get("key")) for item in declarations}
    for key, reason in sorted(registered_navigation.items()):
        if key not in declared_keys:
            errors.append(
                f"navigation exception {key!r} is registered but no longer declared by the "
                f"financial workspace authority; remove it or restore the action"
            )
        if not str(reason or "").strip():
            errors.append(f"navigation exception {key!r} is registered without a reason")

    for item in declarations:
        key = str(item.get("key"))
        method = str(item.get("method") or "").strip() or "<unresolved method>"
        if item.get("propagates_semantics"):
            continue
        if not item.get("binds_method"):
            continue
        semantics = item.get("action_semantics")
        purpose = declared_purpose(semantics)
        if not purpose:
            if key in registered_navigation:
                errors += validate_navigation_exception(key, item)
                continue
            errors.append(
                f"financial workspace action {key!r} binds method {method!r} without a declared "
                f"action purpose and is not a registered navigation action "
                f"{sorted(registered_navigation)}"
            )
            continue
        if purpose not in vocabulary:
            errors.append(
                f"financial workspace action {key!r} declares purpose {purpose!r} outside the "
                f"published vocabulary"
            )
            continue
        if not declares_published_pair(authority, semantics):
            errors.append(
                f"financial workspace action {key!r} declares {semantics!r}, which is not a "
                f"published (kind, purpose, executor) combination; every terminal would drop it"
            )
    return errors


def published_purposes(schema_path: Path) -> set[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    branches = (
        schema.get("$defs", {})
        .get("actionRule", {})
        .get("properties", {})
        .get("actionSemantics", {})
        .get("oneOf", [])
    )
    purposes: set[str] = set()
    for branch in branches if isinstance(branches, list) else []:
        if isinstance(branch, dict):
            purposes |= set((branch.get("properties") or {}).get("purpose", {}).get("enum") or [])
    return purposes


def declared_purpose(value: Any) -> str:
    declared = value if isinstance(value, dict) else {}
    return str(declared.get("purpose") or "").strip().lower()


def load_action_semantics_authority(repo_root: Path) -> Any:
    path = repo_root / ACTION_SEMANTICS_AUTHORITY
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location("workflow_guard_action_semantics_vocabulary", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def declares_published_pair(authority: Any, declared: Any) -> bool:
    """Whether the three parts form one declaration of the published vocabulary."""
    value = declared if isinstance(declared, dict) else {}
    return bool(
        authority.is_declared(value.get("kind"), value.get("purpose"), value.get("executor"))
    )


def validate(
    *,
    vocabulary: set[str],
    authority: Any,
    profiles: dict[str, Any],
    actions: dict[str, Any],
    specs: list[Any],
) -> list[str]:
    errors: list[str] = []
    if not vocabulary:
        return ["no published action purpose vocabulary was read from the schema"]
    if authority is None:
        return [f"the action semantics authority {ACTION_SEMANTICS_AUTHORITY} is missing"]
    if not profiles or not actions:
        return ["no workflow profile/action registry was read; the check would be vacuous"]

    reachable: set[str] = set()
    for model, profile in sorted((profiles or {}).items()):
        if not isinstance(profile, dict):
            continue
        for phase, keys in sorted((profile.get("state_actions") or {}).items()):
            for key in keys or []:
                reachable.add(str(key))
                if str(key) not in actions:
                    errors.append(f"{model}: state {phase!r} declares action {key!r} missing from ACTIONS")
        for key in sorted(profile.get("method_by_action") or {}):
            reachable.add(str(key))
            if str(key) not in actions:
                errors.append(f"{model}: method_by_action declares action {key!r} missing from ACTIONS")
        for key in profile.get("approval_actions") or []:
            reachable.add(str(key))
            if str(key) not in actions:
                errors.append(f"{model}: approval_actions declares action {key!r} missing from ACTIONS")

    checked = 0
    for key in sorted(reachable):
        spec = actions.get(key) or {}
        method = str(spec.get("method") or "").strip()
        if not method:
            for profile in (profiles or {}).values():
                if isinstance(profile, dict):
                    method = str((profile.get("method_by_action") or {}).get(key) or "").strip()
                    if method:
                        break
        if not method:
            if key not in PLATFORM_PERSISTENCE_KEYS:
                errors.append(
                    f"action {key!r} resolves no method and is not a registered platform "
                    f"persistence key {sorted(PLATFORM_PERSISTENCE_KEYS)}"
                )
            continue
        checked += 1
        purpose = declared_purpose(spec.get("action_semantics"))
        if not purpose:
            errors.append(f"action {key!r} binds method {method!r} without a declared action purpose")
        elif purpose not in vocabulary:
            errors.append(f"action {key!r} declares purpose {purpose!r} outside the published vocabulary")
        elif not declares_published_pair(authority, spec.get("action_semantics")):
            errors.append(
                f"action {key!r} declares {spec.get('action_semantics')!r}, which is not a published "
                f"(kind, purpose, executor) combination; every terminal would drop it"
            )

    checked_specs = 0
    for spec in specs or []:
        if not isinstance(spec, dict):
            continue
        method = str(spec.get("method") or "").strip()
        if not method or not spec.get("allowed_states"):
            continue
        checked_specs += 1
        purpose = declared_purpose(spec.get("action_semantics"))
        if not purpose:
            errors.append(f"payment action {spec.get('key')!r} binds method {method!r} without a declared action purpose")
        elif purpose not in vocabulary:
            errors.append(f"payment action {spec.get('key')!r} declares purpose {purpose!r} outside the published vocabulary")
        elif not declares_published_pair(authority, spec.get("action_semantics")):
            errors.append(
                f"payment action {spec.get('key')!r} declares {spec.get('action_semantics')!r}, which is not a "
                f"published (kind, purpose, executor) combination; every terminal would drop it"
            )

    if checked == 0 or checked_specs == 0:
        errors.append("the guard matched no reachable transition; it must not pass vacuously")
    return errors


def references_marker(path: Path, function_name: str, marker: str) -> bool:
    """True only when `marker` decides control flow inside `function_name`.

    A bare occurrence would accept a verdict that is merely logged, or a branch
    that can never be taken -- neither actually consults the runtime approval
    decision, which is the thing this check exists to prove.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    target = next(
        (node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == function_name),
        None,
    )
    if target is None:
        return False
    for node in ast.walk(target):
        if isinstance(node, (ast.If, ast.While, ast.IfExp)):
            test = node.test
        else:
            continue
        if isinstance(test, ast.Constant):
            continue
        if any(
            isinstance(inner, ast.Constant) and inner.value == marker
            for inner in ast.walk(test)
        ):
            return True
    return False


def validate_authorization_binding(
    *,
    specs: list[Any],
    role_hints: dict[str, Any],
    verdict: set[str],
    role_vocabulary: set[str],
    suffix_map: dict[str, Any],
    group_role_map: dict[str, Any],
    role_prefix: str,
    declared_roles: set[str],
    group_vocabulary: set[str],
    approval_actions_declared: bool,
    approval_verdict_consumed: bool,
) -> list[str]:
    """Prove the permission and role side of the same declaration."""
    errors: list[str] = []
    if not role_vocabulary:
        return ["no published role vocabulary was read; the authorization check would be vacuous"]
    if not group_vocabulary:
        return ["no res.groups record was read from the module security files; the gate check would be vacuous"]

    for role in sorted(declared_roles - role_vocabulary):
        errors.append(
            f"capability required_roles declares {role!r}, which is outside the published role vocabulary "
            f"{sorted(role_vocabulary)}"
        )

    offered: list[str] = []
    for spec in specs or []:
        if not isinstance(spec, dict):
            continue
        key = str(spec.get("key") or "").strip()
        method = str(spec.get("method") or "").strip()
        if not key or not method or not spec.get("allowed_states"):
            continue
        offered.append(key)
        if key not in role_hints:
            errors.append(f"payment action {key!r} is offered without a declared role gate")
        if key not in verdict:
            errors.append(
                f"payment action {key!r} is offered without a runtime authorization verdict; "
                f"the verdict covers {sorted(verdict)}"
            )

    for key in sorted(role_hints or {}):
        hint = role_hints.get(key) if isinstance(role_hints.get(key), dict) else {}
        if key not in offered:
            errors.append(f"role gate {key!r} is declared but no offered payment action uses it")
            continue
        if "required_role_key" in hint:
            errors.append(
                f"role gate {key!r} restates a role code; the published role is derived from the gate group "
                "so the two vocabularies cannot drift apart"
            )
        group = str(hint.get("required_group_xmlid") or "").strip()
        if not group:
            errors.append(f"role gate {key!r} declares no required group")
            continue
        if group not in group_vocabulary:
            errors.append(
                f"role gate {key!r} names group {group!r}, which the module security files do not declare"
            )
            continue
        resolved = resolve_role_code(group, suffix_map, group_role_map, role_prefix)
        if not resolved:
            errors.append(f"role gate {key!r} names group {group!r}, which resolves to no published role code")
        elif resolved not in role_vocabulary:
            errors.append(
                f"role gate {key!r} resolves to role {resolved!r}, which the published role vocabulary "
                f"{sorted(role_vocabulary)} does not publish"
            )

    if approval_actions_declared and not approval_verdict_consumed:
        errors.append(
            "workflow profiles publish approval actions without consulting the runtime approval verdict "
            f"({APPROVAL_VERDICT_MARKER!r}); the Web would then be the only decider"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", type=Path, default=SCHEMA)
    parser.add_argument("--workflow-service", type=Path, default=WORKFLOW_SERVICE)
    parser.add_argument("--payment-actions", type=Path, default=PAYMENT_ACTIONS)
    parser.add_argument("--financial-workspace", type=Path, default=FINANCIAL_WORKSPACE)
    parser.add_argument("--capability-registry", type=Path, default=CAPABILITY_REGISTRY)
    parser.add_argument("--actor-roles", type=Path, default=ACTOR_ROLES)
    parser.add_argument("--security-dir", type=Path, default=SECURITY_DIR)
    args = parser.parse_args()

    workflow, unresolved = literal_assignments(args.workflow_service, {"PROFILE_BY_MODEL", "ACTIONS"})
    payment, payment_unresolved = literal_assignments(
        args.payment_actions, {"_ACTION_SPECS", "_ACTION_ROLE_HINTS"}
    )
    profiles = workflow.get("PROFILE_BY_MODEL") or {}
    actions = workflow.get("ACTIONS") or {}
    specs = payment.get("_ACTION_SPECS") or []
    role_hints = payment.get("_ACTION_ROLE_HINTS") or {}
    purposes = published_purposes(args.schema)
    authority = load_action_semantics_authority(ROOT)
    workspace_declarations, workspace_unresolved = financial_workspace_action_declarations(
        args.financial_workspace
    )
    errors = [*unresolved, *payment_unresolved, *workspace_unresolved]
    errors += validate(
        vocabulary=purposes, authority=authority, profiles=profiles, actions=actions, specs=specs
    )
    errors += validate_financial_workspace_actions(
        vocabulary=purposes,
        authority=authority,
        declarations=workspace_declarations,
        registered_navigation=NAVIGATION_METHOD_ACTIONS,
    )

    verdict, verdict_errors = verdict_keys(args.payment_actions, "_authorization_for_action", "key")
    vocabulary, declared_roles, role_errors = role_vocabulary(
        args.capability_registry, args.actor_roles
    )
    suffix_map, group_role_map, role_prefix, map_errors = group_role_maps(args.capability_registry)
    role_errors += map_errors
    errors += verdict_errors + role_errors
    errors += validate_authorization_binding(
        specs=specs,
        role_hints=role_hints,
        verdict=verdict,
        role_vocabulary=vocabulary,
        suffix_map=suffix_map,
        group_role_map=group_role_map,
        role_prefix=role_prefix,
        declared_roles=declared_roles,
        group_vocabulary=declared_group_xmlids(args.security_dir),
        approval_actions_declared=any(
            isinstance(profile, dict) and profile.get("approval_actions") for profile in profiles.values()
        ),
        approval_verdict_consumed=references_marker(
            args.workflow_service, "_available_actions", APPROVAL_VERDICT_MARKER
        ),
    )
    if errors:
        print("Workflow action semantics completeness guard failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    reachable = {
        str(key)
        for profile in profiles.values()
        if isinstance(profile, dict)
        for keys in (profile.get("state_actions") or {}).values()
        for key in keys or []
    }
    print(
        "Workflow action semantics completeness guard passed: "
        f"profiles={len(profiles)} reachable_actions={len(reachable)} "
        f"payment_specs={len(specs)} workspace_actions={len(workspace_declarations)} "
        f"role_gates={len(role_hints)} "
        f"verdict_covers={len(verdict)} roles={len(vocabulary)} vocabulary={len(purposes)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
