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
import json
import sys
from pathlib import Path

import yaml
import jsonschema

ROOT = Path(__file__).resolve().parents[2]
SEMANTIC_REL = Path("contracts/registry/semantic.yaml")
COMPONENT_REL = Path("contracts/registry/component.yaml")
REGISTRY_REL = Path("contracts/registry.yaml")
CARRIER_REL = Path("addons/smart_core/core/contract_runtime/semantic_registry_generated.py")
FRONTEND_REL = Path(
    "frontend/apps/web/src/app/presentation/semantic_registry.generated.ts"
)
DOMAIN_CONTRACTS_REL = Path("contracts/domain")
VIEW_STRUCTURE_REL = Path("contracts/generated/product_view_structure_contract.json")
DOMAIN_SEMANTICS_REL = Path(
    "addons/smart_core/core/contract_runtime/domain_field_semantics_generated.py"
)

# A field's meaning belongs to the entity, not to one surface.  The form view is
# where the editor widgets (statusbar, monetary, percentage, ...) declare that
# meaning, so it is read first and a surface that only re-lists the field cannot
# overwrite it.
SURFACE_ORDER = ("form", "kanban", "tree", "search", "graph", "pivot", "activity")

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


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicates before YAML can silently discard an identity."""

    def construct_mapping(self, node, deep=False):
        keys = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in keys:
                raise SystemExit(f"duplicate YAML key: {key!r}")
            keys.add(key)
        return super().construct_mapping(node, deep=deep)


def load(path: Path) -> dict:
    data = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    return data if isinstance(data, dict) else {}


def validate_component_registry(component: dict) -> None:
    schema = json.loads((ROOT / "contracts/registry/registry.schema.json").read_text())
    try:
        jsonschema.Draft202012Validator(schema).validate(component)
    except jsonschema.ValidationError as exc:
        raise SystemExit(f"invalid component registry: {exc.message}") from exc
    for key, entry in component["components"].items():
        if entry.get("kind", "field") == "field" and entry["renderer"] not in component["renderers"]:
            raise SystemExit(f"component {key!r} names unregistered renderer")


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
    validate_component_registry(component)
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
        if components[component_key].get("kind", "field") != "field":
            raise SystemExit(f"field semantic {key!r} cannot reference node component {component_key!r}")
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
        + "\n# Backend registration identity only; no client support is implied.\n"
        + f"FIELD_CONTRACT_VERSION = {component['defaults']['field_contract_version']!r}\n"
        + "COMPONENT_REGISTRATIONS = {\n"
        + "\n".join(
            f"    {key!r}: {dict(kind=entry.get('kind', 'field'), version=entry['version'] if entry.get('kind') == 'node' else component['defaults']['field_contract_version'])!r},"
            for key, entry in sorted(components.items())
        )
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
    validate_component_registry(component)
    components = component.get("components") or {}
    defaults = component.get("defaults") if isinstance(component.get("defaults"), dict) else {}
    default_readiness = str(defaults.get("readiness") or "ready")
    rows: list[str] = []
    for key, entry in components.items():
        if entry.get("kind", "field") == "node":
            continue
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
        + "\nexport const NODE_COMPONENT_REGISTRATIONS: Readonly<Record<string, {kind: 'node'; version: string}>> = Object.freeze({\n"
        + "\n".join(f"  {key!r}: {{kind: 'node', version: {entry['version']!r}}}," for key, entry in components.items() if entry.get('kind') == 'node')
        + "\n});\n"
    )


def render_frontend_repository(root: Path = ROOT) -> str:
    """Render the frontend carrier a given worktree's declaration should produce."""
    return render_frontend_registry(
        load(root / COMPONENT_REL),
        version=registry_versions(root),
    )


DOMAIN_HEADER = '''# -*- coding: utf-8 -*-
"""GENERATED CONTRACT-RUNTIME CARRIER - do not edit by hand.

Derived from: contracts/generated/product_view_structure_contract.json, the
governed parse of the Odoo model metadata and the resolved view arch, restricted
to the entities ``contracts/domain/*.yaml`` declares.
Regenerate with:

    python3 scripts/contract/generate_semantic_registry.py

The runtime image does not ship ``contracts/``, so each governed entity's field
semantics are projected here as ``model -> field -> semantic``.  Every semantic
is *read from the field facts* by the same registry rules the page assembler
uses; no meaning is authored by hand, which keeps the backend input to the model,
the view and the permission data.

Drift between this carrier and the field facts is a lint failure
(``make verify.semantic.registry.lint``).
"""

from __future__ import annotations

GENERATED_FROM = ('contracts/generated/product_view_structure_contract.json',)

# model -> field -> semantic
DOMAIN_FIELD_SEMANTICS = {
'''


def runtime_semantic_engine():
    """The runtime's own field-fact -> semantic resolution, imported not copied.

    The carrier and the page assembler have to read a field identically, so this
    imports the shipped runtime functions instead of re-implementing widget
    canonicalisation and the derivation-rule walk in a build script.
    """
    addon_root = str((root_of_addons()).resolve())
    if addon_root not in sys.path:
        sys.path.insert(0, addon_root)
    from core.contract_runtime import semantic_resolver  # noqa: PLC0415
    from core.unified_page_contract_v2_assembler import _canonical_widget_type  # noqa: PLC0415

    return semantic_resolver, _canonical_widget_type


