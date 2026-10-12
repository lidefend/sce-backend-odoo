#!/usr/bin/env python3
"""Project the contract semantic/component registry into runtime carriers.

The declaration authority is ``contracts/registry/{semantic,component}.yaml``.
The Odoo runtime image mounts only ``addons/`` (see ``docker-compose.yml``:
``./addons:/mnt/source-addons``), so ``contracts/`` is *not* readable at
runtime.  This generator projects the declaration into a carrier that lives
inside the addon, which is the same "declared in contracts/, generated for the
runtime" shape the repository already uses for
``contracts/generated/contract-registry.json`` and the frontend enum registry.

Only tables the resolver actually consumes are emitted.  Projecting a table
nobody reads would be a declared-but-unconsumed capability, which is exactly the
defect class this programme is removing.

Two carriers are projected from one declaration: the Python runtime carrier the
Odoo addon imports, and the TypeScript table the frontend builds its component
registrations from.  Projecting the frontend table is what removes the second
hand-written frontend vocabulary instead of merely checking it for drift.

``--check`` re-renders in memory and compares with the committed carriers, so a
declaration edit without regeneration is a lint failure instead of silent drift.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SEMANTIC_REL = Path("contracts/registry/semantic.yaml")
COMPONENT_REL = Path("contracts/registry/component.yaml")
REGISTRY_REL = Path("contracts/registry.yaml")
CARRIER_REL = Path("addons/smart_core/core/contract_runtime/semantic_registry_generated.py")
FRONTEND_REL = Path(
    "frontend/apps/web/src/app/presentation/semantic_registry.generated.ts"
)

WHEN_KEYS = ("field_types", "widgets", "widgets_exclude", "widget_suffix")

HEADER = '''# -*- coding: utf-8 -*-
"""GENERATED CONTRACT-RUNTIME CARRIER - do not edit by hand.

Declaration authority: {sources}
Regenerate with:

    python3 scripts/contract/generate_semantic_registry.py

Drift between this carrier and the declaration is a lint failure
(``make verify.semantic.registry.lint``).
"""

from __future__ import annotations

GENERATED_FROM = ({sources_tuple})
REGISTRY_DOCUMENT_VERSION = {version}
DERIVATION_DEFAULT = {default!r}
'''


def load(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def registry_versions(root: Path = ROOT) -> int:
    registry = load(root / REGISTRY_REL)
    entries = registry.get("contracts") if isinstance(registry.get("contracts"), list) else []
    # registry.yaml paths are relative to contracts/, not to the repository root.
    wanted = {
        SEMANTIC_REL.relative_to("contracts").as_posix(),
        COMPONENT_REL.relative_to("contracts").as_posix(),
    }
    versions = {
        entry.get("version")
        for entry in entries
        if isinstance(entry, dict) and entry.get("path") in wanted
    }
    if len(versions) != 1 or not isinstance(next(iter(versions), None), int):
        raise SystemExit(
            "[generate-semantic-registry] FAIL: both registry documents must share one "
            f"integer version in contracts/registry.yaml, found {sorted(map(str, versions))}"
        )
    return versions.pop()


def render_rule(rule: dict) -> str:
    parts = [f'"semantic": {rule["semantic"]!r}']
    when = rule.get("when") if isinstance(rule.get("when"), dict) else {}
    for key in WHEN_KEYS:
        if key not in when:
            continue
        value = when[key]
        if isinstance(value, (list, tuple)):
            parts.append(f'"{key}": (' + ", ".join(repr(item) for item in value) + ",)")
        else:
            parts.append(f'"{key}": {value!r}')
    if rule.get("reason"):
        parts.append(f'"reason": {rule["reason"]!r}')
    return "    {" + ", ".join(parts) + "}"


def render(semantic: dict, component: dict, *, version: int) -> str:
    derivation = semantic.get("derivation") or {}
    rules = derivation.get("rules") or []
    semantics = semantic.get("semantics") or {}
    components = component.get("components") or {}

    default = derivation.get("default")
    if not default or default not in semantics:
        raise SystemExit(f"[generate-semantic-registry] FAIL: unknown derivation default {default!r}")

    lines: list[str] = []
    for rule in rules:
        if not isinstance(rule, dict) or not rule.get("semantic"):
            raise SystemExit("[generate-semantic-registry] FAIL: malformed derivation rule")
        if rule["semantic"] not in semantics:
            raise SystemExit(
                f"[generate-semantic-registry] FAIL: rule names undeclared semantics "
                f"{rule['semantic']!r}"
            )
        lines.append(render_rule(rule) + ",")

    mapping: list[str] = []
    for key in sorted(semantics):
        entry = semantics[key] or {}
        component_key = entry.get("component")
        if not component_key:
            raise SystemExit(f"[generate-semantic-registry] FAIL: semantic {key!r} has no component")
        if component_key not in components:
            raise SystemExit(
                f"[generate-semantic-registry] FAIL: semantic {key!r} points at unregistered "
                f"component {component_key!r}"
            )
        mapping.append(f"    {key!r}: {component_key!r},")

    sources = (SEMANTIC_REL.as_posix(), COMPONENT_REL.as_posix())
    body = HEADER.format(
        sources=" -> ".join(sources),
        sources_tuple=", ".join(repr(item) for item in sources),
        version=version,
        default=default,
    )
    return (
        body
        + "\n# Ordered: the first rule whose conditions all hold decides.  Derived from the\n"
        "# declaration above; there is no second mapping in the assembler.\n"
        "DERIVATION_RULES = (\n"
        + "\n".join(lines)
        + "\n)\n"
        + "\n# semantic -> the component key the frontend renders.\n"
        "SEMANTIC_COMPONENTS = {\n"
        + "\n".join(mapping)
        + "\n}\n"
    )


def render_repository_carrier(root: Path = ROOT) -> str:
    """Render the carrier a given worktree's declaration should produce."""
    return render(
        load(root / SEMANTIC_REL),
        load(root / COMPONENT_REL),
        version=registry_versions(root),
    )


