#!/usr/bin/env python3
"""Fail-closed lint for the delivered form-structure vocabulary.

Contract Runtime boundary fix (FE-CONTRACT-RUNTIME-01): the delivered contract
used to publish one ``layoutPolicy`` string that mixed three different facts
together -- where the body structure comes from, which carrier is the final
structural authority, and (in some producers) the rendering implementation that
happened to consume it.  The payload now names the two facts separately:

* ``structureSource``    -- where the delivered body structure comes from;
* ``structureAuthority`` -- which carrier is the final structural authority.

The defect this closes is a vocabulary that *describes implementation history*
instead of the fact.  This lint therefore refuses, in any contract payload
surface:

1. the retired ``layoutPolicy`` field name; and
2. every value that only made sense as that field's implementation-era spelling.

It also requires both facts to be declared in exactly the reconciled shape, in
all four carriers at once (backend schema, strict decoder literals, strict type
literals, and the producers that actually publish them), so a new vocabulary
sentinel cannot be added on one side only.

It does not judge what a page may render, and it does not accept the retired
spelling as a compatibility alias: an alias is exactly the drift this guards.
Test suites are deliberately out of scope -- a test may inject a retired value
to prove that the decoder refuses it.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SCHEMA_REL = Path("docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json")
DECODER_REL = Path("frontend/apps/web/src/app/contracts/v2/schema.ts")
TYPES_REL = Path("frontend/apps/web/src/app/contracts/v2/types.ts")

# The contract payload surface: producers that publish the structure contract and
# consumers that decode it.  ``addons/*/tests/`` and ``frontend/apps/web/scripts/``
# are excluded on purpose (see the module docstring).
PAYLOAD_RELS = (
    Path("addons/smart_core/handlers/ui_contract_v2.py"),
    Path("addons/smart_core/handlers/ui_contract_v2_projection.py"),
    Path("addons/smart_core/core/unified_page_contract_v2_assembler.py"),
    Path("addons/smart_core/core/unified_page_contract_v2_runtime.py"),
    Path("addons/smart_core/core/unified_page_contract_v2_client.py"),
    DECODER_REL,
    TYPES_REL,
    Path("frontend/apps/web/src/app/contracts/v2/store.ts"),
)

RETIRED_LAYOUT_FIELD = "layoutPolicy"
RETIRED_LAYOUT_VALUES = (
    "container_tree_authority",
    "business_config_sections",
    "overview_then_task_slots",
    "category_sections_as_task_tabs",
    "governed_slots",
)

STRUCTURE_SOURCE_FIELD = "structureSource"
STRUCTURE_AUTHORITY_FIELD = "structureAuthority"
STRUCTURE_SOURCES = (
    "native_view",
    "business_orchestration",
    "business_category_policy",
    "entry_semantic_surface",
)
STRUCTURE_AUTHORITIES = ("container_tree", "native_form_slots", "task_sections")
CONTAINER_TREE_AUTHORITY = "container_tree"

RETIRED_FIELD_RE = re.compile(rf"\b{re.escape(RETIRED_LAYOUT_FIELD)}\b")
DECODER_ARRAY_RE = re.compile(
    r"const\s+(?P<name>FORM_STRUCTURE_[A-Z]+)\s*=\s*\[(?P<body>[^\]]*)\]\s*as const;"
)
TYPES_UNION_RE = re.compile(r"export\s+type\s+(?P<name>\w+)\s*=\s*(?P<body>[^;]+);")
STRING_LITERAL_RE = re.compile(r"'([^']*)'")


def _declared_literals(body):
    return STRING_LITERAL_RE.findall(body)


def _decoder_arrays(source):
    return {
        match.group("name"): _declared_literals(match.group("body"))
        for match in DECODER_ARRAY_RE.finditer(source)
    }


def _type_unions(source):
    return {
        match.group("name"): _declared_literals(match.group("body"))
        for match in TYPES_UNION_RE.finditer(source)
    }


def run(root):
    errors = []
    surfaces = {}
    for rel in (SCHEMA_REL, *PAYLOAD_RELS):
        path = root / rel
        if not path.is_file():
            errors.append(f"{rel.as_posix()}: required contract payload surface is missing")
            continue
        surfaces[rel.as_posix()] = path.read_text(encoding="utf-8")

    # 1/2 -- the retired implementation vocabulary must not exist anywhere on the
    # payload surface.
    for rel, source in surfaces.items():
        if rel == SCHEMA_REL.as_posix():
            continue
        if RETIRED_FIELD_RE.search(source):
            errors.append(
                f"{rel}: contract payload must not publish or read the retired "
                f"'{RETIRED_LAYOUT_FIELD}' field; declare {STRUCTURE_SOURCE_FIELD} and {STRUCTURE_AUTHORITY_FIELD}"
            )
        for value in RETIRED_LAYOUT_VALUES:
            if value in source:
                errors.append(
                    f"{rel}: retired layout vocabulary '{value}' must not appear in a contract "
                    "payload; the delivered structure contract names the fact, not the implementation era"
                )

    # 3 -- the backend schema is the declaration authority for both facts.
    schema_source = surfaces.get(SCHEMA_REL.as_posix())
    schema_contract = {}
    if schema_source is not None:
        payload = json.loads(schema_source)
        schema_contract = (payload.get("$defs") or {}).get("formStructureContract") or {}
        if not schema_contract:
            errors.append(f"{SCHEMA_REL.as_posix()}: $defs.formStructureContract is missing")
        else:
            properties = schema_contract.get("properties") or {}
            required = set(schema_contract.get("required") or [])
            for field, expected in (
                (STRUCTURE_SOURCE_FIELD, STRUCTURE_SOURCES),
                (STRUCTURE_AUTHORITY_FIELD, STRUCTURE_AUTHORITIES),
            ):
                if field not in required:
                    errors.append(
                        f"{SCHEMA_REL.as_posix()}: formStructureContract.required must declare {field}"
                    )
                declared = list((properties.get(field) or {}).get("enum") or [])
                if declared != list(expected):
                    errors.append(
                        f"{SCHEMA_REL.as_posix()}: formStructureContract.{field} enum must be "
                        f"{list(expected)}; declared={declared}"
                    )
            if RETIRED_LAYOUT_FIELD in properties or RETIRED_LAYOUT_FIELD in required:
                errors.append(
                    f"{SCHEMA_REL.as_posix()}: formStructureContract must not declare '{RETIRED_LAYOUT_FIELD}'"
                )
            tree_guards = [
                (rule.get("if") or {}).get("properties") or {}
                for rule in (schema_contract.get("allOf") or [])
            ]
            if not any(
                (guard.get(STRUCTURE_AUTHORITY_FIELD) or {}).get("const") == CONTAINER_TREE_AUTHORITY
                for guard in tree_guards
            ):
                errors.append(
                    f"{SCHEMA_REL.as_posix()}: formStructureContract must bind the container-tree rule to "
                    f"{STRUCTURE_AUTHORITY_FIELD}=={CONTAINER_TREE_AUTHORITY}"
                )

    # 4 -- the strict decoder and the strict types must declare exactly the same
    # two enumerations.  Four carriers, one vocabulary.
    decoder_source = surfaces.get(DECODER_REL.as_posix())
    types_source = surfaces.get(TYPES_REL.as_posix())
    if decoder_source is not None:
        arrays = _decoder_arrays(decoder_source)
        for name, expected in (
            ("FORM_STRUCTURE_SOURCES", STRUCTURE_SOURCES),
            ("FORM_STRUCTURE_AUTHORITIES", STRUCTURE_AUTHORITIES),
        ):
            declared = arrays.get(name)
            if declared is None:
                errors.append(f"{DECODER_REL.as_posix()}: missing '{name}' literal declaration")
            elif declared != list(expected):
                errors.append(
                    f"{DECODER_REL.as_posix()}: {name} must be {list(expected)}; declared={declared}"
                )
    if types_source is not None:
        unions = _type_unions(types_source)
        for name, expected in (
            ("ContractV2FormStructureSource", STRUCTURE_SOURCES),
            ("ContractV2FormStructureAuthority", STRUCTURE_AUTHORITIES),
        ):
            declared = unions.get(name)
            if declared is None:
                errors.append(f"{TYPES_REL.as_posix()}: missing strict type '{name}'")
            elif declared != list(expected):
                errors.append(
                    f"{TYPES_REL.as_posix()}: {name} must be {list(expected)}; declared={declared}"
                )
        if RETIRED_FIELD_RE.search(types_source):
            errors.append(
                f"{TYPES_REL.as_posix()}: ContractV2FormStructureContract must not declare "
                f"'{RETIRED_LAYOUT_FIELD}'"
            )

    # 5 -- the fact vocabulary must actually be published, not merely declared.
    producers = "".join(
        source for rel, source in surfaces.items() if rel.endswith(".py")
    )
    for field in (STRUCTURE_SOURCE_FIELD, STRUCTURE_AUTHORITY_FIELD):
        if f'"{field}"' not in producers:
            errors.append(
                f"addons/smart_core: no contract producer publishes '{field}'; a declared fact "
                "that nothing emits is a declaration gap"
            )

    summary = {
        "payload_surfaces": len(surfaces),
        "structure_sources": list(STRUCTURE_SOURCES),
        "structure_authorities": list(STRUCTURE_AUTHORITIES),
        "retired_values": list(RETIRED_LAYOUT_VALUES),
        "schema_contract_fields": sorted(schema_contract.get("properties") or {}) if schema_contract else [],
    }
    return errors, summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--json", default="")
    args = parser.parse_args()
    errors, summary = run(Path(args.root).resolve())
    if args.json:
        Path(args.json).write_text(
            json.dumps({"errors": errors, "summary": summary}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if errors:
        print("[layout_vocabulary_lint] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "[layout_vocabulary_lint] PASS "
        f"surfaces={summary['payload_surfaces']} "
        f"sources={len(STRUCTURE_SOURCES)} authorities={len(STRUCTURE_AUTHORITIES)} "
        f"retired_values={len(RETIRED_LAYOUT_VALUES)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
