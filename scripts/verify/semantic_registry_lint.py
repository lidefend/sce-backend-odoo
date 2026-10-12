#!/usr/bin/env python3
"""Validate the contract-runtime semantic/component registry pair.

Authority split this guards (FE-CONTRACT-RUNTIME-01):

* ``contracts/registry/semantic.yaml``  declares "what a field means";
* ``contracts/registry/component.yaml`` declares "which component renders it";
* ``contracts/registry/registry.schema.json`` is the machine-readable shape.

The defect being closed is a vocabulary held half in the backend mapping
function and half in the frontend registry, with no declaration and no static
check. This entry therefore asserts, in one place:

1. both documents match the declared schema;
2. no key is silently dropped by a duplicate YAML key;
3. every semantic points at a registered component and vice versa;
4. every declared renderer is registered, and the sentinel is one of them;
5. every derivation rule and the derivation default name a declared semantic;
6. every ``semantic:`` reference used by another contract document is legal;
7. the generated frontend table declares exactly the same component keys, and
   the frontend registry module holds no second hand-written vocabulary;
8. both committed carriers equal the projection of the declaration;
9. every widget spelling the contract schema permits is claimed by a rule.

Checks 7 and 8 are what make a second private vocabulary impossible: a
component key may not exist on one side only, and the runtime cannot keep
rendering the previous vocabulary after the declaration changed, because every
carrier is re-projected here and compared byte for byte.
Check 9 is the coverage census: ``enum_registry.json`` is the closed widget
universe the contract schema permits, so a spelling no rule claims is the
"unrecognised widget silently renders as text" defect.  It is reported as a
declaration gap instead of being left to a fallback.
"""

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

# Repo-relative locations. Every helper takes ``root`` so the checks can be
# exercised against a synthetic tree in focused tests.
CONTRACTS_REL = Path("contracts")
REGISTRY_REL = CONTRACTS_REL / "registry"
SEMANTIC_REL = REGISTRY_REL / "semantic.yaml"
COMPONENT_REL = REGISTRY_REL / "component.yaml"
SCHEMA_REL = REGISTRY_REL / "registry.schema.json"
FRONTEND_REGISTRY_REL = Path(
    "frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts"
)

ENUM_REGISTRY_REL = Path("docs/architecture/unified_page_contract_v2/enum_registry.json")

SEMANTIC_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
GENERATED_ROW_KEY_RE = re.compile(r"componentKey:\s*'([^']+)'")
COMPONENT_KEY_RE = re.compile(r"^sc\.[a-z0-9_]+(\.[a-z0-9_]+)+$")
FRONTEND_REGISTRATION_RE = re.compile(r"registration\(\s*'([^']+)'")
WHEN_KEYS = {"field_types", "widgets", "widgets_exclude", "widget_suffix"}


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def duplicate_yaml_keys(text: str, section: str) -> list[str]:
    """Keys repeated under a top-level mapping section.

    YAML keeps the last duplicate silently, so a repeated semantic or component
    key would otherwise be an invisible overwrite instead of a lint failure.
    Both block (``key:``) and inline (``key: {...}`` / ``key: value``) entries
    are matched, which is the shape this registry actually uses.
    """
    duplicates: list[str] = []
    in_section = False
    seen: set[str] = set()
    entry_re = re.compile(r"^([A-Za-z0-9_.\-]+)\s*:")
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
        match = entry_re.match(stripped)
        if not match:
            continue
        key = match.group(1)
        if key in seen:
            duplicates.append(f"{section}.{key}")
        else:
            seen.add(key)
    return duplicates


def contract_semantic_references(root: Path) -> list[tuple[str, str]]:
    references: list[tuple[str, str]] = []
    contracts = root / CONTRACTS_REL
    for path in sorted(contracts.rglob("*.yaml")):
        if path.parent == root / REGISTRY_REL:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.lstrip().startswith("#"):
                continue
            match = re.match(r"\s*semantic:\s*([A-Za-z0-9_]+)\s*$", line)
            if match:
                references.append((path.relative_to(root).as_posix(), match.group(1)))
    return references


def generated_registry_keys(root: Path) -> list[str]:
    """Component keys declared by the generated frontend table."""
    path = root / carrier.FRONTEND_REL
    if not path.is_file():
        return []
    return GENERATED_ROW_KEY_RE.findall(path.read_text(encoding="utf-8"))


