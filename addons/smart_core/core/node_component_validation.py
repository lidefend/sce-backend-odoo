"""Backend-only validation of explicit form node components before trimming.

No CSS/role inference, client capabilities, runtime storage or production sources.
The caller supplies the authoritative pre-extension tree, never a wire proof.
"""
from copy import deepcopy

from .form_configuration_compiler import FormConfigurationError
from .record_error_proof import validate_record_errors, _context

FEEDBACK = "sc.feedback.message"
ANCHOR = "sc.navigation.anchor"
KEYS = frozenset({FEEDBACK, ANCHOR})
SCALARS = frozenset({"char", "text", "boolean", "integer", "float", "monetary", "selection", "date", "datetime"})


def fail(code, path):
    raise FormConfigurationError(code, path)


def walk(nodes, path="layoutContract.containerTree"):
    if not isinstance(nodes, list):
        fail("FEEDBACK_CONFIG_INVALID", path)
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            fail("FEEDBACK_CONFIG_INVALID", path)
        here = f"{path}[{index}]"
        yield node, here
        yield from walk(node.get("children", []), here + ".children")


def has_components(contract):
    return any(node.get("componentKey") in KEYS for node, _ in
               walk((contract.get("layoutContract") or {}).get("containerTree", [])))


def validate_delivered_references(contract):
    """Supplement pre-trim validation: trimming may not leave dangling refs."""
    rows = list(walk((contract.get("layoutContract") or {}).get("containerTree", [])))
    for node, path in rows:
        key = node.get("componentKey")
        if key == FEEDBACK:
            ref = node["componentConfig"]["contentRef"]["containerId"]
            unique(rows, ref, path)
        elif key == ANCHOR:
            unique(rows, node["componentConfig"]["targetContainerId"], path, "NAVIGATION_TARGET_INVALID")


def condition_dependencies(value, path):
    """Validate only the existing compiled modifier AST, never source strings."""
    if type(value) is bool:
        return set()
    if type(value) is not dict:
        fail("FEEDBACK_CONDITION_INVALID", path)
    kind = value.get("kind")
    if type(kind) is not str:
        fail("FEEDBACK_CONDITION_INVALID", path)
    if kind == "static" and set(value) == {"kind", "value"} and type(value["value"]) is bool:
        return set()
    if kind == "not" and set(value) == {"kind", "expr"}:
        return condition_dependencies(value["expr"], path)
    if kind in {"all", "any"} and set(value) == {"kind", "exprs"} and isinstance(value["exprs"], list) and value["exprs"]:
        return set().union(*(condition_dependencies(v, path) for v in value["exprs"]))
    if kind == "field_truthy" and set(value) == {"kind", "field"}:
        names = [value.get("field")]
    elif (kind == "field_compare" and set(value) in ({"kind", "field", "operator", "value"},
                                                   {"kind", "field", "operator", "value_field"})
          and type(value.get("operator")) is str
          and value.get("operator") in {"=", "==", "!=", ">", ">=", "<", "<=", "in", "not in"}):
        names = [value.get("field")]
        if "value_field" in value:
            names.append(value["value_field"])
    else:
        fail("FEEDBACK_CONDITION_INVALID", path)
    if not names or any(type(name) is not str or not name.isidentifier() for name in names):
        fail("FEEDBACK_CONDITION_INVALID", path)
    return set(names)


def require_nonconstant(value, path):
    # First supported dynamic form is a leaf or its negation. Do not pretend
    # dependency presence proves an arbitrary compound formula nonconstant.
    while isinstance(value, dict) and value.get("kind") == "not":
        value = value["expr"]
    if not isinstance(value, dict) or value.get("kind") not in {"field_truthy", "field_compare"}:
        fail("FEEDBACK_CONDITION_INVALID", path)
    if value["kind"] == "field_compare" and ("value_field" in value or value.get("value") in ([], {})):
        fail("FEEDBACK_CONDITION_INVALID", path)


def unique(rows, identity, path, code="FEEDBACK_SOURCE_INVALID"):
    matches = [node for node, _ in rows if node.get("containerId") == identity]
    if type(identity) is not str or not identity or len(matches) != 1:
        fail(code, path)
    return matches[0]


def native_source(node, originals, path, code="FEEDBACK_SOURCE_INVALID"):
    locator = node.get("nativeLocator")
    occurrence = node.get("occurrenceIndex")
    if not isinstance(locator, str) or not locator or type(occurrence) is not int:
        fail(code, path)
    matches = [n for n, _ in originals if n.get("nativeLocator") == locator and n.get("occurrenceIndex") == occurrence]
    if len(matches) != 1 or not matches[0].get("sourceAuthority"):
        fail(code, path)
    original = matches[0]
    if any(node.get(k) != original.get(k) for k in ("containerId", "name", "type", "sourceAuthority", "text")):
        fail(code, path)
    return original


