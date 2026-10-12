#!/usr/bin/env python3
"""Derive the producer's Contract V2 schema declaration from the schema authority.

The sealed contract publishes ``schemaId``/``schemaVersion``/``schemaSha256``/
``normativeStatus`` inside ``meta.lifecycle``. Those bindings are outside the
semantic ``contractSha256`` coverage, so they must be produced from the schema
authority instead of being hand-maintained next to it.

This entry is the single derivation path:

* ``schemaSha256``      <- bytes of ``docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json``
* ``schemaVersion``     <- ``registryVersion`` of the normative enum registry
* ``normativeStatus``   <- ``normativeStatus`` of the normative enum registry
* ``schemaId``          <- the stable producer protocol identifier (not derivable)

``meta.lifecycle.integrity.contractSha256`` carried by those examples is not a
hand-maintained binding either: it is the body seal itself, so it is recomputed
here with the sealing authority (``contract_lifecycle.payload_sha256`` over
``contract_semantic_payload``) instead of being re-implemented.  A commit that
edits an example body without resealing it leaves a seal that does not verify,
which is exactly what ``verify.backend.contract_lifecycle.authority`` catches.

The same authority owns the sealed-contract provenance carried by the canonical
examples under ``docs/architecture/unified_page_contract_v2/examples``: each
example publishes the derived bindings inside ``meta.lifecycle.definition``, and
those bindings are outside semantic ``contractSha256`` coverage, so they must be
produced here too instead of being hand-maintained. This keeps one derivation
path for every in-repo sealed-contract provenance binding.

``--check`` fails when the committed declaration drifts from the authority;
the default mode rewrites ``addons/smart_core/core/contract_lifecycle.py`` and
refreshes the example bindings in place (formatting-preserving).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json"
REGISTRY = ROOT / "docs/architecture/unified_page_contract_v2/enum_registry.json"
LIFECYCLE = ROOT / "addons/smart_core/core/contract_lifecycle.py"
EXAMPLES_DIR = ROOT / "docs/architecture/unified_page_contract_v2/examples"

SCHEMA_ID = "smart_core.unified_page_contract_v2"

# ``meta.lifecycle.definition`` field -> derived declaration constant. The field
# is named exactly as the schema's contractLifecycle definition names it.
DEFINITION_FIELD_BINDINGS = {
    "schemaId": "UNIFIED_PAGE_SCHEMA_ID",
    "schemaVersion": "UNIFIED_PAGE_SCHEMA_VERSION",
    "schemaSha256": "UNIFIED_PAGE_SCHEMA_SHA256",
    "contractVersion": "UNIFIED_PAGE_SCHEMA_VERSION",
    "normativeStatus": "UNIFIED_PAGE_NORMATIVE_STATUS",
}


def derived_declaration() -> dict[str, str]:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return {
        "UNIFIED_PAGE_SCHEMA_ID": SCHEMA_ID,
        "UNIFIED_PAGE_SCHEMA_VERSION": str(registry["registryVersion"]),
        "UNIFIED_PAGE_SCHEMA_SHA256": hashlib.sha256(SCHEMA.read_bytes()).hexdigest(),
        "UNIFIED_PAGE_NORMATIVE_STATUS": str(registry["normativeStatus"]),
    }


def declared_declaration(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for name in derived_declaration():
        match = re.search(rf'^{name} = "([^"]*)"$', text, flags=re.M)
        if match:
            found[name] = match.group(1)
    return found


def render_declaration(text: str, declaration: dict[str, str]) -> str:
    for name, value in declaration.items():
        text = re.sub(rf'^{name} = "[^"]*"$', f'{name} = "{value}"', text, flags=re.M)
    return text


def _object_span(text: str, key: str, start: int = 0) -> tuple[int, int] | None:
    """Text span of the object value of the first ``"key": {`` at/after ``start``.

    A brace/string-aware scan keeps the edit scoped to one object, so a same-named
    key elsewhere in the document is never touched.
    """
    match = re.search(rf'"{re.escape(key)}"\s*:\s*\{{', text[start:])
    if not match:
        return None
    brace = start + match.end() - 1
    depth = 0
    index = brace
    in_string = False
    escaped = False
    while index < len(text):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return brace, index + 1
        index += 1
    return None


def _definition_span(text: str) -> tuple[int, int] | None:
    """Span of ``meta.lifecycle.definition``; ``None`` when the example has none."""
    lifecycle = _object_span(text, "lifecycle")
    if lifecycle is None:
        return None
    return _object_span(text, "definition", lifecycle[0])


def example_files() -> list[Path]:
    return sorted(EXAMPLES_DIR.glob("*.json"))


def load_lifecycle_authority():
    """The sealing authority itself, so the seal is never re-implemented here."""
    spec = importlib.util.spec_from_file_location(
        "contract_schema_declaration_lifecycle", LIFECYCLE
    )
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise SystemExit(f"cannot load the sealing authority: {LIFECYCLE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def example_integrity_span(text: str) -> tuple[int, int] | None:
    """Span of ``meta.lifecycle.integrity``; ``None`` when the example has none."""
    lifecycle = _object_span(text, "lifecycle")
    if lifecycle is None:
        return None
    return _object_span(text, "integrity", lifecycle[0])


def derived_example_integrity(text: str, authority) -> str:
    """The body seal of one example, from the sealing authority's own functions."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"example is not valid json: {exc}") from exc
    return authority.payload_sha256(authority.contract_semantic_payload(payload))


def example_integrity_drift(text: str, derived: str) -> dict[str, Any]:
    """Body-seal drift inside one example's ``meta.lifecycle.integrity``."""
    span = example_integrity_span(text)
    if span is None:
        return {"contractSha256": {"declared": None, "derived": derived}}
    body = text[span[0]: span[1]]
    declared = re.findall(r'"contractSha256"\s*:\s*"([^"]*)"', body)
    if len(declared) != 1:
        return {"contractSha256": {"declared": declared or None, "derived": derived}}
    if declared[0] != derived:
        return {"contractSha256": {"declared": declared[0], "derived": derived}}
    return {}


def render_example_integrity(text: str, derived: str) -> str:
    """Rebind the body seal in place; every other byte (incl. formatting) is kept."""
    span = example_integrity_span(text)
    if span is None:
        return text
    body = text[span[0]: span[1]]
    rendered = re.sub(
        r'("contractSha256"\s*:\s*)"[^"]*"',
        lambda match: f'{match.group(1)}"{derived}"',
        body,
        count=1,
    )
    return text[: span[0]] + rendered + text[span[1]:]


def example_definition_drift(text: str, declaration: dict[str, str]) -> dict[str, Any]:
    """Derived binding drift inside one example's ``meta.lifecycle.definition``."""
    span = _definition_span(text)
    if span is None:
        return {}
    body = text[span[0]: span[1]]
    drift: dict[str, Any] = {}
    for field, source in DEFINITION_FIELD_BINDINGS.items():
        declared = re.findall(rf'"{re.escape(field)}"\s*:\s*"([^"]*)"', body)
        if len(declared) != 1:
            drift[field] = {"declared": declared or None, "derived": declaration[source]}
        elif declared[0] != declaration[source]:
            drift[field] = {"declared": declared[0], "derived": declaration[source]}
    return drift


def render_example_declaration(text: str, declaration: dict[str, str]) -> str:
    """Rebind derived fields in place; every other byte (incl. formatting) is kept."""
    span = _definition_span(text)
    if span is None:
        return text
    body = text[span[0]: span[1]]

    def _replace(match: re.Match[str]) -> str:
        field = match.group("field")
        source = DEFINITION_FIELD_BINDINGS.get(field)
        if source is None:
            return match.group(0)
        return f'"{field}": "{declaration[source]}"'

    rendered = re.sub(r'"(?P<field>[A-Za-z][A-Za-z0-9]*)":\s*"[^"]*"', _replace, body)
    return text[: span[0]] + rendered + text[span[1]:]


def main() -> int:
    text = LIFECYCLE.read_text(encoding="utf-8")
    authority = derived_declaration()
    declared = declared_declaration(text)
    examples = {path: path.read_text(encoding="utf-8") for path in example_files()}
    sealing_authority = load_lifecycle_authority()
    derived_integrity = {
        path: derived_example_integrity(content, sealing_authority)
        for path, content in examples.items()
    }
    if "--check" in sys.argv:
        mismatch: dict[str, Any] = {
            name: {"declared": declared.get(name), "derived": value}
            for name, value in authority.items()
            if declared.get(name) != value
        }
        example_mismatch = {
            str(path.relative_to(ROOT)): drift
            for path, content in examples.items()
            if (drift := example_definition_drift(content, authority))
        }
        integrity_mismatch = {
            str(path.relative_to(ROOT)): drift
            for path, content in examples.items()
            if (drift := example_integrity_drift(content, derived_integrity[path]))
        }
        if mismatch or example_mismatch or integrity_mismatch:
            payload: dict[str, Any] = dict(mismatch)
            if example_mismatch:
                payload["examples"] = example_mismatch
            if integrity_mismatch:
                payload["exampleIntegrity"] = integrity_mismatch
            raise SystemExit("schema declaration drift: " + json.dumps(payload, sort_keys=True))
        print(
            "[contract_schema_declaration_sync] PASS "
            f"sha256={authority['UNIFIED_PAGE_SCHEMA_SHA256'][:12]} "
            f"version={authority['UNIFIED_PAGE_SCHEMA_VERSION']} "
            f"status={authority['UNIFIED_PAGE_NORMATIVE_STATUS']} "
            f"examples={len(examples)}"
        )
        return 0
    LIFECYCLE.write_text(render_declaration(text, authority), encoding="utf-8")
    print(f"[contract_schema_declaration_sync] WROTE {LIFECYCLE.relative_to(ROOT)}")
    for path, content in examples.items():
        rendered = render_example_declaration(content, authority)
        rendered = render_example_integrity(rendered, derived_integrity[path])
        if rendered != content:
            path.write_text(rendered, encoding="utf-8")
            print(f"[contract_schema_declaration_sync] WROTE {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
