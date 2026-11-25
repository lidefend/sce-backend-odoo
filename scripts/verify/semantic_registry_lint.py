#!/usr/bin/env python3
"""Validate Contract V2.7 semantic/implementation ownership and generated carriers."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "contract"))
import generate_semantic_registry as carrier  # noqa: E402

SCHEMA_REL = Path("contracts/registry/registry.schema.json")
ENUM_REGISTRY_REL = Path("docs/architecture/unified_page_contract_v2/enum_registry.json")
BACKEND_COMPONENT_FACTS = (
    re.compile(r'["\']componentKey["\']\s*:'),
    re.compile(r'["\']component_key["\']\s*:'),
    re.compile(r'["\']componentRegistry["\']\s*:'),
)


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def duplicate_yaml_keys(text: str, section: str) -> list[str]:
    duplicates: list[str] = []
    in_section = False
    seen: set[str] = set()
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()
        if indent == 0:
            in_section = bool(re.match(rf"{re.escape(section)}\s*:", stripped))
            seen = set()
            continue
        if not in_section or indent != 2:
            continue
        match = re.match(r"^([A-Za-z0-9_.\-]+)\s*:", stripped)
        if not match:
            continue
        key = match.group(1)
        if key in seen:
            duplicates.append(f"{section}.{key}")
        seen.add(key)
    return duplicates


def backend_component_facts(root: Path) -> list[tuple[str, int]]:
    """Production backend code may not own frontend component identity."""
    found: list[tuple[str, int]] = []
    base = root / "addons"
    if not base.is_dir():
        return found
    for path in sorted(base.rglob("*.py")):
        rel = path.relative_to(root)
        if "tests" in rel.parts or "__pycache__" in rel.parts:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if line.lstrip().startswith("#"):
                continue
            if any(pattern.search(line) for pattern in BACKEND_COMPONENT_FACTS):
                found.append((rel.as_posix(), number))
    return found


def contract_semantic_references(root: Path) -> list[tuple[str, str]]:
    references: list[tuple[str, str]] = []
    contracts = root / "contracts"
    for path in sorted(contracts.rglob("*.yaml")):
        if path.parent == root / "contracts/registry":
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.lstrip().startswith("#"):
                continue
            match = re.match(r"\s*semantic:\s*([A-Za-z0-9_]+)\s*$", line)
            if match:
                references.append((path.relative_to(root).as_posix(), match.group(1)))
    return references


def run(root: Path = ROOT) -> tuple[list[str], dict]:
    import jsonschema

    errors: list[str] = []
    semantic = load_yaml(root / carrier.SEMANTIC_REL)
    implementation = load_yaml(root / carrier.IMPLEMENTATION_REL)
    schema = json.loads((root / SCHEMA_REL).read_text(encoding="utf-8"))
    try:
        jsonschema.Draft202012Validator(schema).validate(semantic)
        carrier.validate_implementation_registry(semantic, implementation)
    except (jsonschema.ValidationError, SystemExit) as exc:
        errors.append(str(exc))

    for section, path in (
        ("semantics", carrier.SEMANTIC_REL),
        ("node_semantics", carrier.SEMANTIC_REL),
        ("implementations", carrier.IMPLEMENTATION_REL),
        ("node_implementations", carrier.IMPLEMENTATION_REL),
    ):
        for key in duplicate_yaml_keys((root / path).read_text(encoding="utf-8"), section):
            errors.append(f"{path.name}: duplicate key '{key}' overwrites an earlier declaration")

    semantics = semantic.get("semantics") or {}
    node_semantics = semantic.get("node_semantics") or {}
    derivations = (semantic.get("derivation") or {}).get("rules") or []
    for rule in derivations:
        if (rule or {}).get("semantic") not in semantics:
            errors.append(f"semantic.yaml: derivation names undeclared semantic {(rule or {}).get('semantic')!r}")
    default = (semantic.get("derivation") or {}).get("default")
    if default not in semantics:
        errors.append(f"semantic.yaml: derivation default {default!r} is undeclared")
    for name, entry in sorted((semantic.get("native_view_widgets") or {}).items()):
        if (entry or {}).get("semantic") not in node_semantics:
            errors.append(f"semantic.yaml: native widget {name!r} names undeclared node semantic")

    for rel, semantic_type in contract_semantic_references(root):
        if semantic_type not in semantics and semantic_type not in node_semantics:
            errors.append(f"{rel}: references undeclared semantic {semantic_type!r}")

    backend_facts = backend_component_facts(root)
    for rel, line in backend_facts:
        errors.append(
            f"{rel}:{line}: backend production code publishes frontend component identity"
        )

    artifact_rows = (
        (carrier.CARRIER_REL, carrier.render_repository_carrier),
        (carrier.FRONTEND_REL, carrier.render_frontend_repository),
        (carrier.INDUSTRY_FRONTEND_REL, carrier.render_industry_repository),
        (carrier.DOMAIN_SEMANTICS_REL, carrier.render_domain_field_semantics),
    )
    for rel, render in artifact_rows:
        try:
            renderer = render(root)
        except SystemExit as exc:
            errors.append(str(exc))
            continue
        path = root / rel
        if not path.is_file():
            errors.append(f"generated carrier missing: {rel}")
        elif path.read_text(encoding="utf-8") != renderer:
            errors.append(f"generated carrier out of sync: {rel}")

    enum_path = root / ENUM_REGISTRY_REL
    widgets = set()
    if enum_path.is_file():
        widgets = set(json.loads(enum_path.read_text(encoding="utf-8")).get("widgetType") or [])
    declared_widgets = set(semantic.get("native_widgets") or {})
    for widget in sorted(widgets - declared_widgets):
        errors.append(f"semantic.yaml: schema widget {widget!r} has no semantic classification")

    return errors, {
        "semantics": len(semantics),
        "node_semantics": len(node_semantics),
        "field_implementations": len(implementation.get("implementations") or {}),
        "node_implementations": len(implementation.get("node_implementations") or {}),
        "backend_component_identity_facts": len(backend_facts),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args()
    errors, summary = run(Path(args.root).resolve())
    if errors:
        print("[semantic-registry-lint] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[semantic-registry-lint] PASS " + json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
