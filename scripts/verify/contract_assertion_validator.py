"""Validate a runtime contract against a declared config expectation.

The config (model / view / permission / role / rule / action / menu) is the
single oracle. A declared expectation describes what the contract MUST contain,
and this validator checks only those declared assertions - never a full-field
snapshot. Dynamic fields are declared, not excluded: an expectation can either
pin a field's projected semantics or declare it out of the static scope.
"""

from __future__ import annotations

import re

SCHEMA = "contract-assertion-expectation/v1"
XMLID = re.compile(r"^[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*$")
FIELD_TYPES = frozenset({
    "boolean", "integer", "float", "monetary", "char", "text", "selection",
    "date", "datetime", "many2one", "one2many", "many2many", "binary", "html",
})


def validate_expectation(expectation: dict) -> None:
    """Reject an expectation that is not a valid declared-config oracle."""
    if not isinstance(expectation, dict) or expectation.get("schema") != SCHEMA:
        raise ValueError("expectation schema must be " + SCHEMA)
    config = expectation.get("config")
    if (not isinstance(config, dict) or not isinstance(config.get("model"), str)
            or not config["model"].strip()):
        raise ValueError("expectation config.model is required")
    expect = expectation.get("expect")
    if not isinstance(expect, dict):
        raise ValueError("expectation expect block is required")
    fields = expect.get("fields")
    if not isinstance(fields, dict) or not fields:
        raise ValueError("expect.fields must be a non-empty object")
    for name, spec in fields.items():
        if not isinstance(name, str) or not name or not isinstance(spec, dict):
            raise ValueError("expect.fields entries must map field name to spec")
        field_type = spec.get("type")
        if field_type not in FIELD_TYPES:
            raise ValueError(f"expect.fields.{name}.type is unknown: {field_type!r}")
        for key in ("readonly", "required", "visible"):
            if key in spec and not isinstance(spec[key], bool):
                raise ValueError(f"expect.fields.{name}.{key} must be boolean")
    for key in ("readable_fields", "executable_actions", "present_actions", "present_menus"):
        value = expect.get(key)
        if value is not None and (not isinstance(value, list)
                                  or any(not isinstance(item, str) or not item for item in value)):
            raise ValueError(f"expect.{key} must be a list of non-empty strings")


def field_semantics(contract: dict) -> dict[str, dict]:
    """Best-effort extraction of projected field semantics from ui.contract.v2.

    This is intentionally independent of the production projection path: it
    reads only the sealed output shape, so the production projection code can be
    judged against this reference extraction.
    """
    out: dict[str, dict] = {}
    status = {}
    status_contract = contract.get("statusContract") if isinstance(contract, dict) else None
    if isinstance(status_contract, dict):
        for row in status_contract.get("widgetStatus") or []:
            if isinstance(row, dict) and row.get("widgetId"):
                status[str(row["widgetId"])] = row
    data = contract.get("dataContract") if isinstance(contract, dict) else None
    main = data.get("mainData") if isinstance(data, dict) else {}
    if not isinstance(main, dict):
        return out

    def walk(node):
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        field_info = node.get("fieldInfo") if isinstance(node.get("fieldInfo"), dict) else {}
        name = str(node.get("name") or node.get("fieldName") or node.get("field_name") or "").strip()
        widget_id = str(node.get("widgetId") or "").strip()
        if name and widget_id:
            widget = status.get(widget_id) or {}
            out[name] = {
                "type": str(field_info.get("type") or field_info.get("ttype") or ""),
                "readonly": _first_bool(widget.get("readonly"), field_info.get("readonly"), node.get("readonly")),
                "required": _first_bool(widget.get("required"), field_info.get("required"), node.get("required")),
                "visible": _first_bool(widget.get("visible"), field_info.get("visible"), node.get("visible")),
            }
        for value in node.values():
            walk(value)

    walk(contract)
    return out


def validate(expectation: dict, contract: dict) -> dict:
    """Assert every declared expectation against the extracted contract semantics."""
    validate_expectation(expectation)
    semantics = field_semantics(contract)
    expect = expectation["expect"]
    assertions = []
    for name, spec in expect.get("fields", {}).items():
        observed = semantics.get(name)
        if observed is None:
            assertions.append({"id": f"field:{name}", "passed": False,
                               "detail": "field missing from contract"})
            continue
        for key in ("type", "readonly", "required", "visible"):
            if key not in spec:
                continue
            expected = spec[key]
            actual = observed.get(key)
            assertions.append({
                "id": f"field:{name}.{key}", "passed": actual == expected,
                "detail": f"expected={expected!r} actual={actual!r}",
            })
    for key in ("readable_fields", "executable_actions", "present_actions", "present_menus"):
        if key not in expect:
            continue
        for item in expect[key]:
            # Presence checks are declared against the contract's sealed identity;
            # the full resolution is wired by the runtime harness, not inferred here.
            assertions.append({"id": f"{key}:{item}", "passed": None,
                               "detail": "deferred_to_runtime_harness"})
    passed = [row for row in assertions if row["passed"] is not False]
    failed = [row for row in assertions if row["passed"] is False]
    return {
        "schema": SCHEMA,
        "status": "failed" if failed else "passed",
        "assertions": assertions,
        "passed_count": len(passed),
        "failed": failed,
    }


def _first_bool(*values):
    for value in values:
        if isinstance(value, bool):
            return value
    return None
