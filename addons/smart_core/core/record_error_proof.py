"""Request-local proof for reviewed native record errors (not a wire protocol).

Only backend callers may supply the native tree and ORM record. No snapshots,
cached authorizations, page-authored evidence, or field-name fallback are accepted.
Review evidence is attached to the native compute function, not a second registry.
It attests a human source/consumer review; it cannot mechanically prove arbitrary
Python semantics. Unreviewed sources fail closed. No production sources are enrolled.
"""
from dataclasses import dataclass
import hashlib
import inspect
from pathlib import Path
import re
import textwrap

from .form_configuration_compiler import FormConfigurationError


@dataclass(frozen=True)
class RecordErrorReview:
    code: str
    content_field: str
    active_field: str
    implementation_sha256: str
    dependencies: tuple
    # Actual owners, including any legacy owner found by source review.
    owners: tuple
    # (channel, source file, SHA256) for inspected producer/consumer paths.
    # Must be shipped/available for verification; no message copy or side registry.
    evidence: tuple


REVIEW_PATHS = frozenset({"producer", "field_error", "error_summary", "operation_result", "action_guidance"})


def implementation_digest(method):
    """Pin review to the actual compute implementation, not its name."""
    return hashlib.sha256(textwrap.dedent(inspect.getsource(method)).encode()).hexdigest()


def _fail(code, target):
    raise FormConfigurationError(code, target)


def _source(target):
    _fail("FEEDBACK_SOURCE_INVALID", target)


def declarations(model):
    """Read only native _fields; never fields_get or layout fieldInfo metadata."""
    result, codes = {}, set()
    for name, field in model._fields.items():
        declaration = getattr(field, "sc_record_error", None)
        if declaration is None:
            continue
        target = "sc_record_error"
        if (type(declaration) is not dict or set(declaration) != {"code", "active_field", "presentation_owner"}
                or type(declaration["code"]) is not str
                or re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", declaration["code"]) is None
                or declaration["presentation_owner"] != "record_feedback"
                or type(declaration["active_field"]) is not str):
            _source(target)
        code, active = declaration["code"], declaration["active_field"]
        active_field = model._fields.get(active)
        if (field.type not in {"char", "text"} or active_field is None or active_field.type != "boolean"
                or code in codes):
            _source(target)
        for item in (field, active_field):
            if (not getattr(item, "compute", None) or not getattr(item, "readonly", False)
                    or getattr(item, "inverse", None) or getattr(item, "related", None)
                    or getattr(item, "compute_sudo", True)):
                _source(target)
        if field.compute != active_field.compute or type(field.compute) is not str:
            _source(target)
        codes.add(code)
        result[name] = dict(declaration)
    return result


def _review(record, name, declaration, target):
    method = getattr(record, record._fields[name].compute, None)
    review = getattr(method, "_sc_record_error_review", None)
    if not isinstance(review, RecordErrorReview):
        _source(target)
    try:
        digest = implementation_digest(method)
    except (OSError, TypeError):
        _source(target)
    if ((review.code, review.content_field, review.active_field) !=
            (declaration["code"], name, declaration["active_field"])
            or review.implementation_sha256 != digest
            or type(review.dependencies) is not tuple or not review.dependencies
            or review.dependencies != getattr(method, "_depends", None)):
        _source(target)
    # First version permits only direct, stored scalar facts as dependencies.
    # Computed/related/dotted dependencies need a separately reviewed proof chain.
    for dependency in review.dependencies:
        if type(dependency) is not str or not dependency.isidentifier():
            _source(target)
        field = record._fields.get(dependency)
        if (field is None or field.type not in {"char", "text", "boolean", "integer", "float", "date", "datetime", "selection", "monetary"}
                or getattr(field, "compute", None) or getattr(field, "related", None)
                or not getattr(field, "store", False)):
            _source(target)
    if (type(review.evidence) is not tuple or len(review.evidence) != len(REVIEW_PATHS)
            or any(type(row) is not tuple or len(row) != 3 or type(row[0]) is not str
                   or type(row[1]) is not str or not row[1].strip()
                   or type(row[2]) is not str for row in review.evidence)
            or {row[0] for row in review.evidence} != REVIEW_PATHS
            or review.owners != ("record_feedback",)):
        _fail("FEEDBACK_OWNERSHIP_CONFLICT", target)
    # Source review becomes stale when an audited consumer changes. References
    # alone are not evidence. These paths come ONLY from trusted native code.
    for channel, path, digest in review.evidence:
        try:
            actual = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        except (OSError, ValueError):
            _fail("FEEDBACK_OWNERSHIP_CONFLICT", target)
        if actual != digest:
            _fail("FEEDBACK_OWNERSHIP_CONFLICT", target)
        if channel == "producer" and Path(path).resolve() != Path(inspect.getsourcefile(method)).resolve():
            _source(target)
    return review


def _nodes(rows):
    if type(rows) is not list:
        _source("layout")
    for row in rows:
        if not isinstance(row, dict):
            _source("layout")
        yield row
        yield from _nodes(row.get("children", []))


def _context(record):
    return (record._name, record.id, id(record.env), record.env.uid,
            record.env.company.id, tuple(record.env.companies.ids), record.env.su)