def read_facts(record, names, path):
    if record is None or len(record) != 1 or type(record.id) is not int or record.id <= 0 or record.env.su:
        fail("FEEDBACK_SOURCE_FORBIDDEN", path)
    context = _context(record)
    needed, pending = set(), list(names)
    while pending:
        name = pending.pop()
        if name in needed:
            continue
        field = record._fields.get(name)
        if field is None or field.type not in SCALARS or getattr(field, "related", None):
            fail("FEEDBACK_SOURCE_INVALID", path)
        needed.add(name)
        if getattr(field, "compute", None):
            if getattr(field, "compute_sudo", True):
                fail("FEEDBACK_SOURCE_FORBIDDEN", path)
            method = getattr(record, field.compute, None) if isinstance(field.compute, str) else field.compute
            dependencies = getattr(method, "_depends", None)
            if not isinstance(dependencies, tuple) or any(not isinstance(d, str) or not d.isidentifier() for d in dependencies):
                fail("FEEDBACK_SOURCE_INVALID", path)
            pending.extend(dependencies)
    try:
        record.check_access_rights("read")
        record.check_access_rule("read")
        allowed = record.check_field_access_rights("read", sorted(needed))
        if allowed is None or not needed.issubset(allowed):
            fail("FEEDBACK_SOURCE_FORBIDDEN", path)
        values = record.read(sorted(needed))
    except Exception as exc:
        if isinstance(exc, PermissionError) or type(exc).__name__ in {"AccessError", "AccessDenied", "MissingError"}:
            fail("FEEDBACK_SOURCE_FORBIDDEN", path)
        raise
    if _context(record) != context or len(values) != 1 or values[0].get("id") != context[1]:
        fail("FEEDBACK_SOURCE_FORBIDDEN", path)
    if not needed.issubset(values[0]):
        fail("FEEDBACK_SOURCE_INVALID", path)
    return values[0]