FRONTEND_HEADER = """// GENERATED CONTRACT-RUNTIME CARRIER - do not edit by hand.
//
// Declaration authority: __SOURCES__
// Regenerate with: python3 scripts/contract/generate_semantic_registry.py
//
// Drift between this carrier and the declaration is a lint failure
// (`make verify.semantic.registry.lint`).  This is the *only* frontend
// component vocabulary: `professionalComponentRegistry.ts` builds its
// registrations from these rows and must not carry a second hand-written list.

export type SemanticRegistryReadiness = 'ready' | 'readable_fallback' | 'fail_closed';

export type SemanticRegistryRow = {
  readonly componentKey: string;
  readonly semanticType: string;
  readonly supportedFieldTypes: readonly string[];
  readonly readiness: SemanticRegistryReadiness;
  readonly renderer: string;
};

export const SEMANTIC_REGISTRY_VERSION = __VERSION__;

export const SEMANTIC_REGISTRY_ROWS: readonly SemanticRegistryRow[] = [
"""


def render_frontend_registry(component: dict, *, version: int) -> str:
    """Project the component vocabulary into the frontend's generated table.

    Only the *data* is projected.  Presentation-mode profiles, the
    type-directed ``rendererByFieldType`` derivation and the readiness fallback
    are behaviour and stay in ``professionalComponentRegistry.ts``.
    """
    components = component.get("components") or {}
    defaults = component.get("defaults") if isinstance(component.get("defaults"), dict) else {}
    default_readiness = str(defaults.get("readiness") or "ready")
    rows: list[str] = []
    for key, entry in components.items():
        entry = entry if isinstance(entry, dict) else {}
        semantic = entry.get("semantic")
        renderer = entry.get("renderer")
        if not semantic or not renderer:
            raise SystemExit(
                f"[generate-semantic-registry] FAIL: component {key!r} lacks semantic/renderer"
            )
        field_types = entry.get("field_types") or []
        if not isinstance(field_types, (list, tuple)) or not field_types:
            raise SystemExit(
                f"[generate-semantic-registry] FAIL: component {key!r} declares no field_types"
            )
        readiness = str(entry.get("readiness") or default_readiness)
        types = ", ".join(repr(str(item)) for item in field_types)
        rows.append(
            "  {"
            f"componentKey: {key!r}, semanticType: {semantic!r}, "
            f"supportedFieldTypes: [{types}], readiness: {readiness!r}, renderer: {renderer!r}"
            "},"
        )
    sources = (SEMANTIC_REL.as_posix(), COMPONENT_REL.as_posix())
    return (
        FRONTEND_HEADER.replace("__SOURCES__", " -> ".join(sources)).replace(
            "__VERSION__", str(version)
        )
        + "\n".join(rows)
        + "\n];\n"
    )


def render_frontend_repository(root: Path = ROOT) -> str:
    """Render the frontend carrier a given worktree's declaration should produce."""
    return render_frontend_registry(
        load(root / COMPONENT_REL),
        version=registry_versions(root),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the carrier is in sync")
    args = parser.parse_args()

    artifacts = (
        (CARRIER_REL, render_repository_carrier()),
        (FRONTEND_REL, render_frontend_repository()),
    )
    if args.check:
        for rel, rendered in artifacts:
            path = ROOT / rel
            if not path.is_file():
                print(f"[generate-semantic-registry] FAIL: missing carrier {rel}")
                return 2
            if path.read_text(encoding="utf-8") != rendered:
                print(
                    f"[generate-semantic-registry] FAIL: {rel} is out of sync with the "
                    "declaration; run python3 scripts/contract/generate_semantic_registry.py"
                )
                return 2
            print(f"[generate-semantic-registry] PASS {rel} matches the declaration")
        return 0

    for rel, rendered in artifacts:
        path = ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
        print(f"[generate-semantic-registry] wrote {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
