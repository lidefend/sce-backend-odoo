# -*- coding: utf-8 -*-
"""Contract version consumer-compatibility core.

The third L5 gap of the backend contract lifecycle is the missing automatic
N-1/N+1 consumer-compatibility and rollback drill. The lifecycle already appends
a new contract version for every definition change and rolls back by appending a
*higher* version, but nothing proves automatically that a consumer of one version
still works against its adjacent versions.

This module owns the decision logic, expressed as data over *declarations*
rather than over rendered strings:

* ``compare_declarations`` classifies a version delta as ``additive`` or
  ``breaking`` (removed key, newly required key, changed type, removed enum
  member and tightened required flag are breaking; the reverse moves are
  additive);
* ``check_consumer`` decides whether a consumer declaration can read a payload.
  Unknown payload keys are tolerated, which is exactly what makes additive
  evolution safe; a missing required key, a type mismatch or an out-of-enum value
  is a refusal with a specific reason;
* ``drill_adjacent`` runs the N-1 / N / N+1 matrix in both directions and returns
  named checks, so the drill result is a declaration the caller can assert on;
* ``append_only_rollback`` proves a rollback appends a strictly higher version
  instead of rewriting history.

It imports nothing from Odoo so the semantics stay offline-verifiable.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence


COMPATIBILITY_VERSION = "1.0.0"

DELTA_ADDITIVE = "additive"
DELTA_BREAKING = "breaking"
DELTA_IDENTICAL = "identical"

REASON_OPTIONAL_KEY_ADDED = "optional_key_added"
REASON_REQUIRED_RELAXED = "required_relaxed"
REASON_ENUM_MEMBER_ADDED = "enum_member_added"
REASON_KEY_REMOVED = "key_removed"
REASON_REQUIRED_KEY_ADDED = "required_key_added"
REASON_REQUIRED_TIGHTENED = "required_tightened"
REASON_TYPE_CHANGED = "type_changed"
REASON_ENUM_MEMBER_REMOVED = "enum_member_removed"
REASON_ENUM_MEMBER_ADDED_TO_CLOSED_ENUM = "enum_member_added_to_closed_enum"

ADDITIVE_REASONS = (
    REASON_OPTIONAL_KEY_ADDED,
    REASON_REQUIRED_RELAXED,
    REASON_ENUM_MEMBER_ADDED,
)
BREAKING_REASONS = (
    REASON_KEY_REMOVED,
    REASON_REQUIRED_KEY_ADDED,
    REASON_REQUIRED_TIGHTENED,
    REASON_TYPE_CHANGED,
    REASON_ENUM_MEMBER_REMOVED,
    REASON_ENUM_MEMBER_ADDED_TO_CLOSED_ENUM,
)

REASON_MISSING_REQUIRED_KEY = "missing_required_key"
REASON_TYPE_MISMATCH = "type_mismatch"
REASON_ENUM_VALUE_NOT_ALLOWED = "enum_value_not_allowed"

PAYLOAD_TYPES = ("string", "integer", "number", "boolean", "object", "array", "null")


class CompatibilityError(ValueError):
    """Raised when a declaration or payload cannot be interpreted."""


def normalize_declaration(declaration: Any) -> dict[str, dict[str, Any]]:
    """Normalise ``key -> type`` or ``key -> {type, required, enum}`` to one shape."""

    if not isinstance(declaration, Mapping):
        raise CompatibilityError("declaration must be a mapping")
    normalized: dict[str, dict[str, Any]] = {}
    for key, value in declaration.items():
        name = str(key)
        if isinstance(value, str):
            normalized[name] = {"type": value, "required": True, "enum": (), "open_enum": False}
        elif isinstance(value, Mapping):
            entry = {
                "type": str(value.get("type") or "any"),
                "required": bool(value.get("required", True)),
                "enum": tuple(value.get("enum") or ()),
                # An open enum declares that consumers tolerate values they do
                # not know, which is what makes adding a member additive. A
                # closed enum keeps the strict reading.
                "open_enum": bool(value.get("open_enum", False)),
            }
            normalized[name] = entry
        else:
            raise CompatibilityError("declaration entry for %s must be a type name or mapping" % name)
    return normalized


def compare_declarations(older: Any, newer: Any) -> dict[str, Any]:
    """Classify the delta from ``older`` to ``newer`` fail-closed."""

    left = normalize_declaration(older)
    right = normalize_declaration(newer)
    findings: list[dict[str, Any]] = []
    for key, old_entry in left.items():
        new_entry = right.get(key)
        if new_entry is None:
            findings.append({"key": key, "reason": REASON_KEY_REMOVED})
            continue
        if old_entry["type"] != new_entry["type"]:
            findings.append({"key": key, "reason": REASON_TYPE_CHANGED,
                             "from": old_entry["type"], "to": new_entry["type"]})
        if old_entry["required"] and not new_entry["required"]:
            findings.append({"key": key, "reason": REASON_REQUIRED_RELAXED})
        if not old_entry["required"] and new_entry["required"]:
            findings.append({"key": key, "reason": REASON_REQUIRED_TIGHTENED})
        removed = [value for value in old_entry["enum"] if value not in new_entry["enum"]]
        if removed:
            findings.append({"key": key, "reason": REASON_ENUM_MEMBER_REMOVED, "removed": removed})
        added = [value for value in new_entry["enum"] if value not in old_entry["enum"]]
        if added:
            reason = REASON_ENUM_MEMBER_ADDED if new_entry["open_enum"] else REASON_ENUM_MEMBER_ADDED_TO_CLOSED_ENUM
            findings.append({"key": key, "reason": reason, "added": added})
    for key, new_entry in right.items():
        if key in left:
            continue
        findings.append({
            "key": key,
            "reason": REASON_REQUIRED_KEY_ADDED if new_entry["required"] else REASON_OPTIONAL_KEY_ADDED,
        })
    breaking = [finding for finding in findings if finding["reason"] in BREAKING_REASONS]
    if breaking:
        delta = DELTA_BREAKING
    elif findings:
        delta = DELTA_ADDITIVE
    else:
        delta = DELTA_IDENTICAL
    return {
        "compatibilityVersion": COMPATIBILITY_VERSION,
        "delta": delta,
        "breaking": bool(breaking),
        "findings": sorted(findings, key=lambda item: (item["key"], item["reason"])),
        "breakingCount": len(breaking),
        "findingCount": len(findings),
    }


def _matches_type(value: Any, expected: str) -> bool:
    if expected in ("any", ""):
        return True
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "object":
        return isinstance(value, Mapping)
    if expected == "array":
        return isinstance(value, (list, tuple))
    if expected == "null":
        return value is None
    raise CompatibilityError("unknown declared type: %s" % expected)


def check_consumer(consumer_declaration: Any, payload: Any) -> dict[str, Any]:
    """Decide whether a consumer can read a payload.

    Unknown payload keys are tolerated (additive evolution). A missing required
    key, a type mismatch or an out-of-enum value is a refusal.
    """

    declaration = normalize_declaration(consumer_declaration)
    if not isinstance(payload, Mapping):
        return {"compatible": False, "refusals": [{"key": "", "reason": "payload_not_object"}],
                "checkedKeys": 0}
    refusals: list[dict[str, Any]] = []
    for key, entry in sorted(declaration.items()):
        if key not in payload:
            if entry["required"]:
                refusals.append({"key": key, "reason": REASON_MISSING_REQUIRED_KEY})
            continue
        value = payload[key]
        if not _matches_type(value, entry["type"]):
            refusals.append({"key": key, "reason": REASON_TYPE_MISMATCH,
                             "expected": entry["type"], "actual": type(value).__name__})
            continue
        if entry["enum"] and value not in entry["enum"] and not entry["open_enum"]:
            refusals.append({"key": key, "reason": REASON_ENUM_VALUE_NOT_ALLOWED,
                             "allowed": list(entry["enum"])})
    return {
        "compatibilityVersion": COMPATIBILITY_VERSION,
        "compatible": not refusals,
        "refusals": refusals,
        "checkedKeys": len(declaration),
    }


def append_only_rollback(version_sequence: Sequence[int]) -> tuple[bool, str]:
    """A rollback must append a strictly higher version, never rewrite history."""

    numbers = [int(value) for value in version_sequence]
    if not numbers:
        return False, "empty_version_sequence"
    for previous, current in zip(numbers, numbers[1:]):
        if current <= previous:
            return False, "version_not_strictly_increasing:%d->%d" % (previous, current)
    return True, "ok"


def drill_adjacent(versions: Mapping[str, Any], payloads: Mapping[str, Any]) -> dict[str, Any]:
    """Run the N-1 / N / N+1 consumer-compatibility matrix in both directions.

    ``versions`` and ``payloads`` must each carry the keys ``n_minus_one``,
    ``n`` and ``n_plus_one``.
    """

    required_keys = ("n_minus_one", "n", "n_plus_one")
    for label, mapping in (("versions", versions), ("payloads", payloads)):
        missing = [key for key in required_keys if key not in mapping]
        if missing:
            raise CompatibilityError("%s missing keys: %s" % (label, ",".join(missing)))
    delta_lower = compare_declarations(versions["n_minus_one"], versions["n"])
    delta_upper = compare_declarations(versions["n"], versions["n_plus_one"])
    forward = check_consumer(versions["n_minus_one"], payloads["n"])
    backward = check_consumer(versions["n"], payloads["n_minus_one"])
    rollback = check_consumer(versions["n"], payloads["n_plus_one"])
    upgrade = check_consumer(versions["n_plus_one"], payloads["n"])
    checks = [
        ("delta_n_minus_one_to_n_is_additive", not delta_lower["breaking"], delta_lower),
        ("delta_n_to_n_plus_one_is_additive", not delta_upper["breaking"], delta_upper),
        ("n_minus_one_consumer_reads_n_payload", bool(forward["compatible"]), forward),
        ("n_consumer_reads_n_minus_one_payload", bool(backward["compatible"]), backward),
        ("n_consumer_reads_n_plus_one_payload_after_rollback", bool(rollback["compatible"]), rollback),
        ("n_plus_one_consumer_reads_n_payload", bool(upgrade["compatible"]), upgrade),
    ]
    failed = [name for name, ok, _detail in checks if not ok]
    return {
        "compatibilityVersion": COMPATIBILITY_VERSION,
        "versions": list(required_keys),
        "checkCount": len(checks),
        "failedCount": len(failed),
        "failed": failed,
        "checks": [{"name": name, "ok": ok, "detail": detail} for name, ok, detail in checks],
        "deltaLower": delta_lower,
        "deltaUpper": delta_upper,
    }


def check_names() -> tuple[str, ...]:
    """Declaration consumed by tests and guards instead of a duplicated list."""

    return (
        "delta_n_minus_one_to_n_is_additive",
        "delta_n_to_n_plus_one_is_additive",
        "n_minus_one_consumer_reads_n_payload",
        "n_consumer_reads_n_minus_one_payload",
        "n_consumer_reads_n_plus_one_payload_after_rollback",
        "n_plus_one_consumer_reads_n_payload",
    )


def json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, Mapping):
        return "object"
    if isinstance(value, (list, tuple)):
        return "array"
    return "any"


def declaration_from_payload(payload: Any, *, prefix: str = "") -> dict[str, dict[str, Any]]:
    """Project a payload's key surface into a consumer declaration.

    Generic on purpose: no model-, view- or business-specific rule. Every present
    leaf path is declared optional so that *adding* a path is additive and
    *removing* one is breaking, and every leaf records its JSON type so a type
    change is breaking. List elements are expanded by position so an appended
    element is a new path (additive) rather than an opaque array replace. An empty
    mapping declares no leaf surface and therefore contributes no declaration:
    emitting one would add a spurious ``optional_key_added`` finding and mask the
    real breaking removal of a nested leaf.
    """

    out: dict[str, dict[str, Any]] = {}
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            path = "%s.%s" % (prefix, key) if prefix else str(key)
            if isinstance(value, Mapping):
                if value:
                    out.update(declaration_from_payload(value, prefix=path))
            elif isinstance(value, (list, tuple)):
                if value:
                    for index, item in enumerate(value):
                        out.update(declaration_from_payload(item, prefix="%s[%d]" % (path, index)))
                else:
                    out[path] = {"type": "array", "required": False, "enum": ()}
            else:
                out[path] = {"type": json_type(value), "required": False, "enum": ()}
        return out
    out[prefix or "."] = {"type": json_type(payload), "required": False, "enum": ()}
    return out
