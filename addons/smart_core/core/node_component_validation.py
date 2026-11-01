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
    if not isinstance(value, dict):
        fail("FEEDBACK_CONDITION_INVALID", path)
    # Compound visibility conditions are valid only when every branch is a
    # nonconstant leaf; a static branch cannot make the host dynamic.
    if value.get("kind") in {"all", "any"}:
        exprs = value.get("exprs")
        if not isinstance(exprs, list) or not exprs:
            fail("FEEDBACK_CONDITION_INVALID", path)
        for expr in exprs:
            require_nonconstant(expr, path)
        return
    if value.get("kind") not in {"field_truthy", "field_compare"}:
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
    return _read_actor_facts(record, needed, path)


def _read_actor_facts(record, names, path):
    context = _context(record)
    try:
        record.check_access_rights("read")
        record.check_access_rule("read")
        allowed = record.check_field_access_rights("read", sorted(names))
        if allowed is None or not names.issubset(allowed):
            fail("FEEDBACK_SOURCE_FORBIDDEN", path)
        values = record.read(sorted(names))
    except Exception as exc:
        if isinstance(exc, PermissionError) or type(exc).__name__ in {"AccessError", "AccessDenied", "MissingError"}:
            fail("FEEDBACK_SOURCE_FORBIDDEN", path)
        raise
    if _context(record) != context or len(values) != 1 or values[0].get("id") != context[1]:
        fail("FEEDBACK_SOURCE_FORBIDDEN", path)
    if not names.issubset(values[0]):
        fail("FEEDBACK_SOURCE_INVALID", path)
    return values[0]


def native_feedback_fields(record, contract, node, source, invisible, path, parsed_view=None):
    """Prove a legacy advisory against the actor's actual native form.

    A wire native marker grants nothing. Only matching XML host, direct content
    and condition may use native ORM field semantics. Custom declarations keep
    the separately reviewed strict dependency policy.
    """
    config = node.get("componentConfig") or {}
    if config.get("purpose") != "advisory":
        return False
    if source.get("name") and getattr(record._fields.get(source["name"]), "sc_feedback_usage", None) is not None:
        return False
    locator = node.get("nativeLocator")
    if not locator:
        return False
    from xml.etree import ElementTree as ET
    from .unified_page_contract_v2_assembler import _normalize_feedback_condition
    try:
        from odoo.addons.smart_core.utils.native_modifier import normalize_native_modifier
    except ImportError:
        from utils.native_modifier import normalize_native_modifier
    meta = ((contract.get("dataContract") or {}).get("dataMeta") or {}).get("sourceContext") or {}
    view_id = meta.get("formViewId")
    if type(view_id) is not int or view_id <= 0:
        return False
    # Metadata only, never sudo the business record or its field values.
    view_record = record.env["ir.ui.view"].sudo().browse(view_id)
    if view_record.model != record._name or view_record.type != "form":
        fail("FEEDBACK_SOURCE_INVALID", path)
    if (
        parsed_view is not None
        and int(parsed_view.get("_source_view_id") or 0) == view_id
        and parsed_view.get("_arch_root") is not None
    ):
        root = parsed_view["_arch_root"]
    else:
        view = record.get_view(view_id=view_id, view_type="form")
        if view.get("id") != view_id:
            fail("FEEDBACK_SOURCE_INVALID", path)
        try:
            root = ET.fromstring(view.get("arch", ""))
        except (ET.ParseError, TypeError):
            fail("FEEDBACK_SOURCE_INVALID", path)
    if root.tag != "form":
        fail("FEEDBACK_SOURCE_INVALID", path)
    elements, fields = {}, set()
    def visit(element, location):
        elements[location] = element
        if element.tag == "field":
            fields.add(element.get("name"))
            return  # Relation subviews are not declarations on this model.
        counts = {}
        for child in element:
            counts[child.tag] = counts.get(child.tag, 0) + 1
            visit(child, f"{location}/{child.tag}[{counts[child.tag]}]")
    visit(root, "/form[1]")
    host = elements.get(locator)
    if host is None:
        fail("FEEDBACK_SOURCE_INVALID", path)
    classes = set(host.get("class", "").split())
    if not (classes & {"alert", "alert-info", "alert-warning", "alert-danger", "alert-success"}
            or host.get("role", "").lower() == "alert"):
        return False
    # get_view normally prunes groups. A residual restriction must never turn
    # this reader into a way to evaluate hidden native content.
    source_locator = source.get("nativeLocator") or ""
    for location, element in elements.items():
        if (location == locator or locator.startswith(location + "/")
                or location == source_locator):
            if element.get("groups"):
                fail("FEEDBACK_SOURCE_FORBIDDEN", path)
    raw = host.get("invisible")
    if (raw is None or (node.get("attributes") or {}).get("invisible") != raw
            or _normalize_feedback_condition(normalize_native_modifier(raw)) != invisible):
        fail("FEEDBACK_SOURCE_INVALID", path)
    # Bind the same first content selected by the native alert projection.
    text = " ".join((host.text or "").split())
    expected = None
    if text:
        expected = (locator + "/text[1]", "text", None, text)
    else:
        for child in host:
            child_text = " ".join((child.text or "").split())
            if child.tag == "field" or (child.tag in {"div", "span", "label", "p"} and child_text):
                child_locator = next((key for key, value in elements.items() if value is child), None)
                expected = (child_locator, child.tag, child.get("name") if child.tag == "field" else None,
                            None if child.tag == "field" else child_text)
                break
    actual = (source.get("nativeLocator"), source.get("type"), source.get("name"), source.get("text"))
    if expected is None or expected != actual:
        fail("FEEDBACK_SOURCE_INVALID", path)
    needed = condition_dependencies(invisible, path) | ({source["name"]} if source.get("name") else set())
    if not needed.issubset(fields):
        fail("FEEDBACK_SOURCE_INVALID", path)
    return True