def validate_final_nodes(env, contract, native_tree, *, apply_visibility=True, draft_feedback=None):
    """Validate all declarations before modifying visibility. Re-run per request."""
    tree = (contract.get("layoutContract") or {}).get("containerTree", [])
    rows, originals = list(walk(tree)), list(walk(native_tree))
    declarations = [(node, path) for node, path in rows if node.get("componentKey") in KEYS]
    if not declarations:
        return
    from .unified_page_contract_v2_assembler import _evaluate_action_modifier
    from .contract_runtime.semantic_resolver import component_registration
    page = contract.get("pageInfo") or {}
    if page.get("viewType") != "form":
        fail("FEEDBACK_CONFIG_INVALID", "pageInfo.viewType")
    model, record_id = page.get("model"), ((contract.get("dataContract") or {}).get("mainData") or {}).get("id")
    record = env[model].browse(record_id) if env is not None and model and type(record_id) is int and record_id > 0 else None
    draft_only = record is None and draft_feedback is not None
    plans, needed = [], set()
    for node, path in declarations:
        key, config = node["componentKey"], node.get("componentConfig")
        unique(rows, node.get("containerId"), path)
        component_registration(key)
        if key == ANCHOR:
            code = "NAVIGATION_TARGET_INVALID"
            if type(config) is not dict or set(config) != {"targetContainerId"}:
                fail(code, path + ".componentConfig")
            original = native_source(node, originals, path, code)
            if (node.get("type") not in {"text", "div", "span", "label", "p", "a"} or node.get("children")
                    or type(original.get("text")) is not str or not original["text"].strip()
                    or any((node.get("attributes") or {}).get(k) for k in ("href", "onclick", "target", "groups"))):
                fail(code, path)
            target = unique(rows, config["targetContainerId"], path, code)
            if target.get("type") not in {"group", "page", "sheet", "div", "container"}:
                fail(code, path)
            native_source(target, originals, path, code)
            # Narrow first version: require explicit constant visibility, including
            # ancestors. Conditional navigation needs a declared supported target.
            target_path = next(p for n, p in rows if n is target)
            ancestor_ids = set()
            for ancestor, ancestor_path in rows:
                if target_path == ancestor_path or target_path.startswith(ancestor_path + ".children"):
                    ancestor_ids.add(ancestor.get("containerId"))
                    invisible = (ancestor.get("modifiers") or {}).get("invisible", False)
                    from .field_presentation_usage import statically_hidden
                    if (statically_hidden(ancestor) or (ancestor.get("attributes") or {}).get("groups")
                            or invisible not in (False, {"kind": "static", "value": False})):
                        fail(code, path)
            for status in (contract.get("statusContract") or {}).get("containerStatus", []):
                if status.get("containerId") in ancestor_ids and (status.get("visible") is False or status.get("auth") == "none"):
                    fail(code, path)
            plans.append((node, key, None, None, None, path))
            continue
        if type(config) is not dict or "purpose" not in config:
            fail("FEEDBACK_LEGACY_UNDECLARED", path + ".componentConfig")
        if (set(config) not in ({"purpose", "contentRef"}, {"purpose", "contentRef", "evaluation"})
                or type(config.get("purpose")) is not str
                or config.get("purpose") not in {"advisory", "warning", "error", "explanation"}):
            fail("FEEDBACK_CONFIG_INVALID", path + ".componentConfig")
        evaluation = config.get("evaluation")
        if evaluation is not None:
            if (config["purpose"] != "advisory" or type(evaluation) is not dict
                    or set(evaluation) != {"capability", "visibilityOwner"}
                    or evaluation.get("capability") != "form.feedback.draft.v1"
                    or evaluation.get("visibilityOwner") != "feedback_evaluation"):
                fail("FEEDBACK_CONFIG_INVALID", path + ".componentConfig.evaluation")
        if draft_only and config["purpose"] != "advisory":
            fail("FEEDBACK_SOURCE_INVALID", path)
        ref = config["contentRef"]
        if type(ref) is not dict or set(ref) != {"containerId"}:
            fail("FEEDBACK_CONFIG_INVALID", path + ".componentConfig.contentRef")
        source = unique(rows, ref["containerId"], path)
        original = native_source(source, originals, path)
        if config["purpose"] == "error" and source.get("type") != "field":
            fail("FEEDBACK_SOURCE_INVALID", path)
        if (source.get("attributes") or {}).get("groups"):
            fail("FEEDBACK_SOURCE_FORBIDDEN", path)
        if source.get("type") == "field":
            name = original.get("name")
            field_owner = record if record is not None else env[model] if draft_only else None
            if (field_owner is None or name not in field_owner._fields
                    or field_owner._fields[name].type not in SCALARS):
                fail("FEEDBACK_SOURCE_INVALID", path)
            if config["purpose"] != "error":
                needed.add(name)
        elif source.get("type") in {"text", "div", "span", "label", "p"} and type(original.get("text")) is str and not source.get("children"):
            name = None
        else:
            fail("FEEDBACK_SOURCE_INVALID", path)
        modifiers = node.get("modifiers")
        if type(modifiers) is not dict or "invisible" not in modifiers:
            fail("FEEDBACK_CONDITION_INVALID", path)
        invisible = modifiers["invisible"]
        declaration_owner = record if record is not None else env[model] if draft_only else None
        declaration = declaration_owner._fields.get(name) if declaration_owner is not None and name else None
        if evaluation is not None and declaration is not None:
            from .native_advisory import has_draft_evaluation
            if not has_draft_evaluation(declaration_owner, declaration):
                fail("FEEDBACK_SOURCE_INVALID", path + ".componentConfig.evaluation")
        if name and record is None and getattr(env[model]._fields.get(name), "sc_feedback_usage", None) is not None:
            if not draft_only:
                fail("FEEDBACK_SOURCE_INVALID", path)
            invisible = draft_feedback.validate_source(
                env, model, env[model]._fields[name], node, source, originals, path,
            )
        elif name and declaration is not None and getattr(declaration, "sc_feedback_usage", None) is not None:
            from .native_advisory import validate_binding
            invisible = validate_binding(env, model, declaration, node, source, originals, path)
        deps = condition_dependencies(invisible, path)
        if config["purpose"] in {"advisory", "warning", "error"} and not deps:
            fail("FEEDBACK_CONDITION_INVALID", path)
        if config["purpose"] in {"advisory", "warning", "error"}:
            require_nonconstant(invisible, path)
        if config["purpose"] != "error":
            needed.update(deps)
        plans.append((node, config["purpose"], source, name, invisible, path))
    if draft_only:
        registry = contract["layoutContract"].setdefault("componentRegistry", {})
        for node, _ in declarations:
            registration = component_registration(node["componentKey"])
            registry[node["componentKey"]] = {"version": registration["version"]}
        return
    facts = read_facts(record, needed, "layoutContract.feedback") if needed else {}
    error_enabled = validate_record_errors(record, tree, native_tree,
        action_rules=(contract.get("actionContract") or {}).get("actionRuleList", [])) if any(p[1] == "error" for p in plans) else ()
    visibility = {}
    for node, purpose, source, name, invisible, path in plans:
        if purpose == ANCHOR:
            continue
        if purpose == "error":
            # The reviewed proof reads activation and content together; never
            # combine its decision with an older generic facts read.
            visibility[node["containerId"]] = node["containerId"] in error_enabled
            continue
        hidden = _evaluate_action_modifier(invisible, facts, strict=True)
        if hidden is None:
            fail("FEEDBACK_CONDITION_INVALID", path)
        content = facts.get(name) if name else source.get("text")
        present = content is not None and content is not False and (not isinstance(content, str) or bool(content.strip()))
        if purpose in {"warning", "error"} and hidden is False and not present:
            fail("FEEDBACK_CONTENT_MISSING", path)
        visibility[node["containerId"]] = not hidden and present and (purpose != "error" or node["containerId"] in error_enabled)
    # Tighten existing status only. Never alter business actions, field editing or
    # original error ownership. Suppressed containers remain in the checked tree.
    statuses = (contract.get("statusContract") or {}).get("containerStatus", [])
    for node, _ in rows:
        if apply_visibility and node.get("containerId") in visibility and not visibility[node["containerId"]]:
            node["visible"] = False
            for status in statuses:
                if status.get("containerId") == node["containerId"]:
                    status["visible"] = False
    registry = contract["layoutContract"].setdefault("componentRegistry", {})
    for node, _ in declarations:
        registration = component_registration(node["componentKey"])
        registry[node["componentKey"]] = {"version": registration["version"]}
