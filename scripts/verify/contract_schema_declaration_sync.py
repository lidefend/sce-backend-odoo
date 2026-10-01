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

``--check`` fails when the committed declaration drifts from the authority;
the default mode rewrites ``addons/smart_core/core/contract_lifecycle.py``.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json"
REGISTRY = ROOT / "docs/architecture/unified_page_contract_v2/enum_registry.json"
LIFECYCLE = ROOT / "addons/smart_core/core/contract_lifecycle.py"

SCHEMA_ID = "smart_core.unified_page_contract_v2"


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


def main() -> int:
    text = LIFECYCLE.read_text(encoding="utf-8")
    authority = derived_declaration()
    declared = declared_declaration(text)
    if "--check" in sys.argv:
        mismatch = {
            name: {"declared": declared.get(name), "derived": value}
            for name, value in authority.items()
            if declared.get(name) != value
        }
        if mismatch:
            raise SystemExit(f"schema declaration drift: {json.dumps(mismatch, sort_keys=True)}")
        print(
            "[contract_schema_declaration_sync] PASS "
            f"sha256={authority['UNIFIED_PAGE_SCHEMA_SHA256'][:12]} "
            f"version={authority['UNIFIED_PAGE_SCHEMA_VERSION']} "
            f"status={authority['UNIFIED_PAGE_NORMATIVE_STATUS']}"
        )
        return 0
    LIFECYCLE.write_text(render_declaration(text, authority), encoding="utf-8")
    print(f"[contract_schema_declaration_sync] WROTE {LIFECYCLE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