def frontend_registry_code(root: Path) -> str:
    path = root / FRONTEND_REGISTRY_REL
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def declared_widget_spellings(root: Path) -> list[str]:
    """The widget vocabulary the runtime contract schema permits.

    ``enum_registry.json`` is the closed enum domain of the contract schema, not
    a semantic or component table: it answers "which widget spellings can a
    contract express".  Reading it here turns "an unrecognised widget falls back
    to the default" into a check over the declared universe instead of a
    documented hope.
    """
    path = root / ENUM_REGISTRY_REL
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    values = data.get("widgetType") if isinstance(data, dict) else None
    if not isinstance(values, list):
        return []
    return [str(value) for value in values]


def validate_schema(schema_path: Path, documents: dict[str, dict], errors: list[str]) -> None:
    try:
        import jsonschema
    except ImportError:  # pragma: no cover - the repository pins jsonschema
        errors.append("jsonschema is unavailable; the registry shape cannot be enforced")
        return
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    for name, document in documents.items():
        for failure in sorted(validator.iter_errors(document), key=lambda e: list(e.path)):
            location = "/".join(str(part) for part in failure.path) or "<root>"
            errors.append(f"{name}:{location}: {failure.message}")


def run(root: Path = ROOT) -> tuple[list[str], dict]:
    errors: list[str] = []
    semantic_path = root / SEMANTIC_REL
    component_path = root / COMPONENT_REL
    schema_path = root / SCHEMA_REL

    semantic_doc = load_yaml(semantic_path)
    component_doc = load_yaml(component_path)
    validate_schema(schema_path, {"semantic.yaml": semantic_doc, "component.yaml": component_doc}, errors)

    for path, section in ((semantic_path, "semantics"), (component_path, "components")):
        for key in duplicate_yaml_keys(path.read_text(encoding="utf-8"), section):
            errors.append(f"{path.name}: duplicate key '{key}' overwrites an earlier declaration")

    semantics = semantic_doc.get("semantics") if isinstance(semantic_doc.get("semantics"), dict) else {}
    components = component_doc.get("components") if isinstance(component_doc.get("components"), dict) else {}
    renderers = component_doc.get("renderers") if isinstance(component_doc.get("renderers"), list) else []
    derivation = semantic_doc.get("derivation") if isinstance(semantic_doc.get("derivation"), dict) else {}
    rules = derivation.get("rules") if isinstance(derivation.get("rules"), list) else []

    for key in semantics:
        if not SEMANTIC_KEY_RE.match(str(key)):
            errors.append(f"semantic.yaml: semantic key '{key}' is not lower_snake_case")
    for key in components:
        if not COMPONENT_KEY_RE.match(str(key)):
            errors.append(f"component.yaml: component key '{key}' is not a sc.<domain>.<name> key")

    for key, entry in sorted(semantics.items()):
        component = str((entry or {}).get("component") or "")
        if not component:
            errors.append(f"semantic.yaml: semantic '{key}' declares no component")
        elif component not in components:
            errors.append(f"semantic.yaml: semantic '{key}' points at unregistered component '{component}'")

    renderer_set = {str(name) for name in renderers}
    sentinel = str(component_doc.get("type_directed_renderer") or "")
    if not sentinel:
        errors.append("component.yaml: type_directed_renderer is missing")
    elif sentinel not in renderer_set:
        errors.append(f"component.yaml: type_directed_renderer '{sentinel}' is not a registered renderer")

    for key, entry in sorted(components.items()):
        renderer = str((entry or {}).get("renderer") or "")
        if renderer not in renderer_set:
            errors.append(f"component.yaml: component '{key}' declares unregistered renderer '{renderer}'")
        primary = str((entry or {}).get("semantic") or "")
        if primary not in semantics:
            errors.append(f"component.yaml: component '{key}' declares undeclared semantic '{primary}'")

    declared_rule_semantics: set[str] = set()
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            errors.append(f"semantic.yaml: derivation rule #{index} is not a mapping")
            continue
        semantic = str(rule.get("semantic") or "")
        declared_rule_semantics.add(semantic)
        if semantic not in semantics:
            errors.append(f"semantic.yaml: derivation rule #{index} names undeclared semantic '{semantic}'")
        when = rule.get("when")
        if not isinstance(when, dict) or not when:
            errors.append(f"semantic.yaml: derivation rule #{index} has an empty 'when'")
            continue
        unknown = sorted(set(when) - WHEN_KEYS)
        if unknown:
            errors.append(f"semantic.yaml: derivation rule #{index} uses unknown condition(s) {unknown}")
        for field in ("field_types", "widgets", "widgets_exclude"):
            if field in when and (not isinstance(when[field], list) or not when[field]):
                errors.append(f"semantic.yaml: derivation rule #{index} '{field}' must be a non-empty list")
        if "widget_suffix" in when and not str(when["widget_suffix"]).strip():
            errors.append(f"semantic.yaml: derivation rule #{index} 'widget_suffix' must be a non-empty string")

    derivation_default = str(derivation.get("default") or "")
    if not derivation_default:
        errors.append("semantic.yaml: derivation.default is missing")
    elif derivation_default not in semantics:
        errors.append(f"semantic.yaml: derivation.default names undeclared semantic '{derivation_default}'")

    for source, semantic in sorted(set(contract_semantic_references(root))):
        if semantic not in semantics:
            errors.append(f"{source}: references undeclared semantic '{semantic}'")

    generated_keys = sorted(set(generated_registry_keys(root)))
    backend_keys = sorted(components)
    if not generated_keys:
        errors.append(
            f"{carrier.FRONTEND_REL.as_posix()}: no component row found; the cross-side "
            "vocabulary check cannot be satisfied"
        )
    else:
        for key in sorted(set(generated_keys) - set(backend_keys)):
            errors.append(
                f"{carrier.FRONTEND_REL.as_posix()}: component '{key}' is not declared in component.yaml"
            )
        for key in sorted(set(backend_keys) - set(generated_keys)):
            errors.append(f"component.yaml: component '{key}' has no frontend registration")

    # A hand-written registration list in the registry module would re-create the
    # second frontend vocabulary the generated table exists to remove.
    for key in sorted(set(FRONTEND_REGISTRATION_RE.findall(frontend_registry_code(root)))):
        errors.append(
            f"{FRONTEND_REGISTRY_REL.as_posix()}: holds a second component vocabulary "
            f"('{key}'); it must consume {carrier.FRONTEND_REL.as_posix()}"
        )

    # Coverage census: every widget spelling the contract schema permits must be
    # claimed by a derivation rule.  An unclaimed spelling is not a warning -- it
    # is the "unrecognised widget silently renders as text" defect, and the fix
    # belongs in the declaration, not in a fallback.
    claimed_widgets: set[str] = set()
    suffixes: list[str] = []
    for rule in rules:
        when = rule.get("when") if isinstance(rule.get("when"), dict) else {}
        claimed_widgets.update(str(value) for value in (when.get("widgets") or []))
        claimed_widgets.update(str(value) for value in (when.get("widgets_exclude") or []))
        if when.get("widget_suffix"):
            suffixes.append(str(when["widget_suffix"]))
    for spelling in sorted(set(declared_widget_spellings(root)) - claimed_widgets):
        if any(spelling.endswith(suffix) for suffix in suffixes):
            continue
        errors.append(
            f"semantic.yaml: widget spelling '{spelling}' is declared by the contract schema "
            "(enum_registry.json) but no derivation rule claims it; declare what it means "
            "instead of falling back to the default"
        )

    for rel, render_expected in (
        (carrier.CARRIER_REL, carrier.render_repository_carrier),
        (carrier.FRONTEND_REL, carrier.render_frontend_repository),
    ):
        carrier_path = root / rel
        if not carrier_path.is_file():
            errors.append(
                f"{rel.as_posix()}: generated carrier is missing; run "
                "python3 scripts/contract/generate_semantic_registry.py"
            )
            continue
        try:
            expected = render_expected(root)
        except SystemExit as exc:  # the generator refuses malformed declarations
            errors.append(f"{rel.as_posix()}: cannot be projected ({exc})")
        else:
            if carrier_path.read_text(encoding="utf-8") != expected:
                errors.append(
                    f"{rel.as_posix()}: out of sync with the declaration; run "
                    "python3 scripts/contract/generate_semantic_registry.py"
                )

    summary = {
        "semantics": len(semantics),
        "components": len(components),
        "renderers": len(renderer_set),
        "derivation_rules": len(rules),
        "derivation_default": derivation_default,
        "semantics_with_derivation_rule": len(declared_rule_semantics),
        "semantics_declared_only": sorted(set(semantics) - declared_rule_semantics),
        "frontend_component_keys": len(generated_keys),
        "runtime_carrier": carrier.CARRIER_REL.as_posix(),
    }
    return errors, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--json", default="")
    args = parser.parse_args()
    errors, summary = run(Path(args.root).resolve())
    if args.json:
        Path(args.json).write_text(json.dumps({"errors": errors, "summary": summary}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if errors:
        print("[semantic_registry_lint] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "[semantic_registry_lint] PASS "
        f"semantics={summary['semantics']} components={summary['components']} "
        f"renderers={summary['renderers']} derivation_rules={summary['derivation_rules']} "
        f"frontend_keys={summary['frontend_component_keys']}"
    )
    print(
        "[semantic_registry_lint] declared-only semantics (no derivation rule, "
        f"must be declared by their producer): {', '.join(summary['semantics_declared_only'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