def root_of_addons() -> Path:
    """The addon root that holds ``core.contract_runtime`` (import root for the runtime)."""
    return Path(__file__).resolve().parents[2] / "addons" / "smart_core"


def governed_models(root: Path = ROOT) -> set[str]:
    """The Odoo models ``contracts/domain/*.yaml`` binds, keyed by model name.

    ``source_of_truth.model`` is the binding.  A document that only carries
    ``entity`` is bound when that name is already an Odoo model name (dotted);
    a bare class name is not a model and is skipped rather than guessed, so an
    unbound contract stays visibly unprojected instead of silently mis-keyed.
    """
    models: set[str] = set()
    for path in sorted((root / DOMAIN_CONTRACTS_REL).glob("*.yaml")):
        document = load(path)
        source = document.get("source_of_truth")
        model = str((source or {}).get("model") or "").strip().lower() if isinstance(source, dict) else ""
        if not model:
            entity = str(document.get("entity") or "").strip().lower()
            model = entity if "." in entity else ""
        if model:
            models.add(model)
    return models


def _surface_field_facts(surface: dict) -> dict[str, dict]:
    """``field name -> attrs`` for one parsed surface, first occurrence wins."""
    facts: dict[str, dict] = {}

    def walk(node: object) -> None:
        if isinstance(node, dict):
            if node.get("tag") == "field":
                attrs = node.get("attrs")
                name = str((attrs or {}).get("name") or "").strip()
                if name and isinstance(attrs, dict):
                    facts.setdefault(name, attrs)
            for child in node.get("children") or []:
                walk(child)

    walk(surface.get("semantic_structure") or {})
    return facts


def domain_field_semantics(root: Path = ROOT) -> dict[str, dict[str, str]]:
    """The ``model -> field -> semantic`` map, read from the parsed field facts.

    The input is the model metadata and the resolved view arch: for every field
    the governed surfaces expose, the field's Odoo type, widget and comodel are
    fed through the runtime's own resolution, so the carrier can never disagree
    with what the page renders.
    """
    baseline_path = root / VIEW_STRUCTURE_REL
    if not baseline_path.is_file():
        raise SystemExit(
            f"[generate-semantic-registry] FAIL: missing {VIEW_STRUCTURE_REL.as_posix()}; "
            "run the contract view-structure export before regenerating the carriers"
        )
    resolver, canonical_widget_type = runtime_semantic_engine()
    governed = governed_models(root)
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    order = {name: index for index, name in enumerate(SURFACE_ORDER)}
    by_model: dict[str, dict[str, str]] = {}
    for entry in baseline.get("entries") or []:
        model = str(entry.get("res_model") or "").strip().lower()
        if model not in governed:
            continue
        surfaces = [s for s in entry.get("surfaces") or [] if isinstance(s, dict)]
        surfaces.sort(key=lambda s: order.get(str(s.get("view_type") or ""), len(SURFACE_ORDER)))
        facts: dict[str, dict] = {}
        for surface in surfaces:
            for name, attrs in _surface_field_facts(surface).items():
                known = facts.get(name)
                if known is None or ("widget" not in known and "widget" in attrs):
                    facts[name] = attrs
        for name, attrs in facts.items():
            field = {"name": name, "ttype": attrs.get("type"), "type": attrs.get("type")}
            if attrs.get("relation"):
                field["relation"] = attrs["relation"]
            native_widget = str(attrs.get("widget") or "")
            widget = resolver.semantic_widget_type(
                native_widget, canonical_widget_type(native_widget, field)
            )
            by_model.setdefault(model, {})[name] = resolver.resolve(field, widget)["semantic"]
    return by_model


def render_domain_field_semantics(root: Path = ROOT) -> str:
    """Project the parsed field facts into the runtime carrier.

    Every projected semantic must be one ``contracts/registry/semantic.yaml``
    declares; a name the resolver does not know would resolve to nothing at
    runtime, so the projector refuses instead of emitting it.
    """
    semantics = load(root / SEMANTIC_REL).get("semantics") or {}
    projected = domain_field_semantics(root)
    for model, fields in projected.items():
        for name, semantic in fields.items():
            if semantic not in semantics:
                raise SystemExit(
                    f"[generate-semantic-registry] FAIL: model {model!r} field {name!r} resolves to "
                    f"undeclared semantic {semantic!r}"
                )
    lines: list[str] = []
    for model, fields in sorted(projected.items()):
        lines.append(f"    {model!r}: {{")
        for name in sorted(fields):
            lines.append(f"        {name!r}: {fields[name]!r},")
        lines.append("    },")
    body = DOMAIN_HEADER + "\n".join(lines) + ("\n}\n" if lines else "}\n")
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the carrier is in sync")
    args = parser.parse_args()

    # Bootstrap the resolver from the freshly rendered source in memory. The
    # checked-in carrier may predate a generator/runtime protocol change.
    import types
    module_name = "core.contract_runtime.semantic_registry_generated"
    generated = types.ModuleType(module_name)
    exec(compile(render_repository_carrier(), str(CARRIER_REL), "exec"), generated.__dict__)
    sys.modules[module_name] = generated
    artifacts = (
        (CARRIER_REL, render_repository_carrier()),
        (FRONTEND_REL, render_frontend_repository()),
        (DOMAIN_SEMANTICS_REL, render_domain_field_semantics()),
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