def read_native_facts(record, names, path):
    """Read only view-proven direct facts under ordinary ORM permissions."""
    if record is None or len(record) != 1 or type(record.id) is not int or record.id <= 0 or record.env.su:
        fail("FEEDBACK_SOURCE_FORBIDDEN", path)
    for name in names:
        field = record._fields.get(name)
        if field is None or field.type not in SCALARS | {"many2one", "one2many", "many2many"}:
            fail("FEEDBACK_SOURCE_INVALID", path)
    values = _read_actor_facts(record, names, path)
    for name in names:
        if record._fields[name].type == "many2one" and isinstance(values[name], (list, tuple)):
            values[name] = values[name][0] if values[name] else False
    return values


def validate_final_nodes(env, contract, native_tree, *, apply_visibility=True, draft_feedback=None, parsed_view=None):
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
    plans, needed, native_needed, native_plans = [], set(), set(), set()
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
            direct = deps | ({name} if name else set())
            if record is not None and native_feedback_fields(record, contract, node, source, invisible, path, parsed_view=parsed_view):
                native_needed.update(direct)
                native_plans.add(node["containerId"])
            else:
                needed.update(direct)
        plans.append((node, config["purpose"], source, name, invisible, path))
    if draft_only:
        registry = contract["layoutContract"].setdefault("componentRegistry", {})
        for node, _ in declarations:
            registration = component_registration(node["componentKey"])
            registry[node["componentKey"]] = {"version": registration["version"]}
        return
    facts = read_facts(record, needed, "layoutContract.feedback") if needed else {}
    native_facts = read_native_facts(record, native_needed, "layoutContract.feedback") if native_needed else {}
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
        plan_facts = native_facts if node["containerId"] in native_plans else facts
        hidden = _evaluate_action_modifier(invisible, plan_facts, strict=True)
        if hidden is None:
            fail("FEEDBACK_CONDITION_INVALID", path)
        content = plan_facts.get(name) if name else source.get("text")
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