def validate_record_errors(record, final_nodes, native_nodes, *, action_rules):
    """Return enabled feedback container IDs, for THIS call only; mutate nothing.

    Inputs are normalized pre-pruning node forests. native_nodes must be the
    backend native projection before user overlays. Integration belongs to 02B3.
    No values/proof tokens are returned; call again for every assembly/record/env.
    """
    nodes, native = list(_nodes(final_nodes)), list(_nodes(native_nodes))
    errors = [node for node in nodes if node.get("componentKey") == "sc.feedback.message"
              and isinstance(node.get("componentConfig"), dict)
              and node["componentConfig"].get("purpose") == "error"]
    if not errors:
        return ()
    target = "componentConfig.contentRef"
    if len(record) != 1 or type(record.id) is not int or record.id <= 0 or record.env.su:
        _fail("FEEDBACK_SOURCE_FORBIDDEN", target)
    context = _context(record)
    try:
        record.check_access_rights("read")
        record.check_access_rule("read")
    except PermissionError:
        _fail("FEEDBACK_SOURCE_FORBIDDEN", target)
    except Exception as exc:
        # Odoo AccessError is not a Python PermissionError. Do not expose details.
        if exc.__class__.__name__ in {"AccessError", "AccessDenied", "MissingError"}:
            _fail("FEEDBACK_SOURCE_FORBIDDEN", target)
        raise
    declared = declarations(record)
    plans, seen = [], set()
    for node in errors:
        node_id = node.get("containerId")
        target = f"layout.{node_id}.componentConfig" if isinstance(node_id, str) else "layout.componentConfig"
        config = node["componentConfig"]
        if (not isinstance(node_id, str) or not node_id or sum(n.get("containerId") == node_id for n in nodes) != 1
                or set(config) != {"purpose", "contentRef"} or type(config["contentRef"]) is not dict
                or set(config["contentRef"]) != {"containerId"}
                or type(config["contentRef"]["containerId"]) is not str):
            _source(target)
        matches = [n for n in nodes if n.get("containerId") == config["contentRef"]["containerId"]]
        if len(matches) != 1:
            _source(target)
        source = matches[0]
        locator, occurrence = source.get("nativeLocator"), source.get("occurrenceIndex")
        if (source.get("type") != "field" or not isinstance(locator, str) or not locator
                or type(occurrence) is not int or occurrence < 0):
            _source(target)
        originals = [n for n in native if n.get("nativeLocator") == locator and n.get("occurrenceIndex") == occurrence]
        if len(originals) != 1:
            _source(target)
        original = originals[0]
        if (not original.get("sourceAuthority") or any(source.get(k) != original.get(k)
                for k in ("type", "name", "containerId", "sourceAuthority"))):
            _source(target)
        name = original.get("name")
        declaration = declared.get(name)
        if declaration is None:
            _source(target)
        review = _review(record, name, declaration, target)
        for action in action_rules:
            guidance = (action.get("presentation") or {}).get("action_guidance") or {}
            if guidance.get("field") in {name, review.active_field}:
                _fail("FEEDBACK_OWNERSHIP_CONFLICT", target)
        identity = (record._name, record.id, record.env.company.id, review.code)
        if identity in seen:
            _fail("FEEDBACK_OWNERSHIP_CONFLICT", target)
        seen.add(identity)
        # Exact compiled form: invisible = NOT active. No expression equivalence
        # guessing and no config-supplied condition or alternate activation field.
        condition = {"kind": "not", "expr": {"kind": "field_truthy", "field": review.active_field}}
        if type(node.get("modifiers")) is not dict or node["modifiers"].get("invisible") != condition:
            _fail("FEEDBACK_CONDITION_INVALID", target)
        fields = list(dict.fromkeys((name, review.active_field, *review.dependencies)))
        try:
            allowed = record.check_field_access_rights("read", fields)
            if allowed is None or not set(fields).issubset(allowed):
                _fail("FEEDBACK_SOURCE_FORBIDDEN", target)
        except FormConfigurationError:
            raise
        except Exception as exc:
            if isinstance(exc, PermissionError) or exc.__class__.__name__ in {"AccessError", "AccessDenied"}:
                _fail("FEEDBACK_SOURCE_FORBIDDEN", target)
            raise
        plans.append((node_id, name, review.active_field, fields, target))
    # All structure, permission and ownership checks precede visibility/value reads.
    if _context(record) != context:
        _fail("FEEDBACK_SOURCE_FORBIDDEN", target)
    fields = list(dict.fromkeys(field for plan in plans for field in plan[3]))
    try:
        values = record.read(fields)
    except Exception as exc:
        if isinstance(exc, PermissionError) or exc.__class__.__name__ in {"AccessError", "AccessDenied", "MissingError"}:
            _fail("FEEDBACK_SOURCE_FORBIDDEN", target)
        raise
    if _context(record) != context:
        _fail("FEEDBACK_SOURCE_FORBIDDEN", target)
    enabled = []
    for node_id, name, active, fields, target in plans:
        if len(values) != 1 or values[0].get("id") != context[1] or type(values[0].get(active)) is not bool:
            _source(target)
        if not values[0][active]:
            continue
        content = values[0].get(name)
        if not isinstance(content, str) or not content.strip():
            _fail("FEEDBACK_CONTENT_MISSING", target)
        enabled.append(node_id)
    return tuple(enabled)
